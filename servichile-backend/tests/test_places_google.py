from app.domain.ciber_observables import razones_resenas

from app.infrastructure.places_google import (
    FakePlacesGoogle,
    NullPlacesGoogle,
    elegir_lugar,
    resultado_desde_lugar,
)


def test_null_sin_datos():

    r = NullPlacesGoogle().buscar_reputacion(nombre="Gearlabs SpA")

    assert r.encontrado is False

    assert r.rating is None


def test_fake_con_nombre():

    r = FakePlacesGoogle().buscar_reputacion(
        nombre="Gearlabs SpA", direccion="Las Condes"
    )

    assert r.encontrado is True

    assert r.rating == 4.5

    assert r.reviews_count == 120


def test_fake_sin_nombre():

    assert FakePlacesGoogle().buscar_reputacion(nombre="").encontrado is False


def test_elige_por_sitio_web():

    places = [
        {
            "id": "a",
            "websiteUri": "https://otra.cl",
            "rating": 3.0,
            "userRatingCount": 10,
        },
        {
            "id": "b",
            "websiteUri": "https://www.gearlabs.cl",
            "rating": 4.8,
            "userRatingCount": 40,
        },
    ]

    elegido = elegir_lugar(places, "https://gearlabs.cl")

    assert elegido is not None

    assert elegido["id"] == "b"


def test_resultado_desde_lugar():

    r = resultado_desde_lugar(
        {
            "id": "places/xyz",
            "displayName": {"text": "Gearlabs SpA"},
            "rating": 4.7,
            "userRatingCount": 88,
        }
    )

    assert r.encontrado is True

    assert r.rating == 4.7

    assert r.reviews_count == 88

    assert r.nombre == "Gearlabs SpA"


def test_razones_resenas_formato_reporte():

    lineas = razones_resenas(
        ficha="Mercado Libre",
        google_rating_avg=2.0,
        google_reviews_count=1455,
        score=67,
    )

    assert lineas == [
        "Ficha: Mercado Libre",
        "Rating Google: 2.0 / 5",
        "Reseñas: 1.455",
        "Score: 67 / 100",
    ]


def test_razones_resenas_sin_penalizacion_fija():

    lineas = razones_resenas(
        ficha="Pyme Demo",
        google_rating_avg=4.8,
        google_reviews_count=12,
        score=55,
    )

    assert all("Penalización" not in x for x in lineas)
