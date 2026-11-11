"""Documentos curados em Markdown: cada seção separada por '---' vira um trecho próprio.

Serve para conteúdos escritos para o assistente (como o FAQ do CACIC), em que cada
pergunta e a resposta dela devem ficar juntas num único trecho de busca.
"""

import re

_COMENTARIO = re.compile(r"<!--.*?-->", re.S)
_SEPARADOR = re.compile(r"^\s*---+\s*$", re.M)


def secoes_markdown(texto: str) -> list[str]:
    """Remove comentários HTML e divide o texto nas linhas '---', descartando seções vazias."""
    sem_comentarios = _COMENTARIO.sub("", texto)
    return [s.strip() for s in _SEPARADOR.split(sem_comentarios) if s.strip()]
