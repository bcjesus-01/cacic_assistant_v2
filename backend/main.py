from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
import logging

logging.basicConfig(level=logging.DEBUG)
# Instância central da aplicação
app = FastAPI(
    title="CACIC Assistant API",
    description="Backend de Inteligência Artificial para o Centro Acadêmico",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acoplamos nossas rotas modulares na aplicação principal
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    # Inicia o servidor ASGI de alta performance
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
