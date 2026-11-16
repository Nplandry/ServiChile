from uuid import uuid4

from app.dominio.entidades import Negocio
from app.dominio.transparencia.rater.parametros import IDS_ESTADO, PARAMETROS
from app.infraestructura.rater.adaptador import AdaptadorRater, RaterConfig


def _negocio(**kwargs) -> Negocio:
    base = dict(
        id=uuid4(),
        nombre="Demo SpA",
        categoria="tecnologia",
        latitud=None,
        longitud=None,
        direccion=None,
        descripcion=None,
        imagen_url=None,
        logo_url=None,
        requiere_nivel=1,
        is_claimed=True,
        telefono=None,
        sitio_web=None,
        rut_empresa=None,
        docs_empresa={},
    )
    base.update(kwargs)
    return Negocio(**base)


def test_rater_muestra_sin_campos_deja_ceros():
    svc = AdaptadorRater(
        RaterConfig(modo="muestra", app_env="test", places_mode="muestra", chilecompra_mode="muestra")
    )
    res = svc.evaluar(_negocio())
    assert len(res.parametros) == len(PARAMETROS)
    by_id = {p.id: p for p in res.parametros}
    assert by_id["fis_address"].score == 0.0
    assert by_id["fis_phone"].score == 0.0
    for pid in IDS_ESTADO:
        assert by_id[pid].score == 0.0
    assert by_id["dig_website"].score == 0.0
    assert by_id["cyb_https"].score == 0.0


def test_rater_muestra_con_ficha_completa_tiene_scores():
    svc = AdaptadorRater(
        RaterConfig(modo="muestra", app_env="local", places_mode="muestra", chilecompra_mode="muestra")
    )
    res = svc.evaluar(
        _negocio(
            direccion="Av. Providencia 100, Santiago",
            telefono="+56911111111",
            sitio_web="https://ejemplo.cl",
            rut_empresa="76123456-0",
        )
    )
    by_id = {p.id: p for p in res.parametros}
    assert by_id["fis_address"].score and by_id["fis_address"].score > 0
    assert by_id["fis_phone"].score and by_id["fis_phone"].score > 0
    assert by_id["est_proveedor"].score and by_id["est_proveedor"].score > 0
    assert by_id["dig_website"].score == 100.0
    assert res.overall_score is not None
    obs = res.a_observables()
    assert len(obs) == len(PARAMETROS)
    assert {o.grupo for o in obs} >= {"ciber", "contractual", "operativa", "legal"}


def test_reputacion_incluye_observables_rater(client, token_empresa):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Rater Demo SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Apoquindo 3000, Las Condes",
            "sitio_web": "https://rater-demo.cl",
            "rut_empresa": "76999888-5",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    r = client.get(f"/v1/businesses/{bid}/reputation")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["observables"]) >= len(PARAMETROS)
    ids = {o["id"] for o in cuerpo["observables"]}
    assert "fis_address" in ids and "est_proveedor" in ids and "cyb_https" in ids


def test_rater_refresh_titular_refresca_indice(client, token_empresa):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Scan SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Providencia 100, Santiago",
            "sitio_web": "https://scan-demo.cl",
            "rut_empresa": "76888777-2",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    r = client.post(f"/v1/businesses/{bid}/rater-refresh", headers=h)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["business_id"] == bid
    assert len(cuerpo["observables"]) >= len(PARAMETROS)
    assert "descargo" in cuerpo


def test_rater_refresh_ajeno_da_403(client, token_empresa, token):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Ajeno Scan SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Las Condes 1, Las Condes",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    r = client.post(
        f"/v1/businesses/{bid}/rater-refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
