import os

from langchain_google_genai import ChatGoogleGenerativeAI

MODELO_PADRAO = "gemini-3.5-flash-lite"
MAX_TOKENS_PADRAO = 4096


def _criar_gemini(
    modelo: str, api_key: str, max_retries: int, max_output_tokens: int
) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=modelo,
        temperature=0.0,  # respostas determinísticas, sem variação criativa
        max_output_tokens=max_output_tokens,
        timeout=60,
        api_key=api_key,
        max_retries=max_retries,
    )


def instanciar_gemini(max_output_tokens: int | None = None):
    """
    Cria o Gemini calibrado para RAG institucional (temperatura 0).

    Se GEMINI_FALLBACK_MODEL estiver definida, o modelo de reserva assume quando o
    principal falha (por exemplo, erro 503 por alta demanda). Nesse caso o principal
    tenta menos vezes por conta própria, para a troca acontecer logo.

    `max_output_tokens` sobrepõe `GEMINI_MAX_OUTPUT_TOKENS` para este cliente específico
    (ex.: um cliente dedicado e mais barato para reescrever a pergunta de busca, sem
    compartilhar o cliente principal usado na resposta ao aluno).

    Variáveis de ambiente opcionais:
      GEMINI_MODEL              modelo principal (padrão: gemini-3.5-flash-lite)
      GEMINI_FALLBACK_MODEL     modelo de reserva (padrão: nenhum)
      GEMINI_MAX_RETRIES        tentativas do modelo principal (padrão: 1 com reserva, 3 sem)
      GEMINI_MAX_OUTPUT_TOKENS  limite de tokens da resposta (padrão: 4096)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não definida no ambiente.")

    # O limite pode incluir tokens de raciocínio do modelo; um valor baixo demais
    # corta a resposta no meio (era 1024).
    tokens = max_output_tokens or int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", MAX_TOKENS_PADRAO))
    modelo = os.getenv("GEMINI_MODEL", MODELO_PADRAO)
    reserva = os.getenv("GEMINI_FALLBACK_MODEL", "").strip()
    usa_reserva = bool(reserva) and reserva != modelo

    max_retries = int(os.getenv("GEMINI_MAX_RETRIES", 1 if usa_reserva else 3))
    principal = _criar_gemini(modelo, api_key, max_retries, tokens)
    if not usa_reserva:
        return principal

    return principal.with_fallbacks([_criar_gemini(reserva, api_key, max_retries, tokens)])
