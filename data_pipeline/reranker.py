from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.document_compressors import CrossEncoderReranker

def configurar_retriever_com_reranking(qdrant_store):
    """
    Recebe o banco vetorial Qdrant e cria um pipeline de busca em duas etapas:
    1. Busca Híbrida Larga (Top 30)
    2. Leitura Meticulosa Cross-Encoder (Top 5)
    """
    print("Inicializando o modelo Cross-Encoder (BAAI/bge-reranker-v2-m3)...")
    
    # 1. Carregamos o modelo Cross-Encoder otimizado para português/multilíngue
    modelo_cross_encoder = HuggingFaceCrossEncoder(
        model_name="BAAI/bge-reranker-v2-m3",
        model_kwargs={'device': 'cpu'}
    )
    
    # 2. Configuramos o compressor para retornar APENAS os 5 melhores resultados
    compressor = CrossEncoderReranker(
        model=modelo_cross_encoder, 
        top_n=5
    )
    
    # 3. Configuramos o buscador base (Qdrant) para trazer um volume alto (Top 30)
    buscador_base = qdrant_store.as_retriever(search_kwargs={"k": 30})
    
    # 4. Unimos as duas ferramentas: O Qdrant busca 30, o Cross-Encoder filtra para 5
    retriever_avancado = ContextualCompressionRetriever(
        base_compressor=compressor, 
        base_retriever=buscador_base
    )
    
    print("[OK] Pipeline de Re-ranking configurado! Pronto para o LLM.")
    return retriever_avancado
