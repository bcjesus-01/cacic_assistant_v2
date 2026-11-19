"""Detecta se um documento em data/ mudou desde a última vez que foi indexado.

Módulo puro (só hashlib/json/os) pra poder ser testado sem Qdrant nem Gemini. O manifesto é
um JSON simples {nome_do_arquivo: hash_sha256}, guardado em data/ (já ignorado no git).
"""

import hashlib
import json
import os


def calcular_hash(caminho: str) -> str:
    sha256 = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)
    return sha256.hexdigest()


def carregar_manifesto(caminho: str) -> dict:
    if not os.path.exists(caminho):
        return {}
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_manifesto(caminho: str, manifesto: dict) -> None:
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(manifesto, arquivo, indent=2, ensure_ascii=False, sort_keys=True)


def comparar(diretorio: str, manifesto: dict, extensoes: tuple[str, ...] = (".pdf", ".md")) -> dict:
    atuais = {
        nome
        for nome in os.listdir(diretorio)
        if nome.lower().endswith(extensoes) and not nome.startswith(".")
    }
    conhecidos = set(manifesto)

    novos = sorted(atuais - conhecidos)
    removidos = sorted(conhecidos - atuais)
    mudaram = []
    sem_mudanca = []
    for nome in sorted(atuais & conhecidos):
        hash_atual = calcular_hash(os.path.join(diretorio, nome))
        if hash_atual != manifesto[nome]:
            mudaram.append(nome)
        else:
            sem_mudanca.append(nome)

    return {
        "novos": novos,
        "mudaram": mudaram,
        "sem_mudanca": sem_mudanca,
        "removidos": removidos,
    }
