from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from sqlalchemy.orm import Session

from app.domain.transparencia.cmf import InstitucionCmf, normalizar_rut_cmf

from app.infrastructure.persistencia import modelos as orm

from app.tiempo import ahora_utc


class CmfInstitucionRepository:

    def __init__(self, session: Session) -> None:

        self.session = session

    def indice_disponible(self) -> bool:

        m = self.session.get(orm.CmfIndiceMeta, 1)

        return bool(m and m.filas > 0 and (m.sincronizado_en is not None))

    def get_por_rut(self, rut: str) -> InstitucionCmf | None:

        rut_n = normalizar_rut_cmf(rut)

        if not rut_n:

            return None

        row = self.session.scalar(
            select(orm.CmfInstitucion).where(orm.CmfInstitucion.rut == rut_n)
        )

        if row is None:

            return None

        return InstitucionCmf(
            codigo=row.codigo,
            nombre=row.nombre,
            rut=row.rut,
            direccion=row.direccion,
            web=row.web,
            sucursales=row.sucursales,
            empleados=row.empleados,
        )

    def reemplazar_indice(
        self,
        instituciones: list[InstitucionCmf],
        *,
        fuente: str,
        sincronizado_en: datetime | None = None,
    ) -> int:

        ahora = sincronizado_en or ahora_utc()

        self.session.execute(delete(orm.CmfInstitucion))

        vistos: set[str] = set()

        guardadas = 0

        for inst in instituciones:

            rut = normalizar_rut_cmf(inst.rut) if inst.rut else None

            if not rut or rut in vistos:

                continue

            vistos.add(rut)

            self.session.add(
                orm.CmfInstitucion(
                    rut=rut,
                    codigo=inst.codigo[:8],
                    nombre=(inst.nombre or "")[:200],
                    direccion=inst.direccion or None,
                    web=inst.web or None,
                    sucursales=inst.sucursales,
                    empleados=inst.empleados,
                )
            )

            guardadas += 1

        meta = self.session.get(orm.CmfIndiceMeta, 1)

        if meta is None:

            meta = orm.CmfIndiceMeta(id=1)

            self.session.add(meta)

        meta.sincronizado_en = ahora

        meta.filas = guardadas

        meta.fuente = fuente[:200]

        self.session.commit()

        return guardadas
