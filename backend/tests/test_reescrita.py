from types import SimpleNamespace

from agent.reescrita import deve_reescrever, limpar_reescrita, montar_historico_textual


def msg(tipo, conteudo):
    return SimpleNamespace(type=tipo, content=conteudo)


def test_nao_reescreve_na_primeira_mensagem():
    assert deve_reescrever([msg("human", "oi")]) is False


def test_reescreve_quando_ha_historico():
    assert deve_reescrever([msg("human", "oi"), msg("ai", "olá!"), msg("human", "e aí?")]) is True


def test_historico_textual_rotula_aluno_e_assistente_na_ordem():
    mensagens = [
        msg("human", "Quantas horas complementares preciso na matriz 2023?"),
        msg("ai", "120 horas complementares."),
        msg("human", "E para a matriz 2012?"),
    ]
    assert montar_historico_textual(mensagens) == (
        "Aluno: Quantas horas complementares preciso na matriz 2023?\n"
        "Assistente: 120 horas complementares."
    )


def test_historico_textual_ignora_mensagens_vazias():
    mensagens = [msg("human", "   "), msg("ai", "oi"), msg("human", "pergunta atual")]
    assert montar_historico_textual(mensagens) == "Assistente: oi"


def test_historico_textual_sem_mensagens_anteriores_fica_vazio():
    assert montar_historico_textual([msg("human", "pergunta única")]) == ""


def test_historico_textual_aceita_blocos_de_conteudo():
    mensagens = [
        msg("ai", [{"type": "text", "text": "120 horas."}]),
        msg("human", "pergunta atual"),
    ]
    assert montar_historico_textual(mensagens) == "Assistente: 120 horas."


def test_limpar_reescrita_tira_aspas_e_espacos():
    assert limpar_reescrita('  "Qual o prazo do TCC?"  ', "original") == "Qual o prazo do TCC?"


def test_limpar_reescrita_cai_para_original_se_vazia():
    assert limpar_reescrita("   ", "pergunta original") == "pergunta original"
    assert limpar_reescrita("", "pergunta original") == "pergunta original"


def test_limpar_reescrita_cai_para_original_se_saida_absurdamente_longa():
    saida_suspeita = "x" * 501
    assert limpar_reescrita(saida_suspeita, "pergunta original") == "pergunta original"


def test_limpar_reescrita_aceita_blocos_de_conteudo():
    blocos = [{"type": "text", "text": "Qual o prazo do TCC?"}]
    assert limpar_reescrita(blocos, "original") == "Qual o prazo do TCC?"
