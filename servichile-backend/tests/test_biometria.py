from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

def _jpeg(w: int = 120, h: int = 160, color=(30, 90, 160)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_biometria_requiere_sesion(client: TestClient):
    r = client.post(
        "/v1/perfil/biometria", files={"foto": ("a.jpg", _jpeg(), "image/jpeg")}
    )
    assert r.status_code == 401


def test_biometria_guarda_archivo_comprimido(
    client: TestClient, token: str, biometria_dir: Path
):
    h = {"Authorization": f"Bearer {token}"}
    antes = client.get("/v1/perfil", headers=h).json()
    assert antes["biometria_verificada"] is False

    original = _jpeg(800, 1000)
    r = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("selfie.jpg", original, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["biometria_verificada"] is True
    assert body["biometria_verificada_en"]
    assert body["biometria_retener_hasta"]
    assert body["biometria_bytes"] and body["biometria_bytes"] < len(original)
    assert "comprimida" in body["mensaje"].lower() or "retención" in body["mensaje"].lower()

    archivos = list(biometria_dir.glob("*.jpg"))
    assert len(archivos) == 1
    assert archivos[0].stat().st_size == body["biometria_bytes"]

    despues = client.get("/v1/perfil", headers=h).json()
    assert despues["biometria_verificada"] is True
    assert despues["biometria_bytes"] == body["biometria_bytes"]
    assert despues["biometria_retener_hasta"]


def test_biometria_png_tambien_pasa(client: TestClient, token: str):
    png = _jpeg()  # el endpoint acepta imagen; usamos JPEG válido
    # PNG real 64x64
    img = Image.new("RGB", (64, 64), (200, 40, 40))
    buf = BytesIO()
    img.save(buf, format="PNG")
    png = buf.getvalue()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/biometria", headers=h, files={"foto": ("x.png", png, "image/png")}
    )
    assert r.status_code == 201, r.text


def test_biometria_basura_da_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("x.bin", b"no-es-imagen", "application/octet-stream")},
    )
    assert r.status_code == 422


def test_biometria_reenvio_sobrescribe_archivo(
    client: TestClient, token: str, biometria_dir: Path
):
    h = {"Authorization": f"Bearer {token}"}
    r1 = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("a.jpg", _jpeg(200, 200, (10, 10, 10)), "image/jpeg")},
    )
    assert r1.status_code == 201
    sha1 = (biometria_dir / list(biometria_dir.glob("*.jpg"))[0].name).read_bytes()
    assert len(list(biometria_dir.glob("*.jpg"))) == 1

    r2 = client.post(
        "/v1/perfil/biometria",
        headers=h,
        files={"foto": ("b.jpg", _jpeg(320, 240, (200, 20, 20)), "image/jpeg")},
    )
    assert r2.status_code == 201
    archivos = list(biometria_dir.glob("*.jpg"))
    assert len(archivos) == 1
    sha2 = archivos[0].read_bytes()
    assert sha2 != sha1
    perfil = client.get("/v1/perfil", headers=h).json()
    assert perfil["biometria_verificada"] is True


def test_eliminar_cuenta_borra_selfie(
    client: TestClient, token: str, biometria_dir: Path
):
    h = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(
            "/v1/perfil/biometria",
            headers=h,
            files={"foto": ("s.jpg", _jpeg(), "image/jpeg")},
        ).status_code
        == 201
    )
    assert list(biometria_dir.glob("*.jpg"))
    r = client.request(
        "DELETE",
        "/v1/auth/yo",
        headers=h,
        json={"password": "clave-segura-123"},
    )
    assert r.status_code == 204, r.text
    assert list(biometria_dir.glob("*.jpg")) == []
