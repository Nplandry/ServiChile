from app.domain.puertos import VerificadorIdentidad


class FakeVerificadorRut:
    def existe_y_activo(self, rut: str) -> bool:
        return True


def build_verificador_rut(nombre: str) -> VerificadorIdentidad:
    if nombre == "fake":
        return FakeVerificadorRut()
    raise ValueError(f"Verificador de RUT desconocido: {nombre}")
