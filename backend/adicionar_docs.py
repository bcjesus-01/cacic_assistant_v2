"""Adiciona ou remove documentos da coleção existente, sem recriá-la.

Uso (a partir de backend/):
    uv run python adicionar_docs.py data/novo.pdf            # PDF: Markdown + divisão em trechos
    uv run python adicionar_docs.py ../docs/FAQ_CACIC.md     # Markdown curado: 1 trecho por seção '---'
    uv run python adicionar_docs.py --remover "data/antigo.pdf"

É seguro rodar de novo no mesmo arquivo: os trechos antigos dele são removidos antes de
inserir os novos (a 'fonte' é "data/<nome do arquivo>", igual ao etl_pipeline.py).
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

from curados import secoes_markdown

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "cacic_docs"


def fonte_de(caminho: str) -> str:
    return f"data/{os.path.basename(caminho)}"


def filtro_da_fonte(fonte: str) -> models.Filter:
    return models.Filter(
        must=[models.FieldCondition(key="metadata.fonte", match=models.MatchValue(value=fonte))]
    )


def remover_fonte(client: QdrantClient, fonte: str) -> int:
    filtro = filtro_da_fonte(fonte)
    quantos = client.count(COLLECTION_NAME, count_filter=filtro, exact=True).count
    if quantos:
        client.delete(COLLECTION_NAME, points_selector=models.FilterSelector(filter=filtro))
    return quantos


def carregar(caminho: str, fonte: str, chunker: RecursiveCharacterTextSplitter) -> list[Document]:
    if caminho.lower().endswith(".md"):
        texto = Path(caminho).read_text(encoding="utf-8")
        secoes = [Document(page_content=s, metadata={"fonte": fonte}) for s in secoes_markdown(texto)]
        return chunker.split_documents(secoes)  # só divide as seções maiores que o limite
    import pymupdf4llm

    texto = pymupdf4llm.to_markdown(caminho)
    return chunker.split_documents([Document(page_content=texto, metadata={"fonte": fonte})])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("arquivos", nargs="*", help="PDFs ou .md a adicionar")
    ap.add_argument("--remover", action="append", default=[], metavar="FONTE",
                    help='remove os trechos de uma fonte (ex.: "data/antigo.pdf")')
    args = ap.parse_args()
    if not args.arquivos and not args.remover:
        ap.error("informe arquivos para adicionar ou --remover FONTE")

    client = QdrantClient(url=QDRANT_URL)
    if not client.collection_exists(COLLECTION_NAME):
        sys.exit(f"A coleção '{COLLECTION_NAME}' não existe. Rode o etl_pipeline.py uma vez.")

    for fonte in args.remover:
        print(f"-> Removidos {remover_fonte(client, fonte)} trechos de {fonte}")

    chunker = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
    )
    documentos: list[Document] = []
    for caminho in args.arquivos:
        fonte = fonte_de(caminho)
        removidos = remover_fonte(client, fonte)  # reexecução não duplica
        blocos = carregar(caminho, fonte, chunker)
        print(f"-> {caminho}: {len(blocos)} trechos (substituiu {removidos})")
        documentos.extend(blocos)

    if documentos:
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        QdrantVectorStore(
            client=client, collection_name=COLLECTION_NAME, embedding=embeddings
        ).add_documents(documentos)
    print(f"Concluído: {len(documentos)} trechos adicionados.")


if __name__ == "__main__":
    main()
