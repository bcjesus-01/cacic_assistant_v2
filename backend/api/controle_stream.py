"""Controle do fluxo de uma resposta em streaming (sem dependências externas).

Quando o modelo principal falha e o modelo de reserva assume, o LangChain inicia uma
nova chamada de modelo. Se a primeira já tinha enviado tokens ao aluno, a resposta da
reserva chegaria colada ao texto parcial. Este controle detecta o caso para que a rota
avise o frontend de que o texto deve ser reiniciado.
"""


class ControleStream:
    def __init__(self) -> None:
        self.inicios = 0  # quantas chamadas de modelo começaram nesta resposta
        self.tokens = 0  # quantos tokens já foram enviados ao cliente

    def iniciar_modelo(self) -> bool:
        """Registra o início de uma chamada de modelo.

        Retorna True se a chamada anterior já tinha enviado tokens, ou seja, se o texto
        parcial precisa ser descartado no cliente.
        """
        self.inicios += 1
        precisa_reiniciar = self.inicios > 1 and self.tokens > 0
        if precisa_reiniciar:
            self.tokens = 0
        return precisa_reiniciar

    def registrar_token(self) -> None:
        self.tokens += 1

    @property
    def reserva_acionada(self) -> bool:
        return self.inicios > 1
