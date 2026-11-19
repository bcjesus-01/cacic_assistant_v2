"""Compara os documentos em data/ contra o manifesto de hash e relata diferenças.

Só leitura: não reindexa nada, não decide nada. Serve pra saber se algum PDF/MD mudou desde
a última vez que etl_pipeline.py ou adicionar_docs.py o processaram (ambos atualizam o
manifesto automaticamente ao indexar com sucesso).

Uso (a partir de backend/):
    uv run python verificar_documentos.py
"""

from versionamento import carregar_manifesto, comparar

DIRETORIO_DADOS = "data"
MANIFESTO = "data/.manifesto_documentos.json"


def main() -> None:
    manifesto = carregar_manifesto(MANIFESTO)
    resultado = comparar(DIRETORIO_DADOS, manifesto)

    if resultado["novos"]:
        print(f"Novos (nunca indexados) — {len(resultado['novos'])}:")
        for nome in resultado["novos"]:
            print(f"  {nome}")

    if resultado["mudaram"]:
        print(f"Mudaram desde a última indexação — {len(resultado['mudaram'])}:")
        for nome in resultado["mudaram"]:
            print(f"  {nome}")

    if resultado["removidos"]:
        print(f"No manifesto, mas o arquivo não existe mais em data/ — {len(resultado['removidos'])}:")
        for nome in resultado["removidos"]:
            print(f"  {nome}")

    if not resultado["novos"] and not resultado["mudaram"] and not resultado["removidos"]:
        print(f"Tudo em dia: {len(resultado['sem_mudanca'])} documento(s) sem mudança.")


if __name__ == "__main__":
    main()
