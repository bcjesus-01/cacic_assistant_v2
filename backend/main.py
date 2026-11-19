import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from agent.graph import DB_URI, construir_grafo
from api.routes import router
from limites import preparar_tabela_uso

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Modelo (bge-m3), Qdrant, pool do Postgres e grafo — tudo montado uma vez só, na subida,
    # não na importação do módulo nem por requisição. Fica em app.state pra api/routes.py
    # reaproveitar.
    logger.info("Carregando modelo (bge-m3) e conectando ao Qdrant...")
    workflow = construir_grafo()
    logger.info("Conectando ao Postgres e compilando o grafo...")
    async with AsyncConnectionPool(
        conninfo=DB_URI, max_size=10, kwargs={"autocommit": True}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        await preparar_tabela_uso(pool)
        app.state.app_grafo = workflow.compile(checkpointer=checkpointer)
        app.state.pg_pool = pool
        logger.info("Pronto.")
        yield
    logger.info("Pool do Postgres encerrado.")


app = FastAPI(
    title="CACIC Assistant API",
    description="Backend de Inteligência Artificial para o Centro Acadêmico",
    version="2.0.0",
    lifespan=lifespan,
)

# Origens permitidas, separadas por vírgula. Em produção, defina CORS_ORIGINS com o domínio do frontend.
ORIGENS = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
