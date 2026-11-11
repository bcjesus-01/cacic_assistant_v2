from types import SimpleNamespace

from agent.contexto import deduplicar, montar_contexto, nome_fonte, selecionar


def doc(texto, fonte="data/a.pdf"):
    return SimpleNamespace(page_content=texto, metadata={"fonte": fonte})


def test_remove_trecho_identico_de_outro_arquivo():
    docs = [doc("Art. 101 trancamento", "data/regimento.pdf"), doc("Art. 101 trancamento", "data/legislacao.pdf")]
    assert len(deduplicar(docs)) == 1


def test_ignora_espacos_e_maiusculas():
    docs = [doc("O  aluno\npode   trancar"), doc("o aluno pode trancar")]
    assert len(deduplicar(docs)) == 1


def test_remove_trecho_contido_em_outro():
    docs = [doc("Parágrafo único: segunda chamada em três dias úteis. Outro assunto."), doc("segunda chamada em três dias úteis")]
    assert len(deduplicar(docs)) == 1


def test_mantem_trechos_diferentes_e_a_ordem():
    docs = [doc("primeiro"), doc("segundo"), doc("terceiro")]
    assert [d.page_content for d in deduplicar(docs)] == ["primeiro", "segundo", "terceiro"]


def test_descarta_trecho_vazio():
    assert deduplicar([doc("   "), doc("conteúdo")])[0].page_content == "conteúdo"


def test_selecionar_aplica_limite_depois_do_dedup():
    docs = [doc("a"), doc("a"), doc("b"), doc("c"), doc("d")]
    assert [d.page_content for d in selecionar(docs, 3)] == ["a", "b", "c"]


def test_nome_fonte_legivel():
    assert nome_fonte({"fonte": "data/Perguntas_Frequentes_CACIC.pdf"}) == "Perguntas Frequentes CACIC"


def test_nome_fonte_ausente():
    assert nome_fonte(None) == "documento"
    assert nome_fonte({}) == "documento"


def test_montar_contexto_rotula_cada_trecho():
    texto = montar_contexto([doc("T1", "data/regimento.pdf"), doc("T2", "data/Estatuto_CACIC.pdf")])
    assert texto == "[Fonte: regimento]\nT1\n\n[Fonte: Estatuto CACIC]\nT2"
