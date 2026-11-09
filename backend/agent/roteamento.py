"""Decisão de roteamento do agente: conversa geral ou RAG acadêmico.

Módulo sem dependências externas, para poder ser testado isoladamente.
"""

import re
from typing import Literal

Destino = Literal["rag_academico", "conversa_geral"]

# Vocabulário de saudações, agradecimentos e despedidas. Só uma mensagem formada
# inteiramente por estas palavras vai para a conversa geral. Qualquer outra coisa
# passa pelo RAG, cuja "rota de fuga" no prompt trata o que não estiver nos documentos.
VOCABULARIO_SOCIAL = frozenset(
    {
        "oi", "olá", "ola", "opa", "eai", "hey", "hello", "hi",
        "bom", "boa", "dia", "tarde", "noite",
        "tudo", "bem", "e", "aí", "ai", "blz", "beleza",
        "obrigado", "obrigada", "obg", "valeu", "muito",
        "tchau", "até", "logo",
    }
)  # fmt: skip

MAX_PALAVRAS_SOCIAIS = 5


def escolher_destino(pergunta: str) -> Destino:
    palavras = re.findall(r"\w+", pergunta.lower())
    mensagem_social = (
        0 < len(palavras) <= MAX_PALAVRAS_SOCIAIS
        and all(p in VOCABULARIO_SOCIAL for p in palavras)
    )
    return "conversa_geral" if mensagem_social else "rag_academico"
