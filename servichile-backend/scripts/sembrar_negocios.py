"""Siembra / actualiza negocios de prueba del marketplace.

Idempotente por external_ref con prefijo "seed:".
Sirve para cargar una DB vacía o refrescar datos demo en una DB ya migrada.

Uso:
    python -m scripts.sembrar_negocios
    python -m scripts.sembrar_negocios --reset
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.domain.reputacion import EntradaScore, calcular_indice
from app.infrastructure.db import BusinessEntity, BusinessReputationMetrics, get_engine

NEGOCIOS = [
    {
        "external_ref": "seed:fithouse",
        "nombre": "FitHouse Gym & Studio",
        "categoria": "gimnasio",
        "direccion": "Av. Providencia 1420, Providencia",
        "descripcion": "Clases grupales, musculación de alto rendimiento y zona recovery.",
        "imagen_url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=800&h=360&q=80",
        "logo_url": None,
        "latitud": -33.4265,
        "longitud": -70.6190,
        "requiere_nivel": 1,
        "google_rating_avg": 4.6,
        "google_reviews_count": 320,
        "is_verified_profile": True,
    },
    {
        "external_ref": "seed:dentalcare",
        "nombre": "Clínica Odontológica DentalCare",
        "categoria": "clinica-dental",
        "direccion": "Pedro de Valdivia 304, Providencia",
        "descripcion": "Especialistas en estética dental y evaluación integral.",
        "imagen_url": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=800&h=500&q=80",
        "logo_url": None,
        "latitud": -33.4280,
        "longitud": -70.6150,
        "requiere_nivel": 1,
        "google_rating_avg": 4.8,
        "google_reviews_count": 540,
        "is_verified_profile": True,
    },
    {
        "external_ref": "seed:italia-890",
        "nombre": "Dept. Moderno 2D/2B - Barrio Italia",
        "categoria": "arriendo",
        "direccion": "Av. Italia 890, Providencia",
        "descripcion": "Vista despejada, estacionamiento, bodega y áreas verdes. Cerca de Metro.",
        "imagen_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&h=500&q=80",
        "logo_url": None,
        "latitud": -33.4460,
        "longitud": -70.6240,
        "requiere_nivel": 2,
        "google_rating_avg": None,
        "google_reviews_count": 0,
        "is_verified_profile": False,
    },
    {
        "external_ref": "seed:bourgogne",
        "nombre": "Bistró La Bourgogne",
        "categoria": "restaurante",
        "direccion": "Santa Isabel 512, Santiago",
        "descripcion": "Cocina de autor y café de especialidad con terraza pet-friendly.",
        "imagen_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&h=500&q=80",
        "logo_url": None,
        "latitud": -33.4530,
        "longitud": -70.6350,
        "requiere_nivel": 1,
        "google_rating_avg": 4.4,
        "google_reviews_count": 210,
        "is_verified_profile": True,
    },
    {
        "external_ref": "seed:sunset-vip",
        "nombre": "Sunset Electronic Sessions - VIP",
        "categoria": "evento",
        "direccion": "Parque Bustamante - Sector Norte, Providencia",
        "descripcion": "Evento de cupo exclusivo. Acceso solo a perfiles verificados.",
        "imagen_url": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=800&h=500&q=80",
        "logo_url": None,
        "latitud": -33.4420,
        "longitud": -70.6330,
        "requiere_nivel": 2,
        "google_rating_avg": 4.9,
        "google_reviews_count": 95,
        "is_verified_profile": True,
    },
    {
        "external_ref": "seed:umayor",
        "nombre": "Universidad Mayor",
        "categoria": "otro",
        "direccion": "Av. Manuel Montt 367, Providencia",
        "descripcion": "Universidad privada acreditada. Campus Manuel Montt con pregrado, postgrado y educación continua.",
        "imagen_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=800&h=500&q=80",
        "logo_url": None,
        "latitud": -33.4318,
        "longitud": -70.6182,
        "requiere_nivel": 1,
        "google_rating_avg": 4.3,
        "google_reviews_count": 890,
        "is_verified_profile": True,
    },
]

COLUMNAS_REQUERIDAS = (
    "direccion",
    "descripcion",
    "requiere_nivel",
    "imagen_url",
    "logo_url",
)


def _indice(n: dict) -> float:
    return calcular_indice(
        EntradaScore(
            google_rating_avg=n["google_rating_avg"],
            google_reviews_count=n["google_reviews_count"],
            is_verified_profile=n["is_verified_profile"],
        )
    )


def _aplicar_negocio(negocio: BusinessEntity, n: dict) -> None:
    negocio.nombre = n["nombre"]
    negocio.categoria = n["categoria"]
    negocio.direccion = n["direccion"]
    negocio.descripcion = n["descripcion"]
    negocio.imagen_url = n["imagen_url"]
    negocio.logo_url = n["logo_url"]
    negocio.latitud = n["latitud"]
    negocio.longitud = n["longitud"]
    negocio.requiere_nivel = n["requiere_nivel"]


def _aplicar_metricas(negocio: BusinessEntity, n: dict) -> None:
    if negocio.metricas is None:
        negocio.metricas = BusinessReputationMetrics(business_id=negocio.id)
    negocio.metricas.google_rating_avg = n["google_rating_avg"]
    negocio.metricas.google_reviews_count = n["google_reviews_count"]
    negocio.metricas.is_verified_profile = n["is_verified_profile"]
    negocio.metricas.final_score = _indice(n)


def _verificar_esquema(engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("business_entities"):
        raise RuntimeError(
            "Falta la tabla business_entities. Corra db/init_script.sql "
            "o python -m scripts.cargar_db_demo."
        )
    columnas = {c["name"] for c in insp.get_columns("business_entities")}
    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in columnas]
    if faltan:
        raise RuntimeError(
            "El esquema de business_entities está incompleto. Faltan: "
            + ", ".join(faltan)
            + ". Aplique las migraciones 005 y 006, o python -m scripts.cargar_db_demo."
        )
    if not insp.has_table("business_reputation_metrics"):
        raise RuntimeError(
            "Falta business_reputation_metrics. Corra db/init_script.sql "
            "o python -m scripts.cargar_db_demo."
        )


def sembrar(reset: bool) -> None:
    engine = get_engine()
    _verificar_esquema(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        refs = [n["external_ref"] for n in NEGOCIOS]
        if reset:
            for negocio in session.scalars(select(BusinessEntity).where(BusinessEntity.external_ref.in_(refs))):
                session.delete(negocio)
            session.commit()

        existentes = {
            row.external_ref: row
            for row in session.scalars(select(BusinessEntity).where(BusinessEntity.external_ref.in_(refs)))
        }
        creados = 0
        actualizados = 0
        for n in NEGOCIOS:
            actual = existentes.get(n["external_ref"])
            if actual is None:
                negocio = BusinessEntity(external_ref=n["external_ref"])
                _aplicar_negocio(negocio, n)
                session.add(negocio)
                session.flush()
                _aplicar_metricas(negocio, n)
                creados += 1
            else:
                _aplicar_negocio(actual, n)
                _aplicar_metricas(actual, n)
                actualizados += 1
        session.commit()

        total = session.scalar(
            text("SELECT count(*) FROM business_entities WHERE external_ref LIKE 'seed:%'")
        )
        print(f"Negocios demo creados: {creados}. Actualizados: {actualizados}. Total seed: {total}.")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra negocios de prueba del marketplace.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra los negocios seed:* y los recrea desde cero.",
    )
    try:
        sembrar(parser.parse_args().reset)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
