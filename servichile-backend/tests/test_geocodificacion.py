from app.infraestructura.geocodificacion import (
    GeocodificadorDeterminista,
    GeocodificadorNulo,
    construir_geocodificador,
)


def test_determinista_chile():
    g = GeocodificadorDeterminista()
    a = g.geocodificar("Providencia 100, Santiago")
    b = g.geocodificar("Providencia 100, Santiago")
    c = g.geocodificar("Las Condes 2000")
    assert a is not None and a == b
    assert c is not None and c != a
    assert -56.0 <= a[0] <= -17.0
    assert -76.0 <= a[1] <= -66.0


def test_nulo_y_factory():
    assert GeocodificadorNulo().geocodificar("x") is None
    assert isinstance(construir_geocodificador("test"), GeocodificadorDeterminista)
