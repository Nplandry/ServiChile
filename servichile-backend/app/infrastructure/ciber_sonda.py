from __future__ import annotations
import hashlib
import ipaddress
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from app.domain.ciber_observables import HallazgosBlacklist, HallazgosDnssec, HallazgosEmailAuth, HallazgosHeaders, HallazgosPuertos, HallazgosSsl, HallazgosStack, HallazgosSubdominios, HallazgosUptime, HallazgosWhois, ObservableScore, PUERTOS_CRITICOS, armar_observables, score_blacklist, score_dnssec, score_email_auth, score_headers_http, score_puertos, score_ssl_tls, score_stack_vulnerable, score_subdominios, score_uptime, score_whois
from app.infrastructure.ciber_dns import doh_a, doh_ns, doh_tiene_tipo, doh_txt
_SUBS_SENSIBLES = ('dev', 'staging', 'test', 'admin', 'vpn', 'mail', 'ftp', 'db', 'beta')
_DKIM_SELECTORS = ('default', 'google', 'selector1', 'selector2', 'k1', 's1', 'dkim')
_UA = 'ServiChile-CiberSonda/1.0'
_SCORES_SIN_HOST_FAKE = {'ssl-tls': 83, 'email-auth': 80, 'puertos': 88, 'headers-http': 79, 'stack-vulnerable': 74, 'blacklist': 77, 'dnssec': 72, 'subdominios': 85, 'whois': 73, 'uptime': 90}
_SCORES_SIN_HOST_LIVE = {'ssl-tls': 0, 'email-auth': 0, 'puertos': 50, 'headers-http': 0, 'stack-vulnerable': 50, 'blacklist': 50, 'dnssec': 0, 'subdominios': 50, 'whois': 0, 'uptime': 15}

@dataclass(frozen=True)
class ResultadoSondaCiber:
    observables: list[ObservableScore]
    host: str | None
    scores: dict[str, int]

class CiberSonda(Protocol):

    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber:
        ...

def _host_de(sitio_web: str | None) -> str | None:
    if not sitio_web or not str(sitio_web).strip():
        return None
    texto = str(sitio_web).strip()
    if '://' not in texto:
        texto = 'https://' + texto
    host = urllib.parse.urlparse(texto).hostname
    return host.lower() if host else None

def _registrable(host: str) -> str:
    h = host.lower().strip('.')
    if h.startswith('www.'):
        h = h[4:]
    return h

def _cert_vigente(cert: dict | None) -> bool:
    if not cert or 'notAfter' not in cert:
        return False
    fin = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    return fin > datetime.now(timezone.utc)

def _tls_moderno(version: str) -> bool:
    return version in ('TLSv1.2', 'TLSv1.3')

def _resultado(scores: dict[str, int], host: str | None) -> ResultadoSondaCiber:
    return ResultadoSondaCiber(armar_observables(scores), host, scores)

class FakeCiberSonda:

    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber:
        host = _host_de(sitio_web)
        if host is None:
            return _resultado(dict(_SCORES_SIN_HOST_FAKE), None)
        n = int(hashlib.sha256(host.encode()).hexdigest()[:8], 16)

        def v(base: int, spread: int, shift: int) -> int:
            return base + (n >> shift) % (spread + 1)
        scores = {'ssl-tls': v(70, 25, 0), 'email-auth': v(55, 40, 3), 'puertos': v(70, 28, 6), 'headers-http': v(50, 45, 5), 'stack-vulnerable': v(60, 30, 8), 'blacklist': v(70, 28, 10), 'dnssec': v(45, 50, 12), 'subdominios': v(65, 30, 14), 'whois': v(55, 35, 15), 'uptime': v(70, 30, 2)}
        return _resultado(scores, host)

