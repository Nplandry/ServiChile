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


class EmailYaRegistrado(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


class ReporteInvalido(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class PasaporteError(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class RutRechazado(PasaporteError):
    pass


class RutEnUso(PasaporteError):
    pass


class RutYaVerificado(PasaporteError):
    pass


class BiometriaInvalida(PasaporteError):
    pass


class BiometriaMuyGrande(PasaporteError):
    pass


class AntecedentesInvalido(PasaporteError):
    pass


class AntecedentesMuyGrande(PasaporteError):
    pass
