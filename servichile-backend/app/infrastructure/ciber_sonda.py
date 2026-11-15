from __future__ import annotations

import hashlib

import ipaddress

import socket

import ssl

import urllib.error

import urllib.parse

import urllib.request

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime, timezone

from app.domain.puertos import ResultadoSondaCiber, SondaCiber

from app.domain.transparencia.indicadores import (
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
    PUERTOS_CRITICOS,
    armar_observables,
    detectar_cookies_html,
    score_blacklist,
    score_cookies,
    score_dnssec,
    score_email_auth,
    score_headers_http,
    score_puertos,
    score_ssl_tls,
    score_stack_vulnerable,
    score_subdominios,
    score_uptime,
    score_whois,
)

from app.domain.transparencia.docs_legales import ResultadoDocsLegales

from app.infrastructure.busqueda_web import BuscadorWeb

from app.infrastructure.consulta_dns import doh_a, doh_ns, doh_tiene_tipo, doh_txt

from app.infrastructure.sonda_docs_legales import DocsLegalesSonda

from app.infrastructure.contexto_https import ssl_context

_SUBS_SENSIBLES = ("dev", "staging", "admin", "vpn", "mail")

_DKIM_SELECTORS = ("default", "google", "selector1", "selector2")

_UA = "Mozilla/5.0 (compatible; ServiChile-CiberSonda/1.2)"

_BODY_MAX = 120000

_DNS_TIMEOUT = 1.8

_PORT_TIMEOUT = 0.45

_SCORES_DOCS_FAKE = {"politica-privacidad": 72, "terminos": 70, "sla": 48}

_SCORES_DOCS_LIVE_SIN = {"politica-privacidad": 15, "terminos": 15, "sla": 15}

_SCORES_SIN_HOST_FAKE = {
    "ssl-tls": 83,
    "email-auth": 80,
    "puertos": 88,
    "headers-http": 79,
    "stack-vulnerable": 74,
    "blacklist": 77,
    "dnssec": 72,
    "subdominios": 85,
    "whois": 73,
    "uptime": 90,
    "cookies": 84,
    **_SCORES_DOCS_FAKE,
}

_SCORES_SIN_HOST_LIVE = {
    "ssl-tls": 0,
    "email-auth": 0,
    "puertos": 50,
    "headers-http": 0,
    "stack-vulnerable": 50,
    "blacklist": 50,
    "dnssec": 0,
    "subdominios": 50,
    "whois": 0,
    "uptime": 15,
    "cookies": 85,
    **_SCORES_DOCS_LIVE_SIN,
}


def _host_resuelve(host: str) -> bool:

    try:

        socket.getaddrinfo(host, 443)

        return True

    except OSError:

        return False


def _host_de(sitio_web: str | None) -> str | None:

    if not sitio_web or not str(sitio_web).strip():

        return None

    texto = str(sitio_web).strip()

    if "://" not in texto:

        texto = "https://" + texto

    host = urllib.parse.urlparse(texto).hostname

    if not host:

        return None

    host = host.lower()

    if _host_resuelve(host):

        return host

    if not host.startswith("www."):

        www = "www." + host

        if _host_resuelve(www):

            return www

    return host


def _registrable(host: str) -> str:

    h = host.lower().strip(".")

    if h.startswith("www."):

        h = h[4:]

    return h


def _cert_vigente(cert: dict | None) -> bool:

    if not cert or "notAfter" not in cert:

        return False

    fin = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(
        tzinfo=timezone.utc
    )

    return fin > datetime.now(timezone.utc)


def _tls_moderno(version: str) -> bool:

    return version in ("TLSv1.2", "TLSv1.3")


def _resultado(
    scores: dict[str, int],
    host: str | None,
    docs_razones: dict[str, list[str]] | None = None,
) -> ResultadoSondaCiber:

    return ResultadoSondaCiber(armar_observables(scores), host, scores, docs_razones)


