import os
from llama_parse import LlamaParse
from pydantic_settings import BaseSettings, SettingsConfigDict

# Lemos a chave do LlamaCloud usando Pydantic, garantindo segurança
class Settings(BaseSettings):
    LLAMA_CLOUD_API_KEY: str
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
os.environ["LLAMA_CLOUD_API_KEY"] = settings.LLAMA_CLOUD_API_KEY

def extrair_pdf_para_markdown(caminho_arquivo: str) -> str:
    """
    Usa IA de Visão para ler o PDF e converter o layout (tabelas/textos) em Markdown perfeito.
    """
    print(f"Analisando visualmente o arquivo: {caminho_arquivo}...")
    
    parser = LlamaParse(
        result_type="markdown", # Garante que tabelas fiquem formatadas
        verbose=True,
        language="pt" # Otimiza a detecção de caracteres (acentos/cedilha)
    )
    
    documentos = parser.load_data(caminho_arquivo)
    
    # Junta todas as páginas extraídas em uma única string gigante de Markdown
    texto_completo = "\n\n".join([doc.text for doc in documentos])
    return texto_completo
