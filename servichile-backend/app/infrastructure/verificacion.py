"""Adaptadores de verificación del Pasaporte: consulta de RUT.

Las implementaciones reales (proveedor de identidad) se enchufan aquí sin tocar
los servicios. Por ahora solo existe la implementación falsa, que no envía datos
a ningún tercero.
"""
from typing import Protocol


class VerificadorRut(Protocol):
    def existe_y_activo(self, rut: str) -> bool:
        """Confirma que el RUT (ya normalizado y con DV válido) existe y está activo."""
        ...


class FakeVerificadorRut:
    """Acepta cualquier RUT con dígito verificador válido. Solo para desarrollo y pruebas."""

    def existe_y_activo(self, rut: str) -> bool:
        return True


def build_verificador_rut(nombre: str) -> VerificadorRut:
    """Selecciona el verificador de RUT según la configuración. Agregar aquí el proveedor real."""
    if nombre == "fake":
        return FakeVerificadorRut()
    raise ValueError(f"Verificador de RUT desconocido: {nombre}")
