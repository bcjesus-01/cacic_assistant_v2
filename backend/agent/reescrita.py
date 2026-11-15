"""Reescreve uma pergunta de acompanhamento numa pergunta independente, usando o
histórico da conversa, para a busca no Qdrant não depender só da última mensagem
(lógica pura, testável sem LangChain).
"""

LIMITE_SAIDA_RAZOAVEL = 500  # saída do modelo muito maior que isso é suspeita, não uma pergunta

# Marca a chamada de reescrita nos eventos do LangGraph (config["tags"]), para a rota de SSE
# (api/routes.py) não repassar os tokens dela ao cliente nem confundi-la com a troca para o
# modelo de reserva (as duas aparecem como um novo "on_chat_model_start" na mesma resposta).
TAG_CHAMADA_INTERNA = "chamada-interna"

INSTRUCAO_REESCRITA = (
    "Reescreva a ÚLTIMA pergunta do aluno como uma pergunta independente e completa, usando "
    "o histórico só para resolver pronomes e referências implícitas (ex.: 'e para a matriz "
    "2012?', 'e se eu reprovar?'). Se a pergunta já for independente, repita-a sem mudanças. "
    "Responda só com a pergunta reescrita, sem aspas nem explicações."
)

_ROTULO_TIPO = {"human": "Aluno", "ai": "Assistente"}


def deve_reescrever(mensagens: list) -> bool:
    """Há histórico antes da pergunta atual (não é a primeira mensagem do thread)."""
    return len(mensagens) > 1


def _texto(conteudo) -> str:
    """Extrai texto simples de `conteudo` (string ou blocos do langchain-google-genai).

    Pequena duplicata de api.sse.extrair_texto: este módulo é puro e não importa de `api/`
    para não inverter a direção de dependência atual (api depende de agent, não o contrário).
    """
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = []
        for bloco in conteudo:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(bloco.get("text", ""))
        return "".join(partes)
    return ""


def montar_historico_textual(mensagens: list) -> str:
    """Mensagens antes da última, como 'Aluno: ...' / 'Assistente: ...', uma por linha."""
    linhas = []
    for m in mensagens[:-1]:
        texto = _texto(m.content).strip()
        if texto:
            rotulo = _ROTULO_TIPO.get(m.type, m.type)
            linhas.append(f"{rotulo}: {texto}")
    return "\n".join(linhas)


def limpar_reescrita(conteudo, pergunta_original: str) -> str:
    """Limpa a saída do modelo; cai para a pergunta original se vier vazia ou suspeita."""
    texto = _texto(conteudo).strip().strip('"').strip("'").strip()
    if not texto or len(texto) > LIMITE_SAIDA_RAZOAVEL:
        return pergunta_original
    return texto
