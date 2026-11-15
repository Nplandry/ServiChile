from __future__ import annotations

import math

import re

from dataclasses import dataclass

PESO_CIBER = "3.0%"

PESO_OPERATIVA = "4.0%"

PESO_CONTRACTUAL = "4.0%"


@dataclass(frozen=True)
class DefinicionObservable:

    id: str

    etiqueta: str

    detalle: str

    grupo: str

    peso: str


OBSERVABLES_SONDA = (
    DefinicionObservable(
        id="ssl-tls",
        etiqueta="Vigencia y calidad de certificados SSL/TLS",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="email-auth",
        etiqueta="Seguridad de correo y registros DNS",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="puertos",
        etiqueta="Exposición de puertos y servicios críticos",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="headers-http",
        etiqueta="Cabeceras de seguridad HTTP",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="stack-vulnerable",
        etiqueta="Tecnologías web obsoletas o vulnerables (CVEs abiertos)",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="blacklist",
        etiqueta="Reputación de IP y dominio en listas negras globales",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="dnssec",
        etiqueta="Protección de infraestructura DNS y secuestro de dominios",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="subdominios",
        etiqueta="Seguridad en subdominios expuestos (Shadow IT)",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="whois",
        etiqueta="Antigüedad, configuración y estabilidad del dominio",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="uptime",
        etiqueta="Continuidad operativa y estabilidad de infraestructura (uptime)",
        detalle="",
        grupo="operativa",
        peso=PESO_OPERATIVA,
    ),
    DefinicionObservable(
        id="cookies",
        etiqueta="Consentimiento de cookies y rastreadores",
        detalle="",
        grupo="contractual",
        peso=PESO_CONTRACTUAL,
    ),
)

OBSERVABLE_RESENAS = DefinicionObservable(
    id="resenas-reclamos",
    etiqueta="Calificación y volumen de reseñas en Google",
    detalle="",
    grupo="operativa",
    peso=PESO_OPERATIVA,
)


@dataclass(frozen=True)
class HallazgosSsl:

    https_ok: bool = False

    cert_vigente: bool = False

    no_autofirmado: bool = False

    tls_moderno: bool = False


@dataclass(frozen=True)
class HallazgosHeaders:

    hsts: bool = False

    csp: bool = False

    x_frame_options: bool = False

    x_content_type_options: bool = False


@dataclass(frozen=True)
class HallazgosEmailAuth:

    spf: bool = False

    dkim: bool = False

    dmarc: bool = False


@dataclass(frozen=True)
class HallazgosPuertos:

    abiertos: tuple[int, ...] = ()


@dataclass(frozen=True)
class HallazgosStack:

    server_header: str | None = None

    powered_by: str | None = None


@dataclass(frozen=True)
class HallazgosBlacklist:

    marcado_malware: bool = False

    marcado_phishing: bool = False

    marcado_spam: bool = False


@dataclass(frozen=True)
class HallazgosDnssec:

    tiene_ns: bool = False

    tiene_ds_o_dnskey: bool = False

    ns_count: int = 0


@dataclass(frozen=True)
class HallazgosSubdominios:

    expuestos: tuple[str, ...] = ()


@dataclass(frozen=True)
class HallazgosWhois:

    edad_anios: float | None = None

    dns_configurado: bool = False

    renovacion_vigente: bool = False


@dataclass(frozen=True)
class HallazgosUptime:

    responde: bool = False

    status_ok: bool = False


@dataclass(frozen=True)
class HallazgosCookies:

    banner_detectado: bool = False

    script_cmp: bool = False

    opcion_rechazar: bool = False

    html_obtenido: bool = False


@dataclass(frozen=True)
class ObservableScore:

    id: str

    etiqueta: str

    detalle: str

    score: int

    peso: str

    grupo: str


def _clamp_score(valor: float) -> int:

    return int(max(0, min(100, round(valor))))


def score_ssl_tls(h: HallazgosSsl) -> int:

    total = 0.0

    if h.https_ok:

        total += 40

    if h.cert_vigente:

        total += 25

    if h.no_autofirmado:

        total += 20

    if h.tls_moderno:

        total += 15

    return _clamp_score(total)


def score_headers_http(h: HallazgosHeaders) -> int:

    total = 0.0

    if h.hsts:

        total += 25

    if h.csp:

        total += 25

    if h.x_frame_options:

        total += 25

    if h.x_content_type_options:

        total += 25

    return _clamp_score(total)


