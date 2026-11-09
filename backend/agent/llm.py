import os

from langchain_google_genai import ChatGoogleGenerativeAI

MODELO_PADRAO = "gemini-3.5-flash-lite"
MAX_TOKENS_PADRAO = 4096


def instanciar_gemini() -> ChatGoogleGenerativeAI:
    """
    Cria a instância do Gemini calibrada para RAG institucional (temperatura 0).

    Variáveis de ambiente opcionais:
      GEMINI_MODEL              modelo a usar (padrão: gemini-3.5-flash-lite)
      GEMINI_MAX_OUTPUT_TOKENS  limite de tokens da resposta (padrão: 4096)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não definida no ambiente.")

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", MODELO_PADRAO),
        temperature=0.0,  # respostas determinísticas, sem variação criativa
        # O limite pode incluir tokens de raciocínio do modelo; um valor baixo demais
        # corta a resposta no meio (era 1024).
        max_output_tokens=int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", MAX_TOKENS_PADRAO)),
        timeout=60,
        api_key=api_key,
        max_retries=3,
    )
