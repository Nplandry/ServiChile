"""Pruebas de scores ciber (dominio) y exposición en reputación."""
import uuid

from app.domain.ciber_observables import (
    HallazgosBlacklist,
    HallazgosDnssec,
    HallazgosEmailAuth,
    HallazgosHeaders,
    HallazgosPuertos,
    HallazgosSsl,
    HallazgosStack,
    HallazgosSubdominios,
    HallazgosUptime,
    HallazgosWhois,
    score_blacklist,
    score_dnssec,
    score_email_auth,
    score_headers_http,
    score_puertos,
    score_resenas,
    score_ssl_tls,
    score_stack_vulnerable,
    score_subdominios,
    score_uptime,
    score_whois,
)
from app.infrastructure.ciber_sonda import FakeCiberSonda

IDS_SONDA = {
    "ssl-tls",
    "email-auth",
    "puertos",
    "headers-http",
    "stack-vulnerable",
    "blacklist",
    "dnssec",
    "subdominios",
    "whois",
    "uptime",
}
IDS_API = IDS_SONDA | {"resenas-reclamos"}


def test_score_ssl_completo_es_100():
    assert (
        score_ssl_tls(
            HallazgosSsl(
                https_ok=True,
                cert_vigente=True,
                no_autofirmado=True,
                tls_moderno=True,
            )
        )
        == 100
    )


def test_score_headers_parcial():
    assert score_headers_http(HallazgosHeaders(hsts=True, csp=True)) == 50


def test_score_email_auth_spf_dmarc():
    assert score_email_auth(HallazgosEmailAuth(spf=True, dmarc=True)) == 80
    assert score_email_auth(HallazgosEmailAuth(spf=True, dkim=True, dmarc=True)) == 100


def test_score_puertos_con_abiertos():
    assert score_puertos(HallazgosPuertos()) == 100
    assert score_puertos(HallazgosPuertos(abiertos=(22, 3389))) == 64


def test_score_stack_sin_banner():
    assert score_stack_vulnerable(HallazgosStack()) == 70


def test_score_blacklist_limpio_y_spam():
    assert score_blacklist(HallazgosBlacklist()) == 100
    assert score_blacklist(HallazgosBlacklist(marcado_spam=True)) == 80


def test_score_dnssec_completo():
    assert score_dnssec(HallazgosDnssec(tiene_ns=True, tiene_ds_o_dnskey=True, ns_count=2)) == 100


def test_score_subdominios_expuestos():
    assert score_subdominios(HallazgosSubdominios()) == 100
    assert score_subdominios(HallazgosSubdominios(expuestos=("dev", "staging"))) == 60


def test_score_whois_antiguo_estable():
    assert (
        score_whois(
            HallazgosWhois(edad_anios=12, dns_configurado=True, renovacion_vigente=True)
        )
        == 100
    )


def test_score_uptime_y_resenas():
    assert score_uptime(HallazgosUptime(responde=True, status_ok=True)) == 100
    assert score_uptime(HallazgosUptime()) == 15
    assert 40 <= score_resenas(4.5, 120) <= 92


def test_fake_sonda_sin_url_usa_perfil_demo():
    res = FakeCiberSonda().escanear(None)
    por_id = {o.id: o.score for o in res.observables}
    assert set(por_id) == IDS_SONDA
    assert por_id["ssl-tls"] == 83
    assert por_id["email-auth"] == 80
    assert por_id["puertos"] == 88
    assert por_id["headers-http"] == 79
    assert por_id["stack-vulnerable"] == 74
    assert por_id["blacklist"] == 77
    assert por_id["dnssec"] == 72
    assert por_id["subdominios"] == 85
    assert por_id["whois"] == 73
    assert por_id["uptime"] == 90


def test_reputacion_incluye_observables_ciber(client, token_empresa):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Ciber Demo SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Providencia 100, Santiago",
            "sitio_web": "https://ejemplo-ciber.cl",
        },
    )
    assert alta.status_code == 201
    bid = alta.json()["id"]

    r = client.get(f"/v1/businesses/{bid}/reputation")
    assert r.status_code == 200
    cuerpo = r.json()
    obs = cuerpo["observables_ciber"]
    assert len(obs) == len(IDS_API)
    ids = {o["id"] for o in obs}
    assert ids == IDS_API
    for o in obs:
        assert 0 <= o["score"] <= 100
        if o["id"] in ("uptime", "resenas-reclamos"):
            assert o["peso"] == "4.0%"
            assert o["grupo"] == "operativa"
        else:
            assert o["peso"] == "3.0%"
            assert o["grupo"] == "ciber"


def test_ciber_scan_solo_titular(client, token, token_empresa):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Titular Scan SpA",
            "categoria": "logistica",
            "direccion": "Av. Matta 50, Santiago",
            "sitio_web": "https://titular-scan.cl",
        },
    )
    bid = alta.json()["id"]

    ajeno = client.post(
        f"/v1/businesses/{bid}/ciber-scan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ajeno.status_code == 403

    propio = client.post(
        f"/v1/businesses/{bid}/ciber-scan",
        headers={"Authorization": f"Bearer {token_empresa}"},
    )
    assert propio.status_code == 200
    assert len(propio.json()["observables_ciber"]) == len(IDS_API)


def test_reputacion_inexistente(client):
    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")
    assert r.status_code == 404
