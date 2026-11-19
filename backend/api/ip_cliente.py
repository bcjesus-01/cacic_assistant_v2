"""Extrai o IP do cliente a partir dos headers da requisição (lógica pura, sem FastAPI).

Pegar o primeiro IP do X-Forwarded-For só é seguro porque o Caddy (único ponto de entrada em
produção, ver Caddyfile) não tem `trusted_proxies` configurado: por padrão ele ignora qualquer
X-Forwarded-For que o cliente mandou e escreve de novo só com o IP real da conexão TCP. Se um
dia entrar outro proxy/CDN na frente do Caddy, revisar isto.
"""


def extrair_ip(forwarded_for: str | None, client_host: str | None) -> str:
    if forwarded_for:
        primeiro = forwarded_for.split(",")[0].strip()
        if primeiro:
            return primeiro
    return client_host or "desconhecido"
