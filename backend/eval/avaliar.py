#!/usr/bin/env python3
"""Avalia o assistente com perguntas reais dos alunos (só biblioteca padrão).

Uso (a partir de backend/, com o backend no ar):
    python3 eval/avaliar.py
    python3 eval/avaliar.py --api http://localhost:8000/api/v1/chat/stream --pausa 2

Critério automático (primeira triagem, não substitui a leitura das respostas):
  - tipo "resposta": passa se a resposta contém TODOS os grupos de "fatos"
    (em cada grupo basta uma alternativa; sem diferenciar acentos/maiúsculas);
  - tipo "recusa": passa se o assistente usou a resposta padrão de "não encontrei".
Item opcional "conversa": lista de mensagens anteriores, enviadas em sequência na mesma
thread antes da pergunta avaliada (simula uma pergunta de acompanhamento); as respostas
dessas mensagens não são julgadas.
Item opcional "queimado": true marca um item do conjunto held-out que já motivou uma
correção (não é mais um resultado "limpo"); a rodada avisa, mas não impede a execução.
--rodadas N repete a mesma lista de perguntas N vezes e relata a variação entre rodadas.
O relatório final inclui o intervalo de confiança de Wilson (eval/estatistica.py), porque
com poucos itens (ex.: o conjunto held-out) a taxa simples sozinha é pouco informativa.
Todas as respostas completas são salvas em eval/resultados-<data>.json para revisão.
"""

import argparse
import json
import statistics
import sys
import re
import time
import unicodedata
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path

try:
    from estatistica import intervalo_wilson  # rodando direto: python eval/avaliar.py
except ImportError:
    from eval.estatistica import intervalo_wilson  # importado como pacote (ex.: nos testes)

API_PADRAO = "http://localhost:8000/api/v1/chat/stream"
MARCA_RECUSA = "nao encontrei essa informacao"


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def contem(texto: str, alternativa: str) -> bool:
    alt = normalizar(alternativa)
    if len(alt) <= 3:  # fatos curtos (ex.: "6", "4", "pix") só valem como palavra inteira
        return re.search(rf"(?<!\w){re.escape(alt)}(?!\w)", texto) is not None
    return alt in texto


def perguntar(api: str, thread_id: str, pergunta: str, timeout: int) -> tuple[str, bool]:
    """Envia a pergunta nessa thread e devolve (resposta completa, houve_erro)."""
    corpo = json.dumps({"thread_id": thread_id, "message": pergunta}).encode()
    req = urllib.request.Request(
        api, data=corpo, headers={"Content-Type": "application/json"}, method="POST"
    )
    partes: list[str] = []
    erro = False
    evento = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for bruto in resp:
            linha = bruto.decode("utf-8").rstrip("\r\n")
            if linha.startswith("event:"):
                evento = linha[6:].strip()
            elif linha.startswith("data:"):
                dado = linha[5:].strip()
                if dado == "[DONE]":
                    break
                try:
                    valor = json.loads(dado)
                except json.JSONDecodeError:
                    valor = dado
                if evento == "error":
                    erro = True
                # Eventos nomeados que não são texto da resposta (ex.: "fontes", uma lista)
                # não entram na resposta acumulada — só os tokens de texto normais.
                if isinstance(valor, str):
                    partes.append(valor)
            elif linha == "":
                evento = None
    return "".join(partes), erro


def url_saude(api: str) -> str:
    return api.split("/api/")[0] + "/health"


