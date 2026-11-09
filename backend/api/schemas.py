from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # O cliente gera um identificador por sessão (UUID); limitamos formato e tamanho.
    thread_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    message: str = Field(min_length=1, max_length=2000)
