from __future__ import annotations

from dataclasses import dataclass

from app.dominio.transparencia.indicadores import DefinicionObservable, PESO_CIBER

OBSERVABLE_MERCADO_PUBLICO = DefinicionObservable(
    id="mercado-publico",
    etiqueta="Historial y penalidades en compras públicas / Estado",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)


@dataclass(frozen=True)
class HallazgosMercadoPublico:

    consulta_ok: bool = False

    proveedor_encontrado: bool = False

    codigo_proveedor: str | None = None

    tiene_ordenes_recientes: bool = False


def score_mercado_publico(h: HallazgosMercadoPublico) -> int:

    if not h.consulta_ok or not h.proveedor_encontrado:

        return 0

    total = 92.0

    if h.tiene_ordenes_recientes:

        total = 100.0

    return int(max(0, min(100, round(total))))


def rut_desde_documento(texto: str | None) -> str | None:

    if not texto or not str(texto).strip():

        return None

    from app.dominio.pasaporte import RutInvalido, normalizar_rut

    try:

        return normalizar_rut(str(texto).strip())

    except RutInvalido:

        return None


def formato_rut_chilecompra(rut_normalizado: str) -> str:

    cuerpo, dv = rut_normalizado.upper().split("-", 1)

    digitos = list(cuerpo)

    grupos: list[str] = []

    while digitos:

        trozo: list[str] = []

        for _ in range(3):

            if digitos:

                trozo.append(digitos.pop())

        grupos.append("".join(reversed(trozo)))

    return f"{'.'.join(reversed(grupos))}-{dv}"
