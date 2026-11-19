"""Formatação dos eventos SSE enviados ao frontend (sem dependências externas)."""

import json

DONE = "data: [DONE]\n\n"
MENSAGEM_ERRO = "Não consegui gerar a resposta agora. Tente novamente em instantes."
MENSAGEM_LIMITE = "Esta conversa ficou longa. Clique em \"Nova conversa\" para continuar."
MENSAGEM_LIMITE_IP = "Você atingiu o limite de perguntas de hoje. Volte amanhã para continuar."
MENSAGEM_TETO_GLOBAL = (
    "Muitos alunos estão usando o assistente agora e atingimos o limite diário gratuito. "
    "Volte amanhã."
)
# Avisa o cliente de que o texto parcial deve ser descartado (modelo de reserva assumiu).
RESET = 'event: reset\ndata: ""\n\n'


def extrair_texto(content) -> str:
    """Aceita string ou lista de blocos (formato do langchain-google-genai)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(bloco.get("text", ""))
        return "".join(partes)
    return ""


def sse(payload: str | list[str], event: str | None = None) -> str:
    # json.dumps escapa quebras de linha, aspas e unicode com segurança (e serializa listas
    # como array JSON, usado pelo evento "fontes").
    prefixo = f"event: {event}\n" if event else ""
    return f"{prefixo}data: {json.dumps(payload, ensure_ascii=False)}\n\n"
