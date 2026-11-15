from __future__ import annotations

import json

import urllib.error

import urllib.parse

import urllib.request

from datetime import date, timedelta

from app.domain.pasaporte import RutInvalido, normalizar_rut

from app.domain.puertos import NuloMercadoPublico, ProveedorMercadoPublico

from app.domain.transparencia.mercado_publico import (
    HallazgosMercadoPublico,
    formato_rut_chilecompra,
    score_mercado_publico,
)

from app.infrastructure.contexto_https import ssl_context

_BASE = "https://api.mercadopublico.cl/servicios/v1"

_UA = "ServiChile-ChileCompra/1.0"


NullChileCompra = NuloMercadoPublico


class FakeChileCompra:

    def score_para_rut(self, rut: str | None) -> int:

        if not rut:

            return 0

        return score_mercado_publico(
            HallazgosMercadoPublico(
                consulta_ok=True,
                proveedor_encontrado=True,
                codigo_proveedor="17793",
                tiene_ordenes_recientes=True,
            )
        )


class LiveChileCompra:

    def __init__(self, ticket: str, timeout: float = 3.5) -> None:

        self.ticket = ticket.strip()

        self.timeout = timeout

    def score_para_rut(self, rut: str | None) -> int:

        if not rut or not self.ticket:

            return 0

        h = self.consultar(rut)

        if not h.consulta_ok:

            return 0

        return score_mercado_publico(h)

    def consultar(self, rut: str | None) -> HallazgosMercadoPublico:

        if not rut or not self.ticket:

            return HallazgosMercadoPublico(consulta_ok=False)

        try:

            rut_n = normalizar_rut(rut)

        except RutInvalido:

            return HallazgosMercadoPublico(consulta_ok=False)

        codigo, ok = self._buscar_codigo(rut_n)

        if not ok:

            return HallazgosMercadoPublico(consulta_ok=False)

        if codigo is None:

            return HallazgosMercadoPublico(consulta_ok=True, proveedor_encontrado=False)

        ordenes = self._tiene_oc_recientes(codigo)

        return HallazgosMercadoPublico(
            consulta_ok=True,
            proveedor_encontrado=True,
            codigo_proveedor=codigo,
            tiene_ordenes_recientes=ordenes,
        )

    def _get_json(self, path: str, params: dict[str, str]) -> dict | list | None:

        q = dict(params)

        q["ticket"] = self.ticket

        url = f"{_BASE}{path}?{urllib.parse.urlencode(q)}"

        req = urllib.request.Request(
            url, headers={"User-Agent": _UA, "Accept": "application/json"}
        )

        try:

            with urllib.request.urlopen(
                req, timeout=self.timeout, context=ssl_context()
            ) as resp:

                if getattr(resp, "status", 200) >= 400:

                    return None

                raw = resp.read(500000)

                if not raw:

                    return None

                return json.loads(raw.decode("utf-8", errors="ignore"))

        except urllib.error.HTTPError:

            return None

        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

            return None

    def _buscar_codigo(self, rut_n: str) -> tuple[str | None, bool]:

        data = self._get_json(
            "/Publico/Empresas/BuscarProveedor",
            {"rutempresaproveedor": formato_rut_chilecompra(rut_n)},
        )

        if data is None:

            return (None, False)

        items: list = []

        if isinstance(data, list):

            items = data

        elif isinstance(data, dict):

            for key in ("lista", "Listado", "listado"):

                val = data.get(key)

                if isinstance(val, list):

                    items = val

                    break

            if not items and ("CodigoEmpresa" in data or "CodigoProveedor" in data):

                items = [data]

        for item in items:

            if not isinstance(item, dict):

                continue

            codigo = (
                item.get("CodigoEmpresa")
                or item.get("CodigoProveedor")
                or item.get("Codigo")
            )

            if codigo is not None and str(codigo).strip():

                return (str(codigo).strip(), True)

        return (None, True)

    def _tiene_oc_recientes(self, codigo_proveedor: str, dias: int = 5) -> bool:

        hoy = date.today()

        for delta in range(dias):

            dia = hoy - timedelta(days=delta)

            fecha = dia.strftime("%d%m%Y")

            data = self._get_json(
                "/publico/ordenesdecompra.json",
                {"fecha": fecha, "CodigoProveedor": codigo_proveedor},
            )

            if data is None:

                continue

            cantidad = 0

            if isinstance(data, dict):

                cantidad = int(data.get("Cantidad") or data.get("cantidad") or 0)

                lista = data.get("Listado") or data.get("listado") or []

                if isinstance(lista, list) and lista:

                    return True

            if cantidad > 0:

                return True

        return False


def build_chilecompra(ticket: str | None, *, fake: bool = False) -> ProveedorMercadoPublico:

    if fake:

        return FakeChileCompra()

    if not ticket or not str(ticket).strip():

        return NullChileCompra()

    return LiveChileCompra(str(ticket).strip())
