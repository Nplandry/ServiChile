from __future__ import annotations

import json

import urllib.error

import urllib.request

from app.dominio.pasaporte import RutInvalido, normalizar_rut

from app.dominio.puertos import NuloSii, ProveedorSii

from app.dominio.transparencia.sii import (
    HallazgosSii,
    hallazgos_desde_payload,
    score_sii,
)

from app.infraestructura.contexto_https import ssl_context

_BASE = (
    "https://app.apigateway.cl/api/v2/sii/contribuyentes/situacion_tributaria/tercero"
)

_UA = "ServiChile-SiiSonda/1.0"


NullSiiContribuyentes = NuloSii


class MuestraSiiContribuyentes:

    def score_para_rut(self, rut: str | None) -> int:

        if not rut:

            return 0

        return score_sii(
            HallazgosSii(
                consulta_ok=True,
                inicio_actividades=True,
                obligacion_dte=True,
                tiene_dte_timbrado=True,
                termino_giro=False,
                observaciones_riesgo=0,
            )
        )


class ProduccionSiiContribuyentes:

    def __init__(self, token: str, timeout: float = 3.5) -> None:

        self.token = token.strip()

        self.timeout = timeout

    def score_para_rut(self, rut: str | None) -> int:

        if not rut or not self.token:

            return 0

        h = self.consultar(rut)

        return score_sii(h)

    def consultar(self, rut: str | None) -> HallazgosSii:

        if not rut or not self.token:

            return HallazgosSii(consulta_ok=False)

        try:

            rut_n = normalizar_rut(rut)

        except RutInvalido:

            return HallazgosSii(consulta_ok=False)

        url = f"{_BASE}/{rut_n}"

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Token {self.token}",
                "User-Agent": _UA,
                "Accept": "application/json",
            },
        )

        try:

            with urllib.request.urlopen(
                req, timeout=self.timeout, context=ssl_context()
            ) as resp:

                if getattr(resp, "status", 200) >= 400:

                    return HallazgosSii(consulta_ok=False)

                raw = resp.read(500000)

                if not raw:

                    return HallazgosSii(consulta_ok=False)

                body = json.loads(raw.decode("utf-8", errors="ignore"))

        except urllib.error.HTTPError:

            return HallazgosSii(consulta_ok=False)

        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

            return HallazgosSii(consulta_ok=False)

        data = body.get("data") if isinstance(body, dict) else None

        if not isinstance(data, dict):

            return HallazgosSii(consulta_ok=False)

        return hallazgos_desde_payload(data)


def build_sii_contribuyentes(
    token: str | None, *, muestra: bool = False
) -> ProveedorSii:

    if muestra:

        return MuestraSiiContribuyentes()

    if not token or not str(token).strip():

        return NullSiiContribuyentes()

    return ProduccionSiiContribuyentes(str(token).strip())
