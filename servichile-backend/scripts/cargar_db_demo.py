"""Carga o actualiza la base con el esquema marketplace y los negocios de prueba.

No borra usuarios ni reservas ajenas. Solo asegura columnas demo y siembra seed:*.

Uso típico (DB ya creada):
    python -m scripts.cargar_db_demo

Opciones:
    python -m scripts.cargar_db_demo --reset-seed
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from app.infrastructure.db import get_engine
from scripts.sembrar_negocios import sembrar

ROOT = Path(__file__).resolve().parents[1]
MIGRACIONES = [
    ROOT / "db" / "migrations" / "003_negocios.sql",
    ROOT / "db" / "migrations" / "004_pasaporte.sql",
    ROOT / "db" / "migrations" / "005_marketplace.sql",
    ROOT / "db" / "migrations" / "006_marketplace_media.sql",
]


def _psql_url(database_url: str) -> str:
    # Convierte postgresql+psycopg://... a postgresql://... para psql.
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _correr_sql(archivo: Path, database_url: str) -> None:
    url = _psql_url(database_url)
    cmd = ["psql", url, "-v", "ON_ERROR_STOP=1", "-f", str(archivo)]
    print("→", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _schema_listo(engine) -> bool:
    insp = inspect(engine)
    if not insp.has_table("business_entities"):
        return False
    cols = {c["name"] for c in insp.get_columns("business_entities")}
    return {"direccion", "descripcion", "requiere_nivel", "imagen_url", "logo_url"}.issubset(cols)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara schema demo y siembra negocios.")
    parser.add_argument(
        "--reset-seed",
        action="store_true",
        help="Borra y recrea solo los negocios seed:*.",
    )
    parser.add_argument(
        "--solo-seed",
        action="store_true",
        help="No intenta migraciones; solo siembra si el schema ya está listo.",
    )
    args = parser.parse_args()

    engine = get_engine()
    database_url = str(engine.url)

    if not args.solo_seed and not _schema_listo(engine):
        print("Schema incompleto. Aplicando migraciones 003-006...")
        for migracion in MIGRACIONES:
            if not migracion.exists():
                raise SystemExit(f"No existe {migracion}")
            try:
                _correr_sql(migracion, database_url)
            except FileNotFoundError:
                raise SystemExit("No se encontró el comando psql en el PATH.") from None
            except subprocess.CalledProcessError as e:
                raise SystemExit(
                    f"Falló {migracion.name}. Si la tabla es de otro dueño, "
                    "corra el psql con el usuario dueño de la base."
                ) from e

    if not _schema_listo(engine):
        raise SystemExit(
            "El schema sigue incompleto. Cargue db/init_script.sql en una base nueva "
            "o aplique las migraciones manualmente."
        )

    with engine.connect() as conn:
        usuarios = conn.execute(text("SELECT count(*) FROM usuarios")).scalar()
        print(f"DB lista. Usuarios existentes: {usuarios}.")

    sembrar(reset=args.reset_seed)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1) from e
    except subprocess.CalledProcessError:
        raise SystemExit(1) from None
