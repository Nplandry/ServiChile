from app.dominio.transparencia.sii import (
    HallazgosSii,
    hallazgos_desde_payload,
    score_sii,
)

from app.infraestructura.sii import (
    MuestraSiiContribuyentes,
    NullSiiContribuyentes,
)


def test_score_sin_consulta_cero():

    assert score_sii(HallazgosSii()) == 0

    assert score_sii(HallazgosSii(consulta_ok=True, termino_giro=True)) == 0


def test_score_contribuyente_completo():

    assert (
        score_sii(
            HallazgosSii(
                consulta_ok=True,
                inicio_actividades=True,
                obligacion_dte=True,
                tiene_dte_timbrado=True,
            )
        )
        == 100
    )


def test_hallazgos_desde_payload_ejemplo():

    data = {
        "inicio_actividades": True,
        "obligacion_dte": True,
        "documentos_timbrados": [
            {"documento": "Factura Electronica", "ultimo_timbraje": 2024}
        ],
        "observaciones": {
            "inconcurrente": False,
            "termino_giro": False,
            "no_ubicado": False,
        },
    }

    h = hallazgos_desde_payload(data)

    assert h.consulta_ok is True

    assert h.inicio_actividades is True

    assert h.tiene_dte_timbrado is True

    assert score_sii(h) == 100


def test_nulo_y_muestra():

    assert NullSiiContribuyentes().score_para_rut("76.192.083-9") == 0

    assert MuestraSiiContribuyentes().score_para_rut(None) == 0

    assert MuestraSiiContribuyentes().score_para_rut("76192083-9") == 100
