"""Contrato persistido de docs_empresa (MetaDocEmpresa)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class MetaDocEmpresa:
    """Metadatos persistidos de un documento de empresa (contrato de dominio)."""

    verificado: bool = False
    verificado_en: str | None = None
    score: int | None = None
    senales: list[str] = field(default_factory=list)
    verificado_criptograficamente: bool | None = None
    entidad_emisora: str | None = None
    fecha_emision: str | None = None
    sha256_hash: str | None = None
    glosa: str | None = None
    rut_detectado: str | None = None
    grupo: int | str | None = None
    documento_tipo: str | None = None

    def a_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != []}


DocsEmpresa = dict[str, MetaDocEmpresa]


def meta_doc_desde_raw(raw: Any) -> MetaDocEmpresa | None:
    if not isinstance(raw, dict):
        return None
    senales = raw.get("senales")
    return MetaDocEmpresa(
        verificado=bool(raw.get("verificado")),
        verificado_en=raw.get("verificado_en"),
        score=raw.get("score"),
        senales=list(senales) if isinstance(senales, list) else [],
        verificado_criptograficamente=raw.get("verificado_criptograficamente"),
        entidad_emisora=raw.get("entidad_emisora"),
        fecha_emision=raw.get("fecha_emision"),
        sha256_hash=raw.get("sha256_hash"),
        glosa=raw.get("glosa"),
        rut_detectado=raw.get("rut_detectado"),
        grupo=raw.get("grupo"),
        documento_tipo=raw.get("documento_tipo"),
    )


def docs_empresa_desde_raw(raw: Any) -> DocsEmpresa:
    if not isinstance(raw, dict):
        return {}
    out: DocsEmpresa = {}
    for tipo, meta in raw.items():
        normalizado = meta_doc_desde_raw(meta)
        if normalizado is not None:
            out[str(tipo)] = normalizado
    return out


def docs_empresa_a_raw(docs: DocsEmpresa | None) -> dict[str, Any]:
    if not docs:
        return {}
    out: dict[str, Any] = {}
    for tipo, meta in docs.items():
        if isinstance(meta, MetaDocEmpresa):
            out[str(tipo)] = meta.a_dict()
    return out

