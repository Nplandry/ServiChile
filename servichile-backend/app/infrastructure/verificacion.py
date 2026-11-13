from typing import Protocol

class VerificadorRut(Protocol):

    def existe_y_activo(self, rut: str) -> bool:
        ...

class FakeVerificadorRut:

    def existe_y_activo(self, rut: str) -> bool:
        return True

def build_verificador_rut(nombre: str) -> VerificadorRut:
    if nombre == 'fake':
        return FakeVerificadorRut()
    raise ValueError(f'Verificador de RUT desconocido: {nombre}')
