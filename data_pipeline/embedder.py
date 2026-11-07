from langchain_huggingface import HuggingFaceEmbeddings

def carregar_modelo_embeddings():
    """
    Inicializa o modelo BGE-M3 (BAAI General Embedding) para geração de vetores.
    Este modelo será o 'tradutor matemático' utilizado pelo nosso banco de dados vetorial.
    """
    print("Inicializando o motor matemático BGE-M3 (BAAI/bge-m3)...")
    
    # model_name: O caminho exato do modelo open-source no repositório HuggingFace.
    # model_kwargs: Define onde o modelo vai rodar. Se o servidor tiver placa de vídeo, 
    # mude para 'cuda'. Para CPUs tradicionais, mantemos 'cpu'.
    # encode_kwargs: A normalização (normalize_embeddings=True) força todos os vetores
    # a terem o mesmo tamanho de magnitude. Isso é EXTREMAMENTE importante para que o 
    # cálculo de Similaridade por Cosseno seja feito de forma ultra-rápida no banco vetorial.
    
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True} 
    )
    
    print("[OK] Modelo BGE-M3 carregado e normalizado com sucesso!")
    return embeddings
