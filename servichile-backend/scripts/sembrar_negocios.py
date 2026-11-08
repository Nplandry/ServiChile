"""Siembra negocios de ejemplo geolocalizados para el marketplace, con sus métricas e índice.

Uso:
    python -m scripts.sembrar_negocios          # inserta los que falten (idempotente por external_ref)
    python -m scripts.sembrar_negocios --reset  # borra los sembrados y los vuelve a crear

Coordenadas reales de Santiago (Providencia / Barrio Italia). El Índice de Transparencia
se calcula con la fórmula del dominio, igual que en producción.
"""
import argparse

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domain.reputacion import EntradaScore, calcular_indice
from app.infrastructure.db import BusinessEntity, BusinessReputationMetrics, get_engine

# external_ref con prefijo "seed:" para poder identificarlos y reinsertarlos sin duplicar.
NEGOCIOS = [
    {
        "external_ref": "seed:fithouse",
        "nombre": "FitHouse Gym & Studio",
        "categoria": "gimnasio",
        "direccion": "Av. Providencia 1420, Providencia",
        "descripcion": "Clases grupales, musculación de alto rendimiento y zona recovery.",
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
        "latitud": -33.4420,
        "longitud": -70.6330,
        "requiere_nivel": 2,
        "google_rating_avg": 4.9,
        "google_reviews_count": 95,
        "is_verified_profile": True,
    },
]


def _indice(n: dict) -> float:
    return calcular_indice(
        EntradaScore(
            google_rating_avg=n["google_rating_avg"],
            google_reviews_count=n["google_reviews_count"],
            is_verified_profile=n["is_verified_profile"],
        )
    )


def sembrar(reset: bool) -> None:
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        refs = [n["external_ref"] for n in NEGOCIOS]
        if reset:
            for negocio in session.scalars(select(BusinessEntity).where(BusinessEntity.external_ref.in_(refs))):
                session.delete(negocio)
            session.commit()

        existentes = set(
            session.scalars(select(BusinessEntity.external_ref).where(BusinessEntity.external_ref.in_(refs)))
        )
        creados = 0
        for n in NEGOCIOS:
            if n["external_ref"] in existentes:
                continue
            negocio = BusinessEntity(
                external_ref=n["external_ref"],
                nombre=n["nombre"],
                categoria=n["categoria"],
                direccion=n["direccion"],
                descripcion=n["descripcion"],
                latitud=n["latitud"],
                longitud=n["longitud"],
                requiere_nivel=n["requiere_nivel"],
            )
            negocio.metricas = BusinessReputationMetrics(
                google_rating_avg=n["google_rating_avg"],
                google_reviews_count=n["google_reviews_count"],
                is_verified_profile=n["is_verified_profile"],
                final_score=_indice(n),
            )
            session.add(negocio)
            creados += 1
        session.commit()
        print(f"Negocios creados: {creados}. Ya existían: {len(existentes)}.")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra negocios de ejemplo del marketplace.")
    parser.add_argument("--reset", action="store_true", help="Borra los negocios sembrados y los recrea.")
    sembrar(parser.parse_args().reset)


if __name__ == "__main__":
    main()
