import uuid

from fastapi.testclient import TestClient

from app.dominio.radar_comercial import DatosReporte, lineas_reporte
from app.infraestructura.persistencia.modelos import (
    EntidadNegocio,
    MetricasReputacionNegocio,
)

def test_el_resumen_textual_no_es_el_radar():
    texto = "\n".join(
        lineas_reporte(
            DatosReporte(
                nombre="Gearlabs",
                categoria="tecnologia",
                rut="76.123.456-0",
                direccion="Las Condes",
                telefono=None,
                sitio_web=None,
                descripcion="Software",
                indice=3.0,
                indice_pct=30,
                docs_verificados=1,
                docs_total=11,
                servicios=("Bodega",),
                industrias=("mineria",),
                contrataciones=(),
                monto="medio",
                plazo=None,
                referencias=(),
            )
        )
    )
    assert "Reporte de transparencia empresarial" in texto
    assert "Alerta Legal" not in texto

def test_smtp_de_plataforma_avisa_al_correo_del_registro(
    client: TestClient, session_factory
):
    email = f"reporte.{uuid.uuid4().hex[:8]}@example.com"
    assert (
        client.post(
            "/v1/auth/registro",
            json={
                "email": email,
                "nombre": "Ana Pérez",
                "password": "clave-segura-123",
                "perfil": {"tipo_cuenta": "persona"},
            },
        ).status_code
        == 201
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": "clave-segura-123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with session_factory() as s:
        negocio = EntidadNegocio(
            nombre="Gearlabs", categoria="tecnologia", rut_empresa="76123456-0"
        )
        s.add(negocio)
        s.flush()
        s.add(MetricasReputacionNegocio(business_id=negocio.id, final_score=3.0))
        s.commit()
        business_id = negocio.id

    ini = client.post(
        "/v1/pagos/informe",
        json={"business_id": str(business_id)},
        headers=headers,
    ).json()
    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200, conf.text

    out = client.post(f"/v1/businesses/{business_id}/informe-riesgo", headers=headers)
    assert out.status_code == 200, out.text
    cuerpo = out.json()
    assert cuerpo["destino"] == email
    assert cuerpo["enviado"] is True
    assert "qr_payload" in cuerpo
