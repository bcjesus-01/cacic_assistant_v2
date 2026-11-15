import pytest

from eval.estatistica import intervalo_wilson


def test_zero_acertos_limite_inferior_e_zero():
    inferior, superior = intervalo_wilson(0, 10)
    assert inferior == pytest.approx(0.0, abs=1e-9)
    assert 0.0 < superior < 1.0


def test_todos_acertos_limite_superior_e_um():
    inferior, superior = intervalo_wilson(10, 10)
    assert superior == pytest.approx(1.0, abs=1e-9)
    assert 0.0 < inferior < 1.0


def test_intervalo_contem_a_taxa_simples():
    inferior, superior = intervalo_wilson(7, 8)
    assert inferior < 7 / 8 < superior


def test_poucos_itens_da_intervalo_mais_largo_que_muitos_itens():
    inferior_poucos, superior_poucos = intervalo_wilson(7, 8)
    inferior_muitos, superior_muitos = intervalo_wilson(700, 800)
    largura_poucos = superior_poucos - inferior_poucos
    largura_muitos = superior_muitos - inferior_muitos
    assert largura_poucos > largura_muitos


def test_confianca_maior_da_intervalo_mais_largo():
    inferior_95, superior_95 = intervalo_wilson(7, 8, confianca=0.95)
    inferior_99, superior_99 = intervalo_wilson(7, 8, confianca=0.99)
    assert (superior_99 - inferior_99) > (superior_95 - inferior_95)


def test_total_zero_levanta_erro():
    with pytest.raises(ValueError):
        intervalo_wilson(0, 0)


def test_acertos_fora_do_intervalo_valido_levanta_erro():
    with pytest.raises(ValueError):
        intervalo_wilson(11, 10)
    with pytest.raises(ValueError):
        intervalo_wilson(-1, 10)
