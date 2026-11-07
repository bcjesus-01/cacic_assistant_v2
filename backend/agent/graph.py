import os
import re
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from agent.llm import instanciar_gemini
from agent.prompts import prompt_rag_academico


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm = instanciar_gemini()
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

qdrant = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="cacic_docs",
    url=QDRANT_URL,
)
retriever = qdrant.as_retriever(search_kwargs={"k": 3})

# Mantém só as últimas 10 mensagens, sempre começando por uma do usuário.
# Aplicado ao montar o prompt (não altera o histórico salvo no checkpointer).
token_trimmer = trim_messages(
    max_tokens=10,
    strategy="last",
    token_counter=len,
    start_on="human",
    include_system=True,
)

SAUDACOES = {
    "oi", "olá", "ola", "bom", "boa", "obrigado", "obrigada",
    "valeu", "tchau", "hey", "hello",
}

SISTEMA_CONVERSA_GERAL = SystemMessage(
    content=(
        "Você é o Assistente Virtual do CACIC da UESC. Nesta conversa, apenas cumprimente, "
        "agradeça ou explique brevemente o que você faz. Se o aluno perguntar algo sobre "
        "regras, prazos, ACC, TCC, estágio, matriz curricular ou processos acadêmicos, "
        "peça que ele reformule a pergunta de forma específica. Nunca responda questões "
        "acadêmicas com conhecimento próprio."
    )
)


def decisor(state: AgentState) -> dict:
    return {}  # nó de passagem; a decisão acontece nas arestas condicionais


def roteador(state: AgentState) -> Literal["rag_academico", "conversa_geral"]:
    pergunta = str(state["messages"][-1].content).strip().lower()
    palavras = re.findall(r"\w+", pergunta)

    # Só saudações/agradecimentos curtos vão para a conversa geral.
    # Todo o resto passa pelo RAG, que tem a "rota de fuga" no prompt.
    destino = (
        "conversa_geral"
        if palavras and len(palavras) <= 4 and palavras[0] in SAUDACOES
        else "rag_academico"
    )
    print(f"[ROTEADOR] '{pergunta[:60]}' -> {destino}", flush=True)
    return destino


async def rag_academico(state: AgentState, config: RunnableConfig) -> dict:
    mensagens = token_trimmer.invoke(state["messages"])
    pergunta = str(state["messages"][-1].content)

    documentos = await retriever.ainvoke(pergunta, config=config)
    print(f"[RAG] {len(documentos)} documentos recuperados", flush=True)
    for d in documentos:
        print("   >", repr(d.page_content[:120]), flush=True)

    contexto = "\n\n".join(d.page_content for d in documentos)

    cadeia_rag = prompt_rag_academico | llm
    resposta = await cadeia_rag.ainvoke(
        {"messages": mensagens, "contexto": contexto}, config=config
    )
    return {"messages": [resposta]}


async def conversa_geral(state: AgentState, config: RunnableConfig) -> dict:
    mensagens = token_trimmer.invoke(state["messages"])
    resposta = await llm.ainvoke([SISTEMA_CONVERSA_GERAL, *mensagens], config=config)
    return {"messages": [resposta]}


workflow = StateGraph(AgentState)
workflow.add_node("decisor", decisor)
workflow.add_node("rag_academico", rag_academico)
workflow.add_node("conversa_geral", conversa_geral)
workflow.add_edge(START, "decisor")
workflow.add_conditional_edges("decisor", roteador)
workflow.add_edge("rag_academico", END)
workflow.add_edge("conversa_geral", END)

DB_URI = os.environ["DATABASE_URL"]