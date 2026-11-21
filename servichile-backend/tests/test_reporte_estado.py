from app.dominio.reporte_estado import estado_reporte, nivel_reporte, score_confiabilidad

def test_score_confiabilidad_es_concretados_sobre_cerrados():
    assert score_confiabilidad(concretados=3, no_concretados=1) == 75.0
    assert score_confiabilidad(concretados=5, no_concretados=0) == 100.0

def test_score_confiabilidad_sin_historial_es_null():
    assert score_confiabilidad(concretados=0, no_concretados=0) is None

def test_nivel_reporte_siempre_1():
    assert nivel_reporte() == 1

def test_estado_reporte_segun_rut():
    assert estado_reporte(False) == "basico"
    assert estado_reporte(True) == "verificado"
