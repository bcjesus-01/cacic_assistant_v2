"""Documentos regulatórios (resoluções, regimento, editais) em Markdown: divide por
artigo/seção numerada antes do chunker genérico, para o trecho procedural de um artigo não
ficar diluído dentro de um parágrafo sobre outro assunto (ver docs/DECISOES.md).

Um cabeçalho markdown (numerado ou não) também é limite: `legislacao_graduacao.pdf` é uma
coletânea de várias resoluções concatenadas, e um cabeçalho de título/capítulo/seção sem
número (ex.: "## **MATRÍCULA**") marca a troca de assunto tão bem quanto um "Art. N" —
sem essa regra, o fim de um artigo ficava colado ao início da resolução seguinte, sobre
outro assunto (caso real: Art. 179 sobre advertência colado a um cabeçalho de MATRÍCULA).
"""

import re

_LIMITE = re.compile(
    r"(?=^\s*(?:Art(?:igo)?\.?\s*\d+|§\s*\d+|#{1,6}\s))", re.M
)

DOCUMENTOS_POR_ARTIGO = frozenset({
    "regimento.pdf",
    "legislacao_graduacao.pdf",
    "CONSEPE_EXTENSÃO.pdf",
    "Edital_Mais_Futuro_Auxilio_Permanencia.pdf",
    "Lei_Mais_Futuro.pdf",
    "Estatuto_CACIC.pdf",
    "regulamentoestagio.pdf",
    "regulamentoestagio0.pdf",
})


def secoes_por_artigo(texto: str) -> list[str]:
    """Divide antes de cada Art./Artigo/§/cabeçalho numerado; descarta seções vazias."""
    return [s.strip() for s in _LIMITE.split(texto) if s.strip()]
