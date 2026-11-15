from __future__ import annotations

import ssl

import urllib.error

import urllib.request

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.dominio.transparencia.docs_legales import (
    TIPOS,
    HallazgoDocLegal,
    ResultadoDocsLegales,
    clasificar_url_candidata,
    consulta_busqueda_unica,
    enriquecer_con_pagina,
    extraer_candidatos_desde_html,
    fusionar_sla_desde_otros,
    mejor_hallazgo,
    mismo_sitio,
    pagina_parece_util,
    rutas_rapidas,
    url_irrelevante,
)

from app.infraestructura.busqueda.web import BuscadorWeb

_UA = "Mozilla/5.0 (compatible; ServiChile-Docs/1.4)"

_BODY_MAX = 90000

_TIMEOUT = 3.5

_MAX_FETCH = 6

_SSL_CTX = ssl._create_unverified_context()


class DocsLegalesSonda:

    def __init__(
        self, buscador: BuscadorWeb | None = None, timeout: float = _TIMEOUT
    ) -> None:

        self.buscador = buscador

        self.timeout = timeout

    def escanear(self, host: str, html_home: str = "") -> ResultadoDocsLegales:

        base = f"https://{host}/"

        if not (html_home and html_home.strip()):

            got = self._get(base)

            if got and pagina_parece_util(got[0], got[1], got[2]):

                html_home = got[2]

        sitio_ok = bool(html_home and html_home.strip())

        hall: dict[str, HallazgoDocLegal] = {t: HallazgoDocLegal() for t in TIPOS}

        htmls: dict[str, list[tuple[str, str]]] = {t: [] for t in TIPOS}

        desde_home = extraer_candidatos_desde_html(html_home or "", base)

        for t in TIPOS:

            if desde_home[t]:

                hall[t] = HallazgoDocLegal(enlace_en_home=True)

        self._fetch_y_aplicar(hall, htmls, self._cola_rapida(base, desde_home))

        faltan = [
            t for t in ("politica-privacidad", "terminos") if not hall[t].pagina_ok
        ]

        if faltan and self.buscador is not None:

            self._fetch_y_aplicar(hall, htmls, self._cola_buscador(host, faltan))

        hall["sla"] = fusionar_sla_desde_otros(
            hall["sla"], htmls["politica-privacidad"] + htmls["terminos"]
        )

        return ResultadoDocsLegales(
            privacidad=hall["politica-privacidad"],
            terminos=hall["terminos"],
            sla=hall["sla"],
            sitio_alcanzado=sitio_ok or any(h.pagina_ok for h in hall.values()),
        )

    def _cola_rapida(
        self,
        base: str,
        desde_home: dict[str, list[str]],
    ) -> list[tuple[str, str, bool]]:

        cola: list[tuple[str, str, bool]] = []

        vistos: set[str] = set()

        def add(tipo: str, url: str, desde: bool) -> None:

            key = url.rstrip("/").lower()

            if key in vistos or len(cola) >= _MAX_FETCH:

                return

            vistos.add(key)

            cola.append((tipo, url, desde))

        for tipo in TIPOS:

            for u in desde_home[tipo][:1]:

                add(tipo, u, True)

        sin_home = [t for t in ("politica-privacidad", "terminos") if not desde_home[t]]

        for tipo, u in rutas_rapidas(base, sin_home, por_tipo=2):

            add(tipo, u, False)

        return cola

    def _cola_buscador(
        self, host: str, faltan: list[str]
    ) -> list[tuple[str, str, bool]]:

        assert self.buscador is not None

        try:

            hits = self.buscador.buscar(consulta_busqueda_unica(host), max_resultados=5)

        except Exception:

            return []

        cola: list[tuple[str, str, bool]] = []

        vistos: set[str] = set()

        for sn in hits:

            url = (sn.url or "").strip()

            if not url or not mismo_sitio(host, url):

                continue

            tipo = clasificar_url_candidata(url, sn.titulo or "")

            if tipo is None or tipo not in faltan:

                continue

            key = url.rstrip("/").lower()

            if key in vistos:

                continue

            vistos.add(key)

            cola.append((tipo, url, True))

            if len(cola) >= 3:

                break

        return cola

    def _aplicar_resultado(
        self,
        hall: dict[str, HallazgoDocLegal],
        htmls: dict[str, list[tuple[str, str]]],
        tipo: str,
        desde: bool,
        got: tuple[str, int, str],
    ) -> None:

        final, code, body = got

        if url_irrelevante(final) or not pagina_parece_util(final, code, body):

            return

        tipo_final = clasificar_url_candidata(final) or tipo

        payload = final if final.lower().endswith(".pdf") else body

        htmls.setdefault(tipo_final, []).append((final, payload))

        cand = enriquecer_con_pagina(
            hall[tipo_final], final, payload, tipo_final, desde_enlace=desde
        )

        hall[tipo_final] = mejor_hallazgo(hall[tipo_final], cand)

    def _fetch_y_aplicar(
        self,
        hall: dict[str, HallazgoDocLegal],
        htmls: dict[str, list[tuple[str, str]]],
        cola: list[tuple[str, str, bool]],
    ) -> None:

        if not cola:

            return

        deadline = self.timeout + 0.8

        pool = ThreadPoolExecutor(max_workers=min(6, len(cola)))

        futs = {pool.submit(self._get, url): (tipo, desde) for tipo, url, desde in cola}

        aplicados: set = set()

        try:

            for fut in as_completed(futs, timeout=deadline):

                aplicados.add(fut)

                tipo, desde = futs[fut]

                try:

                    got = fut.result()

                except Exception:

                    continue

                if got:

                    self._aplicar_resultado(hall, htmls, tipo, desde, got)

        except TimeoutError:

            for fut, (tipo, desde) in futs.items():

                if fut in aplicados:

                    continue

                if not fut.done():

                    fut.cancel()

                    continue

                try:

                    got = fut.result(timeout=0)

                except Exception:

                    continue

                if got:

                    self._aplicar_resultado(hall, htmls, tipo, desde, got)

        finally:

            pool.shutdown(wait=False, cancel_futures=True)

    def _get(self, url: str) -> tuple[str, int, str] | None:

        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
            },
        )

        try:

            with urllib.request.urlopen(
                req, timeout=self.timeout, context=_SSL_CTX
            ) as resp:

                return (
                    resp.geturl() or url,
                    int(getattr(resp, "status", 200) or 200),
                    resp.read(_BODY_MAX).decode("utf-8", errors="ignore"),
                )

        except urllib.error.HTTPError as exc:

            try:

                raw = exc.read(_BODY_MAX) if exc.fp is not None else b""

            except Exception:

                raw = b""

            return (
                str(getattr(exc, "url", None) or url),
                int(exc.code or 404),
                raw.decode("utf-8", errors="ignore") if raw else "",
            )

        except (urllib.error.URLError, OSError, ValueError, TimeoutError):

            return None
