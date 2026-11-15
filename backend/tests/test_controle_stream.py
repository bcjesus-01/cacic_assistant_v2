from api.controle_stream import ControleStream


def test_resposta_normal_nao_reinicia():
    c = ControleStream()
    assert c.iniciar_modelo() is False
    c.registrar_token()
    c.registrar_token()
    assert c.reserva_acionada is False


def test_falha_antes_do_primeiro_token_nao_reinicia():
    c = ControleStream()
    c.iniciar_modelo()  # principal falha sem enviar nada
    assert c.iniciar_modelo() is False  # a reserva assume
    assert c.reserva_acionada is True


def test_falha_depois_de_tokens_pede_reinicio():
    c = ControleStream()
    c.iniciar_modelo()
    c.registrar_token()
    assert c.iniciar_modelo() is True


def test_reinicio_zera_a_contagem_de_tokens():
    c = ControleStream()
    c.iniciar_modelo()
    c.registrar_token()
    c.iniciar_modelo()  # reinicia
    # uma terceira chamada sem tokens novos não pede outro reinício
    assert c.iniciar_modelo() is False
    c.registrar_token()
    assert c.iniciar_modelo() is True
