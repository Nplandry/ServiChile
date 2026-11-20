"""Rutas de evidencia contractuales del rastreador (no headers cyb_*)."""

from app.dominio.transparencia.evaluador.motor import construir_puntajes
from app.infraestructura.evaluador.rastreador_web import (
    _analizar,
    _rutas_evidencia_con,
    ruta_mostrar,
)


def test_ruta_mostrar_acorta_url_y_link():
    assert ruta_mostrar("https://ejemplo.cl/politica-de-privacidad") == "/politica-de-privacidad"
    assert ruta_mostrar("link:/terminos-y-condiciones") == "/terminos-y-condiciones"
    assert ruta_mostrar("link:https://ejemplo.cl/cookies?x=1") == "/cookies"
    assert ruta_mostrar(None) is None


def test_analizar_guarda_url_en_ley_cookies_contacto():
    page_texts = {
        "https://ejemplo.cl/privacidad": (
            "Política de privacidad. Cumple la Ley 21.719. "
            "Contacto datos: privacidad@ejemplo.cl. Cookies y consentimiento."
        ),
        "https://ejemplo.cl/": "Home",
    }
    page_html = {
        "https://ejemplo.cl/privacidad": "<html>cookies consentimiento</html>",
        "https://ejemplo.cl/": "<html></html>",
    }
    hallazgos = _analizar(page_texts, page_html)
    by = {h["doc_type"]: h for h in hallazgos}
    assert by["privacy_policy"]["found"] is True
    assert by["privacy_policy"]["url"]
    assert by["ley_21719"]["found"] is True
    assert by["ley_21719"]["url"] == "https://ejemplo.cl/privacidad"
    assert by["cookies_notice"]["found"] is True
    assert by["cookies_notice"]["url"]
    assert by["data_contact"]["found"] is True
    assert by["data_contact"]["url"] == "https://ejemplo.cl/privacidad"


def test_rutas_evidencia_solo_con_no_cyb():
    hallazgos = [
        {
            "doc_type": "privacy_policy",
            "found": True,
            "url": "https://ejemplo.cl/politica-de-privacidad",
        },
        {"doc_type": "terms", "found": True, "url": "https://ejemplo.cl/terminos"},
        {"doc_type": "ley_21719", "found": False, "url": None},
    ]
    rutas = _rutas_evidencia_con(hallazgos, home_url="https://ejemplo.cl/")
    assert rutas == {
        "con_privacy": "/politica-de-privacidad",
        "con_tyc": "/terminos",
    }
    assert "cyb_https" not in rutas


def test_observable_con_privacy_detalle_es_ruta_sin_fuente():
    res = construir_puntajes(
        pistas={"con_privacy": 100.0, "cyb_https": 100.0},
        mapa_evidencia={"con_privacy": "/politica-de-privacidad"},
        mapa_fuentes={"con_privacy": "rastreador_web", "cyb_https": "rastreador_web"},
        mapa_estados={"con_privacy": "ok", "cyb_https": "ok"},
    )
    by = {o.id: o for o in res.a_observables()}
    assert by["con_privacy"].detalle == "/politica-de-privacidad"
    # Headers: sin evidencia de ruta → solo fuente; el FE no la muestra en cyb_*.
    assert by["cyb_https"].detalle == "rastreador_web"
