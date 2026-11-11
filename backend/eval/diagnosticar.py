#!/usr/bin/env python3
"""Mostra o que a busca vetorial devolve para uma pergunta (top-5 com score e fonte).

Serve para separar "o documento não está na base" de "a busca não achou o trecho".

Uso (a partir de backend/, com o Qdrant no ar):
    uv run python eval/diagnosticar.py                      # perguntas que falharam na 1a rodada
    uv run python eval/diagnosticar.py "Como regulamento meu estágio?" --k 8
"""

import argparse
import os

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

PADRAO = [
    "Em que casos eu sou desligado do auxílio Mais Futuro?",
    "Como regulamento meu estágio com a UESC?",
    "O TCC e o estágio são a mesma coisa?",
    "Qual a diferença entre horas complementares e horas de extensão?",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("perguntas", nargs="*", default=PADRAO)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    loja = QdrantVectorStore.from_existing_collection(
        embedding=HuggingFaceEmbeddings(model_name="BAAI/bge-m3"),
        collection_name="cacic_docs",
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    )
    for pergunta in args.perguntas:
        print(f"\n=== {pergunta}")
        for i, (doc, score) in enumerate(loja.similarity_search_with_score(pergunta, k=args.k), 1):
            trecho = " ".join(doc.page_content.split())[:160]
            print(f"{i}. [{score:.3f}] {doc.metadata.get('fonte')}\n   {trecho}")


if __name__ == "__main__":
    main()
