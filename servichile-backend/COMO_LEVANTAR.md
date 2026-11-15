# Cómo levantar

## Backend

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Pegue el token en JWT_SECRET del .env
```

Base Postgres (solo si aún no tiene contenedor):

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

### Base nueva (schema completo + datos demo)

```bash
psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
python -m scripts.cargar_db_demo
uvicorn app.principal:app --reload
```

`init_script.sql` ya incluye marketplace (`direccion`, `descripcion`, `requiere_nivel`, `imagen_url`, `logo_url`).  
`cargar_db_demo` siembra/actualiza los 6 negocios `seed:*` (fotos Unsplash, índices, niveles) y aplica migraciones pendientes (incl. biometría y XP).

Biometría (Zero-Retention): `POST /v1/perfil/biometria` con foto; cualquier imagen válida pasa y **no se guarda** la imagen, solo `biometria_verificada`.

### Base ya existente (solo migrar + seed)

```bash
python -m scripts.cargar_db_demo
# o, si prefiere SQL a mano:
# psql "postgresql://USUARIO@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/migrations/003_negocios.sql
# psql ... -f db/migrations/004_pasaporte.sql
# psql ... -f db/migrations/005_marketplace.sql
# psql ... -f db/migrations/006_marketplace_media.sql
# python -m scripts.sembrar_negocios
```

Refrescar solo el seed (borra y recrea `seed:*`):

```bash
python -m scripts.cargar_db_demo --reset-seed
# o: python -m scripts.sembrar_negocios --reset
```

## Frontend

```bash
cd servichile-frontend
python3 -m http.server 5500
```

```
API:       http://localhost:8000/docs
Frontend:  http://localhost:5500/index.html
```

## Tests

```bash
pytest
lint-imports
```
