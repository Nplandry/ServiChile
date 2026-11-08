"""Pruebas del Pasaporte de Confianza: reglas de dominio y carga de documentos de arriendo."""
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.domain.pasaporte import (
    ExtraccionFallida,
    MetricasFinancieras,
    RutInvalido,
    dv_rut,
    nivel_pasaporte,
    normalizar_rut,
    score_arriendo,
    score_confiabilidad,
)
from app.infrastructure.verificacion import FakeExtractorFinanciero

PDF_MINIMO = b"%PDF-1.4\n% contenido de prueba\n%%EOF"



@pytest.mark.parametrize(
    ("cuerpo", "dv"),
    [("12345678", "5"), ("11111111", "1"), ("7654321", "6"), ("8765432", "K"), ("22222222", "2")],
)
def test_dv_rut_modulo_11(cuerpo, dv):
    assert dv_rut(cuerpo) == dv


def test_normalizar_rut_acepta_formatos_comunes():
    assert normalizar_rut("12.345.678-5") == "12345678-5"
    assert normalizar_rut("123456785") == "12345678-5"
    assert normalizar_rut("8765432-k") == "8765432-K"


def test_normalizar_rut_rechaza_dv_incorrecto():
    with pytest.raises(RutInvalido):
        normalizar_rut("12345678-0")


def test_normalizar_rut_rechaza_formato_invalido():
    for malo in ["abc", "1234-5", "123456789-5", ""]:
        with pytest.raises(RutInvalido):
            normalizar_rut(malo)



def test_score_confiabilidad_es_asistencias_sobre_cerradas():
    assert score_confiabilidad(asistidos=3, no_show=1) == 75.0
    assert score_confiabilidad(asistidos=5, no_show=0) == 100.0


def test_score_confiabilidad_sin_historial_es_null():
    assert score_confiabilidad(asistidos=0, no_show=0) is None


def test_nivel_pasaporte_sube_solo_con_arriendo_verificado():
    assert nivel_pasaporte(False) == 1
    assert nivel_pasaporte(True) == 2



def test_score_arriendo_proporcional_a_capacidad_de_pago():
    m = MetricasFinancieras(ingreso_liquido=1_000_000, deudas_mensuales=200_000, morosidad_dicom=False)
    assert score_arriendo(m) == 800


def test_score_arriendo_con_morosidad_tiene_tope():
    m = MetricasFinancieras(ingreso_liquido=1_000_000, deudas_mensuales=0, morosidad_dicom=True)
    assert score_arriendo(m) == 300


def test_score_arriendo_sin_ingreso_es_cero():
    m = MetricasFinancieras(ingreso_liquido=0, deudas_mensuales=0, morosidad_dicom=False)
    assert score_arriendo(m) == 0



def _subir(client: TestClient, headers, contenido: bytes, nombre="liquidacion.pdf"):
    return client.post(
        "/v1/perfil/documentos",
        files={"archivo": (nombre, contenido, "application/pdf")},
        headers=headers,
    )


def test_subir_pdf_calcula_score_y_sube_a_nivel_2(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = _subir(client, h, PDF_MINIMO)
    assert r.status_code == 201, r.text
    assert r.json()["estado_verificacion"] == "verificado"
    assert r.json()["score_financiero"] == 800

    perfil = client.get("/v1/perfil", headers=h).json()
    assert perfil["nivel_pasaporte"] == 2
    assert perfil["estado_pasaporte"] == "verificado"
    assert perfil["inmobiliaria_scoring"]["score_financiero"] == 800


def test_archivo_que_no_es_pdf_da_422(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = _subir(client, h, b"<html>no soy un pdf</html>", nombre="x.pdf")
    assert r.status_code == 422
    assert client.get("/v1/perfil", headers=h).json()["nivel_pasaporte"] == 1


def test_archivo_mayor_a_1mb_da_413(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = _subir(client, h, PDF_MINIMO + b"0" * (1024 * 1024))
    assert r.status_code == 413


def test_pdf_ilegible_da_422(client: TestClient, token: str):
    class ExtractorRoto:
        def extraer(self, contenido: bytes):
            raise ExtraccionFallida()

    client.app.dependency_overrides[deps.get_extractor] = lambda: ExtractorRoto()
    h = {"Authorization": f"Bearer {token}"}
    assert _subir(client, h, PDF_MINIMO).status_code == 422


def test_documento_no_se_guarda_en_la_base(client: TestClient, session_factory, token: str):
    h = {"Authorization": f"Bearer {token}"}
    _subir(client, h, PDF_MINIMO)
    # La tabla solo tiene puntaje y fechas: ninguna columna puede contener el PDF.
    from sqlalchemy import text

    with session_factory() as s:
        columnas = {fila[1] for fila in s.execute(text("PRAGMA table_info(pasaporte_arriendo)"))}
    assert columnas == {"id", "usuario_id", "estado", "score", "verificado_en", "creado_en"}


def test_subir_documento_requiere_sesion(client: TestClient):
    r = client.post("/v1/perfil/documentos", files={"archivo": ("x.pdf", PDF_MINIMO, "application/pdf")})
    assert r.status_code == 401


def test_extractor_fake_no_depende_del_contenido():
    assert FakeExtractorFinanciero().extraer(b"lo que sea") == FakeExtractorFinanciero().extraer(b"otro")
