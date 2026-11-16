from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.dominio import progreso_cliente as reglas


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (96, 128), (20, 80, 140))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


_JPEG_BYTES = _jpeg_bytes()


def _headers(token: str) -> dict[str, str]:

    return {"Authorization": f"Bearer {token}"}


def test_registro_otorga_xp_base(client: TestClient):

    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "xp-reg@servichile.cl",
            "nombre": "XP Reg",
            "password": "clave-segura-123",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    assert r.status_code == 201

    perfil = r.json()["perfil"]

    assert perfil["xp"] == reglas.XP_REGISTRO

    assert perfil["nivel_xp"] == 1


def test_perfil_basico_suma_xp(client: TestClient, token: str):

    h = _headers(token)

    antes = client.get("/v1/auth/yo", headers=h).json()["perfil"]["xp"]

    r = client.patch(
        "/v1/perfil", headers=h, json={"edad": 30, "telefono": "+56 9 1111 2222"}
    )

    assert r.status_code == 200

    assert r.json()["xp"] == antes + reglas.XP_PERFIL_BASICO

    r2 = client.patch(
        "/v1/perfil", headers=h, json={"edad": 31, "telefono": "+56 9 1111 2222"}
    )

    assert r2.status_code == 200

    assert r2.json()["xp"] == antes + reglas.XP_PERFIL_BASICO


def test_biometria_suma_xp_una_vez(client: TestClient, token: str):

    h = _headers(token)

    antes = client.get("/v1/auth/yo", headers=h).json()["perfil"]["xp"]

    r = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("a.jpg", _JPEG_BYTES, "image/jpeg")},
    )

    assert r.status_code == 201

    assert r.json()["xp"] == antes + reglas.XP_BIOMETRIA

    assert r.json()["nivel_xp"] >= 1

    r2 = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("b.jpg", _JPEG_BYTES, "image/jpeg")},
    )

    assert r2.status_code == 201

    assert r2.json()["xp"] == antes + reglas.XP_BIOMETRIA


def test_rut_suma_xp(client: TestClient, token: str):

    h = _headers(token)

    antes = client.get("/v1/auth/yo", headers=h).json()["perfil"]["xp"]

    r = client.patch("/v1/perfil", headers=h, json={"rut": "12.345.678-5"})

    assert r.status_code == 200

    assert r.json()["xp"] == antes + reglas.XP_RUT

    r2 = client.patch("/v1/perfil", headers=h, json={"rut": "12.345.678-5"})

    assert r2.status_code == 200

    assert r2.json()["xp"] == antes + reglas.XP_RUT


def test_asistencia_suma_xp(client: TestClient, token_empresa: str):

    import uuid

    titular = _headers(token_empresa)

    creada = client.post(
        "/v1/businesses",
        headers=titular,
        json={
            "nombre": "XP Tech",
            "categoria": "tecnologia",
            "direccion": "Av. Siempre Viva 100",
        },
    )

    assert creada.status_code == 201, creada.text

    bid = creada.json()["id"]

    datos = {
        "email": "xp-cliente@servichile.cl",
        "nombre": "Cliente XP",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "persona"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    tok = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    ).json()["access_token"]

    cliente = _headers(tok)

    antes = client.get("/v1/auth/yo", headers=cliente).json()["perfil"]["xp"]

    reserva = client.post(
        "/v1/reservas", json={"business_id": str(bid)}, headers=cliente
    ).json()

    assert (
        client.post(
            f"/v1/businesses/{bid}/checkin",
            json={"qr_token": reserva["qr_token"]},
            headers=titular,
        ).status_code
        == 200
    )

    despues = client.get("/v1/auth/yo", headers=cliente).json()["perfil"]["xp"]

    assert despues == antes + reglas.XP_ASISTENCIA

    assert uuid.UUID(reserva["id"])


def test_nivel_por_xp_umbrales():

    assert reglas.nivel_por_xp(0) == 1

    assert reglas.nivel_por_xp(99) == 1

    assert reglas.nivel_por_xp(100) == 2

    assert reglas.nivel_por_xp(249) == 2

    assert reglas.nivel_por_xp(250) == 3

    assert reglas.nivel_por_xp(9999) == 3
