"""Verificación biométrica: cualquier imagen válida pasa; no se persiste la foto."""
from fastapi.testclient import TestClient

# JPEG mínimo válido (1x1).
_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\xff\xd9"
)


def test_biometria_requiere_sesion(client: TestClient):
    r = client.post("/v1/perfil/biometria", files={"foto": ("a.jpg", _JPEG, "image/jpeg")})
    assert r.status_code == 401


def test_biometria_cualquier_jpeg_pasa(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    antes = client.get("/v1/perfil", headers=h).json()
    assert antes["biometria_verificada"] is False

    r = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("selfie.jpg", _JPEG, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["biometria_verificada"] is True
    assert body["biometria_verificada_en"]
    assert "no se almacen" in body["mensaje"].lower()

    despues = client.get("/v1/perfil", headers=h).json()
    assert despues["biometria_verificada"] is True
    assert despues["biometria_verificada_en"]


def test_biometria_png_tambien_pasa(client: TestClient, token: str):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/perfil/biometria", headers=h, files={"foto": ("x.png", png, "image/png")})
    assert r.status_code == 201, r.text


def test_biometria_basura_da_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("x.bin", b"no-es-imagen", "application/octet-stream")},
    )
    assert r.status_code == 422
