"""Tipo de cuenta (persona/empresa) desde onboarding/registro."""
from fastapi.testclient import TestClient


def test_registro_con_tipo_empresa(client: TestClient):
    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "empresa@servichile.cl",
            "nombre": "Servicios Sur SpA",
            "password": "clave-segura-123",
            "perfil": {"tipo_cuenta": "empresa"},
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["perfil"]["tipo_cuenta"] == "empresa"
    assert r.json()["perfil"]["edad"] is None


def test_registro_con_tipo_persona_y_edad(client: TestClient):
    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "persona@servichile.cl",
            "nombre": "Ana Pérez",
            "password": "clave-segura-123",
            "perfil": {"tipo_cuenta": "persona", "edad": 42},
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["perfil"]["tipo_cuenta"] == "persona"
    assert r.json()["perfil"]["edad"] == 42


def test_tipo_cuenta_invalido_da_422(client: TestClient):
    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "malo@servichile.cl",
            "nombre": "X",
            "password": "clave-segura-123",
            "perfil": {"tipo_cuenta": "otro"},
        },
    )
    assert r.status_code == 422


def test_registro_sin_tipo_cuenta_da_422(client: TestClient):
    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "sintipo@servichile.cl",
            "nombre": "Sin Tipo",
            "password": "clave-segura-123",
        },
    )
    assert r.status_code == 422
