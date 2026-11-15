from __future__ import annotations

import json

import urllib.error

import urllib.parse

import urllib.request

from datetime import date

from typing import Any

from app.dominio.transparencia.cmf import InstitucionCmf, normalizar_rut_cmf

from app.infraestructura.contexto_https import ssl_context

_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

_UA = "ServiChile-CmfBancos/1.0"


class CmfApiCliente:

    def __init__(self, apikey: str, timeout: float = 20.0) -> None:

        self.apikey = apikey.strip()

        self.timeout = timeout

    def listar_codigos_instituciones(
        self, *, anio: int | None = None, mes: int | None = None
    ) -> list[tuple[str, str]]:

        hoy = date.today()

        y = anio or hoy.year

        m = mes or hoy.month

        data = self._get(f"/resultados/{y}/{m:02d}/instituciones")

        return self._parse_instituciones(data)

    def perfil_institucion(
        self, codigo: str, *, anio: int | None = None, mes: int | None = None
    ) -> InstitucionCmf | None:

        hoy = date.today()

        y = anio or hoy.year

        m = mes or hoy.month

        cod = str(codigo).strip().zfill(3)

        data = self._get(f"/perfil/instituciones/{cod}/{y}/{m:02d}")

        return self._parse_perfil(data, cod)

    def _get(self, path: str) -> dict[str, Any] | list[Any] | None:

        q = urllib.parse.urlencode({"apikey": self.apikey, "formato": "json"})

        url = f"{_BASE}{path}?{q}"

        req = urllib.request.Request(
            url, headers={"User-Agent": _UA, "Accept": "application/json"}
        )

        try:

            with urllib.request.urlopen(
                req, timeout=self.timeout, context=ssl_context()
            ) as resp:

                if getattr(resp, "status", 200) >= 400:

                    return None

                raw = resp.read(2000000)

                if not raw:

                    return None

                return json.loads(raw.decode("utf-8", errors="ignore"))

        except urllib.error.HTTPError:

            return None

        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):

            return None

    def _parse_instituciones(self, data: object) -> list[tuple[str, str]]:

        out: list[tuple[str, str]] = []

        for item in self._walk(data):

            if not isinstance(item, dict):

                continue

            codigo = (
                item.get("CodigoInstitucion")
                or item.get("codigoInstitucion")
                or item.get("Codigo")
                or item.get("codigo")
            )

            nombre = (
                item.get("NombreInstitucion")
                or item.get("nombreInstitucion")
                or item.get("Nombre")
                or item.get("nombre")
            )

            if codigo is None:

                continue

            out.append((str(codigo).strip().zfill(3), str(nombre or "").strip()))

        vistos: set[str] = set()

        unicos: list[tuple[str, str]] = []

        for c, n in out:

            if c in vistos:

                continue

            vistos.add(c)

            unicos.append((c, n))

        return unicos

    def _parse_perfil(self, data: object, codigo: str) -> InstitucionCmf | None:

        perfil = None

        for item in self._walk(data):

            if isinstance(item, dict) and (
                "rut" in item
                or "Rut" in item
                or "nombre" in item
                or ("Nombre" in item)
                or ("codigoSWIFT" in item)
            ):

                if any(
                    (
                        k in item
                        for k in (
                            "rut",
                            "Rut",
                            "direccionPrincipal",
                            "DireccionPrincipal",
                            "sucursales",
                            "empleados",
                        )
                    )
                ):

                    perfil = item

                    break

                if perfil is None:

                    perfil = item

        if not isinstance(perfil, dict):

            return InstitucionCmf(codigo=codigo, nombre="")

        nombre = str(perfil.get("nombre") or perfil.get("Nombre") or "").strip()

        rut_raw = perfil.get("rut") or perfil.get("Rut")

        rut = normalizar_rut_cmf(str(rut_raw) if rut_raw is not None else None)

        suc = perfil.get("sucursales") or perfil.get("Sucursales")

        emp = perfil.get("empleados") or perfil.get("Empleados")

        try:

            suc_i = int(suc) if suc is not None else None

        except (TypeError, ValueError):

            suc_i = None

        try:

            emp_i = int(emp) if emp is not None else None

        except (TypeError, ValueError):

            emp_i = None

        return InstitucionCmf(
            codigo=codigo,
            nombre=nombre,
            rut=rut,
            direccion=str(
                perfil.get("direccionPrincipal")
                or perfil.get("DireccionPrincipal")
                or ""
            ).strip()
            or None,
            web=str(
                perfil.get("direccionWeb") or perfil.get("DireccionWeb") or ""
            ).strip()
            or None,
            sucursales=suc_i,
            empleados=emp_i,
        )

    def _walk(self, node: object) -> list[object]:

        out: list[object] = []

        if isinstance(node, list):

            for x in node:

                out.extend(self._walk(x))

            return out

        if isinstance(node, dict):

            out.append(node)

            for v in node.values():

                out.extend(self._walk(v))

        return out
