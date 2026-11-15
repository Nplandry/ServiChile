from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.dominio.transparencia.indicadores import PESO_CIBER, DefinicionObservable

PESO_DATALUX = "2.0%"
SCORE_BASE = 50
SCORE_MATCH = 100
OIDS_DATALUX = ("persona-juridica", "domicilio", "huella-digital")

OBSERVABLE_PERSONA_JURIDICA = DefinicionObservable(
    id="persona-juridica",
    etiqueta="Vigencia y estado de la persona jurídica",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)
OBSERVABLE_DOMICILIO = DefinicionObservable(
    id="domicilio",
    etiqueta="Verificación de domicilio operativo real y oficinas",
    detalle="",
    grupo="operativa",
    peso=PESO_DATALUX,
)
OBSERVABLE_HUELLA = DefinicionObservable(
    id="huella-digital",
    etiqueta="Coherencia y solidez de huella digital y reputación corporativa",
    detalle="",
    grupo="operativa",
    peso=PESO_DATALUX,
)
OBSERVABLES_DATALUX = (
    OBSERVABLE_PERSONA_JURIDICA,
    OBSERVABLE_DOMICILIO,
    OBSERVABLE_HUELLA,
)

_RE_NO_ALNUM = re.compile(r"[^a-z0-9]+")
_RE_SPLIT = re.compile(r"[^a-z0-9]+")
_RE_RUT = re.compile(r"^(\d{7,8})-?([\dK])$")
_RE_FECHA = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
_RE_QUIEBRA = re.compile(
    r"\b(quiebra|insolvencia|cesacion de pagos|cesación de pagos)\b",
    re.I,
)
_RE_DISOLUCION = re.compile(
    r"\b(disolu|liquidaci|termino de giro|término de giro)\b",
    re.I,
)
_ESTADOS_ACTIVOS = ("vigente", "activo", "activa")


@dataclass(frozen=True)
class ActividadEconomica:
    nombre: str = ""
    fecha_inicio: str = ""


@dataclass(frozen=True)
class FichaDatalux:
    nombre: str = ""
    rut: str = ""
    estado: str = ""
    direccion: str = ""
    comuna: str = ""
    resumen: str = ""
    anio_inicio: str = ""
    actividades_economicas: tuple[ActividadEconomica, ...] = ()


@dataclass(frozen=True)
class HallazgosDatalux:
    ficha: FichaDatalux | None = None
    rut_coincide: bool = False
    domicilio_coincide: bool = False
    empresa_activa: bool = False
    documento_presente: bool = False


@dataclass(frozen=True)
class ScoresDatalux:
    domicilio: int
    huella_digital: int
    persona_juridica: int
    razones: dict[str, list[str]]

    def como_dict(self) -> dict[str, int]:
        return {
            "persona-juridica": self.persona_juridica,
            "domicilio": self.domicilio,
            "huella-digital": self.huella_digital,
        }


def _ascii_lower(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _fold(texto: str) -> str:
    return _RE_NO_ALNUM.sub("", _ascii_lower(texto))


def _tokens(texto: str) -> set[str]:
    return {p for p in _RE_SPLIT.split(_ascii_lower(texto)) if len(p) >= 3}


def _solape(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if ta and tb:
        return len(ta & tb) / max(1, min(len(ta), len(tb)))
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return 0.0
    return 1.0 if fa in fb or fb in fa else 0.0


def _clip(valor: int) -> int:
    return max(0, min(100, valor))


def normalizar_rut(texto: str | None) -> str | None:
    raw = (texto or "").strip().upper().replace(".", "").replace(" ", "")
    m = _RE_RUT.match(raw)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _estado_activo(estado: str) -> bool:
    e = (estado or "").lower()
    return any(x in e for x in _ESTADOS_ACTIVOS)


def evaluar_match(
    *,
    nombre: str | None,
    direccion: str | None,
    rut_empresa: str | None,
    ficha: FichaDatalux | None,
) -> HallazgosDatalux:
    doc = bool(normalizar_rut(rut_empresa))
    if ficha is None:
        return HallazgosDatalux(documento_presente=doc)

    rn, rf = normalizar_rut(rut_empresa), normalizar_rut(ficha.rut)
    dir_local = (direccion or "").strip()
    dir_ficha = " ".join(p for p in (ficha.direccion, ficha.comuna) if p)
    return HallazgosDatalux(
        ficha=ficha,
        rut_coincide=bool(rn and rf and rn == rf),
        domicilio_coincide=bool(
            dir_local and dir_ficha and _solape(dir_local, dir_ficha) >= 0.6
        ),
        empresa_activa=_estado_activo(ficha.estado),
        documento_presente=doc,
    )


def score_domicilio(h: HallazgosDatalux) -> int:
    if h.ficha is not None and h.documento_presente and h.domicilio_coincide:
        return SCORE_MATCH
    return SCORE_BASE


def score_huella_digital(h: HallazgosDatalux) -> int:
    if (
        h.ficha is not None
        and h.documento_presente
        and h.rut_coincide
        and h.empresa_activa
    ):
        return SCORE_MATCH
    return SCORE_BASE


def score_persona_juridica(ficha: FichaDatalux | None) -> int:
    if ficha is None:
        return 0

    texto = " ".join(p for p in (ficha.nombre, ficha.estado, ficha.resumen) if p)
    estado = (ficha.estado or "").lower()
    activa = _estado_activo(ficha.estado)
    puntaje = 0
    if activa:
        puntaje += 50
    if normalizar_rut(ficha.rut):
        puntaje += 20
    if ficha.anio_inicio or any(
        _RE_FECHA.search(a.fecha_inicio or "") for a in ficha.actividades_economicas
    ):
        puntaje += 15
    if ficha.actividades_economicas:
        puntaje += 15
    if _RE_QUIEBRA.search(texto):
        puntaje -= 40
    if _RE_DISOLUCION.search(texto):
        puntaje -= 30
    if estado and not activa:
        puntaje -= 20
    return _clip(puntaje)


def _razones(
    h: HallazgosDatalux,
    *,
    sc_dom: int,
    sc_huella: int,
    sc_pj: int,
) -> dict[str, list[str]]:
    ficha = h.ficha
    if ficha is None:
        return {oid: [] for oid in OIDS_DATALUX}

    nombre = [ficha.nombre] if ficha.nombre else []
    return {
        "persona-juridica": [
            *nombre,
            *([ficha.estado] if ficha.estado else []),
            *(["Persona jurídica vigente"] if sc_pj >= 70 else []),
        ],
        "domicilio": [
            *nombre,
            *([ficha.direccion] if ficha.direccion else []),
            *(["Domicilio verificado"] if sc_dom == SCORE_MATCH else []),
        ],
        "huella-digital": [
            *nombre,
            *([ficha.rut] if ficha.rut else []),
            *(["Identidad verificada"] if sc_huella == SCORE_MATCH else []),
        ],
    }


def scores_desde_ficha(
    *,
    nombre: str | None,
    direccion: str | None,
    rut_empresa: str | None,
    ficha: FichaDatalux | None,
) -> ScoresDatalux:
    h = evaluar_match(
        nombre=nombre, direccion=direccion, rut_empresa=rut_empresa, ficha=ficha
    )
    sc_dom = score_domicilio(h)
    sc_huella = score_huella_digital(h)
    sc_pj = score_persona_juridica(ficha)
    return ScoresDatalux(
        domicilio=sc_dom,
        huella_digital=sc_huella,
        persona_juridica=sc_pj,
        razones=_razones(h, sc_dom=sc_dom, sc_huella=sc_huella, sc_pj=sc_pj),
    )
