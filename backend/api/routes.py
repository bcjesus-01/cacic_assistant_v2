import asyncio
import json
import traceback

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.graph import workflow, DB_URI

router = APIRouter()


class ChatRequest(BaseModel):
    thread_id: str
    message: str


def extrair_texto(content) -> str:
    """Aceita string ou lista de blocos (formato do langchain-google-genai)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(bloco.get("text", ""))
        return "".join(partes)
    return ""


def sse(payload: str) -> str:
    # json.dumps escapa quebras de linha, aspas e unicode com segurança
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    mensagem_humana = HumanMessage(content=request.message)

    async def gerador_eventos():
        async with AsyncConnectionPool(
            conninfo=DB_URI, max_size=10, kwargs={"autocommit": True}
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            app_grafo = workflow.compile(checkpointer=checkpointer)

            try:
                async for event in app_grafo.astream_events(
                    {"messages": [mensagem_humana]}, config, version="v2"
                ):
                    if event["event"] != "on_chat_model_stream":
                        continue

                    chunk_data = event.get("data", {}).get("chunk")
                    if chunk_data is None:
                        continue

                    # Log de diagnóstico (remova depois de confirmar)
                    print(
                        "CHUNK:",
                        type(chunk_data).__name__,
                        repr(getattr(chunk_data, "content", chunk_data)),
                        flush=True,
                    )

                    token = extrair_texto(getattr(chunk_data, "content", chunk_data))
                    if token:
                        yield sse(token)
                        await asyncio.sleep(0)  # cede o loop sem atrasar o stream

                yield "data: [DONE]\n\n"

            except Exception as e:
                traceback.print_exc()
                yield sse(f"[ERRO INTERNO] {e}")
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        gerador_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )