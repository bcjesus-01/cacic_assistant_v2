from eval.classificar_erros import documento_esta_na_base, fatos_presentes


def test_documento_esta_na_base_reconhece_citacao_legivel():
    # fonte_gabarito cita o documento em texto legível, não o caminho bruto do arquivo.
    fontes = {"data/legislacao_graduacao.pdf", "data/regimento.pdf", "data/FAQ_CACIC.md"}
    assert documento_esta_na_base(
        "Coletânea da Legislação da Graduação (2016), Resolução CONSEPE 014/1996", fontes
    )


def test_documento_esta_na_base_nao_confunde_documentos_diferentes():
    fontes = {"data/Edital_Mais_Futuro_Auxilio_Permanencia.pdf"}
    assert not documento_esta_na_base("Edital SEC nº 15/2026 (Mais Futuro), item 5", fontes)


def test_documento_esta_na_base_sem_fontes_e_falso():
    assert not documento_esta_na_base("Regimento Geral da UESC, art. 1", set())


def test_fatos_presentes_exige_todos_os_grupos():
    fatos = [["120"], ["80"]]
    assert fatos_presentes(fatos, "a matriz 2023 exige 120 horas e 80 horas de extensao")
    assert not fatos_presentes(fatos, "a matriz 2023 exige 120 horas complementares")
