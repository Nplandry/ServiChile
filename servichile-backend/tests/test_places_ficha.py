"""Selección de ficha Places: dual listing y caché."""

from app.dominio.transparencia.evaluador.ficha import elegir_lugar_confiable
from app.infraestructura.evaluador import cache_lugares


def test_elige_ficha_con_website_sobre_duplicado_sin_web():
    principal = {
        "id": "a",
        "displayName": {"text": "Gearlabs"},
        "formattedAddress": "Av. Apoquindo 6410, Las Condes, Chile",
        "nationalPhoneNumber": "+56 9 9824 0036",
        "websiteUri": "https://www.gearlabs.cl/",
        "rating": 5.0,
        "userRatingCount": 17,
        "regularOpeningHours": {"weekdayDescriptions": ["lunes: 9:00–19:00"]},
    }
    secundaria = {
        "id": "b",
        "displayName": {"text": "GearLabs"},
        "formattedAddress": "Portugal 1862, Santiago, Chile",
        "nationalPhoneNumber": "+56 9 9824 0036",
        "websiteUri": None,
        "userRatingCount": 0,
    }
    elegido, evaluacion = elegir_lugar_confiable(
        [secundaria, principal],
        nombre_empresa="Gearlabs Spa",
        dominio="gearlabs.cl",
        comuna="Las Condes",
        ciudad="Santiago",
    )
    assert elegido is not None
    assert elegido["id"] == "a"
    assert evaluacion.coincidencia_dominio is True
    assert evaluacion.nombre_lugar == "Gearlabs"


def test_cache_lugares_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cache_lugares, "_dir", lambda: tmp_path / "places"
    )
    cache_lugares.limpiar("demo.cl")
    assert cache_lugares.obtener("demo.cl") is None
    carga = {
        "place": {"displayName": {"text": "Demo"}, "websiteUri": "https://demo.cl"},
        "ficha_assessment": {"nombre_lugar": "Demo", "confiable": True},
    }
    cache_lugares.guardar("demo.cl", carga)
    got = cache_lugares.obtener("www.demo.cl")
    assert got is not None
    assert got["ficha_assessment"]["nombre_lugar"] == "Demo"