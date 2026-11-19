import os
import asyncio
from dotenv import load_dotenv
import pymupdf4llm  # A biblioteca especializada em LLMs e RAG
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from regulamentos import DOCUMENTOS_POR_ARTIGO, secoes_por_artigo
from versionamento import calcular_hash, salvar_manifesto

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "cacic_docs"
MANIFESTO = "data/.manifesto_documentos.json"

async def executar_pipeline_etl():
    print("1. Lendo documentos para Markdown com pymupdf4llm (Alta Fidelidade)...")
    arquivos_pdf = [f"data/{f}" for f in os.listdir("data") if f.endswith(".pdf")]

    documentos_brutos = []
    arquivos_processados = []
    for arquivo in arquivos_pdf:
        print(f"   -> Mapeando tabelas de: {arquivo}")
        try:
            # Esta única linha faz todo o trabalho de visão computacional offline
            texto_markdown = pymupdf4llm.to_markdown(arquivo)
            if os.path.basename(arquivo) in DOCUMENTOS_POR_ARTIGO:
                # Resolução/edital/regimento: divide por artigo/seção antes do chunker, pra
                # um trecho procedural não ficar diluído dentro de um parágrafo sobre outro
                # assunto (ver docs/DECISOES.md).
                for secao in secoes_por_artigo(texto_markdown):
                    documentos_brutos.append(Document(page_content=secao, metadata={"fonte": arquivo}))
            else:
                documentos_brutos.append(Document(page_content=texto_markdown, metadata={"fonte": arquivo}))
            arquivos_processados.append(arquivo)
        except Exception as e:
            print(f"      [ERRO] Falha ao processar {arquivo}: {e}")

    print(f"   Total de PDFs mapeados: {len(documentos_brutos)}")

    if not documentos_brutos:
        print("Erro crítico: Abortando ETL.")
        return

    print("2. Carregando modelo BGE-M3 (Embeddings)...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    print("3. Executando Chunking Recursivo (Inteligente para Markdown)...")
    chunker = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    documentos_processados = chunker.split_documents(documentos_brutos)
    print(f"   Texto dividido em {len(documentos_processados)} blocos contextuais (Fast).")

    print("4. Conectando ao Qdrant e Injetando Dados...")
    client = QdrantClient(url=QDRANT_URL)
    
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
    )

    QdrantVectorStore.from_documents(
        documentos_processados,
        embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )
    manifesto = {os.path.basename(a): calcular_hash(a) for a in arquivos_processados}
    salvar_manifesto(MANIFESTO, manifesto)
    print("🚀 ETL DE ALTA QUALIDADE CONCLUÍDO!")

if __name__ == "__main__":
    asyncio.run(executar_pipeline_etl())
