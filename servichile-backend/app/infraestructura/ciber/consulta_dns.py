from __future__ import annotations

import json

import urllib.error

import urllib.parse

import urllib.request

from app.infraestructura.contexto_https import ssl_context

_DOH = "https://cloudflare-dns.com/dns-query"

_UA = "ServiChile-CiberSonda/1.0"


def doh_json(nombre: str, tipo: str, timeout: float) -> dict:

    url = f"{_DOH}?name={urllib.parse.quote(nombre)}&type={urllib.parse.quote(tipo)}"

    req = urllib.request.Request(
        url, headers={"Accept": "application/dns-json", "User-Agent": _UA}
    )

    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:

        return json.loads(resp.read().decode("utf-8", errors="replace"))


def doh_txt(nombre: str, timeout: float) -> list[str]:

    try:

        data = doh_json(nombre, "TXT", timeout)

    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

        return []

    out: list[str] = []

    for ans in data.get("Answer") or []:

        if ans.get("type") != 16:

            continue

        raw = str(ans.get("data") or "").strip().strip('"')

        out.append(raw.replace('" "', "").replace('"', ""))

    return out


def doh_ns(nombre: str, timeout: float) -> list[str]:

    try:

        data = doh_json(nombre, "NS", timeout)

    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

        return []

    return [
        str(a.get("data") or "").rstrip(".")
        for a in data.get("Answer") or []
        if a.get("type") == 2
    ]


def doh_tiene_tipo(nombre: str, tipo: str, timeout: float) -> bool:

    try:

        data = doh_json(nombre, tipo, timeout)

    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

        return False

    wanted = {"DS": 43, "DNSKEY": 48}.get(tipo.upper())

    if wanted is None:

        return bool(data.get("Answer"))

    return any((a.get("type") == wanted for a in data.get("Answer") or []))


def doh_a(nombre: str, timeout: float) -> list[str]:

    try:

        data = doh_json(nombre, "A", timeout)

    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

        return []

    return [
        str(a.get("data") or "") for a in data.get("Answer") or [] if a.get("type") == 1
    ]
