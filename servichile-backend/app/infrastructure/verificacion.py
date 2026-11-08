"""Adaptadores de verificación del Pasaporte: consulta de RUT y extracción de datos de PDF.

Las implementaciones reales (proveedor de identidad, Gemini) se enchufan aquí sin tocar
los servicios. Por ahora solo existen las implementaciones falsas, que no envían datos
a ningún tercero.
"""
from typing import Protocol

from app.domain.pasaporte import MetricasFinancieras


class VerificadorRut(Protocol):
    def existe_y_activo(self, rut: str) -> bool:
        """Confirma que el RUT (ya normalizado y con DV válido) existe y está activo."""
        ...


class ExtractorFinanciero(Protocol):
    def extraer(self, contenido: bytes) -> MetricasFinancieras:
        """Lee el PDF en memoria y devuelve solo las métricas. Lanza ExtraccionFallida si no puede leerlo."""
        ...


class FakeVerificadorRut:
    """Acepta cualquier RUT con dígito verificador válido. Solo para desarrollo y pruebas."""

    def existe_y_activo(self, rut: str) -> bool:
        return True


class FakeExtractorFinanciero:
    """Devuelve métricas fijas sin leer el documento. Solo para desarrollo y pruebas."""

    def extraer(self, contenido: bytes) -> MetricasFinancieras:
        return MetricasFinancieras(ingreso_liquido=1_000_000, deudas_mensuales=200_000, morosidad_dicom=False)


def build_verificador_rut(nombre: str) -> VerificadorRut:
    """Selecciona el verificador de RUT según la configuración. Agregar aquí el proveedor real."""
    if nombre == "fake":
        return FakeVerificadorRut()
    raise ValueError(f"Verificador de RUT desconocido: {nombre}")


def build_extractor(nombre: str) -> ExtractorFinanciero:
    """Selecciona el extractor de PDF según la configuración. Agregar aquí la extracción con Gemini."""
    if nombre == "fake":
        return FakeExtractorFinanciero()
    raise ValueError(f"Extractor de PDF desconocido: {nombre}")
