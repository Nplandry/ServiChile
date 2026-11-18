class NegocioNoEncontrado(Exception):
    pass


class NoEsTitularDelNegocio(Exception):
    pass


class TrabajoNoEncontrado(Exception):
    pass


class TrabajoYaCerrado(Exception):
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


class ReporteError(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class RutRechazado(ReporteError):
    pass


class RutEnUso(ReporteError):
    pass


class RutYaVerificado(ReporteError):
    pass


class BiometriaInvalida(ReporteError):
    pass


class BiometriaMuyGrande(ReporteError):
    pass


class AntecedentesInvalido(ReporteError):
    pass


class AntecedentesMuyGrande(ReporteError):
    pass


class CedulaInvalida(ReporteError):
    pass


class CedulaMuyGrande(ReporteError):
    pass


class AvalInvalido(ReporteError):
    pass


class AvalMuyGrande(ReporteError):
    pass


class DocEmpresaInvalido(ReporteError):
    pass


class DocEmpresaMuyGrande(ReporteError):
    pass


class EvaluadorIndisponible(Exception):
    def __init__(
        self, mensaje: str = "No se pudo refrescar el índice de señales."
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
