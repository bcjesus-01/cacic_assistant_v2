#!/usr/bin/env python3
"""Classifica os erros de uma rodada de avaliação, separando onde a falha realmente está.

Uso (a partir de backend/, com o Qdrant no ar):
    uv run python eval/classificar_erros.py eval/historico/<resultado>.json

Para cada item com "passou": false e tipo "resposta", tenta classificar automaticamente em:
  (a) a busca não trouxe o trecho certo entre os K_BUSCA recuperados
      (ou trouxe, mas a seleção/dedup cortou antes do contexto final);
  (b) o trecho estava no contexto final e o modelo respondeu errado ou incompleto;
  (c) o documento citado em "fonte_gabarito" não está indexado na coleção.
(d) gabarito errado NUNCA é atribuído automaticamente — o relatório mostra fonte_gabarito,
    pergunta, resposta e trechos recuperados para você decidir; confira a fonte antes de
    aceitar (a)/(b)/(c).
Itens com "conversa" usam só a última pergunta na busca de diagnóstico (aproximação: não
refaz a chamada de reescrita da Etapa 2), o que o relatório deixa marcado.
Falhas de tipo "recusa" (respondeu quando devia recusar) e falhas operacionais (erro do
servidor, resposta vazia) ficam em buckets próprios, fora de (a)-(d).
"""

import argparse
import json
import os
import sys
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

# Reaproveita a lógica pura de seleção de contexto do agente (backend/ precisa estar no
# sys.path; scripts em eval/ não ganham isso automaticamente, só a própria pasta).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.contexto import selecionar  # noqa: E402

from avaliar import contem, normalizar  # mesma pasta (eval/); noqa: E402

K_BUSCA = int(os.getenv("RAG_K_BUSCA", 8))
K_CONTEXTO = int(os.getenv("RAG_K_CONTEXTO", 5))

FALHAS_OPERACIONAIS = {"erro do servidor", "resposta vazia"}


def carregar_qdrant() -> QdrantVectorStore:
    return QdrantVectorStore.from_existing_collection(
        embedding=HuggingFaceEmbeddings(model_name="BAAI/bge-m3"),
        collection_name="cacic_docs",
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    )


def fontes_indexadas(loja: QdrantVectorStore) -> set[str]:
    """Nomes distintos de metadata.fonte presentes na coleção (percorre tudo via scroll)."""
    fontes: set[str] = set()
    deslocamento = None
    while True:
        pontos, deslocamento = loja.client.scroll(
            collection_name=loja.collection_name,
            limit=256,
            offset=deslocamento,
            with_payload=["metadata"],
            with_vectors=False,
        )
        for p in pontos:
            fonte = (p.payload or {}).get("metadata", {}).get("fonte")
            if fonte:
                fontes.add(fonte)
        if deslocamento is None:
            break
    return fontes


def documento_esta_na_base(fonte_gabarito: str, fontes: set[str]) -> bool:
    """fonte_gabarito deve começar pelo nome do arquivo indexado (convenção pedida ao
    preencher o held-out); por isso basta checar se algum nome indexado aparece no texto."""
    alvo = normalizar(fonte_gabarito)
    return any(normalizar(fonte) in alvo for fonte in fontes)


def fatos_presentes(fatos: list[list[str]], texto: str) -> bool:
    return all(any(contem(texto, alt) for alt in grupo) for grupo in fatos)


def classificar(item: dict, loja: QdrantVectorStore, fontes: set[str]) -> dict:
    motivo = item.get("motivo", "")
    nota_conversa = " [aproximação: item tem 'conversa', busca usou só a última pergunta]" if item.get("conversa") else ""

    if motivo in FALHAS_OPERACIONAIS:
        return {"bucket": "falha operacional", "detalhe": motivo, "nota": nota_conversa}

    if item["tipo"] == "recusa":
        return {"bucket": "recusa esperada, respondeu", "detalhe": motivo, "nota": nota_conversa}

    recuperados = loja.similarity_search(item["pergunta"], k=K_BUSCA)
    contexto_final = selecionar(recuperados, K_CONTEXTO)

    texto_busca = normalizar(" ".join(d.page_content for d in recuperados))
    texto_contexto = normalizar(" ".join(d.page_content for d in contexto_final))
    fatos = item.get("fatos", [])

    if fatos and fatos_presentes(fatos, texto_contexto):
        bucket, detalhe = "(b) contexto certo, resposta errada", "o(s) fato(s) estavam no contexto final enviado ao modelo"
    elif fatos and fatos_presentes(fatos, texto_busca):
        bucket, detalhe = "(a) busca encontrou, seleção cortou", "fato(s) nos K_BUSCA recuperados, mas fora do contexto final (top K_CONTEXTO)"
    elif documento_esta_na_base(item.get("fonte_gabarito", ""), fontes):
        bucket, detalhe = "(a) busca não achou", "documento parece estar indexado, mas não veio nos K_BUSCA recuperados"
    else:
        bucket, detalhe = "(c) documento não está na base", "nenhuma fonte indexada parece corresponder a fonte_gabarito"

    return {
        "bucket": bucket,
        "detalhe": detalhe,
        "nota": nota_conversa,
        "fontes_recuperadas": [d.metadata.get("fonte") for d in recuperados],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("resultado", help="arquivo resultados-*.json (saída de avaliar.py)")
    args = ap.parse_args()

    itens = json.loads(Path(args.resultado).read_text(encoding="utf-8"))
    falhas = [item for item in itens if not item.get("passou", True)]
    if not falhas:
        print("Nenhuma falha neste resultado.")
        return

    print(f"Carregando Qdrant e o bge-m3 para diagnosticar {len(falhas)} falha(s)...")
    loja = carregar_qdrant()
    fontes = fontes_indexadas(loja)

    for item in falhas:
        c = classificar(item, loja, fontes)
        print(f"\n=== [{item['id']}] {c['bucket']}{c['nota']}")
        print(f"Pergunta: {item['pergunta']}")
        print(f"Fonte do gabarito: {item.get('fonte_gabarito', '(não informada)')}")
        print(f"Resposta do chat: {item['resposta'][:200]!r}")
        print(f"Diagnóstico: {c['detalhe']}")
        if "fontes_recuperadas" in c:
            print(f"Fontes recuperadas (top {K_BUSCA}): {c['fontes_recuperadas']}")
        print("-> Confira a fonte do gabarito antes de aceitar esta classificação "
              "(se a fonte estiver errada, o problema é o gabarito, não o chat).")


if __name__ == "__main__":
    main()
