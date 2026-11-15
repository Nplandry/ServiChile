from datetime import UTC, datetime, timedelta

import jwt

from fastapi.testclient import TestClient

from app.configuracion import get_settings


def _cuenta(
    client: TestClient, email: str, nombre: str = "Usuario Prueba"
) -> dict[str, str]:

    datos = {
        "email": email,
        "nombre": nombre,
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "persona"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    t = client.post(
        "/v1/auth/login", json={"email": email, "password": datos["password"]}
    ).json()

    return {"Authorization": f"Bearer {t['access_token']}"}


def test_emitir_reporte_requiere_sesion(client: TestClient):

    assert client.get("/v1/reporte").status_code == 401


def test_emitir_reporte_devuelve_payload_firmado(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    r = client.get("/v1/reporte", headers=h)

    assert r.status_code == 200, r.text

    body = r.json()

    assert body["payload"].startswith("servichile://reporte/")

    assert body["token"]

    assert body["expires_in"] > 0

    assert body["nombre"] == "María González"

    assert body["email"].lower() == "maria@servichile.cl"

    assert body["nivel_pasaporte"] in (1, 2)

    assert body["estado_pasaporte"] in (
        "basico",
        "pendiente",
        "verificado",
        "rechazado",
    )

    assert "rut" not in body


def test_validar_qr_de_otro_usuario(client: TestClient, token: str):

    titular = {"Authorization": f"Bearer {token}"}

    emitido = client.get("/v1/reporte", headers=titular).json()

    otro = _cuenta(client, "validador@servichile.cl", "Validador Comercio")

    r = client.post(
        "/v1/reporte/validar", json={"payload": emitido["payload"]}, headers=otro
    )

    assert r.status_code == 200, r.text

    body = r.json()

    assert body["es_propio"] is False

    assert body["nombre"] == "María González"

    assert "email" not in body

    assert "rut" not in body

    assert body["nivel_pasaporte"] in (1, 2)

    assert body["tipo_cuenta"] == "persona"


def _cuenta_empresa(
    client: TestClient, email: str, nombre: str = "Empresa Prueba"
) -> dict[str, str]:

    datos = {
        "email": email,
        "nombre": nombre,
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "proveedor"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    t = client.post(
        "/v1/auth/login", json={"email": email, "password": datos["password"]}
    ).json()

    return {"Authorization": f"Bearer {t['access_token']}"}


def test_persona_valida_qr_de_proveedor(client: TestClient, token: str):

    empresa = _cuenta_empresa(client, "qr-empresa@servichile.cl", "Proveedor SPA")

    emitido = client.get("/v1/reporte", headers=empresa).json()

    assert emitido["tipo_cuenta"] == "proveedor"

    persona = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/v1/reporte/validar", json={"payload": emitido["payload"]}, headers=persona
    )

    assert r.status_code == 200, r.text

    body = r.json()

    assert body["es_propio"] is False

    assert body["nombre"] == "Proveedor SPA"

    assert body["tipo_cuenta"] == "proveedor"


def test_proveedor_valida_qr_de_persona(client: TestClient, token: str):

    persona = {"Authorization": f"Bearer {token}"}

    emitido = client.get("/v1/reporte", headers=persona).json()

    empresa = _cuenta_empresa(client, "lector-empresa@servichile.cl", "Lector SPA")

    r = client.post(
        "/v1/reporte/validar", json={"payload": emitido["payload"]}, headers=empresa
    )

    assert r.status_code == 200, r.text

    body = r.json()

    assert body["es_propio"] is False

    assert body["tipo_cuenta"] == "persona"

    assert body["nombre"] == "María González"


def test_validar_acepta_jwt_crudo(client: TestClient, token: str):

    titular = {"Authorization": f"Bearer {token}"}

    emitido = client.get("/v1/reporte", headers=titular).json()

    otro = _cuenta(client, "lector@servichile.cl")

    r = client.post(
        "/v1/reporte/validar", json={"payload": emitido["token"]}, headers=otro
    )

    assert r.status_code == 200, r.text

    assert r.json()["nombre"] == "María González"


def test_validar_propio_marca_es_propio(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    emitido = client.get("/v1/reporte", headers=h).json()

    r = client.post(
        "/v1/reporte/validar", json={"payload": emitido["payload"]}, headers=h
    )

    assert r.status_code == 200

    assert r.json()["es_propio"] is True


def test_token_de_sesion_no_sirve_como_reporte(client: TestClient, token: str):

    otro = _cuenta(client, "otro@servichile.cl")

    r = client.post("/v1/reporte/validar", json={"payload": token}, headers=otro)

    assert r.status_code == 422


def test_qr_expirado_da_422(client: TestClient, token: str):

    settings = get_settings()

    yo = client.get("/v1/auth/yo", headers={"Authorization": f"Bearer {token}"}).json()

    vencido = jwt.encode(
        {
            "sub": yo["id"],
            "pur": "reporte",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    otro = _cuenta(client, "expira@servichile.cl")

    r = client.post(
        "/v1/reporte/validar",
        json={"payload": "servichile://reporte/" + vencido},
        headers=otro,
    )

    assert r.status_code == 422

    assert "expir" in r.json()["detail"].lower()


def test_payload_basura_da_422(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/v1/reporte/validar",
        json={"payload": "https://ejemplo.cl/no-es-qr"},
        headers=h,
    )

    assert r.status_code == 422
