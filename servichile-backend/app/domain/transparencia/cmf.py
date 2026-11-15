from __future__ import annotations

from dataclasses import dataclass

from app.domain.transparencia.indicadores import DefinicionObservable, PESO_CIBER

from app.domain.pasaporte import RutInvalido, normalizar_rut

OBSERVABLE_CMF = DefinicionObservable(
    id="cmf",
    etiqueta="Supervisión CMF Bancos (ficha institucional)",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)


@dataclass(frozen=True)
class InstitucionCmf:

    codigo: str

    nombre: str

    rut: str | None = None

    direccion: str | None = None

    web: str | None = None

    sucursales: int | None = None

    empleados: int | None = None


@dataclass(frozen=True)
class HallazgosCmf:

    indice_disponible: bool = False

    rut_consultable: bool = False

    entidad_supervisada: bool = False

    ficha_completa: bool = False


def normalizar_rut_cmf(texto: str | None) -> str | None:

    if not texto or not str(texto).strip():

        return None

    try:

        return normalizar_rut(str(texto).strip())

    except RutInvalido:

        limpio = str(texto).replace(".", "").replace(" ", "").upper()

        if "-" in limpio:

            try:

                return normalizar_rut(limpio)

            except RutInvalido:

                return None

        return None


def score_cmf(h: HallazgosCmf) -> int:

    if not h.rut_consultable or not h.indice_disponible:

        return 0

    if not h.entidad_supervisada:

        return 100

    if h.ficha_completa:

        return 100

    return 80


def hallazgos_desde_institucion(
    *,
    indice_disponible: bool,
    rut_consultable: bool,
    institucion: InstitucionCmf | None,
) -> HallazgosCmf:

    if not indice_disponible or not rut_consultable:

        return HallazgosCmf(
            indice_disponible=indice_disponible, rut_consultable=rut_consultable
        )

    if institucion is None:

        return HallazgosCmf(
            indice_disponible=True, rut_consultable=True, entidad_supervisada=False
        )

    completa = bool(
        institucion.nombre
        and institucion.rut
        and (institucion.direccion or institucion.web)
    )

    return HallazgosCmf(
        indice_disponible=True,
        rut_consultable=True,
        entidad_supervisada=True,
        ficha_completa=completa,
    )