class FakeCiberSonda:

    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber:

        host = _host_de(sitio_web)

        if host is None:

            return _resultado(dict(_SCORES_SIN_HOST_FAKE), None)

        n = int(hashlib.sha256(host.encode()).hexdigest()[:8], 16)

        def v(base: int, spread: int, shift: int) -> int:

            return base + (n >> shift) % (spread + 1)

        scores = {
            "ssl-tls": v(70, 25, 0),
            "email-auth": v(55, 40, 3),
            "puertos": v(70, 28, 6),
            "headers-http": v(50, 45, 5),
            "stack-vulnerable": v(60, 30, 8),
            "blacklist": v(70, 28, 10),
            "dnssec": v(45, 50, 12),
            "subdominios": v(65, 30, 14),
            "whois": v(55, 35, 15),
            "uptime": v(70, 30, 2),
            "cookies": v(45, 50, 7),
            "politica-privacidad": v(55, 35, 9),
            "terminos": v(52, 35, 11),
            "sla": v(28, 40, 13),
        }

        return _resultado(scores, host)


class LiveCiberSonda:

    def __init__(
        self,
        timeout: float = 2.2,
        workers: int = 12,
        buscador: BuscadorWeb | None = None,
    ) -> None:

        self.timeout = timeout

        self.workers = workers

        self.dns_timeout = min(_DNS_TIMEOUT, timeout)

        self.docs = DocsLegalesSonda(buscador=buscador, timeout=max(3.5, timeout + 1.0))

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

            headers_raw, stack_h, uptime_h, cookies_h, html = self._ok(
                f_http,
                (
                    HallazgosHeaders(),
                    HallazgosStack(),
                    HallazgosUptime(),
                    HallazgosCookies(html_obtenido=False),
                    "",
                ),
            )

            f_docs = pool.submit(
                self.docs.escanear, host, html if isinstance(html, str) else ""
            )

            ssl_h = self._ok(f_ssl, HallazgosSsl())

            email_h = self._ok(f_email, HallazgosEmailAuth())

            dnssec_h = self._ok(f_dnssec, HallazgosDnssec())

            whois_h = self._ok(f_whois, HallazgosWhois())

            black_h = self._ok(f_black, HallazgosBlacklist())

            puertos_h = self._ok(f_puertos, HallazgosPuertos())

            subs_h = self._ok(f_subs, HallazgosSubdominios())

            try:

                docs = f_docs.result(timeout=max(10.0, self.timeout + 8.0))

            except Exception:

                docs = ResultadoDocsLegales()

        scores = {
            "ssl-tls": score_ssl_tls(ssl_h),
            "email-auth": score_email_auth(email_h),
            "puertos": score_puertos(puertos_h),
            "headers-http": score_headers_http(headers_raw),
            "stack-vulnerable": score_stack_vulnerable(stack_h),
            "blacklist": score_blacklist(black_h),
            "dnssec": score_dnssec(dnssec_h),
            "subdominios": score_subdominios(subs_h),
            "whois": score_whois(whois_h),
            "uptime": score_uptime(uptime_h),
            "cookies": score_cookies(cookies_h),
        }

        scores.update(docs.scores())

        return _resultado(scores, host, docs.razones())

    def _ok(self, fut, default):

        try:

            return fut.result(timeout=self.timeout + 1.2)

        except Exception:

            return default

    def _ssl(self, host: str) -> HallazgosSsl:

        try:

            ctx = ssl_context()

            with socket.create_connection((host, 443), timeout=self.timeout) as sock:

                with ctx.wrap_socket(sock, server_hostname=host) as ssock:

                    cert = ssock.getpeercert()

                    version = ssock.version() or ""

                    return HallazgosSsl(
                        True, _cert_vigente(cert), True, _tls_moderno(version)
                    )

        except ssl.SSLCertVerificationError:

            ok, vig, auto, tls = self._ssl_sin_verificar(host)

            return HallazgosSsl(ok, vig, auto, tls)

        except OSError:

            return HallazgosSsl()

    def _ssl_sin_verificar(self, host: str) -> tuple[bool, bool, bool, bool]:

        try:

            ctx = getattr(ssl, "_create_unverified_context")()

            with socket.create_connection((host, 443), timeout=self.timeout) as sock:

                with ctx.wrap_socket(sock, server_hostname=host) as ssock:

                    cert = ssock.getpeercert()

                    version = ssock.version() or ""

                    return (True, _cert_vigente(cert), False, _tls_moderno(version))

        except OSError:

            return (False, False, False, False)

    def _http_get(self, host: str, context: ssl.SSLContext | None = None):

        req = urllib.request.Request(
            f"https://{host}/", method="GET", headers={"User-Agent": _UA}
        )

        return urllib.request.urlopen(req, timeout=self.timeout, context=context)

    def _pack_http(
        self, headers: dict[str, str], code: int, html: str
    ) -> tuple[
        HallazgosHeaders, HallazgosStack, HallazgosUptime, HallazgosCookies, str
    ]:

        uptime = HallazgosUptime(responde=True, status_ok=200 <= int(code) < 400)

        stack = HallazgosStack(
            server_header=headers.get("server"), powered_by=headers.get("x-powered-by")
        )

        sec = HallazgosHeaders(
            hsts="strict-transport-security" in headers,
            csp="content-security-policy" in headers,
            x_frame_options="x-frame-options" in headers,
            x_content_type_options="x-content-type-options" in headers,
        )

        if int(code) >= 400:

            return (
                sec,
                stack,
                uptime,
                HallazgosCookies(html_obtenido=False),
                html or "",
            )

        return (sec, stack, uptime, detectar_cookies_html(html), html or "")

    def _http_bundle(
        self, host: str
    ) -> tuple[
        HallazgosHeaders, HallazgosStack, HallazgosUptime, HallazgosCookies, str
    ]:

        intentos: list[ssl.SSLContext | None] = [
            ssl_context(),
            getattr(ssl, "_create_unverified_context")(),
        ]

        http_error: urllib.error.HTTPError | None = None

        for ctx in intentos:

            try:

                with self._http_get(host, ctx) as resp:

                    headers = {k.lower(): v for k, v in resp.headers.items()}

                    code = getattr(resp, "status", 200) or 200

                    raw = resp.read(_BODY_MAX)

                    html = raw.decode("utf-8", errors="ignore")

                    return self._pack_http(headers, int(code), html)

            except urllib.error.HTTPError as exc:

                http_error = exc

                headers = {
                    k.lower(): v
                    for k, v in (exc.headers.items() if exc.headers else [])
                }

                try:

                    raw = exc.read(_BODY_MAX) if exc.fp is not None else b""

                except Exception:

                    raw = b""

                html = raw.decode("utf-8", errors="ignore") if raw else ""

                return self._pack_http(headers, int(exc.code or 404), html)

            except (urllib.error.URLError, OSError, ValueError):

                continue

        _ = http_error

        return (
            HallazgosHeaders(),
            HallazgosStack(),
            HallazgosUptime(),
            HallazgosCookies(html_obtenido=False),
            "",
        )

    def _email_auth(self, apex: str) -> HallazgosEmailAuth:

        t = self.dns_timeout

        with ThreadPoolExecutor(max_workers=6) as pool:

            f_txt = pool.submit(doh_txt, apex, t)

            f_dmarc = pool.submit(doh_txt, f"_dmarc.{apex}", t)

            f_dkim = [
                pool.submit(doh_txt, f"{sel}._domainkey.{apex}", t)
                for sel in _DKIM_SELECTORS
            ]

            txts = f_txt.result()

            dmarc_txt = f_dmarc.result()

            dkim = False

            for fut in f_dkim:

                recs = fut.result()

                if any(("v=dkim1" in x.lower() or "p=" in x.lower() for x in recs)):

                    dkim = True

                    break

        return HallazgosEmailAuth(
            spf=any((x.lower().startswith("v=spf1") for x in txts)),
            dkim=dkim,
            dmarc=any(("v=dmarc1" in x.lower() for x in dmarc_txt)),
        )

    def _dnssec(self, apex: str) -> HallazgosDnssec:

        t = self.dns_timeout

        with ThreadPoolExecutor(max_workers=3) as pool:

            f_ns = pool.submit(doh_ns, apex, t)

            f_ds = pool.submit(doh_tiene_tipo, apex, "DS", t)

            f_key = pool.submit(doh_tiene_tipo, apex, "DNSKEY", t)

            ns = f_ns.result()

            ds = f_ds.result()

            dnskey = f_key.result()

        return HallazgosDnssec(
            tiene_ns=bool(ns), tiene_ds_o_dnskey=ds or dnskey, ns_count=len(ns)
        )

    def _whois(self, apex: str, host: str) -> HallazgosWhois:

        dns_ok = False

        for nombre in (host, apex):

            try:

                socket.getaddrinfo(nombre, None)

                dns_ok = True

                break

            except OSError:

                continue

        return HallazgosWhois(
            edad_anios=None, dns_configurado=dns_ok, renovacion_vigente=dns_ok
        )

    def _blacklist(self, host: str) -> HallazgosBlacklist:

        ips = doh_a(host, self.dns_timeout)

        if not ips:

            try:

                infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)

                ips = list({i[4][0] for i in infos if i and i[4]})

            except OSError:

                return HallazgosBlacklist(marcado_malware=True)

        consultas: list[tuple[str, str]] = []

        for ip in ips[:2]:

            try:

                addr = ipaddress.ip_address(ip)

            except ValueError:

                continue

            if addr.version != 4:

                continue

            rev = ".".join(reversed(ip.split(".")))

            consultas.append(("spam", f"{rev}.bl.spamcop.net"))

            consultas.append(("malware", f"{rev}.dnsbl.sorbs.net"))

        if not consultas:

            return HallazgosBlacklist()

        spam = False

        malware = False

        with ThreadPoolExecutor(max_workers=min(4, len(consultas))) as pool:

            futs = {
                pool.submit(doh_a, nombre, self.dns_timeout): tipo
                for tipo, nombre in consultas
            }

            for fut, tipo in futs.items():

                if fut.result():

                    if tipo == "spam":

                        spam = True

                    else:

                        malware = True

        return HallazgosBlacklist(
            marcado_malware=malware, marcado_phishing=False, marcado_spam=spam
        )

    def _puerto_abierto(self, host: str, puerto: int) -> bool:

        try:

            with socket.create_connection((host, puerto), timeout=_PORT_TIMEOUT):

                return True

        except OSError:

            return False

    def _puertos(self, host: str) -> HallazgosPuertos:

        with ThreadPoolExecutor(max_workers=min(8, len(PUERTOS_CRITICOS))) as pool:

            futs = {
                pool.submit(self._puerto_abierto, host, p): p for p in PUERTOS_CRITICOS
            }

            abiertos = [p for fut, p in futs.items() if fut.result()]

        return HallazgosPuertos(abiertos=tuple(sorted(abiertos)))

    def _sub_expuesto(self, pref: str, apex: str) -> str | None:

        nombre = f"{pref}.{apex}"

        if doh_a(nombre, self.dns_timeout):

            return pref

        try:

            socket.getaddrinfo(nombre, None)

            return pref

        except OSError:

            return None

    def _subdominios(self, apex: str) -> HallazgosSubdominios:

        with ThreadPoolExecutor(max_workers=min(6, len(_SUBS_SENSIBLES))) as pool:

            futs = [
                pool.submit(self._sub_expuesto, pref, apex) for pref in _SUBS_SENSIBLES
            ]

            expuestos = [r for fut in futs if (r := fut.result())]

        return HallazgosSubdominios(expuestos=tuple(expuestos))


def build_ciber_sonda(provider: str, buscador: BuscadorWeb | None = None) -> SondaCiber:

    if provider == "live":

        return LiveCiberSonda(buscador=buscador)

    return FakeCiberSonda()
