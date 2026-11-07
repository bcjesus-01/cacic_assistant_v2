from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from qdrant_client import QdrantClient
from pydantic_settings import BaseSettings, SettingsConfigDict
# Importa a fábrica de embeddings densos que criamos na etapa anterior
from embedder import carregar_modelo_embeddings 

class Settings(BaseSettings):
    VECTOR_DB_HOST: str
    VECTOR_DB_PORT: int
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()

def configurar_qdrant_hibrido(nome_colecao: str = "cacic_docs"):
    """
    Conecta ao Qdrant e inicializa o motor de busca híbrida.
    """
    print(f"Conectando ao banco Qdrant em {settings.VECTOR_DB_HOST}:{settings.VECTOR_DB_PORT}...")
    
    # Cliente de conexão com o banco de dados
    client = QdrantClient(url=f"http://{settings.VECTOR_DB_HOST}:{settings.VECTOR_DB_PORT}")
    
    # 1. Carrega o modelo de Busca Densa (Semântica)
    embeddings_densos = carregar_modelo_embeddings()
    
    # 2. Carrega o modelo de Busca Esparsa (Lexical/BM25)
    # FastEmbed é altamente otimizado para gerar vetores lexicais via CPU
    print("Inicializando o motor léxico (BM25) para busca esparsa...")
    embeddings_esparsos = FastEmbedSparse(model_name="Qdrant/bm25")
    
    # 3. Instancia o repositório configurado nativamente para Hybrid Search
    qdrant_store = QdrantVectorStore(
        client=client,
        collection_name=nome_colecao,
        embedding=embeddings_densos,
        sparse_embedding=embeddings_esparsos,
        # Essa constante avisa ao Qdrant para fundir os scores (Dense + Sparse)
        retrieval_mode=RetrievalMode.HYBRID,
    )
    
    print(f"[OK] Qdrant configurado com sucesso em modo Híbrido para a coleção '{nome_colecao}'!")
    return qdrant_store