class LiveCiberSonda:

    def __init__(self, timeout: float=4.0, workers: int=10) -> None:
        self.timeout = timeout
        self.workers = workers

    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber:
        host = _host_de(sitio_web)
        if host is None:
            return _resultado(dict(_SCORES_SIN_HOST_LIVE), None)
        apex = _registrable(host)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            f_http = pool.submit(self._http_bundle, host)
            f_ssl = pool.submit(self._ssl, host)
            f_email = pool.submit(self._email_auth, apex)
            f_dnssec = pool.submit(self._dnssec, apex)
            f_whois = pool.submit(self._whois, apex, host)
            f_black = pool.submit(self._blacklist, host)
            f_puertos = pool.submit(self._puertos, host)
            f_subs = pool.submit(self._subdominios, apex)
            headers_raw, stack_h, uptime_h = f_http.result()
            ssl_h = f_ssl.result()
            email_h = f_email.result()
            dnssec_h = f_dnssec.result()
            whois_h = f_whois.result()
            black_h = f_black.result()
            puertos_h = f_puertos.result()
            subs_h = f_subs.result()
        scores = {'ssl-tls': score_ssl_tls(ssl_h), 'email-auth': score_email_auth(email_h), 'puertos': score_puertos(puertos_h), 'headers-http': score_headers_http(headers_raw), 'stack-vulnerable': score_stack_vulnerable(stack_h), 'blacklist': score_blacklist(black_h), 'dnssec': score_dnssec(dnssec_h), 'subdominios': score_subdominios(subs_h), 'whois': score_whois(whois_h), 'uptime': score_uptime(uptime_h)}
        return _resultado(scores, host)

    def _ssl(self, host: str) -> HallazgosSsl:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    version = ssock.version() or ''
                    return HallazgosSsl(True, _cert_vigente(cert), True, _tls_moderno(version))
        except ssl.SSLCertVerificationError:
            ok, vig, auto, tls = self._ssl_sin_verificar(host)
            return HallazgosSsl(ok, vig, auto, tls)
        except OSError:
            return HallazgosSsl()

    def _ssl_sin_verificar(self, host: str) -> tuple[bool, bool, bool, bool]:
        try:
            ctx = getattr(ssl, '_create_unverified_context')()
            with socket.create_connection((host, 443), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    version = ssock.version() or ''
                    return (True, _cert_vigente(cert), False, _tls_moderno(version))
        except OSError:
            return (False, False, False, False)

    def _http_bundle(self, host: str) -> tuple[HallazgosHeaders, HallazgosStack, HallazgosUptime]:
        req = urllib.request.Request(f'https://{host}/', method='GET', headers={'User-Agent': _UA})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                code = getattr(resp, 'status', 200) or 200
                uptime = HallazgosUptime(responde=True, status_ok=200 <= int(code) < 400)
                stack = HallazgosStack(server_header=headers.get('server'), powered_by=headers.get('x-powered-by'))
                sec = HallazgosHeaders(hsts='strict-transport-security' in headers, csp='content-security-policy' in headers, x_frame_options='x-frame-options' in headers, x_content_type_options='x-content-type-options' in headers)
                return (sec, stack, uptime)
        except (urllib.error.URLError, OSError, ValueError):
            return (HallazgosHeaders(), HallazgosStack(), HallazgosUptime())

    def _email_auth(self, apex: str) -> HallazgosEmailAuth:
        txts = doh_txt(apex, self.timeout)
        dmarc_txt = doh_txt(f'_dmarc.{apex}', self.timeout)
        dkim = False
        for sel in _DKIM_SELECTORS:
            recs = doh_txt(f'{sel}._domainkey.{apex}', self.timeout)
            if any(('v=dkim1' in t.lower() or 'p=' in t.lower() for t in recs)):
                dkim = True
                break
        return HallazgosEmailAuth(spf=any((t.lower().startswith('v=spf1') for t in txts)), dkim=dkim, dmarc=any(('v=dmarc1' in t.lower() for t in dmarc_txt)))

    def _dnssec(self, apex: str) -> HallazgosDnssec:
        ns = doh_ns(apex, self.timeout)
        ds = doh_tiene_tipo(apex, 'DS', self.timeout)
        dnskey = doh_tiene_tipo(apex, 'DNSKEY', self.timeout)
        return HallazgosDnssec(tiene_ns=bool(ns), tiene_ds_o_dnskey=ds or dnskey, ns_count=len(ns))

    def _whois(self, apex: str, host: str) -> HallazgosWhois:
        dns_ok = False
        for nombre in (host, apex):
            try:
                socket.getaddrinfo(nombre, None)
                dns_ok = True
                break
            except OSError:
                continue
        return HallazgosWhois(edad_anios=None, dns_configurado=dns_ok, renovacion_vigente=dns_ok)

    def _blacklist(self, host: str) -> HallazgosBlacklist:
        ips = doh_a(host, self.timeout)
        if not ips:
            try:
                infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                ips = list({i[4][0] for i in infos if i and i[4]})
            except OSError:
                return HallazgosBlacklist(marcado_malware=True)
        consultas: list[tuple[str, str]] = []
        for ip in ips[:3]:
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if addr.version != 4:
                continue
            rev = '.'.join(reversed(ip.split('.')))
            consultas.append(('spam', f'{rev}.bl.spamcop.net'))
            consultas.append(('malware', f'{rev}.dnsbl.sorbs.net'))
        spam = False
        malware = False
        for tipo, nombre in consultas:
            if doh_a(nombre, self.timeout):
                if tipo == 'spam':
                    spam = True
                else:
                    malware = True
        return HallazgosBlacklist(marcado_malware=malware, marcado_phishing=False, marcado_spam=spam)

    def _puerto_abierto(self, host: str, puerto: int) -> bool:
        try:
            with socket.create_connection((host, puerto), timeout=min(1.5, self.timeout)):
                return True
        except OSError:
            return False

    def _puertos(self, host: str) -> HallazgosPuertos:
        abiertos = [p for p in PUERTOS_CRITICOS if self._puerto_abierto(host, p)]
        return HallazgosPuertos(abiertos=tuple(sorted(abiertos)))

    def _subdominios(self, apex: str) -> HallazgosSubdominios:
        expuestos: list[str] = []
        for pref in _SUBS_SENSIBLES:
            nombre = f'{pref}.{apex}'
            if doh_a(nombre, self.timeout):
                expuestos.append(pref)
                continue
            try:
                socket.getaddrinfo(nombre, None)
                expuestos.append(pref)
            except OSError:
                pass
        return HallazgosSubdominios(expuestos=tuple(expuestos))

def build_ciber_sonda(provider: str) -> CiberSonda:
    if provider == 'live':
        return LiveCiberSonda()
    return FakeCiberSonda()
