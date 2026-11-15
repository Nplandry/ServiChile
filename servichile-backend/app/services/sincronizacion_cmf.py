from __future__ import annotations

from app.domain.puertos import ClienteCmfApi, RepositorioCmf, ResultadoSyncCmf
from app.domain.transparencia.cmf import InstitucionCmf


class CmfSyncService:
    def __init__(self, api: ClienteCmfApi, repo: RepositorioCmf) -> None:
        self.api = api
        self.repo = repo

    def sincronizar(self) -> ResultadoSyncCmf:
        pares = self.api.listar_codigos_instituciones()
        pares = [(c, n) for c, n in pares if c != "999"]
        fichas: list[InstitucionCmf] = []
        ok = 0
        for codigo, nombre_lista in pares:
            perfil = self.api.perfil_institucion(codigo)
            if perfil is None:
                continue
            ok += 1
            if not perfil.nombre and nombre_lista:
                perfil = InstitucionCmf(
                    codigo=perfil.codigo,
                    nombre=nombre_lista,
                    rut=perfil.rut,
                    direccion=perfil.direccion,
                    web=perfil.web,
                    sucursales=perfil.sucursales,
                    empleados=perfil.empleados,
                )
            if perfil.rut:
                fichas.append(perfil)
        guardadas = self.repo.reemplazar_indice(
            fichas, fuente="api.cmfchile.cl/api-sbifv3 perfil+instituciones"
        )
        return ResultadoSyncCmf(
            instituciones=guardadas, perfiles_ok=ok, codigos=len(pares)
        )
