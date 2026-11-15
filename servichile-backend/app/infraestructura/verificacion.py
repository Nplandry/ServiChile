from app.dominio.puertos import VerificadorIdentidad


class MuestraVerificadorRut:
    def existe_y_activo(self, rut: str) -> bool:
        return True


def build_verificador_rut(nombre: str) -> VerificadorIdentidad:
    if nombre == "muestra":
        return MuestraVerificadorRut()
    raise ValueError(f"Verificador de RUT desconocido: {nombre}")