def aguardar_backend(api: str, limite: int) -> bool:
    """Espera o /health responder (o backend leva um bom tempo para carregar o bge-m3)."""
    fim = time.time() + limite
    while time.time() < fim:
        try:
            with urllib.request.urlopen(url_saude(api), timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001 - ainda subindo
            pass
        time.sleep(3)
    return False


def perguntar_com_tentativas(api: str, thread_id: str, pergunta: str, timeout: int, tentativas: int):
    """Repete em falhas transitórias (conexão ou erro do servidor, ex.: 503 do Gemini)."""
    for n in range(1, tentativas + 1):
        try:
            resposta, erro = perguntar(api, thread_id, pergunta, timeout)
        except Exception as e:  # noqa: BLE001
            resposta, erro = f"[falha de conexão: {e}]", True
        if not erro or n == tentativas:
            return resposta, erro, n
        time.sleep(3 * n)


def enviar_conversa_anterior(
    api: str, thread_id: str, conversa: list[str], timeout: int, tentativas: int, pausa: float
) -> None:
    """Manda as mensagens anteriores na mesma thread, só para construir o histórico.

    As respostas não são avaliadas; uma falha aqui só vai para o log, porque o que importa é
    a pergunta final (perguntar_com_tentativas já repete essa em falha transitória).
    """
    for msg in conversa:
        _, erro, _ = perguntar_com_tentativas(api, thread_id, msg, timeout, tentativas)
        if erro:
            print(f"      aviso: falha ao enviar mensagem de contexto {msg!r} (thread_id={thread_id})")
        time.sleep(pausa)


def julgar(item: dict, resposta: str, erro: bool) -> tuple[bool, str]:
    texto = normalizar(resposta)
    recusou = MARCA_RECUSA in texto
    if erro:
        return False, "erro do servidor"
    if not resposta.strip():
        return False, "resposta vazia"
    if item["tipo"] == "recusa":
        return (True, "ok") if recusou else (False, "deveria recusar e respondeu")
    if recusou:
        return False, "recusou (documento ausente ou busca falhou)"
    faltando = [
        grupo[0]
        for grupo in item["fatos"]
        if not any(contem(texto, alt) for alt in grupo)
    ]
    return (True, "ok") if not faltando else (False, "faltou: " + ", ".join(faltando))


def rodar_rodada(itens: list[dict], args) -> list[dict]:
    """Faz uma pergunta (ou conversa) por item e devolve os resultados julgados."""
    resultados = []
    for i, item in enumerate(itens, 1):
        thread_id = uuid.uuid4().hex
        conversa = item.get("conversa") or []
        if conversa:
            enviar_conversa_anterior(
                args.api, thread_id, conversa, args.timeout, args.tentativas, args.pausa
            )

        inicio = time.time()
        resposta, erro, tentativas = perguntar_com_tentativas(
            args.api, thread_id, item["pergunta"], args.timeout, args.tentativas
        )
        passou, motivo = julgar(item, resposta, erro)
        segundos = time.time() - inicio

        print(f"[{i:02d}/{len(itens)}] {'OK ' if passou else 'FALHA'} {item['id']:<22} "
              f"{segundos:4.1f}s  {'' if passou else motivo}"
              f"{'  (precisou de ' + str(tentativas) + ' tentativas)' if tentativas > 1 else ''}")
        resultados.append({**item, "resposta": resposta, "passou": passou,
                           "motivo": motivo, "segundos": round(segundos, 1),
                           "tentativas": tentativas})
        time.sleep(args.pausa)
    return resultados


def relatorio(resultados: list[dict]) -> tuple[int, int]:
    """Imprime o relatório de uma rodada; devolve (acertos, total) para agregação entre rodadas."""
    total = len(resultados)
    acertos = sum(r["passou"] for r in resultados)

    por_categoria = defaultdict(lambda: [0, 0])
    for r in resultados:
        por_categoria[r["categoria"]][1] += 1
        por_categoria[r["categoria"]][0] += int(r["passou"])

    print("\nPor categoria:")
    for cat, (ok, n) in por_categoria.items():
        print(f"  {cat:<24} {ok}/{n}")

    if total == 0:
        print("\nTOTAL: nenhum item no arquivo.")
        return 0, 0

    inferior, superior = intervalo_wilson(acertos, total)
    aviso_largo = "  (poucos itens: intervalo largo)" if total < 30 else ""
    print(f"\nTOTAL: {acertos}/{total} ({100 * acertos / total:.0f}%) · "
          f"IC 95% Wilson: [{100 * inferior:.0f}%, {100 * superior:.0f}%]{aviso_largo}")

    instaveis = sum(r["tentativas"] > 1 for r in resultados)
    if instaveis:
        print(f"Instabilidade: {instaveis} pergunta(s) precisaram de nova tentativa (erro do servidor/Gemini).")

    com_historico = [r["segundos"] for r in resultados if r.get("conversa")]
    sem_historico = [r["segundos"] for r in resultados if not r.get("conversa")]
    if com_historico and sem_historico:
        media_com = sum(com_historico) / len(com_historico)
        media_sem = sum(sem_historico) / len(sem_historico)
        print(
            f"Latência média: {media_sem:.1f}s sem histórico (n={len(sem_historico)}) "
            f"vs {media_com:.1f}s com histórico (n={len(com_historico)}), "
            f"{media_com - media_sem:+.1f}s"
        )
    return acertos, total


def main() -> None:
    pasta = Path(__file__).parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--api", default=API_PADRAO)
    ap.add_argument("--arquivo", default=str(pasta / "perguntas.json"))
    ap.add_argument("--pausa", type=float, default=1.0, help="segundos entre perguntas")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--espera", type=int, default=180, help="segundos esperando o /health do backend")
    ap.add_argument("--tentativas", type=int, default=3, help="tentativas por pergunta em falha transitória")
    ap.add_argument("--rodadas", type=int, default=1, help="repete a mesma lista de perguntas N vezes")
    args = ap.parse_args()

    print(f"Aguardando o backend em {url_saude(args.api)} ...")
    if not aguardar_backend(args.api, args.espera):
        sys.exit(
            "O backend não respondeu em /health. Suba com 'docker-compose up -d backend' e "
            "espere 'Application startup complete' nos logs antes de avaliar."
        )

    itens = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    queimados = [item["id"] for item in itens if item.get("queimado")]
    if queimados:
        print(f"Aviso: {len(queimados)} item(ns) marcados como queimados (não é mais um resultado "
              f"limpo): {', '.join(queimados)}")

    acertos_por_rodada = []
    for rodada in range(1, args.rodadas + 1):
        if args.rodadas > 1:
            print(f"\n=== Rodada {rodada}/{args.rodadas} ===")
        resultados = rodar_rodada(itens, args)
        acertos, total = relatorio(resultados)
        acertos_por_rodada.append(acertos)

        saida = pasta / f"resultados-{time.strftime('%Y%m%d-%H%M%S')}.json"
        saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Respostas completas em: {saida}")

    if args.rodadas > 1 and total > 0:
        media = statistics.mean(acertos_por_rodada)
        desvio = statistics.pstdev(acertos_por_rodada)
        print(f"\n=== Variação entre as {args.rodadas} rodadas ===")
        print(f"Acertos por rodada: {acertos_por_rodada} (de {total})")
        print(f"Média: {media:.1f}/{total} · Desvio padrão: {desvio:.2f}")


if __name__ == "__main__":
    main()
