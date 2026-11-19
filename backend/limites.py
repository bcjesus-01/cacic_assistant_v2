"""Limite por IP e teto diário global, para proteger a cota grátis do Gemini (free tier,
compartilhada por toda a chave de API, não por aluno). Efeito colateral em Postgres, tolerante
a falha — mesmo princípio de `registro.py` — mas, diferente dele, roda em toda mensagem
aceita, então reaproveita o pool do checkpointer (`app.state.pg_pool`) em vez de abrir uma
conexão nova por chamada.
"""

import logging
from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)
FUSO = ZoneInfo("America/Bahia")
IP_GLOBAL = "__global__"  # linha-sentinela: guarda o total do dia, somando todos os IPs


class ResultadoUso(Enum):
    ACEITO = "aceito"
    LIMITE_IP = "limite_ip"
    TETO_GLOBAL = "teto_global"


def dia_atual() -> date:
    return datetime.now(FUSO).date()


async def preparar_tabela_uso(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS uso_diario (
                dia DATE NOT NULL,
                ip TEXT NOT NULL,
                mensagens INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (dia, ip)
            )"""
        )


async def _incrementar(conn, dia: date, ip: str, peso: int) -> int:
    cur = await conn.execute(
        """INSERT INTO uso_diario (dia, ip, mensagens) VALUES (%s, %s, %s)
           ON CONFLICT (dia, ip) DO UPDATE SET mensagens = uso_diario.mensagens + EXCLUDED.mensagens
           RETURNING mensagens""",
        (dia, ip, peso),
    )
    linha = await cur.fetchone()
    return linha[0]


async def verificar_e_registrar(
    pool: AsyncConnectionPool,
    ip: str,
    dia: date,
    peso_global: int,
    limite_ip: int,
    teto_global: int,
) -> ResultadoUso:
    """Incrementa os dois contadores (IP real e a linha-sentinela global) e decide; sempre
    incrementa primeiro e decide depois, então nunca subconta. Falha ao acessar o Postgres
    deixa passar: o checkpointer do LangGraph já depende do Postgres, então se ele estiver
    fora do ar o chat já não funciona de qualquer jeito (mesmo princípio de registro.py)."""
    try:
        async with pool.connection() as conn:
            contagem_ip = await _incrementar(conn, dia, ip, 1)
            total_global = await _incrementar(conn, dia, IP_GLOBAL, peso_global)
        if total_global > teto_global:
            return ResultadoUso.TETO_GLOBAL
        if contagem_ip > limite_ip:
            return ResultadoUso.LIMITE_IP
        return ResultadoUso.ACEITO
    except Exception:
        logger.exception("Falha ao verificar limite de uso diário (ip=%s)", ip)
        return ResultadoUso.ACEITO
