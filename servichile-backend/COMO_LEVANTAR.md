# Cómo levantar

```bash
cd servicia-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
docker run -d --name servicia-db -p 5432:5432 -e POSTGRES_USER=servicia -e POSTGRES_PASSWORD=servicia -e POSTGRES_DB=servicia pgvector/pgvector:pg16
psql "postgresql://servicia:servicia@localhost:5432/servicia" -v ON_ERROR_STOP=1 -f db/init_script.sql
uvicorn app.main:app --reload
```

```bash
cd serviclia-frontend
python3 -m http.server 5500
```

```
API:       http://localhost:8000/docs
Frontend:  http://localhost:5500/index.html
```

```bash
psql "postgresql://nicolaspoblete@localhost:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/003_negocios.sql
psql "postgresql://nicolaspoblete@localhost:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/004_pasaporte.sql
psql "postgresql://nicolaspoblete@localhost:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/005_marketplace.sql
python -m scripts.sembrar_negocios
```

```bash
pytest
lint-imports
```
