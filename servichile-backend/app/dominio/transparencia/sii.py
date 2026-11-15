from __future__ import annotations

from dataclasses import dataclass

from app.dominio.transparencia.indicadores import DefinicionObservable, PESO_CIBER

OBSERVABLE_SII = DefinicionObservable(
    id="sii",
    etiqueta="Situación tributaria, cumplimiento y facturación electrónica",
    detalle="",
    grupo="legal",
    peso=PESO_CIBER,
)

_OBS_RIESGO = (
    "inconcurrente",
    "suplantado",
    "no_ubicado",
    "termino_giro",
    "domicilio_inexistente",
    "actividad_esporadica",
    "no_habido_domicilio",
    "termino_giro_obligatorio",
)


@dataclass(frozen=True)
class HallazgosSii:

    consulta_ok: bool = False

    inicio_actividades: bool = False

    obligacion_dte: bool = False

    tiene_dte_timbrado: bool = False

    termino_giro: bool = False

    observaciones_riesgo: int = 0


def score_sii(h: HallazgosSii) -> int:

    if not h.consulta_ok or h.termino_giro:

        return 0

    total = 10.0

    if h.inicio_actividades:

        total += 40

    if h.obligacion_dte:

        total += 25

    if h.tiene_dte_timbrado:

        total += 25

    total -= min(50.0, 10.0 * max(0, h.observaciones_riesgo))

    return int(max(0, min(100, round(total))))


def hallazgos_desde_payload(data: dict) -> HallazgosSii:

    obs = (
        data.get("observaciones") if isinstance(data.get("observaciones"), dict) else {}
    )

    riesgos = sum((1 for k in _OBS_RIESGO if bool(obs.get(k))))

    docs = data.get("documentos_timbrados") or []

    tiene_docs = isinstance(docs, list) and len(docs) > 0

    termino = bool(obs.get("termino_giro") or obs.get("termino_giro_obligatorio"))

    return HallazgosSii(
        consulta_ok=True,
        inicio_actividades=bool(data.get("inicio_actividades")),
        obligacion_dte=bool(data.get("obligacion_dte")),
        tiene_dte_timbrado=tiene_docs,
        termino_giro=termino,
        observaciones_riesgo=riesgos,
    )
