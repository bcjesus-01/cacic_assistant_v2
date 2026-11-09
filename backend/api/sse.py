"""Formatação dos eventos SSE enviados ao frontend (sem dependências externas)."""

import json

DONE = "data: [DONE]\n\n"
MENSAGEM_ERRO = "Não consegui gerar a resposta agora. Tente novamente em instantes."


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


def sse(payload: str, event: str | None = None) -> str:
    # json.dumps escapa quebras de linha, aspas e unicode com segurança
    prefixo = f"event: {event}\n" if event else ""
    return f"{prefixo}data: {json.dumps(payload, ensure_ascii=False)}\n\n"
