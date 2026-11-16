from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.dominio.aval import clasificar_tipo, validar_aval
from app.infraestructura.pdf_aval import analizar_pdf_aval


_TEXTO_AVAL_OK = """
CARTA DE AVAL
Banco Estado de Chile
Yo, Juan Perez Avalista, RUT 12.345.678-5, me constituyo en avalista solidario
de Maria Gonzalez, por un monto de $1.500.000 (CLP), con vigencia desde
15/01/2026 hasta 15/01/2027.
Notaria Santiago Centro.
Respaldo y garantia de cumplimiento.
"""


def _pdf_texto(texto: str) -> bytes:
    """PDF mínimo con stream de texto (capa real, no imagen)."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]
    # Contenido Tipografía simple
    safe = (
        texto.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", ") Tj T* (")
    )
    content = f"BT /F1 10 Tf 50 750 Td 14 TL ({safe}) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(content.encode("latin-1", errors="replace"))
    page[NameObject("/Contents")] = stream
    # Font dict mínimo
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _pdf_vacio_imagen() -> bytes:
    """PDF con página en blanco (sin texto suficiente → rechazo escaneo)."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_clasificar_tipo_keywords():
    assert clasificar_tipo("Boleta de Garantía Banco X") == "boleta"
    assert clasificar_tipo("Póliza de seguro de garantía") == "poliza"
    assert clasificar_tipo("Carta de aval del avalista") == "carta_aval"
    assert clasificar_tipo("Contrato de arriendo cualquiera") == "otro"


def test_validar_aval_texto_ok():
    r = validar_aval(
        texto=_TEXTO_AVAL_OK,
        rut_perfil="12345678-5",
        nombre_perfil="María González",
    )
    assert r.aceptado is True
    assert r.tipo == "carta_aval"
    assert "palabra-clave" in r.senales
    assert "rut-valido" in r.senales
    assert r.score >= 70


def test_validar_aval_rechaza_sin_clave():
    r = validar_aval(texto="Contrato de prestación de servicios 12.345.678-5 $1000 01/01/2026 Banco")
    assert r.aceptado is False


def test_analizar_pdf_aval_ok():
    pdf = _pdf_texto(_TEXTO_AVAL_OK)
    r = analizar_pdf_aval(pdf, rut_perfil="12345678-5", nombre_perfil="Maria Gonzalez")
    assert r.aceptado is True
    assert r.tipo == "carta_aval"


def test_analizar_pdf_rechaza_sin_texto():
    r = analizar_pdf_aval(_pdf_vacio_imagen())
    assert r.aceptado is False
    assert "escaneo-o-imagen" in r.senales or "texto" in r.motivo.lower()


def test_analizar_pdf_rechaza_no_pdf():
    r = analizar_pdf_aval(b"no-es-pdf")
    assert r.aceptado is False
    assert "no-pdf" in r.senales


def test_endpoint_aval_ok(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    # Asegura RUT en perfil para coherencia (opcional)
    client.patch(
        "/v1/perfil",
        headers=h,
        json={"rut": "12345678-5", "telefono": "+56912345678", "edad": 30},
    )
    pdf = _pdf_texto(_TEXTO_AVAL_OK)
    r = client.post(
        "/v1/perfil/aval",
        headers=h,
        files={"archivo": ("aval.pdf", pdf, "application/pdf")},
        data={"nombre_archivo": "aval.pdf"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["aval_verificado"] is True
    assert body["aval_score"] >= 70
    assert body["aval_tipo"] == "carta_aval"
    assert "gemini" not in body
    assert "no se" in body["motivo"].lower() or "válido" in body["motivo"].lower()

    perfil = client.get("/v1/perfil", headers=h).json()
    assert perfil["aval_verificado"] is True
    assert perfil["aval_tipo"] == "carta_aval"


def test_endpoint_aval_escaneo_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/aval",
        headers=h,
        files={"archivo": ("scan.pdf", _pdf_vacio_imagen(), "application/pdf")},
    )
    assert r.status_code == 422


def test_endpoint_aval_imagen_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/perfil/aval",
        headers=h,
        files={"archivo": ("x.jpg", b"\xff\xd8\xff" + b"0" * 100, "image/jpeg")},
    )
    assert r.status_code == 422
