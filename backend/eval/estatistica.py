"""Intervalo de confiança para a taxa de acerto da avaliação (lógica pura, só biblioteca
padrão — mesma convenção de agent/contexto.py e api/controle_stream.py).

Com poucos itens (15-20, caso do conjunto held-out), a taxa simples (acertos/total) sozinha
é enganosa: o intervalo de Wilson mostra a faixa plausível do valor real.
"""

from statistics import NormalDist


def intervalo_wilson(acertos: int, total: int, confianca: float = 0.95) -> tuple[float, float]:
    """Intervalo de confiança de Wilson para uma proporção (acertos/total).

    Retorna (limite_inferior, limite_superior), ambos em [0, 1].
    """
    if total <= 0:
        raise ValueError("total deve ser maior que zero")
    if not 0 <= acertos <= total:
        raise ValueError("acertos deve estar entre 0 e total")

    z = NormalDist().inv_cdf(1 - (1 - confianca) / 2)
    n = total
    p = acertos / n

    denominador = 1 + z**2 / n
    centro = p + z**2 / (2 * n)
    ajuste = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5)

    inferior = (centro - ajuste) / denominador
    superior = (centro + ajuste) / denominador
    return max(0.0, inferior), min(1.0, superior)
