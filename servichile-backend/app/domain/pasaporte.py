"""Reglas del Pasaporte de Confianza: RUT, score de confiabilidad y nivel.

Código puro, sin base de datos ni red. Las fórmulas se prueban aquí de forma aislada.
"""
import re

_RUT_PATRON = re.compile(r"^(\d{1,8})-?([0-9K])$")


class RutInvalido(ValueError):
    pass


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


def nivel_pasaporte() -> int:
    """Nivel de pasaporte. Sin solvencia/arriendo: todo usuario registrado es nivel 1."""
    return 1


def estado_pasaporte(rut_verificado: bool) -> str:
    """Estado legible del Pasaporte según verificación de identidad."""
    return "verificado" if rut_verificado else "basico"
