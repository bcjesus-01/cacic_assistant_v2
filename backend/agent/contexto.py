"""Seleção e montagem do contexto do RAG (lógica pura, testável sem Qdrant nem modelos)."""

import os
import re


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().lower()


def deduplicar(documentos: list) -> list:
    """Remove trechos repetidos, mantendo a ordem de relevância.

    Descarta um trecho se o texto dele (sem diferenças de espaço/maiúsculas) é igual ou
    está contido num trecho já mantido, o que acontece quando o mesmo regulamento foi
    indexado em dois arquivos.
    """
    mantidos: list = []
    textos: list[str] = []
    for doc in documentos:
        texto = _normalizar(doc.page_content)
        if not texto or any(texto in outro for outro in textos):
            continue
        mantidos.append(doc)
        textos.append(texto)
    return mantidos


def selecionar(documentos: list, limite: int) -> list:
    """Dedup + os `limite` primeiros trechos."""
    return deduplicar(documentos)[:limite]


def nome_fonte(metadata: dict | None) -> str:
    """'data/Perguntas_Frequentes_CACIC.pdf' -> 'Perguntas Frequentes CACIC'."""
    fonte = (metadata or {}).get("fonte") or "documento"
    base = os.path.splitext(os.path.basename(str(fonte)))[0]
    return base.replace("_", " ").strip() or "documento"


def montar_contexto(documentos: list) -> str:
    """Junta os trechos, cada um identificado pela fonte."""
    return "\n\n".join(
        f"[Fonte: {nome_fonte(d.metadata)}]\n{d.page_content}" for d in documentos
    )
