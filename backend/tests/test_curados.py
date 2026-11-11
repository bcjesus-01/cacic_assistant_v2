from pathlib import Path

import pytest

from curados import secoes_markdown

FAQ = Path(__file__).resolve().parents[2] / "docs" / "FAQ_CACIC.md"


def test_divide_nas_linhas_de_separador():
    assert secoes_markdown("A\n\n---\n\nB\n---\nC") == ["A", "B", "C"]


def test_remove_comentarios_html():
    assert secoes_markdown("<!-- nota\nmultilinha -->\n\nA\n---\nB") == ["A", "B"]


def test_descarta_secoes_vazias_e_espacos():
    assert secoes_markdown("\n---\n  A  \n---\n\n---\n") == ["A"]


def test_sem_separador_vira_uma_secao():
    assert secoes_markdown("só um bloco") == ["só um bloco"]


def test_hifen_no_meio_da_linha_nao_separa():
    assert secoes_markdown("a --- b") == ["a --- b"]


@pytest.mark.skipif(not FAQ.exists(), reason="docs/FAQ_CACIC.md ausente")
def test_faq_tem_pergunta_e_resposta_em_cada_secao():
    secoes = secoes_markdown(FAQ.read_text(encoding="utf-8"))
    assert len(secoes) >= 20
    for s in secoes:
        assert s.startswith("Pergunta:"), s[:60]
        assert "\nResposta:" in s, s[:60]
        assert len(s) <= 1500, f"seção longa demais: {s[:60]}"
