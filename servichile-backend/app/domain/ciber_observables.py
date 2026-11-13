from __future__ import annotations
import math
from dataclasses import dataclass
PESO_CIBER = '3.0%'
PESO_OPERATIVA = '4.0%'

@dataclass(frozen=True)
class DefinicionObservable:
    id: str
    etiqueta: str
    detalle: str
    grupo: str
    peso: str
OBSERVABLES_SONDA = (DefinicionObservable(id='ssl-tls', etiqueta='Vigencia y calidad de certificados SSL/TLS', detalle='HTTPS válido, TLS moderno y ausencia de certificados expirados o autofirmados.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='email-auth', etiqueta='Seguridad de correo (SPF, DKIM, DMARC)', detalle='Registros DNS para prevenir spoofing y suplantación de identidad corporativa.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='puertos', etiqueta='Exposición de puertos y servicios críticos', detalle='Detección pasiva de puertos/servicios administrativos abiertos (RDP, SSH, DB, SMB).', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='headers-http', etiqueta='Cabeceras de seguridad HTTP', detalle='HSTS, CSP, X-Frame-Options y X-Content-Type-Options.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='stack-vulnerable', etiqueta='Tecnologías web obsoletas o vulnerables (CVEs abiertos)', detalle='CMS, servidores o librerías con CVEs críticos conocidos sin remediación.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='blacklist', etiqueta='Reputación de IP y dominio en listas negras globales', detalle='Marcas por malware, phishing o spam en blocklists globales.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='dnssec', etiqueta='Protección de infraestructura DNS y secuestro de dominios', detalle='DNSSEC, DNS resiliente y señales de riesgo de hijacking.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='subdominios', etiqueta='Seguridad en subdominios expuestos (Shadow IT)', detalle='Entornos dev/staging/test u otros subdominios públicos sin autenticación.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='whois', etiqueta='Antigüedad, configuración y estabilidad del dominio', detalle='Edad WHOIS, configuración DNS y vigencia de renovación.', grupo='ciber', peso=PESO_CIBER), DefinicionObservable(id='uptime', etiqueta='Continuidad operativa y estabilidad de infraestructura (uptime)', detalle='Disponibilidad histórica de canales digitales e infraestructura.', grupo='operativa', peso=PESO_OPERATIVA))
OBSERVABLE_RESENAS = DefinicionObservable(id='resenas-reclamos', etiqueta='Reseñas B2B verificadas, satisfacción y resolución de reclamos', detalle='Calificaciones B2B validadas y tasa de respuesta/resolución de reclamos.', grupo='operativa', peso=PESO_OPERATIVA)

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
    blob = f'{h.server_header or ''} {h.powered_by or ''}'.lower()
    if not blob.strip():
        return 70
    riesgos = (('php/5', 35), ('php/7.0', 25), ('php/7.1', 20), ('apache/2.2', 30), ('iis/7', 25), ('iis/8.0', 15), ('openssl/1.0', 30), ('asp.net', 5), ('wordpress', 10), ('nginx/1.1', 15))
    for marca, resta in riesgos:
        if marca in blob:
            total -= resta
    if 'nginx' in blob or 'cloudflare' in blob:
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

def score_resenas(google_rating_avg: float | None, google_reviews_count: int) -> int:
    rating = float(google_rating_avg or 0.0)
    reviews = max(0, int(google_reviews_count or 0))
    rating_part = max(0.0, min(5.0, rating)) / 5.0 * 55.0 + 20.0
    volume_part = min(25.0, math.log1p(reviews) / math.log1p(500) * 25.0) if reviews else 0.0
    return _clamp_score(min(92.0, rating_part + volume_part))

def armar_observables(valores: dict[str, int]) -> list[ObservableScore]:
    out: list[ObservableScore] = []
    for d in OBSERVABLES_SONDA:
        if d.id not in valores:
            continue
        out.append(ObservableScore(id=d.id, etiqueta=d.etiqueta, detalle=d.detalle, score=_clamp_score(valores[d.id]), peso=d.peso, grupo=d.grupo))
    if 'resenas-reclamos' in valores:
        d = OBSERVABLE_RESENAS
        out.append(ObservableScore(id=d.id, etiqueta=d.etiqueta, detalle=d.detalle, score=_clamp_score(valores[d.id]), peso=d.peso, grupo=d.grupo))
    return out
