"""Cabeceras de reputación + /salud (deps omitidas en APP_ENV=test)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_salud_incluye_dependencias(client: TestClient):
    r = client.get("/salud")
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] in ("ok", "degradado")
    assert body["dependencias"]["redis"] == "omitido"
    assert body["dependencias"]["postgres"] == "omitido"
    assert body["dependencias"]["smtp"] in ("omitido", "configurado")
    assert "background_jobs" in body
    assert "evaluador" in body
    assert "pagos_reconciliar" in body


def test_reputation_public_headers_y_teaser(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Cache Audit SpA",
            "categoria": "tecnologia",
            "direccion": "Santiago",
        },
    )
    assert alta.status_code == 201
    bid = alta.json()["id"]

    pub = client.get(f"/v1/businesses/{bid}/reputation")
    assert pub.status_code == 200
    assert pub.headers.get("cache-control", "").startswith("private")
    assert "authorization" in (pub.headers.get("vary") or "").lower()
    assert pub.headers.get("x-cache") in ("MISS", "HIT")
    assert pub.json().get("docs_empresa") is None
    assert len(pub.json()["observables"]) == 3

    tit = client.get(f"/v1/businesses/{bid}/reputation", headers=h)
    assert tit.status_code == 200
    assert tit.headers.get("x-cache") == "BYPASS"
    assert tit.headers.get("cache-control", "").startswith("private")
    assert len(tit.json()["observables"]) > 3


def test_print_secret_no_es_jwt_crudo():
    from app.configuracion import Configuracion

    cfg = Configuracion(
        app_env="test",
        jwt_secret="test-secret-de-al-menos-32-caracteres-xx",
        print_token_secret=None,
    )
    assert cfg.secreto_print_token() != cfg.jwt_secret.get_secret_value()
    assert len(cfg.secreto_print_token()) == 64
