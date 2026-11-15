from __future__ import annotations

import re

from datetime import datetime

from pypdf import PdfReader

from pypdf.errors import PdfReadError

from app.domain.antecedentes import (
    ResultadoAntecedentes,
    validar_certificado_antecedentes,
)


def _parse_pdf_date(raw: str | None) -> datetime | None:

    if not raw:

        return None

    m = re.match("D:(\\d{4})(\\d{2})(\\d{2})(\\d{2})(\\d{2})(\\d{2})", str(raw).strip())

    if not m:

        return None

    y, mo, d, h, mi, s = (int(x) for x in m.groups())

    try:

        return datetime(y, mo, d, h, mi, s)

    except ValueError:

        return None


def analizar_pdf_antecedentes(
    pdf_bytes: bytes, nombre_archivo: str | None = None
) -> ResultadoAntecedentes:

    try:

        from io import BytesIO

        reader = PdfReader(BytesIO(pdf_bytes))

    except (PdfReadError, Exception):

        return validar_certificado_antecedentes(
            pdf_bytes,
            nombre_archivo=nombre_archivo,
            encrypted=False,
            num_paginas=0,
            texto="",
        )

    encrypted = bool(reader.is_encrypted)

    if encrypted:

        try:

            reader.decrypt("")

        except Exception:

            return validar_certificado_antecedentes(
                pdf_bytes,
                nombre_archivo=nombre_archivo,
                encrypted=True,
                num_paginas=0,
                texto="",
            )

    meta = reader.metadata

    producer = None

    creation = None

    if meta is not None:

        producer = getattr(meta, "producer", None) or meta.get("/Producer")

        creation_raw = getattr(meta, "creation_date", None)

        if creation_raw is None:

            creation = _parse_pdf_date(meta.get("/CreationDate"))

        elif isinstance(creation_raw, datetime):

            creation = creation_raw.replace(tzinfo=None)

        else:

            creation = _parse_pdf_date(str(creation_raw))

    textos: list[str] = []

    for page in reader.pages:

        try:

            textos.append(page.extract_text() or "")

        except Exception:

            continue

    return validar_certificado_antecedentes(
        pdf_bytes,
        nombre_archivo=nombre_archivo,
        meta_creation=creation,
        producer=str(producer) if producer else None,
        encrypted=False,
        num_paginas=len(reader.pages),
        texto="\n".join(textos),
    )


class AnalizadorPdfAntecedentes:
    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes:
        return analizar_pdf_antecedentes(contenido, nombre_archivo)
