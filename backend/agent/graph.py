import logging
import os
import time
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from agent.contexto import montar_contexto, nome_fonte, selecionar
from agent.llm import instanciar_gemini
from agent.prompts import RECUSA_PADRAO, prompt_rag_academico
from agent.reescrita import (
    INSTRUCAO_REESCRITA,
    TAG_CHAMADA_INTERNA,
    deve_reescrever,
    extrair_texto,
    limpar_reescrita,
    montar_historico_textual,
)
from agent.roteamento import escolher_destino

logger = logging.getLogger(__name__)

DB_URI = os.environ["DATABASE_URL"]


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def decisor(state: AgentState) -> dict:
    return {}  # nó de passagem; a decisão acontece nas arestas condicionais


def roteador(state: AgentState) -> Literal["rag_academico", "conversa_geral"]:
    pergunta = str(state["messages"][-1].content).strip()
    # Regra em agent/roteamento.py (testada de forma isolada)
    destino = escolher_destino(pergunta)
    logger.info("[ROTEADOR] '%s' -> %s", pergunta[:60], destino)
    return destino


def conectar_qdrant(
    embeddings: HuggingFaceEmbeddings, tentativas: int = 5, espera: float = 2.0
) -> QdrantVectorStore:
    """O docker-compose não tem healthcheck pro Qdrant (diferente do Postgres): o contêiner
    pode estar de pé sem a API dele estar pronta ainda. Tenta algumas vezes antes de desistir,
    em vez de derrubar a subida do backend na primeira falha."""
    url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    for tentativa in range(1, tentativas + 1):
        try:
            return QdrantVectorStore.from_existing_collection(
                embedding=embeddings, collection_name="cacic_docs", url=url
            )
        except Exception:
            if tentativa == tentativas:
                raise
            logger.warning(
                "Qdrant indisponível (tentativa %d/%d); tentando de novo em %.0fs",
                tentativa,
                tentativas,
                espera,
            )
            time.sleep(espera)
    raise RuntimeError("inalcançável")  # só pra satisfazer o checador de tipos


def construir_grafo() -> StateGraph:
    """Carrega o modelo, conecta ao Qdrant e monta o grafo. Chamada uma vez só, no lifespan
    de main.py — não na importação do módulo (o modelo/bge-m3/Qdrant eram carregados aqui
    antes; mover pro lifespan dá controle sobre quando isso acontece e, com conectar_qdrant,
    tolerância a uma inicialização lenta do contêiner do Qdrant)."""
    llm = instanciar_gemini()
    # Cliente dedicado para a reescrita (mesmos modelos principal/reserva, saída bem menor):
    # evita compartilhar o cliente usado na resposta ao aluno.
    llm_reescrita = instanciar_gemini(max_output_tokens=60)
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
    qdrant = conectar_qdrant(embeddings)

    # Busca mais trechos do que o necessário, remove duplicados (o mesmo regulamento pode
    # estar em mais de um PDF) e envia só os melhores ao modelo.
    k_busca = int(os.getenv("RAG_K_BUSCA", 8))
    k_contexto = int(os.getenv("RAG_K_CONTEXTO", 5))
    retriever = qdrant.as_retriever(search_kwargs={"k": k_busca})

    # Mantém só as últimas 10 mensagens, sempre começando por uma do usuário.
    # Aplicado ao montar o prompt (não altera o histórico salvo no checkpointer).
    token_trimmer = trim_messages(
        max_tokens=10,
        strategy="last",
        token_counter=len,
        start_on="human",
        include_system=True,
    )

    sistema_conversa_geral = SystemMessage(
        content=(
            "Você é o Assistente Virtual do CACIC da UESC. Nesta conversa, apenas cumprimente, "
            "agradeça ou explique brevemente o que você faz. Se o aluno perguntar algo sobre "
            "regras, prazos, ACC, TCC, estágio, matriz curricular ou processos acadêmicos, "
            "peça que ele reformule a pergunta de forma específica. Nunca responda questões "
            "acadêmicas com conhecimento próprio."
        )
    )

    async def reescrever_para_busca(mensagens: list, pergunta: str, config: RunnableConfig) -> str:
        """Pergunta de acompanhamento (ex.: "e para a matriz 2012?") sozinha não diz muita coisa
        para a busca; reescreve numa pergunta independente usando o histórico. Qualquer falha
        ou saída vazia cai para a pergunta original, sem quebrar o stream."""
        if not deve_reescrever(mensagens):
            return pergunta
        try:
            historico = montar_historico_textual(mensagens)
            # A tag deixa api/routes.py ignorar esses tokens: não são a resposta ao aluno, e um
            # "on_chat_model_start" aqui não pode ser lido como troca para o modelo de reserva.
            config_interno = {
                **config,
                "tags": [*(config.get("tags") or []), TAG_CHAMADA_INTERNA],
            }
            resposta = await llm_reescrita.ainvoke(
                [
                    SystemMessage(content=INSTRUCAO_REESCRITA),
                    HumanMessage(content=f"Histórico:\n{historico}\n\nÚltima pergunta: {pergunta}"),
                ],
                config=config_interno,
            )
            pergunta_busca = limpar_reescrita(resposta.content, pergunta)
        except Exception:
            logger.exception("Falha ao reescrever a pergunta de busca; usando a original")
            pergunta_busca = pergunta
        logger.info("[REESCRITA] %r -> %r", pergunta[:60], pergunta_busca[:60])
        return pergunta_busca

    async def rag_academico(state: AgentState, config: RunnableConfig) -> dict:
        mensagens = token_trimmer.invoke(state["messages"])
        pergunta = str(state["messages"][-1].content)
        pergunta_busca = await reescrever_para_busca(mensagens, pergunta, config)

        recuperados = await retriever.ainvoke(pergunta_busca, config=config)
        documentos = selecionar(recuperados, k_contexto)
        logger.info("[RAG] %d recuperados, %d no contexto", len(recuperados), len(documentos))
        for d in documentos:
            logger.info("[RAG]   > [%s] %r", nome_fonte(d.metadata), d.page_content[:100])

        contexto = montar_contexto(documentos)

        cadeia_rag = prompt_rag_academico | llm
        resposta = await cadeia_rag.ainvoke(
            {"messages": mensagens, "contexto": contexto}, config=config
        )
        # Fontes realmente usadas nesta resposta, pro frontend exibir (ver api/routes.py). Não
        # faz sentido mostrar fontes numa recusa — os trechos recuperados não respondem a pergunta.
        if extrair_texto(resposta.content).strip() != RECUSA_PADRAO:
            resposta.additional_kwargs["fontes"] = sorted(
                {nome_fonte(d.metadata) for d in documentos}
            )
        return {"messages": [resposta]}

    async def conversa_geral(state: AgentState, config: RunnableConfig) -> dict:
        mensagens = token_trimmer.invoke(state["messages"])
        resposta = await llm.ainvoke([sistema_conversa_geral, *mensagens], config=config)
        return {"messages": [resposta]}

    workflow = StateGraph(AgentState)
    workflow.add_node("decisor", decisor)
    workflow.add_node("rag_academico", rag_academico)
    workflow.add_node("conversa_geral", conversa_geral)
    workflow.add_edge(START, "decisor")
    workflow.add_conditional_edges("decisor", roteador)
    workflow.add_edge("rag_academico", END)
    workflow.add_edge("conversa_geral", END)
    return workflow
