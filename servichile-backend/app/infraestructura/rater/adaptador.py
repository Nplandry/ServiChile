"""Adaptador del rater: combina clientes HTTP + motor de dominio."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal

from app.dominio.entidades import Negocio
from app.dominio.transparencia.rater.fijos import hints_fijos
from app.dominio.transparencia.rater.motor import (
    ResultadoRater,
    block_fisica,
    build_scores,
)
from app.dominio.transparencia.rater.parametros import IDS_ESTADO, IDS_FISICA, IDS_SITIO
from app.infraestructura.rater.chilecompra import ChileCompraCliente
from app.infraestructura.rater.crawler import crawl_homepage, dominio_de_url
from app.infraestructura.rater.places import GooglePlacesCliente

Modo = Literal["muestra", "produccion"]


@dataclass(frozen=True, slots=True)
class RaterConfig:
    modo: Modo = "muestra"
    app_env: str = "local"
    chilecompra_ticket: str = ""
    chilecompra_mode: Modo = "muestra"
    google_places_api_key: str = ""
    places_mode: Modo = "muestra"
    budget_seconds: float = 2.0


def _usar_fijos(modo: Modo, app_env: str, configurado: bool) -> bool:
    if app_env == "test":
        return True
    if modo == "muestra":
        return True
    return not configurado


def _comuna_ciudad(direccion: str | None) -> tuple[str | None, str | None]:
    if not direccion or not direccion.strip():
        return None, None
    partes = [p.strip() for p in re.split(r",|\|", direccion) if p.strip()]
    if not partes:
        return None, None
    if len(partes) == 1:
        return partes[0], partes[0]
    return partes[-2] if len(partes) >= 2 else partes[0], partes[-1]


def _aplicar_ceros_por_campos(
    hints: dict[str, float],
    status: dict[str, str],
    evidence: dict[str, str],
    negocio: Negocio,
) -> None:
    """Campos no rellenados por la empresa → score 0 (no inventar)."""
    if not (negocio.direccion or "").strip():
        hints["fis_address"] = 0.0
        status["fis_address"] = "ok"
        evidence.pop("fis_address", None)
    if not (negocio.telefono or "").strip():
        hints["fis_phone"] = 0.0
        status["fis_phone"] = "ok"
        evidence.pop("fis_phone", None)
    if not (negocio.rut_empresa or "").strip():
        for pid in IDS_ESTADO:
            hints[pid] = 0.0
            status[pid] = "ok"
            evidence.pop(pid, None)
    if not (negocio.sitio_web or "").strip():
        for pid in IDS_SITIO:
            hints[pid] = 0.0
            status[pid] = "ok"
            evidence.pop(pid, None)


def _nombre_proveedor(prov: dict[str, Any] | None) -> str | None:
    if not isinstance(prov, dict):
        return None
    lista = prov.get("listaEmpresas") or prov.get("Listado") or []
    if isinstance(lista, list) and lista and isinstance(lista[0], dict):
        nombre = lista[0].get("NombreEmpresa")
        return str(nombre) if nombre else None
    return None


class AdaptadorRater:
    """Adaptador infra del puerto ``EvaluadorRater``."""

    def __init__(self, config: RaterConfig) -> None:
        self.config = config
        self.places = GooglePlacesCliente(config.google_places_api_key)
        self.chilecompra = ChileCompraCliente(config.chilecompra_ticket)

    def evaluar(self, negocio: Negocio) -> ResultadoRater:
        hints: dict[str, float] = {}
        evidence: dict[str, str] = {}
        sources: dict[str, str] = {}
        status: dict[str, str] = {}
        meta: dict = {"modo": self.config.modo, "app_env": self.config.app_env}
        timeout = max(0.5, min(float(self.config.budget_seconds or 2.0), 8.0))
        ficha_fiable: bool | None = None

        domain = dominio_de_url(negocio.sitio_web) or ""
        name = negocio.nombre
        comuna, ciudad = _comuna_ciudad(negocio.direccion)
        tiene_sitio = bool((negocio.sitio_web or "").strip())
        tiene_rut = bool((negocio.rut_empresa or "").strip())

        crawl_fijos = tiene_sitio and _usar_fijos(
            self.config.modo, self.config.app_env, True
        )
        places_fijos = _usar_fijos(
            self.config.places_mode,
            self.config.app_env,
            self.places.configurado,
        )
        cc_fijos = _usar_fijos(
            self.config.chilecompra_mode,
            self.config.app_env,
            self.chilecompra.configurado,
        )

        # --- Atajos muestra / sin datos (sin red) ---
        if not tiene_sitio:
            meta["crawler"] = {"skipped": True, "reason": "sin sitio_web"}
        elif crawl_fijos:
            for k, v in hints_fijos().items():
                if k in IDS_SITIO:
                    hints[k] = v
                    sources[k] = "muestra"
                    status[k] = "ok"
            meta["crawler"] = {"mode": "muestra"}

        if places_fijos:
            for pid in IDS_FISICA:
                hints[pid] = hints_fijos()[pid]
                sources[pid] = "muestra"
                status[pid] = "ok"
            ficha_fiable = True
            meta["places"] = {"mode": "muestra"}
        elif not domain:
            block_fisica(
                hints, evidence, sources, status, reason="Sin sitio web para Places"
            )
            ficha_fiable = False
            meta["places"] = {"skipped": True}

        if not tiene_rut:
            for pid in IDS_ESTADO:
                hints[pid] = 0.0
                status[pid] = "ok"
                evidence.pop(pid, None)
                sources[pid] = "ficha"
            meta["chilecompra"] = {"skipped": True, "reason": "sin rut"}
        elif cc_fijos:
            for pid in IDS_ESTADO:
                hints[pid] = hints_fijos()[pid]
                sources[pid] = "muestra"
                status[pid] = "ok"
            meta["chilecompra"] = {"mode": "muestra"}

        # --- I/O en paralelo: crawler + Places + ChileCompra ---
        need_crawl = tiene_sitio and not crawl_fijos
        need_places = (not places_fijos) and bool(domain)
        need_cc = tiene_rut and not cc_fijos

        crawl_out: dict[str, Any] | None = None
        places_out: tuple[bool, dict[str, Any] | None, str | None] | None = None
        cc_out: tuple[bool, dict[str, Any] | None, str | None] | None = None

        jobs: dict[str, Any] = {}
        if need_crawl:
            jobs["crawl"] = lambda: crawl_homepage(
                negocio.sitio_web or "", timeout=timeout
            )
        if need_places:
            jobs["places"] = lambda: self.places.find_business(
                name, domain, comuna, ciudad, timeout=timeout
            )
        if need_cc:
            jobs["chilecompra"] = lambda: self.chilecompra.buscar_proveedor(
                negocio.rut_empresa or "", timeout=timeout
            )

        if jobs:
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                futures = {key: pool.submit(fn) for key, fn in jobs.items()}
                if "crawl" in futures:
                    crawl_out = futures["crawl"].result()
                if "places" in futures:
                    places_out = futures["places"].result()
                if "chilecompra" in futures:
                    cc_out = futures["chilecompra"].result()

        if crawl_out is not None:
            hints.update(crawl_out.get("score_hints") or {})
            for pid in crawl_out.get("score_hints") or {}:
                sources[pid] = "crawler"
                status[pid] = "ok"
            meta["crawler"] = {
                "pages_scanned": crawl_out.get("pages_scanned", 0),
                "findings": crawl_out.get("findings_count", 0),
            }

        if places_out is not None:
            ok, data, err = places_out
            ficha_fiable = self._apply_places(
                data if ok else data, hints, evidence, sources, status, meta
            )
            if err:
                meta["places_error"] = err

        if cc_out is not None:
            ok, prov, err = cc_out
            codigo = ChileCompraCliente.codigo_desde(prov) if ok else None
            inscrito = bool(codigo)
            hints["est_proveedor"] = 100.0 if inscrito else 0.0
            if inscrito:
                nombre = _nombre_proveedor(prov if isinstance(prov, dict) else None)
                evidence["est_proveedor"] = (
                    f"Código {codigo}" + (f" · {nombre}" if nombre else "")
                )
            else:
                evidence["est_proveedor"] = err or "No inscrito en Mercado Público"
            for pid in IDS_ESTADO:
                sources[pid] = "chilecompra"
                status[pid] = "ok"
            meta["chilecompra"] = {"ok": ok, "codigo": codigo, "error": err}

        _aplicar_ceros_por_campos(hints, status, evidence, negocio)

        return build_scores(
            hints=hints,
            evidence_map=evidence,
            source_map=sources,
            status_map=status,
            rubro=negocio.categoria,
            company_name=name,
            ficha_fiable=ficha_fiable,
            summary=(
                f"Rater de {name}"
                + (f" ({domain})" if domain else "")
                + f". Señales: {len([k for k, v in hints.items() if v is not None])}."
            ),
            recommendations=self._recs(hints),
            metadata=meta,
        )

    def _apply_places(
        self, data, hints, evidence, sources, status, meta
    ) -> bool | None:
        if not isinstance(data, dict):
            block_fisica(hints, evidence, sources, status, reason="Places no disponible")
            return False
        assessment = data.get("ficha_assessment") or {}
        meta["ficha_assessment"] = assessment
        place = data.get("place") if isinstance(data.get("place"), dict) else None
        reliable = bool(assessment.get("reliable")) if assessment else bool(place)
        if not reliable or not place:
            reason = "; ".join(assessment.get("reasons") or []) or "Sin ficha confiable"
            block_fisica(hints, evidence, sources, status, reason=reason)
            return False
        hints["fis_places_exists"] = 100.0
        rating = place.get("rating")
        if isinstance(rating, (int, float)):
            hints["fis_rating"] = min(100.0, (float(rating) / 5.0) * 100.0)
            evidence["fis_rating"] = f"{rating}/5"
        else:
            hints["fis_rating"] = 40.0
        count = place.get("userRatingCount") or 0
        hints["fis_reviews"] = min(100.0, 20.0 + float(count) * 2.0)
        evidence["fis_reviews"] = f"{count} reseñas"
        hints["fis_address"] = 95.0 if place.get("formattedAddress") else 20.0
        evidence["fis_address"] = place.get("formattedAddress") or ""
        hints["fis_phone"] = 95.0 if place.get("nationalPhoneNumber") else 20.0
        evidence["fis_phone"] = place.get("nationalPhoneNumber") or ""
        hints["fis_hours"] = 90.0 if place.get("regularOpeningHours") else 30.0
        if place.get("websiteUri") and assessment.get("domain_match"):
            hints["dig_website"] = max(hints.get("dig_website", 0), 100.0)
            evidence["dig_website"] = place["websiteUri"]
        for pid in IDS_FISICA:
            sources[pid] = "google_places"
            status[pid] = "ok"
        return True

    @staticmethod
    def _recs(hints: dict[str, float]) -> list[str]:
        recs: list[str] = []
        if hints.get("con_privacy", 0) < 50:
            recs.append("Publicar Política de Privacidad accesible.")
        if hints.get("con_ley_21719", 0) < 50:
            recs.append("Incorporar referencias a la Ley 21.719.")
        if hints.get("fis_places_exists", 0) < 50:
            recs.append("Crear/verificar ficha Google Business Profile.")
        if hints.get("est_proveedor", 0) <= 0:
            recs.append("Completar RUT de empresa para cruzar Mercado Público.")
        return recs[:6]
