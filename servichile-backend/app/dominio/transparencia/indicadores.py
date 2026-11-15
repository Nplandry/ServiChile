from __future__ import annotations

import math

from dataclasses import dataclass

PESO_CIBER = "3.0%"

PESO_OPERATIVA = "4.0%"

PESO_CONTRACTUAL = "4.0%"

PESO_DATALUX = "2.0%"


@dataclass(frozen=True)
class DefinicionObservable:

    id: str

    etiqueta: str

    detalle: str

    grupo: str

    peso: str


OBSERVABLES_SONDA = (
    DefinicionObservable(
        id="ssl-tls",
        etiqueta="Vigencia y calidad de certificados SSL/TLS",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="email-auth",
        etiqueta="Seguridad de correo y registros DNS",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="puertos",
        etiqueta="Exposición de puertos y servicios críticos",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="headers-http",
        etiqueta="Cabeceras de seguridad HTTP",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="stack-vulnerable",
        etiqueta="Tecnologías web obsoletas o vulnerables",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="blacklist",
        etiqueta="Reputación de IP y dominio en listas negras globales",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="dnssec",
        etiqueta="Protección de infraestructura DNS y secuestro de dominios",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="subdominios",
        etiqueta="Seguridad en subdominios expuestos",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="whois",
        etiqueta="Antigüedad, configuración y estabilidad del dominio",
        detalle="",
        grupo="ciber",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="uptime",
        etiqueta="Continuidad operativa y estabilidad de infraestructura",
        detalle="",
        grupo="operativa",
        peso=PESO_OPERATIVA,
    ),
    DefinicionObservable(
        id="cookies",
        etiqueta="Consentimiento de cookies y rastreadores",
        detalle="",
        grupo="contractual",
        peso=PESO_CONTRACTUAL,
    ),
)

OBSERVABLE_RESENAS = DefinicionObservable(
    id="resenas-reclamos",
    etiqueta="Calificación y volumen de reseñas en Google",
    detalle="",
    grupo="operativa",
    peso=PESO_OPERATIVA,
)

OBSERVABLE_MERCADO_PUBLICO = DefinicionObservable(
    id="mercado-publico",
    etiqueta="Historial y penalidades en compras públicas / Estado",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)

OBSERVABLE_SII = DefinicionObservable(
    id="sii",
    etiqueta="Situación tributaria, cumplimiento y facturación electrónica",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)

OBSERVABLE_CMF = DefinicionObservable(
    id="cmf",
    etiqueta="Supervisión CMF Bancos",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)

OBSERVABLE_INCIDENTES = DefinicionObservable(
    id="incidentes",
    etiqueta="Historial de incidentes físicos, brechas o escándalos públicos",
    detalle="",
    grupo="operativa",
    peso=PESO_OPERATIVA,
)

OBSERVABLE_PRIVACIDAD = DefinicionObservable(
    id="politica-privacidad",
    etiqueta="Política de Privacidad accesible e información acerca de la Ley 21.719",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)

OBSERVABLE_TERMINOS = DefinicionObservable(
    id="terminos",
    etiqueta="Términos y Condiciones públicos de la oferta comercial",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)

OBSERVABLE_SLA = DefinicionObservable(
    id="sla",
    etiqueta="Cláusulas de servicio, SLA y DPA",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)

OBSERVABLES_DATALUX = (
    DefinicionObservable(
        id="persona-juridica",
        etiqueta="Vigencia y estado de la persona jurídica",
        detalle="",
        grupo="legal",
        peso=PESO_CIBER,
    ),
    DefinicionObservable(
        id="domicilio",
        etiqueta="Verificación de domicilio operativo real y oficinas",
        detalle="",
        grupo="operativa",
        peso=PESO_DATALUX,
    ),
    DefinicionObservable(
        id="huella-digital",
        etiqueta="Coherencia y solidez de huella digital y reputación corporativa",
        detalle="",
        grupo="operativa",
        peso=PESO_DATALUX,
    ),
)

_CATALOGO_OBSERVABLES = (
    *OBSERVABLES_SONDA,
    OBSERVABLE_MERCADO_PUBLICO,
    OBSERVABLE_SII,
    OBSERVABLE_CMF,
    OBSERVABLE_INCIDENTES,
    OBSERVABLE_RESENAS,
    OBSERVABLE_PRIVACIDAD,
    OBSERVABLE_TERMINOS,
    OBSERVABLE_SLA,
    *OBSERVABLES_DATALUX,
)


@dataclass(frozen=True)
class ObservableScore:

    id: str

    etiqueta: str

    detalle: str

    score: int

    peso: str

    grupo: str


def _clamp_score(valor: float) -> int:

    return int(max(0, min(100, round(valor))))


_RESENAS_PRIOR = 3.2

_RESENAS_PRIOR_PESO = 24.0

_RESENAS_VOLUMEN_REF = 1500.0


def score_resenas(google_rating_avg: float | None, google_reviews_count: int) -> int:

    rating = max(0.0, min(5.0, float(google_rating_avg or 0.0)))

    reviews = max(0, int(google_reviews_count or 0))

    if reviews <= 0:

        return 20

    bayes = (_RESENAS_PRIOR * _RESENAS_PRIOR_PESO + rating * reviews) / (
        _RESENAS_PRIOR_PESO + reviews
    )

    rating_part = (bayes / 5.0) * 60.0 + 18.0

    volume_part = min(
        24.0, math.log1p(reviews) / math.log1p(_RESENAS_VOLUMEN_REF) * 24.0
    )

    return _clamp_score(min(92.0, rating_part + volume_part))


def razones_resenas(
    *,
    ficha: str | None,
    google_rating_avg: float | None,
    google_reviews_count: int,
    score: int | None = None,
) -> list[str]:

    out: list[str] = []

    nombre = (ficha or "").strip()

    if nombre:

        out.append(f"Ficha: {nombre}")

    else:

        out.append("Ficha: sin match en Google Places")

    if google_rating_avg is None:

        out.append("Rating Google: n/d")

    else:

        out.append(f"Rating Google: {float(google_rating_avg):.1f} / 5")

    reviews = max(0, int(google_reviews_count or 0))

    out.append(f"Reseñas: {reviews:,}".replace(",", "."))

    if score is not None:

        out.append(f"Score: {int(score)} / 100")

    return out


def armar_observables(valores: dict[str, int]) -> list[ObservableScore]:

    out: list[ObservableScore] = []

    for d in _CATALOGO_OBSERVABLES:

        if d.id not in valores:

            continue

        out.append(
            ObservableScore(
                id=d.id,
                etiqueta=d.etiqueta,
                detalle=d.detalle,
                score=_clamp_score(valores[d.id]),
                peso=d.peso,
                grupo=d.grupo,
            )
        )

    return out
