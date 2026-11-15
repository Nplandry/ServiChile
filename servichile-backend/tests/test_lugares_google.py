from app.dominio.transparencia.indicadores import razones_resenas


def test_razones_resenas_sin_penalizacion_fija():
    lineas = razones_resenas(
        ficha="Pyme Demo",
        google_rating_avg=4.8,
        google_reviews_count=12,
        score=55,
    )
    assert all("Penalización" not in x for x in lineas)
