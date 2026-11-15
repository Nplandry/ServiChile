import uuid

from app.dominio.transparencia.indicadores import (
    HallazgosBlacklist,
    HallazgosCookies,
    HallazgosDnssec,
    HallazgosEmailAuth,
    HallazgosHeaders,
    HallazgosPuertos,
    HallazgosSsl,
    HallazgosStack,
    HallazgosSubdominios,
    HallazgosUptime,
    HallazgosWhois,
    detectar_cookies_html,
    score_blacklist,
    score_cookies,
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

from app.infraestructura.ciber.sonda import MuestraCiberSonda

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
    "cookies",
    "politica-privacidad",
    "terminos",
    "sla",
}

IDS_API = IDS_SONDA | {
    "resenas-reclamos",
    "mercado-publico",
    "sii",
    "cmf",
    "incidentes",
}

IDS_CONTRACTUAL = {"cookies", "politica-privacidad", "terminos", "sla"}


def test_score_ssl_completo_es_100():

    assert (
        score_ssl_tls(
            HallazgosSsl(
                https_ok=True, cert_vigente=True, no_autofirmado=True, tls_moderno=True
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

    assert (
        score_dnssec(HallazgosDnssec(tiene_ns=True, tiene_ds_o_dnskey=True, ns_count=2))
        == 100
    )


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

    assert score_resenas(5.0, 2) <= 70

    assert score_resenas(4.2, 2383) >= 88

    assert score_resenas(5.0, 2) < score_resenas(4.2, 2383)

    assert score_resenas(5.0, 10) < score_resenas(5.0, 200)


def test_detectar_cookies_banner_cmp_y_rechazo():

    html = '\n    <div id="cookie-banner">Usamos cookies.\n      <script src="https://cdn.cookielaw.org/scripttemplates/otSDKStub.js"></script>\n      <button>Rechazar todas</button>\n    </div>\n    '

    h = detectar_cookies_html(html)

    assert h.banner_detectado is True

    assert h.script_cmp is True

    assert h.opcion_rechazar is True

    assert score_cookies(h) == 100


def test_score_cookies_sin_senales_ni_404_no_castiga():

    assert score_cookies(HallazgosCookies(html_obtenido=False)) == 85

    assert score_cookies(HallazgosCookies(html_obtenido=True)) == 85

    assert (
        score_cookies(HallazgosCookies(banner_detectado=True, html_obtenido=True)) == 90
    )


def test_muestra_sonda_sin_url_usa_perfil():

    res = MuestraCiberSonda().escanear(None)

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

    assert por_id["cookies"] == 84

    assert por_id["politica-privacidad"] == 72

    assert por_id["terminos"] == 70

    assert por_id["sla"] == 48


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

        if o["id"] in ("uptime", "resenas-reclamos", "incidentes"):

            assert o["peso"] == "4.0%"

            assert o["grupo"] == "operativa"

            if o["id"] == "incidentes":

                assert o["score"] in (0, 100)

        elif o["id"] in IDS_CONTRACTUAL:

            assert o["peso"] == "4.0%"

            assert o["grupo"] == "contractual"

        elif o["id"] in ("mercado-publico", "sii", "cmf"):

            assert o["peso"] == "3.0%"

            assert o["grupo"] == "legal"

            assert o["score"] == 0

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
        f"/v1/businesses/{bid}/ciber-scan", headers={"Authorization": f"Bearer {token}"}
    )

    assert ajeno.status_code == 403

    propio = client.post(
        f"/v1/businesses/{bid}/ciber-scan",
        headers={"Authorization": f"Bearer {token_empresa}"},
    )

    assert propio.status_code == 200

    assert len(propio.json()["observables_ciber"]) == len(IDS_API)


def test_mercado_sii_y_cmf_reales_con_rut(client, token_empresa):

    from app.api.dependencias import (
        get_chilecompra,
        get_cmf_indice,
        get_incidentes_scanner,
        get_places_google,
        get_sii_contribuyentes,
    )

    from app.infraestructura.chilecompra import MuestraChileCompra

    from app.infraestructura.cmf.indice import MuestraCmfIndice

    from app.infraestructura.busqueda.escaner import MuestraIncidentesScanner

    from app.infraestructura.lugares_google import MuestraPlacesGoogle

    from app.infraestructura.sii import MuestraSiiContribuyentes

    from app.principal import app

    app.dependency_overrides[get_chilecompra] = lambda: MuestraChileCompra()

    app.dependency_overrides[get_sii_contribuyentes] = lambda: MuestraSiiContribuyentes()

    app.dependency_overrides[get_cmf_indice] = lambda: MuestraCmfIndice()

    app.dependency_overrides[get_incidentes_scanner] = lambda: MuestraIncidentesScanner()

    app.dependency_overrides[get_places_google] = lambda: MuestraPlacesGoogle()

    try:

        alta = client.post(
            "/v1/businesses",
            headers={"Authorization": f"Bearer {token_empresa}"},
            json={
                "nombre": "Proveedor MP SpA",
                "categoria": "tecnologia",
                "direccion": "Av. Apoquindo 1, Santiago",
                "sitio_web": "https://proveedor-mp.cl",
                "documento_verificacion": "76.543.210-3",
            },
        )

        assert alta.status_code == 201

        bid = alta.json()["id"]

        r = client.post(
            f"/v1/businesses/{bid}/ciber-scan",
            headers={"Authorization": f"Bearer {token_empresa}"},
        )

        assert r.status_code == 200

        cuerpo = r.json()

        ids = {o["id"]: o for o in cuerpo["observables_ciber"]}

        assert set(ids) == IDS_API

        assert ids["mercado-publico"]["score"] == 100

        assert ids["sii"]["score"] == 100

        assert ids["cmf"]["score"] == 100

        assert ids["cmf"]["grupo"] == "legal"

        assert ids["incidentes"]["score"] == 100

        assert ids["incidentes"]["grupo"] == "operativa"

        assert cuerpo["google_rating_avg"] == 4.5

        assert cuerpo["google_reviews_count"] == 120

        assert ids["resenas-reclamos"]["score"] >= 70

        razones = ids["resenas-reclamos"].get("razones") or []

        assert any(str(x).startswith("Ficha:") for x in razones)

        assert any("Rating Google:" in str(x) for x in razones)

        assert any(str(x).startswith("Reseñas:") for x in razones)

    finally:

        app.dependency_overrides.pop(get_chilecompra, None)

        app.dependency_overrides.pop(get_sii_contribuyentes, None)

        app.dependency_overrides.pop(get_cmf_indice, None)

        app.dependency_overrides.pop(get_incidentes_scanner, None)

        app.dependency_overrides.pop(get_places_google, None)


def test_reputacion_inexistente(client):

    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")

    assert r.status_code == 404
