"""Puertos del dominio: contratos que la infraestructura debe cumplir.

Los servicios dependen de estos protocolos, no de SQLAlchemy, HTTP ni
proveedores concretos. Cada adaptador en ``app.infraestructura`` implementa
uno de ellos. ``app.api.dependencias`` es el único ensamblador.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.dominio.antecedentes import ResultadoAntecedentes
from app.dominio.entidades import Negocio, Reserva, TokenEmitido, Usuario


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


class VerificadorIdentidad(Protocol):
    def existe_y_activo(self, rut: str) -> bool: ...


class HasherContrasena(Protocol):
    def hash(self, password: str) -> str: ...

    def verificar(self, password_hash: str | None, password: str) -> bool: ...


class EmisorSesion(Protocol):
    def emitir(self, usuario_id: uuid.UUID) -> TokenEmitido: ...

    def sujeto(self, token: str) -> uuid.UUID: ...


@dataclass(frozen=True)
class TokenReporteFirmado:
    token: str
    expires_in: int
    expires_at: datetime


@dataclass(frozen=True)
class TokenReporteLeido:
    usuario_id: uuid.UUID
    expires_at: datetime


class EmisorReporte(Protocol):
    def emitir(self, usuario_id: uuid.UUID) -> TokenReporteFirmado: ...

    def leer(self, token: str) -> TokenReporteLeido: ...


class AnalizadorAntecedentes(Protocol):
    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes: ...


class NuloVerificadorIdentidad:
    def existe_y_activo(self, rut: str) -> bool:
        return False
