"""Registra perguntas sem resposta e feedback útil/não útil, pra decisões sobre o FAQ virem
de dados reais em vez de palpite. Efeitos colaterais em Postgres, tolerantes a falha (um erro
aqui nunca pode derrubar o chat do aluno) — mesmo princípio já usado em
`agent.graph.reescrever_para_busca`.
"""

import logging
import os

import psycopg

logger = logging.getLogger(__name__)
DB_URI = os.environ["DATABASE_URL"]


async def salvar_feedback(thread_id: str, pergunta: str, resposta: str, util: bool) -> None:
    try:
        async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    pergunta TEXT NOT NULL,
                    resposta TEXT NOT NULL,
                    util BOOLEAN NOT NULL,
                    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
                )"""
            )
            await conn.execute(
                "INSERT INTO feedback (thread_id, pergunta, resposta, util) "
                "VALUES (%s, %s, %s, %s)",
                (thread_id, pergunta, resposta, util),
            )
    except Exception:
        logger.exception("Falha ao salvar feedback (thread_id=%s)", thread_id)


async def registrar_recusa(thread_id: str, pergunta: str) -> None:
    try:
        async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS perguntas_sem_resposta (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    pergunta TEXT NOT NULL,
                    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
                )"""
            )
            await conn.execute(
                "INSERT INTO perguntas_sem_resposta (thread_id, pergunta) VALUES (%s, %s)",
                (thread_id, pergunta),
            )
    except Exception:
        logger.exception("Falha ao registrar pergunta sem resposta (thread_id=%s)", thread_id)
