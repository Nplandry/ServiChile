from app.domain.transparencia.cmf import (
    HallazgosCmf,
    InstitucionCmf,
    hallazgos_desde_institucion,
    score_cmf,
)

from app.infrastructure.cmf.indice import FakeCmfIndice, NullCmfIndice


def test_score_sin_rut_o_indice_cero():

    assert score_cmf(HallazgosCmf()) == 0

    assert score_cmf(HallazgosCmf(indice_disponible=True, rut_consultable=False)) == 0

    assert score_cmf(HallazgosCmf(indice_disponible=False, rut_consultable=True)) == 0


def test_score_no_supervisada_con_rut_es_100():

    assert (
        score_cmf(
            HallazgosCmf(
                indice_disponible=True, rut_consultable=True, entidad_supervisada=False
            )
        )
        == 100
    )


def test_score_ficha_completa_100():

    h = hallazgos_desde_institucion(
        indice_disponible=True,
        rut_consultable=True,
        institucion=InstitucionCmf(
            codigo="001",
            nombre="Banco Demo",
            rut="97004000-5",
            direccion="Santiago",
            web="https://banco.cl",
        ),
    )

    assert h.entidad_supervisada is True

    assert h.ficha_completa is True

    assert score_cmf(h) == 100


def test_score_ficha_incompleta_80():

    h = hallazgos_desde_institucion(
        indice_disponible=True,
        rut_consultable=True,
        institucion=InstitucionCmf(codigo="001", nombre="Banco Demo", rut="97004000-5"),
    )

    assert h.entidad_supervisada is True

    assert h.ficha_completa is False

    assert score_cmf(h) == 80


def test_null_y_fake():

    assert NullCmfIndice().score_para_rut("97.004.000-5") == 0

    assert FakeCmfIndice().score_para_rut(None) == 0

    assert FakeCmfIndice().score_para_rut("97004000-5") == 100
