from pathlib import Path

from fastapi.testclient import TestClient

from app.domain import xp as reglas

from app.domain.antecedentes import detectar_anotaciones, run_valido

from app.infrastructure.antecedentes_pdf import analizar_pdf_antecedentes

FIXTURE = Path(__file__).parent / "fixtures" / "ANT_500727268737_21082350.pdf"


def test_run_dv():

    assert run_valido("21.082.350-6")

    assert not run_valido("21.082.350-5")


def test_detectar_anotaciones_sin():

    assert (
        detectar_anotaciones(
            "CERTIFICADO DE ANTECEDENTES REGISTRO CIVIL SIN ANTECEDENTES PARTICULARES"
        )
        is False
    )


def test_detectar_anotaciones_con():

    texto = "CERTIFICADO DE ANTECEDENTES REGISTRO CIVIL REGISTRO GENERAL DE CONDENAS CONDENA 2020"

    assert detectar_anotaciones(texto) is True


def test_analizar_fixture_acepta_sin_anotaciones():

    assert FIXTURE.exists(), FIXTURE

    r = analizar_pdf_antecedentes(FIXTURE.read_bytes(), FIXTURE.name)

    assert r.aceptado is True

    assert r.score >= 70

    assert r.anotaciones is False

    assert r.folio == "500727268737"

    assert r.codigo == "513bd82d89e7"

    assert "formato-srcei" in r.senales

    assert "itext" in r.senales

    assert "folio-etiquetado" in r.senales

    assert "codigo-etiquetado" in r.senales


def test_pdf_de_clase_o_apuntes_se_rechaza():

    from pypdf import PdfWriter

    from io import BytesIO

    w = PdfWriter()

    w.add_blank_page(width=400, height=400)

    buf = BytesIO()

    w.write(buf)

    basura = buf.getvalue()

    from app.domain.antecedentes import validar_certificado_antecedentes

    r = validar_certificado_antecedentes(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF",
        nombre_archivo="apuntes-clase.pdf",
        producer="Word",
        encrypted=False,
        num_paginas=3,
        texto="Apuntes de clase: el Registro Civil emite certificados. Hablar de certificado de antecedentes en general. Codigo 513bd82d89e7 folio 500727268737",
    )

    assert r.aceptado is False

    assert r.anotaciones is None


def test_endpoint_antecedentes_suma_xp(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    antes = client.get("/v1/perfil", headers=h).json()["xp"]

    with FIXTURE.open("rb") as f:

        r = client.post(
            "/v1/perfil/antecedentes",
            headers=h,
            files={"archivo": (FIXTURE.name, f, "application/pdf")},
            data={"nombre_archivo": FIXTURE.name},
        )

    assert r.status_code == 201, r.text

    body = r.json()

    assert body["antecedentes_verificados"] is True

    assert body["antecedentes_anotaciones"] is False

    assert body["antecedentes_score"] >= 70

    assert body["xp"] == antes + reglas.XP_ANTECEDENTES

    r2 = client.post(
        "/v1/perfil/antecedentes",
        headers=h,
        files={"archivo": (FIXTURE.name, FIXTURE.read_bytes(), "application/pdf")},
        data={"nombre_archivo": FIXTURE.name},
    )

    assert r2.status_code == 201

    assert r2.json()["xp"] == antes + reglas.XP_ANTECEDENTES

    perfil = client.get("/v1/perfil", headers=h).json()

    assert perfil["antecedentes_verificados"] is True

    assert perfil["antecedentes_anotaciones"] is False

    reporte = client.get("/v1/reporte", headers=h).json()

    assert reporte["antecedentes_verificados"] is True

    assert reporte["antecedentes_anotaciones"] is False


def test_pdf_basura_da_422(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/v1/perfil/antecedentes",
        headers=h,
        files={"archivo": ("falso.pdf", b"no es un pdf", "application/pdf")},
    )

    assert r.status_code == 422
