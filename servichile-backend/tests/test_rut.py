import pytest

from app.dominio.rut import RutInvalido, dv_rut, normalizar_rut


def test_dv_rut_conocido():
    assert dv_rut("12345678") == "5"
    assert dv_rut("11111111") == "1"


def test_normalizar_rut_acepta_puntos_y_guion():
    assert normalizar_rut("12.345.678-5") == "12345678-5"
    assert normalizar_rut("12345678-5") == "12345678-5"


def test_normalizar_rut_rechaza_dv_malo():
    with pytest.raises(RutInvalido):
        normalizar_rut("12345678-0")
