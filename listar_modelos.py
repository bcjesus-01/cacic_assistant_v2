import os
import google.generativeai as genai

# Pega a chave da sua variável de ambiente (ou coloque-a diretamente aqui como string para testar)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "COLE_SUA_CHAVE_AQUI_SE_PRECISAR")

genai.configure(api_key=GOOGLE_API_KEY)

print("Buscando modelos disponíveis para a sua API Key...\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Nome do Modelo: {m.name}")
            print(f"Descrição: {m.description}\n")
except Exception as e:
    print(f"Erro ao acessar a API: {e}")