def score_email_auth(h: HallazgosEmailAuth) -> int:

    total = 0.0

    if h.spf:

        total += 40

    if h.dmarc:

        total += 40

    if h.dkim:

        total += 20

    return _clamp_score(total)


PUERTOS_CRITICOS = (22, 23, 445, 3389, 3306, 5432, 27017, 6379, 9200)


def score_puertos(h: HallazgosPuertos) -> int:

    total = 100.0 - 18.0 * len(set(h.abiertos))

    return _clamp_score(max(10.0, total))


def score_stack_vulnerable(h: HallazgosStack) -> int:

    total = 85.0

    blob = f"{h.server_header or ''} {h.powered_by or ''}".lower()

    if not blob.strip():

        return 70

    riesgos = (
        ("php/5", 35),
        ("php/7.0", 25),
        ("php/7.1", 20),
        ("apache/2.2", 30),
        ("iis/7", 25),
        ("iis/8.0", 15),
        ("openssl/1.0", 30),
        ("asp.net", 5),
        ("wordpress", 10),
        ("nginx/1.1", 15),
    )

    for marca, resta in riesgos:

        if marca in blob:

            total -= resta

    if "nginx" in blob or "cloudflare" in blob:

        total += 5

    return _clamp_score(total)


def score_blacklist(h: HallazgosBlacklist) -> int:

    total = 100.0

    if h.marcado_malware:

        total -= 45

    if h.marcado_phishing:

        total -= 40

    if h.marcado_spam:

        total -= 20

    return _clamp_score(total)


def score_dnssec(h: HallazgosDnssec) -> int:

    total = 0.0

    if h.tiene_ns:

        total += 40

    if h.ns_count >= 2:

        total += 20

    elif h.ns_count == 1:

        total += 8

    if h.tiene_ds_o_dnskey:

        total += 40

    return _clamp_score(total)


def score_subdominios(h: HallazgosSubdominios) -> int:

    total = 100.0 - 20.0 * len(set(h.expuestos))

    return _clamp_score(max(15.0, total))


def score_whois(h: HallazgosWhois) -> int:

    total = 0.0

    if h.edad_anios is None:

        total += 20

    elif h.edad_anios >= 10:

        total += 50

    elif h.edad_anios >= 5:

        total += 40

    elif h.edad_anios >= 2:

        total += 30

    elif h.edad_anios >= 1:

        total += 20

    else:

        total += 10

    if h.dns_configurado:

        total += 25

    if h.renovacion_vigente:

        total += 25

    return _clamp_score(total)


def score_uptime(h: HallazgosUptime) -> int:

    if h.responde and h.status_ok:

        return 100

    if h.responde:

        return 55

    return 15


_BANNER_PATRONES = (
    "cookie-banner",
    "cookie_banner",
    "cookiebanner",
    "cookie-consent",
    "cookie_consent",
    "cookieconsent",
    "cookies-banner",
    "consent-banner",
    "consent_banner",
    "cookie-notice",
    "cookie_notice",
    "cookie-popup",
    "cookie-modal",
    "cc-banner",
    "cc-window",
    "ot-sdk",
    "onetrust",
    "cky-consent",
    "utilizamos cookies",
    "usamos cookies",
    "we use cookies",
    "this site uses cookies",
    "este sitio utiliza cookies",
    "aceptar cookies",
    "accept cookies",
    "acepto las cookies",
    "gestionar cookies",
    "manage cookies",
    "preferencias de cookies",
    "cookie preferences",
)

_CMP_PATRONES = (
    "onetrust",
    "cookiebot",
    "cookielaw.org",
    "cdn.cookielaw",
    "trustarc",
    "quantcast.mgr",
    "iubenda",
    "didomi",
    "usercentrics",
    "osano.com",
    "cookieyes",
    "termly.io",
    "complianz",
    "cookieconsent",
    "cookie-consent",
    "gdpr-cookie",
    "civicuk.com/cookie",
    "axeptio",
    "sirdata",
)

_RECHAZAR_PATRONES = (
    "rechazar",
    "rechazar todas",
    "rechazar cookies",
    "solo esenciales",
    "solo necesarias",
    "cookies necesarias",
    "reject all",
    "reject cookies",
    "decline cookies",
    "deny cookies",
    "necessary only",
    "essential only",
    "only necessary",
    "opt-out",
    "opt out",
    "no aceptar",
)


