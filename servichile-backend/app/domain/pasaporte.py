"""Reglas del Pasaporte de Confianza: RUT, score de confiabilidad, nivel y score de arriendo.

Código puro, sin base de datos ni red. Las fórmulas se prueban aquí de forma aislada.
"""
import re
from dataclasses import dataclass

SCORE_ARRIENDO_MAX = 1000
# Tope aplicado si el usuario tiene morosidad en Dicom. Valor provisional, ver score_arriendo.
TOPE_CON_MOROSIDAD = 300

_RUT_PATRON = re.compile(r"^(\d{1,8})-?([0-9K])$")


class RutInvalido(ValueError):
    pass


class ExtraccionFallida(Exception):
    """El extractor no pudo leer el documento (PDF dañado, escaneado sin texto, etc.)."""


def dv_rut(cuerpo: str) -> str:
    """Calcula el dígito verificador de un RUT con el algoritmo módulo 11."""
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = factor + 1 if factor < 7 else 2
    resto = 11 - suma % 11
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(texto: str) -> str:
    """Acepta '12.345.678-5', '123456785' o '12345678-k' y devuelve '12345678-5'.

    Lanza RutInvalido si el formato no calza o el dígito verificador no corresponde.
    """
    limpio = texto.replace(".", "").replace(" ", "").upper()
    coincidencia = _RUT_PATRON.match(limpio)
    if not coincidencia:
        raise RutInvalido("Formato de RUT inválido.")
    cuerpo, dv = coincidencia.group(1), coincidencia.group(2)
    if dv_rut(cuerpo) != dv:
        raise RutInvalido("El dígito verificador del RUT no es correcto.")
    return f"{cuerpo}-{dv}"


def score_confiabilidad(asistidos: int, no_show: int) -> float | None:
    """Asistencias / reservas cerradas x 100, con reservas cerradas = asistidos + no_show.

    Devuelve None si el usuario todavía no tiene reservas cerradas. Así un usuario nuevo
    no queda penalizado antes de tener historial.
    """
    cerradas = asistidos + no_show
    if cerradas == 0:
        return None
    return round(asistidos / cerradas * 100, 1)


def nivel_pasaporte(arriendo_verificado: bool) -> int:
    """Nivel 2 solo con verificación de arriendo aprobada. Todo usuario registrado es nivel 1."""
    return 2 if arriendo_verificado else 1


def estado_pasaporte(estado_arriendo: str | None) -> str:
    """Estado legible del Pasaporte. 'basico' significa que nunca subió documentos."""
    if estado_arriendo is None:
        return "basico"
    return estado_arriendo


@dataclass(frozen=True)
class MetricasFinancieras:
    """Datos extraídos del PDF por el extractor. No incluye el documento original."""

    ingreso_liquido: int  # sueldo líquido mensual en pesos
    deudas_mensuales: int  # cuotas y deudas mensuales en pesos
    morosidad_dicom: bool


def score_arriendo(metricas: MetricasFinancieras) -> int:
    """Score de arriendo de 0 a 1000.

    PROVISIONAL: la fórmula de negocio aún no está definida. Esta regla solo mide la
    capacidad de pago (ingreso libre de deudas sobre ingreso) y aplica un tope si hay
    morosidad. Reemplazar cuando se defina el modelo de scoring.
    """
    if metricas.ingreso_liquido <= 0:
        return 0
    libre = (metricas.ingreso_liquido - metricas.deudas_mensuales) / metricas.ingreso_liquido
    capacidad = min(max(libre, 0.0), 1.0)
    score = round(capacidad * SCORE_ARRIENDO_MAX)
    if metricas.morosidad_dicom:
        score = min(score, TOPE_CON_MOROSIDAD)
    return score
