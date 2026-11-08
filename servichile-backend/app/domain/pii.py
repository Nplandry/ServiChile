"""Validación de RUT y redacción de datos personales antes de enviar texto al modelo de IA.

Las reglas replican js/core/security.js del frontend para que ambos lados redacten igual.
Son funciones puras: no guardan ni registran el texto original.
"""
import re

_RUT_RE = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9kK]\b")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?56\s?9\s?\d{4}\s?\d{4}")
_CARD_RE = re.compile(r"\b(?:\d[ ]?){13,19}\b")


def clean_rut(rut: str) -> str:
    return rut.replace(".", "").replace("-", "").strip().upper()


def is_valid_rut(rut: str) -> bool:
    cleaned = clean_rut(rut)
    if not re.fullmatch(r"\d{7,8}[0-9K]", cleaned):
        return False
    body, check = cleaned[:-1], cleaned[-1]
    total, factor = 0, 2
    for digit in reversed(body):
        total += int(digit) * factor
        factor = 2 if factor == 7 else factor + 1
    expected = 11 - total % 11
    expected_digit = {11: "0", 10: "K"}.get(expected, str(expected))
    return expected_digit == check


def redact_text(text: str) -> str:
    """Reemplaza RUT, correos, teléfonos móviles y números de tarjeta por marcadores."""
    text = _RUT_RE.sub("[RUT]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[TELEFONO]", text)
    text = _CARD_RE.sub("[NUMERO]", text)
    return text.strip()
