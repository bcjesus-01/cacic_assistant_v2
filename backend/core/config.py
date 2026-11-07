from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Classe central de configurações do Backend.
    O Pydantic vai ler o arquivo .env e validar os tipos automaticamente.
    Se uma variável sem valor padrão (como GOOGLE_API_KEY) faltar, o app não inicia.
    """
    PROJECT_NAME: str = "CACIC Assistant API"
    API_PORT: int = 8000
    
    # LLM
    GOOGLE_API_KEY: str
    
    # Vector DB
    VECTOR_DB_HOST: str = "localhost"
    VECTOR_DB_PORT: int = 6333

    # Configuração para buscar o .env na pasta raiz do projeto
    model_config = SettingsConfigDict(
        env_file="../.env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Instanciamos a classe uma única vez (Padrão Singleton)
# Qualquer outro arquivo do backend fará apenas: `from core.config import settings`
settings = Settings()
