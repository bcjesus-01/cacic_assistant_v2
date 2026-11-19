import asyncio
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from agent.prompts import RECUSA_PADRAO
from agent.reescrita import TAG_CHAMADA_INTERNA
from api.ip_cliente import extrair_ip
from api.schemas import ChatRequest, FeedbackRequest
from api.controle_stream import ControleStream
from api.sse import (
    DONE,
    MENSAGEM_ERRO,
    MENSAGEM_LIMITE,
    MENSAGEM_LIMITE_IP,
    MENSAGEM_TETO_GLOBAL,
    RESET,
    extrair_texto,
    sse,
)
from limites import ResultadoUso, dia_atual, verificar_e_registrar
from registro import registrar_recusa, salvar_feedback

logger = logging.getLogger(__name__)
router = APIRouter()

# Orçamento é zero: os três limites abaixo são sobre não esgotar a cota grátis do Gemini
# (free tier, compartilhada por toda a chave de API), não sobre dinheiro.
LIMITE_MENSAGENS_POR_THREAD = int(os.getenv("LIMITE_MENSAGENS_POR_THREAD", 15))
LIMITE_MENSAGENS_POR_IP_POR_DIA = int(os.getenv("LIMITE_MENSAGENS_POR_IP_POR_DIA", 50))
TETO_MENSAGENS_POR_DIA = int(os.getenv("TETO_MENSAGENS_POR_DIA", 400))


@router.post("/chat/stream")
async def chat_stream(dados: ChatRequest, request: Request):
    app_grafo = request.app.state.app_grafo
    config = {"configurable": {"thread_id": dados.thread_id}}
    mensagem_humana = HumanMessage(content=dados.message)
    ip = extrair_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )

    async def gerador_eventos():
        controle = ControleStream()
        try:
            estado = await app_grafo.aget_state(config)
            mensagens_existentes = estado.values.get("messages", [])
            if len(mensagens_existentes) >= LIMITE_MENSAGENS_POR_THREAD:
                yield sse(MENSAGEM_LIMITE, event="limite")
                yield DONE
                return

            # Pergunta de acompanhamento custa uma chamada extra ao Gemini (reescrita para a
            # busca, ver agent/reescrita.py); conta em dobro no teto global por isso.
            peso_global = 2 if mensagens_existentes else 1
            resultado = await verificar_e_registrar(
                request.app.state.pg_pool,
                ip,
                dia_atual(),
                peso_global,
                LIMITE_MENSAGENS_POR_IP_POR_DIA,
                TETO_MENSAGENS_POR_DIA,
            )
            if resultado is ResultadoUso.TETO_GLOBAL:
                yield sse(MENSAGEM_TETO_GLOBAL, event="bloqueado")
                yield DONE
                return
            if resultado is ResultadoUso.LIMITE_IP:
                yield sse(MENSAGEM_LIMITE_IP, event="bloqueado")
                yield DONE
                return

            async for event in app_grafo.astream_events(
                {"messages": [mensagem_humana]}, config, version="v2"
            ):
                if TAG_CHAMADA_INTERNA in (event.get("tags") or []):
                    # Chamada interna (ex.: reescrita da pergunta para a busca); não é a
                    # resposta ao aluno, e não conta como troca para o modelo de reserva.
                    continue

                if event["event"] == "on_chat_model_start":
                    if controle.iniciar_modelo():
                        # O modelo de reserva assumiu depois de tokens já enviados.
                        yield RESET
                    if controle.reserva_acionada:
                        logger.warning(
                            "Modelo de reserva acionado (thread_id=%s)", dados.thread_id
                        )
                    continue

                if event["event"] != "on_chat_model_stream":
                    continue

                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue

                token = extrair_texto(getattr(chunk, "content", chunk))
                if token:
                    controle.registrar_token()
                    yield sse(token)
                    await asyncio.sleep(0)  # cede o loop sem atrasar o stream

            # Lê a mensagem final do grafo pra pegar metadados que não vêm no stream de
            # tokens: fontes usadas (agent.graph.rag_academico) e se foi uma recusa.
            estado_final = await app_grafo.aget_state(config)
            ultima_mensagem = estado_final.values["messages"][-1]
            texto_final = extrair_texto(getattr(ultima_mensagem, "content", ""))
            fontes = getattr(ultima_mensagem, "additional_kwargs", {}).get("fontes") or []
            if fontes:
                yield sse(fontes, event="fontes")
            if texto_final.strip() == RECUSA_PADRAO:
                await registrar_recusa(dados.thread_id, dados.message)

            yield DONE

        except Exception:
            # O detalhe técnico fica só no log do servidor; o cliente recebe uma mensagem genérica.
            logger.exception(
                "Falha ao gerar a resposta (thread_id=%s, tokens_enviados=%d)",
                dados.thread_id,
                controle.tokens,
            )
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


@router.post("/feedback")
async def feedback(request: FeedbackRequest):
    await salvar_feedback(request.thread_id, request.pergunta, request.resposta, request.util)
    return {"status": "ok"}
