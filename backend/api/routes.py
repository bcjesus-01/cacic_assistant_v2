import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from agent.graph import DB_URI, workflow
from api.schemas import ChatRequest
from api.sse import DONE, MENSAGEM_ERRO, extrair_texto, sse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    mensagem_humana = HumanMessage(content=request.message)

    async def gerador_eventos():
        try:
            async with AsyncConnectionPool(
                conninfo=DB_URI, max_size=10, kwargs={"autocommit": True}
            ) as pool:
                checkpointer = AsyncPostgresSaver(pool)
                await checkpointer.setup()
                app_grafo = workflow.compile(checkpointer=checkpointer)

                async for event in app_grafo.astream_events(
                    {"messages": [mensagem_humana]}, config, version="v2"
                ):
                    if event["event"] != "on_chat_model_stream":
                        continue

                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue

                    token = extrair_texto(getattr(chunk, "content", chunk))
                    if token:
                        yield sse(token)
                        await asyncio.sleep(0)  # cede o loop sem atrasar o stream

                yield DONE

        except Exception:
            # O detalhe técnico fica só no log do servidor; o cliente recebe uma mensagem genérica.
            logger.exception("Falha ao gerar a resposta (thread_id=%s)", request.thread_id)
            yield sse(MENSAGEM_ERRO, event="error")
            yield DONE

    return StreamingResponse(
        gerador_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
