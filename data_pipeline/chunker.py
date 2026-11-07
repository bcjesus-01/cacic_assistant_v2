from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

def dividir_por_semantica(texto_markdown: str):
    """
    Agrupa frases que falam do mesmo assunto. Quebra o bloco quando o assunto muda.
    """
    print("Aplicando Chunking Semântico nas frases...")
    
    # Motor matemático rápido para calcular a distância entre as frases em português
    embeddings_rapido = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # Usa a quebra por percentil: se a diferença de assunto entre duas frases 
    # for maior que 80% das diferenças normais do texto, ele corta e cria um novo bloco.
    text_splitter = SemanticChunker(
        embeddings_rapido, 
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=80.0
    )
    
    # Cria os fragmentos baseados na lógica de ideias completas
    docs = text_splitter.create_documents([texto_markdown])
    print(f"Processo concluído. {len(docs)} blocos de ideias independentes gerados.")
    
    return docs
