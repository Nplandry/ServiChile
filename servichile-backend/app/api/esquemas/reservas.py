"""Esquemas de reservas y cuenta."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class ReservaIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    business_id: UUID


class ReservaOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    business_id: UUID

    estado: Literal["reservada", "asistido", "no_show", "cancelada"]

    qr_token: str

    creado_en: datetime


class CheckinIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    qr_token: str = Field(min_length=10, max_length=64)


class EliminarCuentaIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


