import json

from api.sse import DONE, MENSAGEM_ERRO, extrair_texto, sse


def test_extrair_texto_de_string():
    assert extrair_texto("oi") == "oi"


def test_extrair_texto_de_blocos_do_gemini():
    blocos = [{"type": "text", "text": "Olá "}, {"type": "text", "text": "mundo"}]
    assert extrair_texto(blocos) == "Olá mundo"


def test_extrair_texto_ignora_blocos_que_nao_sao_texto():
    blocos = [{"type": "thinking", "text": "raciocínio interno"}, "!", {"type": "text"}]
    assert extrair_texto(blocos) == "!"


def test_extrair_texto_de_tipos_desconhecidos():
    assert extrair_texto(None) == ""
    assert extrair_texto(123) == ""
    assert extrair_texto({"type": "text", "text": "x"}) == ""


def test_sse_escapa_quebras_de_linha_e_preserva_acentos():
    assert sse("a\nb") == 'data: "a\\nb"\n\n'
    assert sse("ação") == 'data: "ação"\n\n'


def test_sse_com_evento_nomeado():
    assert sse("falhou", event="error") == 'event: error\ndata: "falhou"\n\n'


def test_token_literal_done_nao_confunde_o_cliente():
    # O token vai entre aspas (JSON), então nunca é igual ao sinal de fim "[DONE]"
    assert sse("[DONE]") == 'data: "[DONE]"\n\n'
    assert sse("[DONE]") != DONE


def test_mensagem_de_erro_nao_expoe_detalhes_tecnicos():
    for termo in ("Traceback", "psycopg", "postgresql", "Exception"):
        assert termo not in MENSAGEM_ERRO


def _parse_sse(texto: str) -> list[tuple[str, str]]:
    """Mini-parser que segue a mesma regra do frontend (app/page.tsx)."""
    eventos = []
    for bloco in texto.split("\n\n"):
        if not bloco.strip():
            continue
        nome, dados = "message", []
        for linha in bloco.split("\n"):
            if linha.startswith("event:"):
                nome = linha[6:].strip()
            elif linha.startswith("data:"):
                valor = linha[5:]
                dados.append(valor[1:] if valor.startswith(" ") else valor)
        eventos.append((nome, "\n".join(dados)))
    return eventos


def test_stream_completo_reconstroi_a_resposta_original():
    tokens = ["Olá", ", ", "ação\nlinha 2", ' com "aspas"', "a\r\nb", "\\n literal", "[DONE]"]
    stream = "".join(sse(t) for t in tokens) + DONE

    eventos = _parse_sse(stream)

    assert eventos[-1] == ("message", "[DONE]")
    texto = "".join(json.loads(dados) for _, dados in eventos[:-1])
    assert texto == "".join(tokens)


def test_stream_com_erro_termina_com_done():
    stream = sse("parcial") + sse(MENSAGEM_ERRO, event="error") + DONE

    eventos = _parse_sse(stream)

    assert [nome for nome, _ in eventos] == ["message", "error", "message"]
    assert json.loads(eventos[1][1]) == MENSAGEM_ERRO
    assert eventos[-1][1] == "[DONE]"
