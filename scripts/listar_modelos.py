"""Lista os modelos do Gemini disponíveis para a sua chave de API.

Uso:
    GOOGLE_API_KEY=sua_chave python scripts/listar_modelos.py

Usa só a biblioteca padrão do Python (não precisa instalar nada).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"


def main() -> int:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Defina a variável de ambiente GOOGLE_API_KEY antes de executar.")
        return 1

    modelos: list[dict] = []
    pagina = ""
    while True:
        url = URL + (f"&pageToken={urllib.parse.quote(pagina)}" if pagina else "")
        requisicao = urllib.request.Request(url, headers={"x-goog-api-key": api_key})
        try:
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                dados = json.load(resposta)
        except urllib.error.HTTPError as erro:
            print(f"Erro da API: HTTP {erro.code}")
            return 1
        except urllib.error.URLError as erro:
            print(f"Erro de conexão: {erro.reason}")
            return 1

        modelos += dados.get("models", [])
        pagina = dados.get("nextPageToken", "")
        if not pagina:
            break

    for modelo in modelos:
        if "generateContent" in modelo.get("supportedGenerationMethods", []):
            print(modelo["name"])
            print(f"  {modelo.get('description', '')}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
