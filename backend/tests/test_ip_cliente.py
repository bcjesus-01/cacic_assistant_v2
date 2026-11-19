from api.ip_cliente import extrair_ip


def test_usa_o_primeiro_ip_do_x_forwarded_for():
    assert extrair_ip("203.0.113.5", "172.18.0.1") == "203.0.113.5"


def test_x_forwarded_for_com_varios_ips_pega_o_primeiro():
    assert extrair_ip("203.0.113.5, 10.0.0.1, 172.18.0.1", "172.18.0.1") == "203.0.113.5"


def test_x_forwarded_for_vazio_cai_para_client_host():
    assert extrair_ip("", "172.18.0.1") == "172.18.0.1"


def test_sem_x_forwarded_for_usa_client_host():
    assert extrair_ip(None, "172.18.0.1") == "172.18.0.1"


def test_sem_nenhum_dos_dois_retorna_desconhecido():
    assert extrair_ip(None, None) == "desconhecido"
