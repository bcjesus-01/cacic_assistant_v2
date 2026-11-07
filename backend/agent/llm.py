import os
from langchain_google_genai import ChatGoogleGenerativeAI

def instanciar_gemini() -> ChatGoogleGenerativeAI:
    """
    Fábrica que cria a instância do Gemini calibrada para RAG Institucional.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("ERRO CRÍTICO: GOOGLE_API_KEY não definida no ambiente.")
    
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite", 
        temperature=0.0,          # Precisão matemática (0 alucinação)
        max_output_tokens=1024,   # Limita respostas longas desnecessárias
        timeout=60,
        api_key=api_key,
        max_retries=3
    )
