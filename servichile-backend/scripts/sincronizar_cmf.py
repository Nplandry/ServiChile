from __future__ import annotations

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:

    sys.path.insert(0, str(ROOT))

from app.config import get_settings

from app.infrastructure.cmf_api import CmfApiCliente

from app.infrastructure.cmf_repository import CmfInstitucionRepository

from app.infrastructure.db import get_engine

from app.services.cmf_sync_service import CmfSyncService

from sqlalchemy.orm import sessionmaker


def main() -> int:

    settings = get_settings()

    token = settings.cmf_api_key.get_secret_value() if settings.cmf_api_key else None

    if not token:

        print("Falta CMF_API_KEY en .env")

        return 1

    Session = sessionmaker(bind=get_engine(), expire_on_commit=False)

    session = Session()

    try:

        svc = CmfSyncService(CmfApiCliente(token), CmfInstitucionRepository(session))

        res = svc.sincronizar()

        print(
            f"OK CMF sync: codigos={res.codigos} perfiles_ok={res.perfiles_ok} guardadas_con_rut={res.instituciones}"
        )

        return 0

    finally:

        session.close()


if __name__ == "__main__":

    raise SystemExit(main())
