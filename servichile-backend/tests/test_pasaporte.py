import pytest

from app.dominio.pasaporte import (
    RutInvalido,
    dv_rut,
    estado_pasaporte,
    nivel_pasaporte,
    normalizar_rut,
    score_confiabilidad,
)


@pytest.mark.parametrize(
    ("cuerpo", "dv"),
    [
        ("12345678", "5"),
        ("11111111", "1"),
        ("7654321", "6"),
        ("8765432", "K"),
        ("22222222", "2"),
    ],
)
def test_dv_rut_modulo_11(cuerpo, dv):

    assert dv_rut(cuerpo) == dv


def test_normalizar_rut_acepta_formatos_comunes():

    assert normalizar_rut("12.345.678-5") == "12345678-5"

    assert normalizar_rut("123456785") == "12345678-5"

    assert normalizar_rut("8765432-k") == "8765432-K"


def test_normalizar_rut_rechaza_dv_incorrecto():

    with pytest.raises(RutInvalido):

        normalizar_rut("12345678-0")


def test_normalizar_rut_rechaza_formato_invalido():

    for malo in ["abc", "1234-5", "123456789-5", ""]:

        with pytest.raises(RutInvalido):

            normalizar_rut(malo)


def test_score_confiabilidad_es_asistencias_sobre_cerradas():

    assert score_confiabilidad(asistidos=3, no_show=1) == 75.0

    assert score_confiabilidad(asistidos=5, no_show=0) == 100.0


def test_score_confiabilidad_sin_historial_es_null():

    assert score_confiabilidad(asistidos=0, no_show=0) is None


def test_nivel_pasaporte_siempre_1():

    assert nivel_pasaporte() == 1


def test_estado_pasaporte_segun_rut():

    assert estado_pasaporte(False) == "basico"

    assert estado_pasaporte(True) == "verificado"
