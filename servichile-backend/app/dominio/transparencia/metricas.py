"""Desglose del índice. Siempre el mismo ejemplo, sin leer la base ni buscar afuera."""

from app.dominio.entidades import ObservableCiber
from app.dominio.transparencia.indicadores import armar_observables

# Lo que muestra el desglose de cualquier ficha.
SCORES_MOCK: dict[str, int] = {
    "ssl-tls": 100,
    "email-auth": 100,
    "puertos": 100,
    "headers-http": 0,
    "stack-vulnerable": 85,
    "blacklist": 100,
    "dnssec": 60,
    "subdominios": 80,
    "whois": 70,
    "persona-juridica": 85,
    "sii": 0,
    "mercado-publico": 0,
    "cmf": 0,
    "politica-privacidad": 18,
    "cookies": 85,
    "terminos": 18,
    "sla": 22,
    "domicilio": 50,
    "huella-digital": 50,
    "incidentes": 100,
    "uptime": 100,
    "resenas-reclamos": 20,
}


_OBSERVABLES_MOCK: tuple[ObservableCiber, ...] = tuple(
    ObservableCiber(
        id=item.id,
        etiqueta=item.etiqueta,
        detalle=item.detalle,
        score=item.score,
        peso=item.peso,
        grupo=item.grupo,
    )
    for item in armar_observables(SCORES_MOCK)
)


def observables_mock() -> list[ObservableCiber]:
    return list(_OBSERVABLES_MOCK)
