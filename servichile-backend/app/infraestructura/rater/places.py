from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.dominio.transparencia.rater.ficha import (
    FichaAssessment,
    brand_tokens,
    domain_stem,
    pick_reliable_place,
)
from app.infraestructura.rater.http_sync import post_json


class GooglePlacesCliente:
    def __init__(self, api_key: str, *, base: str | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.base = (base or "https://places.googleapis.com/v1").rstrip("/")

    @property
    def configurado(self) -> bool:
        return bool(self.api_key)

    def _queries(
        self,
        name: str | None,
        domain: str,
        comuna: str | None,
        ciudad: str | None,
    ) -> list[str]:
        brand = (brand_tokens(name, domain) or [domain_stem(domain) or ""])[0]
        loc = " ".join(p for p in [comuna, ciudad] if p)
        queries: list[str] = [f"{domain} Chile"]
        if brand and brand not in domain:
            queries.append(f"{brand} {domain} Chile")
        if name:
            queries.append(f'"{name}" {loc} Chile' if loc else f'"{name}" Chile')
        if brand and loc:
            queries.append(f"{brand} {loc} Chile")
        elif brand:
            queries.append(f"{brand} Chile")
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            qn = " ".join(q.split())
            if qn and qn not in seen:
                seen.add(qn)
                out.append(qn)
        return out[:2]

    def text_search(
        self, query: str, *, timeout: float = 2.0, max_results: int = 3
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        if not self.configurado:
            return False, None, "GOOGLE_PLACES_API_KEY no configurado"
        url = f"{self.base}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.nationalPhoneNumber,places.websiteUri,places.rating,"
                "places.userRatingCount,places.regularOpeningHours,"
                "places.location,places.googleMapsUri"
            ),
        }
        payload = {
            "textQuery": query,
            "regionCode": "CL",
            "languageCode": "es",
            "maxResultCount": max_results,
        }
        return post_json(url, payload, headers=headers, timeout=timeout)

    def find_business(
        self,
        name: str | None,
        domain: str,
        comuna: str | None = None,
        ciudad: str | None = None,
        *,
        timeout: float = 2.0,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        queries = self._queries(name, domain, comuna, ciudad)
        places: list[dict[str, Any]] = []
        errors: list[str] = []
        if queries:
            with ThreadPoolExecutor(max_workers=len(queries)) as pool:
                futs = [
                    pool.submit(
                        lambda q=q: self.text_search(q, timeout=timeout)
                    )
                    for q in queries
                ]
                for fut in as_completed(futs):
                    ok, data, err = fut.result()
                    if ok and isinstance(data, dict):
                        places.extend(data.get("places") or [])
                    elif err:
                        errors.append(err)
        # dedup
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for p in places:
            key = str(p.get("id") or p.get("name") or id(p))
            if key in seen:
                continue
            seen.add(key)
            merged.append(p)
        place, assessment = pick_reliable_place(
            merged,
            company_name=name,
            domain=domain,
            comuna=comuna,
            ciudad=ciudad,
        )
        payload: dict[str, Any] = {
            "ficha_assessment": assessment.to_dict(),
            "candidates_considered": len(merged),
        }
        if place is None or not assessment.reliable:
            if errors and not merged:
                payload["ficha_assessment"] = FichaAssessment(
                    reliable=False,
                    confidence=0.0,
                    match_score=0,
                    reasons=errors[:3],
                ).to_dict()
            return False, payload, "Sin ficha Places confiable"
        payload["place"] = place
        return True, payload, None
