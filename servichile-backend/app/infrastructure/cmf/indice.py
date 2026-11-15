from __future__ import annotations

from app.domain.puertos import NuloCmf, ProveedorCmf, RepositorioCmf

from app.domain.transparencia.cmf import (
    HallazgosCmf,
    hallazgos_desde_institucion,
    normalizar_rut_cmf,
    score_cmf,
)


class NullCmfIndice(NuloCmf):
    pass


class FakeCmfIndice:

    def score_para_rut(self, rut: str | None) -> int:

        if not normalizar_rut_cmf(rut):

            return 0

        return score_cmf(
            HallazgosCmf(
                indice_disponible=True,
                rut_consultable=True,
                entidad_supervisada=True,
                ficha_completa=True,
            )
        )


class LocalCmfIndice:

    def __init__(self, repo: RepositorioCmf) -> None:

        self.repo = repo

    def score_para_rut(self, rut: str | None) -> int:

        rut_n = normalizar_rut_cmf(rut)

        if not rut_n:

            return score_cmf(
                HallazgosCmf(
                    indice_disponible=self.repo.indice_disponible(),
                    rut_consultable=False,
                )
            )

        disponible = self.repo.indice_disponible()

        inst = self.repo.get_por_rut(rut_n) if disponible else None

        return score_cmf(
            hallazgos_desde_institucion(
                indice_disponible=disponible, rut_consultable=True, institucion=inst
            )
        )


def build_cmf_indice(repo: RepositorioCmf | None, *, mode: str) -> ProveedorCmf:

    if mode == "fake":

        return FakeCmfIndice()

    if mode == "off" or repo is None:

        return NullCmfIndice()

    return LocalCmfIndice(repo)