def detectar_cookies_html(html: str) -> HallazgosCookies:

    if not html or not html.strip():

        return HallazgosCookies(html_obtenido=False)

    texto = html.lower()

    banner = any((p in texto for p in _BANNER_PATRONES))

    if not banner and re.search(
        "(id|class)=[\"\\'][^\"\\']*cookie[^\"\\']*(banner|consent|notice|popup|modal)",
        texto,
    ):

        banner = True

    cmp = any((p in texto for p in _CMP_PATRONES))

    rechazar = any((p in texto for p in _RECHAZAR_PATRONES))

    return HallazgosCookies(
        banner_detectado=banner,
        script_cmp=cmp,
        opcion_rechazar=rechazar,
        html_obtenido=True,
    )


def score_cookies(h: HallazgosCookies) -> int:

    neutro = 85

    if not h.html_obtenido:

        return neutro

    if not (h.banner_detectado or h.script_cmp or h.opcion_rechazar):

        return neutro

    total = float(neutro)

    if h.banner_detectado:

        total += 5

    if h.script_cmp:

        total += 5

    if h.opcion_rechazar:

        total += 5

    return _clamp_score(total)


_RESENAS_PRIOR = 3.2

_RESENAS_PRIOR_PESO = 24.0

_RESENAS_VOLUMEN_REF = 1500.0


def score_resenas(google_rating_avg: float | None, google_reviews_count: int) -> int:

    rating = max(0.0, min(5.0, float(google_rating_avg or 0.0)))

    reviews = max(0, int(google_reviews_count or 0))

    if reviews <= 0:

        return 20

    bayes = (_RESENAS_PRIOR * _RESENAS_PRIOR_PESO + rating * reviews) / (
        _RESENAS_PRIOR_PESO + reviews
    )

    rating_part = (bayes / 5.0) * 60.0 + 18.0

    volume_part = min(
        24.0, math.log1p(reviews) / math.log1p(_RESENAS_VOLUMEN_REF) * 24.0
    )

    return _clamp_score(min(92.0, rating_part + volume_part))


def razones_resenas(
    *,
    ficha: str | None,
    google_rating_avg: float | None,
    google_reviews_count: int,
    score: int | None = None,
) -> list[str]:

    out: list[str] = []

    nombre = (ficha or "").strip()

    if nombre:

        out.append(f"Ficha: {nombre}")

    else:

        out.append("Ficha: sin match en Google Places")

    if google_rating_avg is None:

        out.append("Rating Google: n/d")

    else:

        out.append(f"Rating Google: {float(google_rating_avg):.1f} / 5")

    reviews = max(0, int(google_reviews_count or 0))

    out.append(f"Reseñas: {reviews:,}".replace(",", "."))

    if score is not None:

        out.append(f"Score: {int(score)} / 100")

    return out


def armar_observables(valores: dict[str, int]) -> list[ObservableScore]:

    from app.domain.transparencia.cmf import OBSERVABLE_CMF

    from app.domain.transparencia.mercado_publico import OBSERVABLE_MERCADO_PUBLICO

    from app.domain.transparencia.sii import OBSERVABLE_SII

    out: list[ObservableScore] = []

    for d in OBSERVABLES_SONDA:

        if d.id not in valores:

            continue

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if "mercado-publico" in valores:

        d = OBSERVABLE_MERCADO_PUBLICO

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if "sii" in valores:

        d = OBSERVABLE_SII

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if "cmf" in valores:

        d = OBSERVABLE_CMF

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if "incidentes" in valores:

        from app.domain.transparencia.incidentes import OBSERVABLE_INCIDENTES

        d = OBSERVABLE_INCIDENTES

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if "resenas-reclamos" in valores:

        d = OBSERVABLE_RESENAS

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    if any(k in valores for k in ("politica-privacidad", "terminos", "sla")):

        from app.domain.transparencia.docs_legales import (
            OBSERVABLE_PRIVACIDAD,
            OBSERVABLE_SLA,
            OBSERVABLE_TERMINOS,
        )

        for d in (OBSERVABLE_PRIVACIDAD, OBSERVABLE_TERMINOS, OBSERVABLE_SLA):

            if d.id in valores:

                out.append(
                    ObservableScore(
                        id=d.id,
                        etiqueta=d.etiqueta,
                        detalle=d.detalle,
                        score=_clamp_score(valores[d.id]),
                        peso=d.peso,
                        grupo=d.grupo,
                    )
                )

    return out
