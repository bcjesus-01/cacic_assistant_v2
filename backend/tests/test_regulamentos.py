from regulamentos import secoes_por_artigo


def test_divide_em_artigos_numerados():
    texto = "Art. 1 - Primeira regra.\nArt. 2 - Segunda regra."
    assert secoes_por_artigo(texto) == ["Art. 1 - Primeira regra.", "Art. 2 - Segunda regra."]


def test_divide_em_artigo_com_palavra_completa():
    texto = "Artigo 1 - Primeira regra.\nArtigo 2 - Segunda regra."
    assert secoes_por_artigo(texto) == ["Artigo 1 - Primeira regra.", "Artigo 2 - Segunda regra."]


def test_divide_em_paragrafos():
    texto = "Art. 3 - Regra geral.\n§ 1º - Primeira exceção.\n§ 2º - Segunda exceção."
    assert secoes_por_artigo(texto) == [
        "Art. 3 - Regra geral.",
        "§ 1º - Primeira exceção.",
        "§ 2º - Segunda exceção.",
    ]


def test_divide_em_cabecalho_numerado_com_negrito():
    texto = "#### **5. DOS VALORES**\nTexto da seção 5.\n#### **6. DAS INSCRIÇÕES**\nTexto da seção 6."
    assert secoes_por_artigo(texto) == [
        "#### **5. DOS VALORES**\nTexto da seção 5.",
        "#### **6. DAS INSCRIÇÕES**\nTexto da seção 6.",
    ]


def test_divide_em_cabecalho_numerado_sem_negrito():
    texto = "#### 5. DOS VALORES\nTexto da seção 5."
    assert secoes_por_artigo(texto) == ["#### 5. DOS VALORES\nTexto da seção 5."]


def test_divide_em_cabecalho_sem_numero():
    # legislacao_graduacao.pdf é uma coletânea de resoluções concatenadas: o fim de um
    # artigo não pode ficar colado ao cabeçalho (sem número) da resolução seguinte.
    texto = "Art. 179 - Regra do artigo.\n## **MATRÍCULA**\nTexto de outra resolução."
    assert secoes_por_artigo(texto) == [
        "Art. 179 - Regra do artigo.",
        "## **MATRÍCULA**\nTexto de outra resolução.",
    ]


def test_texto_sem_marcador_vira_uma_secao_so():
    texto = "Preâmbulo sem nenhum artigo numerado."
    assert secoes_por_artigo(texto) == ["Preâmbulo sem nenhum artigo numerado."]


def test_ignora_linhas_e_secoes_vazias():
    texto = "\n\nArt. 1 - Regra.\n\n\n"
    assert secoes_por_artigo(texto) == ["Art. 1 - Regra."]


def test_preambulo_antes_do_primeiro_artigo_fica_na_propria_secao():
    texto = "Preâmbulo introdutório.\nArt. 1 - Primeira regra."
    assert secoes_por_artigo(texto) == ["Preâmbulo introdutório.", "Art. 1 - Primeira regra."]
