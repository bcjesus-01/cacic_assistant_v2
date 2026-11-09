import pytest
from pydantic import ValidationError

from api.schemas import ChatRequest

UUID = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"


@pytest.mark.parametrize(
    "thread_id",
    [UUID, "cacic-sessao-1", "lt3k9x2a-ab12cd34ef", "a" * 8, "a" * 64],
)
def test_thread_id_valido(thread_id):
    assert ChatRequest(thread_id=thread_id, message="oi").thread_id == thread_id


@pytest.mark.parametrize(
    "thread_id",
    [
        "curto",  # menos de 8 caracteres
        "a" * 65,  # mais de 64 caracteres
        "com espaço 12345",
        "../../etc/passwd",
        "id;DROP TABLE x",
        "",
    ],
)
def test_thread_id_invalido(thread_id):
    with pytest.raises(ValidationError):
        ChatRequest(thread_id=thread_id, message="oi")


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_message_fora_do_limite(message):
    with pytest.raises(ValidationError):
        ChatRequest(thread_id=UUID, message=message)


def test_message_no_limite_e_aceita():
    assert len(ChatRequest(thread_id=UUID, message="x" * 2000).message) == 2000


def test_contrato_antigo_do_frontend_e_rejeitado():
    # Campos de versões antigas do frontend ("pergunta", "session_id") não servem mais
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"pergunta": "oi", "session_id": "sessao_estudante_1"})
