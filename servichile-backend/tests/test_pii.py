from app.domain.pii import is_valid_rut, redact_text
from scripts.ingest_pdfs import CHUNK_CHARS, partir


def test_rut_valido():
    assert is_valid_rut("12.345.678-5")
    assert is_valid_rut("123456785")
    assert not is_valid_rut("12.345.678-9")
    assert not is_valid_rut("abc")


def test_redaccion():
    texto = "RUT 12345678-5, correo a.b@mail.cl, fono +56 9 1234 5678, tarjeta 4111 1111 1111 1111"
    assert redact_text(texto) == "RUT [RUT], correo [EMAIL], fono [TELEFONO], tarjeta [NUMERO]"


def test_partir_respeta_tamano():
    texto = "Artículo primero. " * 300
    partes = partir(texto)
    assert len(partes) > 1
    assert all(len(p) <= CHUNK_CHARS for p in partes)
