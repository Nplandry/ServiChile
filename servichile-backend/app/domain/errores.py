class NegocioNoEncontrado(Exception):
    pass

class NegocioYaReclamado(Exception):
    pass

class NoEsTitularDelNegocio(Exception):
    pass

class ReservaNoEncontrada(Exception):
    pass

class ReservaYaCerrada(Exception):
    pass

class NivelInsuficiente(Exception):

    def __init__(self, requiere: int) -> None:
        self.requiere = requiere

class ContrasenaIncorrecta(Exception):
    pass
