import pytest

from agent.roteamento import escolher_destino


@pytest.mark.parametrize(
    "texto",
    [
        "oi",
        "OI",
        "Olá!",
        "bom dia",
        "Boa tarde",
        "boa noite!",
        "oi, tudo bem?",
        "obrigado",
        "Muito obrigada!",
        "valeu",
        "tchau",
        "até logo",
        "e aí",
    ],
)
def test_saudacoes_e_agradecimentos_vao_para_conversa_geral(texto):
    assert escolher_destino(texto) == "conversa_geral"


@pytest.mark.parametrize(
    "texto",
    [
        "Quantas horas de ACC preciso cumprir?",
        "qual o prazo do TCC",
        "Qual o pré-requisito de Estrutura de Dados?",
        # saudação seguida de pergunta: não pode cair na conversa geral
        "oi qual o prazo",
        "oi qual o prazo do TCC",
        "bom dia, como funciona o estágio?",
        # pergunta de acompanhamento curta
        "e quantas horas?",
        # entradas sem conteúdo: seguem para o RAG, que tem a rota de fuga no prompt
        "",
        "   ",
        "???",
    ],
)
def test_demais_mensagens_vao_para_o_rag(texto):
    assert escolher_destino(texto) == "rag_academico"


def test_mensagem_social_longa_demais_vai_para_o_rag():
    # Limite documentado: mais de 5 palavras deixa de ser tratada como saudação
    assert escolher_destino("bom dia bom dia bom dia bom dia bom dia bom dia") == "rag_academico"
