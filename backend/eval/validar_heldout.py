"""Valida o conjunto de avaliação held-out (lógica pura, só biblioteca padrão — mesma
convenção de agent/contexto.py e api/controle_stream.py).

Verifica: esquema de cada item, ids únicos (no held-out e contra o conjunto de
desenvolvimento) e nenhuma pergunta repetida ou quase igual a uma do conjunto de
desenvolvimento (held-out só vale se o sistema nunca viu a pergunta).

Uso (a partir de backend/):
    uv run python eval/validar_heldout.py
"""

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

LIMIAR_QUASE_IGUAL = 0.85  # razão do SequenceMatcher acima disso é tratado como "repetida"

CAMPOS_OBRIGATORIOS = {"id", "categoria", "tipo", "pergunta", "fonte_gabarito", "origem"}
TIPOS_VALIDOS = {"resposta", "recusa"}
ORIGENS_VALIDAS = {"aluno", "bruno"}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def _quase_igual(a: str, b: str) -> bool:
    return SequenceMatcher(None, _normalizar(a), _normalizar(b)).ratio() >= LIMIAR_QUASE_IGUAL


def _validar_esquema_item(item: dict) -> list[str]:
    problemas = []
    faltando = CAMPOS_OBRIGATORIOS - item.keys()
    if faltando:
        problemas.append(f"campos faltando: {sorted(faltando)}")
        return problemas  # sem os campos básicos, não dá para checar o resto

    if item["tipo"] not in TIPOS_VALIDOS:
        problemas.append(f"tipo inválido: {item['tipo']!r} (esperado {TIPOS_VALIDOS})")
    if item["origem"] not in ORIGENS_VALIDAS:
        problemas.append(f"origem inválida: {item['origem']!r} (esperado {ORIGENS_VALIDAS})")
    if not isinstance(item.get("fonte_gabarito"), str) or not item["fonte_gabarito"].strip():
        problemas.append("fonte_gabarito vazia ou ausente")
    if "queimado" in item and not isinstance(item["queimado"], bool):
        problemas.append(f"queimado deveria ser booleano, veio {item['queimado']!r}")

    if item["tipo"] == "resposta":
        fatos = item.get("fatos")
        if not fatos or not isinstance(fatos, list):
            problemas.append("tipo 'resposta' precisa do campo 'fatos' (lista não vazia)")
        elif any(not grupo for grupo in fatos):
            problemas.append("'fatos' tem um grupo vazio")

    conversa = item.get("conversa")
    if conversa is not None and (
        not isinstance(conversa, list) or not all(isinstance(m, str) for m in conversa)
    ):
        problemas.append("'conversa' precisa ser uma lista de strings")

    return problemas


def validar_itens(heldout: list[dict], dev: list[dict]) -> list[str]:
    """Devolve a lista de problemas encontrados (vazia = conjunto válido)."""
    problemas: list[str] = []

    for item in heldout:
        ident = item.get("id", "<sem id>")
        for problema in _validar_esquema_item(item):
            problemas.append(f"[{ident}] {problema}")

    ids_heldout = [item.get("id") for item in heldout]
    for id_duplicado in {i for i in ids_heldout if ids_heldout.count(i) > 1}:
        problemas.append(f"id duplicado dentro do held-out: {id_duplicado!r}")

    ids_dev = {item.get("id") for item in dev}
    for id_colidindo in set(ids_heldout) & ids_dev:
        problemas.append(f"id já usado no conjunto de desenvolvimento: {id_colidindo!r}")

    for item in heldout:
        pergunta = item.get("pergunta", "")
        if not pergunta:
            continue
        for outro in dev:
            if _quase_igual(pergunta, outro.get("pergunta", "")):
                problemas.append(
                    f"[{item.get('id')}] pergunta quase igual à do conjunto de desenvolvimento "
                    f"{outro.get('id')!r}: {pergunta!r}"
                )
        for outro in heldout:
            if outro is not item and _quase_igual(pergunta, outro.get("pergunta", "")):
                problemas.append(
                    f"[{item.get('id')}] pergunta quase igual a outro item do held-out "
                    f"{outro.get('id')!r}: {pergunta!r}"
                )

    return problemas


def main() -> None:
    pasta = Path(__file__).parent
    heldout = json.loads((pasta / "perguntas_heldout.json").read_text(encoding="utf-8"))
    dev = json.loads((pasta / "perguntas.json").read_text(encoding="utf-8"))

    problemas = validar_itens(heldout, dev)
    print(f"{len(heldout)} item(ns) no held-out, {len(dev)} no conjunto de desenvolvimento.")
    if problemas:
        print(f"\n{len(problemas)} problema(s) encontrado(s):")
        for p in problemas:
            print(f"  - {p}")
        raise SystemExit(1)
    print("OK: nenhum problema encontrado.")


if __name__ == "__main__":
    main()
