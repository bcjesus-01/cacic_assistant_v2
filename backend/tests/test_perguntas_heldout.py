import json
from pathlib import Path

from eval.validar_heldout import validar_itens

PASTA_EVAL = Path(__file__).parent.parent / "eval"


def item_valido(**sobrescreve):
    base = {
        "id": "ho-base",
        "categoria": "Horas complementares",
        "tipo": "resposta",
        "origem": "bruno",
        "fonte_gabarito": "data/regimento.pdf, art. 1",
        "pergunta": "Quantas horas complementares preciso cumprir na matriz 2023?",
        "esperado": "120 horas complementares.",
        "fatos": [["120"]],
        "queimado": False,
    }
    base.update(sobrescreve)
    return base


def test_arquivo_real_held_out_e_valido():
    """O arquivo real (vazio, ou já preenchido) nunca pode ter problemas pendentes."""
    heldout = json.loads((PASTA_EVAL / "perguntas_heldout.json").read_text(encoding="utf-8"))
    dev = json.loads((PASTA_EVAL / "perguntas.json").read_text(encoding="utf-8"))
    assert validar_itens(heldout, dev) == []


def test_item_valido_nao_gera_problema():
    assert validar_itens([item_valido()], []) == []


def test_detecta_campo_obrigatorio_faltando():
    item = item_valido()
    del item["fonte_gabarito"]
    problemas = validar_itens([item], [])
    assert any("campos faltando" in p for p in problemas)


def test_detecta_fonte_gabarito_vazia():
    problemas = validar_itens([item_valido(fonte_gabarito="   ")], [])
    assert any("fonte_gabarito" in p for p in problemas)


def test_detecta_tipo_invalido():
    problemas = validar_itens([item_valido(tipo="afirmacao")], [])
    assert any("tipo inválido" in p for p in problemas)


def test_detecta_origem_invalida():
    problemas = validar_itens([item_valido(origem="professor")], [])
    assert any("origem inválida" in p for p in problemas)


def test_resposta_sem_fatos_e_invalida():
    item = item_valido()
    del item["fatos"]
    problemas = validar_itens([item], [])
    assert any("fatos" in p for p in problemas)


def test_recusa_nao_precisa_de_fatos():
    item = item_valido(tipo="recusa")
    del item["fatos"]
    assert validar_itens([item], []) == []


def test_conversa_precisa_ser_lista_de_strings():
    problemas = validar_itens([item_valido(conversa="não é lista")], [])
    assert any("conversa" in p for p in problemas)


def test_detecta_id_duplicado_dentro_do_held_out():
    itens = [item_valido(id="ho-1", pergunta="Pergunta A?"), item_valido(id="ho-1", pergunta="Pergunta B?")]
    problemas = validar_itens(itens, [])
    assert any("id duplicado" in p for p in problemas)


def test_detecta_id_colidindo_com_conjunto_de_desenvolvimento():
    heldout = [item_valido(id="mf-quem")]
    dev = [item_valido(id="mf-quem", pergunta="Outra pergunta qualquer, bem diferente.")]
    problemas = validar_itens(heldout, dev)
    assert any("já usado no conjunto de desenvolvimento" in p for p in problemas)


def test_detecta_pergunta_quase_igual_ao_conjunto_de_desenvolvimento():
    dev = [item_valido(id="dev-1", pergunta="Quantas horas complementares preciso cumprir na matriz 2023?")]
    heldout = [item_valido(id="ho-1", pergunta="Quantas horas complementares eu preciso cumprir na matriz 2023?")]
    problemas = validar_itens(heldout, dev)
    assert any("quase igual" in p for p in problemas)


def test_perguntas_bem_diferentes_nao_sao_marcadas():
    dev = [item_valido(id="dev-1", pergunta="Qual é o telefone do reitor?")]
    heldout = [item_valido(id="ho-1", pergunta="Como funciona o pedido de camisas do CACIC?")]
    assert validar_itens(heldout, dev) == []
