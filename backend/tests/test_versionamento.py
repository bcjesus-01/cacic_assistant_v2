from versionamento import calcular_hash, carregar_manifesto, comparar, salvar_manifesto


def test_calcular_hash_eh_estavel_e_sensivel_ao_conteudo(tmp_path):
    arquivo = tmp_path / "a.pdf"
    arquivo.write_bytes(b"conteudo original")
    hash1 = calcular_hash(str(arquivo))
    assert hash1 == calcular_hash(str(arquivo))

    arquivo.write_bytes(b"conteudo mudou")
    assert calcular_hash(str(arquivo)) != hash1


def test_carregar_manifesto_inexistente_retorna_vazio(tmp_path):
    assert carregar_manifesto(str(tmp_path / "nao-existe.json")) == {}


def test_salvar_e_carregar_manifesto_ida_e_volta(tmp_path):
    caminho = str(tmp_path / "manifesto.json")
    manifesto = {"a.pdf": "abc123"}
    salvar_manifesto(caminho, manifesto)
    assert carregar_manifesto(caminho) == manifesto


def test_comparar_classifica_novo_sem_mudanca_mudou_e_removido(tmp_path):
    (tmp_path / "novo.pdf").write_bytes(b"novo")
    (tmp_path / "igual.pdf").write_bytes(b"nao mudou")
    (tmp_path / "editado.pdf").write_bytes(b"conteudo depois da edicao")
    (tmp_path / "ignorado.txt").write_bytes(b"nao eh pdf nem md")

    manifesto = {
        "igual.pdf": calcular_hash(str(tmp_path / "igual.pdf")),
        "editado.pdf": calcular_hash(str(tmp_path / "editado.pdf")),
        "sumiu.pdf": "hash-de-arquivo-que-nao-existe-mais",
    }
    (tmp_path / "editado.pdf").write_bytes(b"conteudo DEPOIS da edicao, mudou de verdade")

    resultado = comparar(str(tmp_path), manifesto)

    assert resultado["novos"] == ["novo.pdf"]
    assert resultado["mudaram"] == ["editado.pdf"]
    assert resultado["sem_mudanca"] == ["igual.pdf"]
    assert resultado["removidos"] == ["sumiu.pdf"]


def test_comparar_manifesto_vazio_marca_tudo_como_novo(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.md").write_bytes(b"b")

    resultado = comparar(str(tmp_path), {})

    assert resultado["novos"] == ["a.pdf", "b.md"]
    assert resultado["mudaram"] == []
    assert resultado["sem_mudanca"] == []
    assert resultado["removidos"] == []
