"""Puertos del dominio: contratos que la infraestructura debe cumplir.

Los servicios dependen de estos protocolos, no de SQLAlchemy, HTTP ni
proveedores concretos. Cada adaptador en ``app.infrastructure`` implementa
uno de ellos. ``app.api.dependencias`` es el único ensamblador.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.antecedentes import ResultadoAntecedentes
from app.domain.entidades import Negocio, Reserva, Usuario
from app.domain.transparencia.cmf import InstitucionCmf
from app.domain.transparencia.indicadores import ObservableScore


@dataclass(frozen=True)
class ResultadoSondaCiber:
    observables: list[ObservableScore]
    host: str | None
    scores: dict[str, int]
    docs_razones: dict[str, list[str]] | None = None


@dataclass(frozen=True)
class ResultadoIncidentes:
    score: int
    razones: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoPlaces:
    encontrado: bool
    rating: float | None = None
    reviews_count: int = 0
    place_id: str | None = None
    nombre: str | None = None


@dataclass(frozen=True)
class ResultadoSyncCmf:
    instituciones: int
    perfiles_ok: int
    codigos: int


class RepositorioUsuarios(Protocol):
    def get_by_email(self, email: str) -> Usuario | None: ...

    def get(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    def get_by_rut(self, rut: str) -> Usuario | None: ...

    def crear(self, email: str, nombre: str, password_hash: str) -> Usuario: ...

    def eliminar(self, usuario_id: uuid.UUID) -> None: ...

    def guardar(self, usuario: Usuario) -> Usuario: ...


class RepositorioNegocios(Protocol):
    def get(self, business_id: uuid.UUID) -> Negocio | None: ...

    def listar(
        self, categoria: str | None = None, q: str | None = None, limite: int = 100
    ) -> list[Negocio]: ...

    def listar_reclamados_por(self, usuario_id: uuid.UUID) -> list[Negocio]: ...

    def guardar(self, negocio: Negocio) -> Negocio: ...


class RepositorioReservas(Protocol):
    def crear(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID, qr_token: str
    ) -> Reserva: ...

    def get(self, reserva_id: uuid.UUID) -> Reserva | None: ...

    def get_por_qr(self, business_id: uuid.UUID, qr_token: str) -> Reserva | None: ...

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Reserva]: ...

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]: ...

    def guardar(self, reserva: Reserva) -> Reserva: ...


class RepositorioXp(Protocol):
    def otorgar(self, usuario_id: uuid.UUID, evento: str, puntos: int) -> int: ...

    def total(self, usuario_id: uuid.UUID) -> int: ...


class RepositorioCmf(Protocol):
    def indice_disponible(self) -> bool: ...

    def get_por_rut(self, rut: str) -> InstitucionCmf | None: ...

    def reemplazar_indice(
        self,
        instituciones: list[InstitucionCmf],
        *,
        fuente: str,
        sincronizado_en: datetime | None = None,
    ) -> int: ...


class VerificadorIdentidad(Protocol):
    def existe_y_activo(self, rut: str) -> bool: ...


class SondaCiber(Protocol):
    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber: ...


class ProveedorMercadoPublico(Protocol):
    def score_para_rut(self, rut: str | None) -> int: ...


class ProveedorSii(Protocol):
    def score_para_rut(self, rut: str | None) -> int: ...


class ProveedorCmf(Protocol):
    def score_para_rut(self, rut: str | None) -> int: ...


class ProveedorIncidentes(Protocol):
    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes: ...

    def score_para_nombre(self, nombre: str | None) -> int: ...


class ProveedorPlaces(Protocol):
    def buscar_reputacion(
        self,
        *,
        nombre: str | None,
        direccion: str | None = None,
        sitio_web: str | None = None,
    ) -> ResultadoPlaces: ...


class AnalizadorAntecedentes(Protocol):
    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes: ...


class ClienteCmfApi(Protocol):
    def listar_codigos_instituciones(
        self, *, anio: int | None = None, mes: int | None = None
    ) -> list[tuple[str, str]]: ...

    def perfil_institucion(
        self, codigo: str, *, anio: int | None = None, mes: int | None = None
    ) -> InstitucionCmf | None: ...


class NuloSondaCiber:
    def escanear(self, sitio_web: str | None) -> ResultadoSondaCiber:
        return ResultadoSondaCiber(observables=[], host=None, scores={})


class NuloMercadoPublico:
    def score_para_rut(self, rut: str | None) -> int:
        return 0


class NuloSii:
    def score_para_rut(self, rut: str | None) -> int:
        return 0


class NuloCmf:
    def score_para_rut(self, rut: str | None) -> int:
        return 0


class NuloIncidentes:
    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes:
        return ResultadoIncidentes(0, ("Módulo de incidentes no disponible.",))

    def score_para_nombre(self, nombre: str | None) -> int:
        return self.evaluar_nombre(nombre).score


class NuloPlaces:
    def buscar_reputacion(
        self,
        *,
        nombre: str | None,
        direccion: str | None = None,
        sitio_web: str | None = None,
    ) -> ResultadoPlaces:
        return ResultadoPlaces(encontrado=False)


class NuloAnalizadorAntecedentes:
    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes:
        return ResultadoAntecedentes(
            aceptado=False,
            score=0,
            anotaciones=None,
            folio=None,
            codigo=None,
            run=None,
            senales=(),
            motivo="Analizador de antecedentes no disponible.",
        )


class NuloVerificadorIdentidad:
    def existe_y_activo(self, rut: str) -> bool:
        return False
