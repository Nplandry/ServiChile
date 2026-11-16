"""Crawl rápido del sitio (homepage): headers + docs legales → hints de score."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[misc, assignment]

DOC_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "privacy_policy": [
        re.compile(r"pol[ií]tica\s+de\s+privacidad", re.I),
        re.compile(r"privacy\s*policy", re.I),
        re.compile(r"protecci[oó]n\s+de\s+datos", re.I),
    ],
    "terms": [
        re.compile(r"t[eé]rminos\s+y\s+condiciones", re.I),
        re.compile(r"terms\s*(and|&)\s*conditions", re.I),
        re.compile(r"condiciones\s+de\s+uso", re.I),
    ],
    "sla": [re.compile(r"\bSLA\b"), re.compile(r"nivel(?:es)?\s+de\s+servicio", re.I)],
    "dpa": [
        re.compile(r"\bDPA\b"),
        re.compile(r"acuerdo\s+de\s+tratamiento\s+de\s+datos", re.I),
    ],
    "service_clauses": [
        re.compile(r"cl[aá]usulas?\s+de\s+servicio", re.I),
        re.compile(r"condiciones\s+del?\s+servicio", re.I),
    ],
}
LEY_21719 = re.compile(r"21\.?\s*719|ley\s+21\.?719", re.I)
COOKIE_NOTICE = re.compile(r"cookie|cookies|consentimiento", re.I)
CONTACT_DATA = re.compile(
    r"delegad[oa]\s+de\s+datos|dpo|contacto.*datos|ARCO|habeas\s+data", re.I
)


def _normalize_url(url: str) -> str:
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u.rstrip("/")


def crawl_homepage(site_url: str, *, timeout: float = 1.5) -> dict[str, Any]:
    """Devuelve {pages_scanned, score_hints, findings_count, headers_info}."""
    start = _normalize_url(site_url)
    vacio = {
        "pages_scanned": 0,
        "score_hints": {},
        "findings_count": 0,
        "headers_info": {},
    }
    if BeautifulSoup is None:
        return vacio

    page_texts: dict[str, str] = {}
    page_html: dict[str, str] = {}
    headers_info: dict[str, Any] = {}
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout, connect=0.5),
            follow_redirects=True,
            headers={"User-Agent": "ServiChileRater/1.0"},
        ) as client:
            rr = client.get(start)
    except Exception:  # noqa: BLE001
        return vacio

    if rr.status_code >= 400:
        return vacio

    headers_info = {
        "url": str(rr.url),
        "status": rr.status_code,
        "headers": {k.lower(): v for k, v in rr.headers.items()},
        "is_https": str(rr.url).startswith("https"),
        "set_cookie": (
            rr.headers.get_list("set-cookie")
            if hasattr(rr.headers, "get_list")
            else ([rr.headers["set-cookie"]] if "set-cookie" in rr.headers else [])
        ),
    }
    ct = rr.headers.get("content-type", "")
    if "text/html" in ct or "application/xhtml" in ct:
        html = rr.text
        page_html[str(rr.url)] = html
        soup = BeautifulSoup(html, "lxml")
        page_texts[str(rr.url)] = soup.get_text(" ", strip=True)
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").lower()
            label = f"{a.get_text(' ', strip=True)} {href}".lower()
            page_texts[f"link:{href}"] = f"{label} {href}"[:500]

    findings = _analyze(page_texts, page_html)
    hints = _hints(findings, headers_info, page_texts)
    return {
        "pages_scanned": len([u for u in page_texts if not u.startswith("link:")]),
        "score_hints": hints,
        "findings_count": sum(1 for f in findings if f.get("found")),
        "headers_info": {
            k: v for k, v in headers_info.items() if k != "headers"
        },
    }


def _analyze(page_texts: dict[str, str], page_html: dict[str, str]) -> list[dict]:
    findings: list[dict] = []
    for doc_type, patterns in DOC_PATTERNS.items():
        best_conf = 0.0
        found_url = None
        for url, text in page_texts.items():
            blob = f"{url} {text[:8000]}"
            hits = sum(1 for p in patterns if p.search(blob))
            if hits == 0:
                continue
            conf = min(1.0, 0.35 * hits + (0.25 if any(p.search(url) for p in patterns) else 0))
            if conf > best_conf:
                best_conf = conf
                found_url = url
        min_conf = 0.55 if doc_type == "privacy_policy" else 0.35
        findings.append(
            {"doc_type": doc_type, "found": best_conf >= min_conf, "url": found_url}
        )

    ley = any(LEY_21719.search(t) for t in page_texts.values())
    findings.append({"doc_type": "ley_21719", "found": ley, "url": None})
    cookie = any(COOKIE_NOTICE.search(t[:3000]) for t in page_texts.values()) or any(
        COOKIE_NOTICE.search(h[:2000]) for h in page_html.values()
    )
    findings.append({"doc_type": "cookies_notice", "found": cookie, "url": None})
    contact = any(CONTACT_DATA.search(t) for t in page_texts.values())
    findings.append({"doc_type": "data_contact", "found": contact, "url": None})
    return findings


def _hints(
    findings: list[dict], headers_info: dict[str, Any], page_texts: dict[str, str]
) -> dict[str, float]:
    by_type = {f["doc_type"]: f for f in findings}
    headers = (headers_info or {}).get("headers") or {}

    def hdr(name: str) -> str:
        return str(headers.get(name, "")).lower()

    cookies = headers_info.get("set_cookie") or []
    cookie_str = " ".join(cookies).lower()
    found = lambda t: bool(by_type.get(t, {}).get("found"))

    return {
        "cyb_https": 100.0 if headers_info.get("is_https") else 10.0,
        "cyb_hsts": 100.0 if "strict-transport-security" in headers else 0.0,
        "cyb_csp": 100.0 if "content-security-policy" in headers else 0.0,
        "cyb_xfo": 100.0
        if "x-frame-options" in headers or "frame-ancestors" in hdr("content-security-policy")
        else 0.0,
        "cyb_xcto": 100.0 if "nosniff" in hdr("x-content-type-options") else 0.0,
        "cyb_referrer": 100.0 if "referrer-policy" in headers else 0.0,
        "cyb_cookies": 80.0
        if cookies and ("secure" in cookie_str or "httponly" in cookie_str)
        else (40.0 if not cookies else 20.0),
        "cyb_mixed": 70.0,
        "con_privacy": 100.0 if found("privacy_policy") else 0.0,
        "con_ley_21719": 100.0 if found("ley_21719") else 0.0,
        "con_tyc": 100.0 if found("terms") else 0.0,
        "con_sla": 100.0 if found("sla") else 0.0,
        "con_dpa": 100.0 if found("dpa") else 0.0,
        "con_clausulas": 100.0 if found("service_clauses") else (50.0 if found("terms") else 0.0),
        "con_contacto_datos": 100.0 if found("data_contact") else 0.0,
        "con_cookies_notice": 100.0 if found("cookies_notice") else 0.0,
        "dig_website": 100.0 if page_texts else 0.0,
    }


def dominio_de_url(sitio: str | None) -> str | None:
    if not sitio or not str(sitio).strip():
        return None
    raw = str(sitio).strip()
    if not raw.startswith("http"):
        raw = "https://" + raw
    host = (urlparse(raw).netloc or "").removeprefix("www.").lower()
    return host or None
