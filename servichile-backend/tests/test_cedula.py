from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.dominio.cedula import validar_cedula

_TEXTO_CEDULA_OK = """
CÉDULA DE REPÚBLICA DE CHILE
IDENTIDAD SERVICIO DE REGISTRO CIVIL E IDENTIFICACIÓN
APELLIDOS
GONZALEZ
PEREZ
NOMBRES
MARIA
NACIONALIDAD: SEXO
CHILENA M
FECHA DE NACIMIENTO NÚMERO DOCUMENTO
15 ENE 1990 A1B.123.456
FECHA DE EMISIÓN FECHA DE VENCIMIENTO
27 MAYO 2025 15 ENE 2032
FIRMA DEL TITULAR
RUN
12.345.678-5
"""

_TEXTO_CEDULA_NUEVA_VIGENTE = """
REPÚBLICA DE CHILE
CÉDULA DE IDENTIDAD
POBLETE
LANDRY
NICOLAS ALEJANDRO
CHILENA M
21 ABR 2003 B5J.212.039
FECHA DE EMISION FECHA DE VENCIMIENTO
27 MAYO 2025 21 ABR 2033
RUN 12.345.678-5
"""

def _foto_carnet(w: int = 900, h: int = 560) -> bytes:
    img = Image.new("RGB", (w, h), (240, 240, 235))

    px = img.load()
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            px[x, y] = ((x * 17 + y * 31) % 200, (x + y) % 180, (x * 3) % 220)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

def _selfie() -> bytes:
    img = Image.new("RGB", (480, 640), (210, 180, 160))
    px = img.load()
    for y in range(0, 640, 2):
        for x in range(0, 480, 2):
            px[x, y] = ((x * 11 + y) % 220, (y * 7) % 200, (x + y) % 180)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()

def _subir_biometria(client: TestClient, headers: dict) -> None:
    r = client.post(
        "/v1/perfil/biometria",
        headers=headers,
        files={"foto": ("selfie.jpg", _selfie(), "image/jpeg")},
    )
    assert r.status_code in (200, 201), r.text

def test_validar_cedula_texto_ok():
    r = validar_cedula(
        texto_ocr=_TEXTO_CEDULA_OK,
        ancho=900,
        alto=560,
        bytes_=40_000,
        rut_perfil=None,
        nombre_perfil="María González",
        rut_perfil_verificado=False,
        face_score=0.88,
    )
    assert r.aceptado is True
    assert r.rut == "12345678-5"
    assert "formato-chile" in r.senales
    assert "rut-valido" in r.senales
    assert "face-match" in r.senales
    assert "vigente" in r.senales
    assert r.nombre_ocr and "GONZALEZ" in r.nombre_ocr.upper()

def test_validar_cedula_no_marca_vencida_si_emision_pasa():
    r = validar_cedula(
        texto_ocr=_TEXTO_CEDULA_NUEVA_VIGENTE,
        ancho=642,
        alto=422,
        bytes_=50_000,
        nombre_perfil="Nicolas Poblete",
        rut_perfil_verificado=False,
        face_score=0.8,
    )
    assert r.aceptado is True
    assert "vigente" in r.senales
    assert "cédula vencida" not in r.motivo.lower()

def test_validar_cedula_rechaza_sin_face_match():
    r = validar_cedula(
        texto_ocr=_TEXTO_CEDULA_OK,
        ancho=900,
        alto=560,
        bytes_=40_000,
        face_score=0.2,
    )
    assert r.aceptado is False
    assert "face-match" not in r.senales

def test_validar_cedula_rechaza_sin_selfie():
    r = validar_cedula(
        texto_ocr=_TEXTO_CEDULA_OK,
        ancho=900,
        alto=560,
        bytes_=40_000,
        face_score=None,
    )
    assert r.aceptado is False

def test_validar_cedula_rechaza_rut_distinto():
    r = validar_cedula(
        texto_ocr=_TEXTO_CEDULA_OK,
        ancho=900,
        alto=560,
        bytes_=40_000,
        rut_perfil="11111111-1",
        rut_perfil_verificado=True,
        face_score=0.9,
    )
    assert r.aceptado is False

def test_endpoint_cedula_exige_biometria_previa(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/cedula",
        headers=h,
        files={"foto": ("carnet.jpg", _foto_carnet(), "image/jpeg")},
    )
    assert r.status_code == 422
    assert "biométr" in r.json()["detail"].lower() or "selfie" in r.json()["detail"].lower()

def test_endpoint_cedula_verifica_rut_sin_guardar_foto(
    client: TestClient, token: str, cedula_dir: Path
):
    h = {"Authorization": f"Bearer {token}"}
    _subir_biometria(client, h)
    antes = client.get("/v1/perfil", headers=h).json()
    assert antes["cedula_verificada"] is False
    assert antes["rut_verificado"] is False
    assert antes["biometria_verificada"] is True

    r = client.post(
        "/v1/perfil/cedula",
        headers=h,
        files={"foto": ("carnet.jpg", _foto_carnet(), "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cedula_verificada"] is True
    assert body["cedula_score"] >= 70
    assert body["rut_verificado"] is True
    assert body["cedula_bytes"]
    assert body.get("face_score") is not None and body["face_score"] >= 0.5
    assert "face-match" in body["senales"]
    assert body["cedula_verificada"] is True
    assert list(cedula_dir.glob("*.jpg")) == []

    perfil = client.get("/v1/perfil", headers=h).json()
    assert perfil["cedula_verificada"] is True
    assert perfil["rut_verificado"] is True
    assert perfil.get("cedula_retener_hasta") in (None,)

def test_endpoint_cedula_basura_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    _subir_biometria(client, h)
    r = client.post(
        "/v1/perfil/cedula",
        headers=h,
        files={"foto": ("x.bin", b"no-es-imagen", "application/octet-stream")},
    )
    assert r.status_code == 422

def test_cedula_ok_deja_carpeta_vacia(client: TestClient, token: str, cedula_dir: Path):
    h = {"Authorization": f"Bearer {token}"}
    _subir_biometria(client, h)
    assert (
        client.post(
            "/v1/perfil/cedula",
            headers=h,
            files={"foto": ("c.jpg", _foto_carnet(), "image/jpeg")},
        ).status_code
        == 201
    )
    assert list(cedula_dir.glob("*.jpg")) == []
