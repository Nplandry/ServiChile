# ServiChile API

## Endpoints

| Método | Ruta                                            | Sesión        | Descripción                                       | Archivo                  | Estado                 |
| ------ | ----------------------------------------------- | ------------- | ------------------------------------------------- | ------------------------ | ---------------------- |
| GET    | /salud                                          | No            | Healthcheck                                       | app.principal            | Implementado y probado |
| POST   | /v1/auth/registro                               | No            | Registra usuario                                  | app.api.v1.autenticacion | Implementado y probado |
| POST   | /v1/auth/login                                  | No            | Login JWT                                         | app.api.v1.autenticacion | Implementado y probado |
| GET    | /v1/auth/yo                                     | Sí            | Datos del usuario autenticado                     | app.api.v1.autenticacion | Implementado y probado |
| GET    | /v1/perfil                                      | Sí            | Estado del Reporte de Confianza                   | app.api.v1.perfil        | Implementado y probado |
| PATCH  | /v1/perfil                                      | Sí            | Actualiza edad, teléfono y verifica el RUT        | app.api.v1.perfil        | Implementado y probado |
| POST   | /v1/perfil/biometria                            | Sí            | Verificación biométrica                           | app.api.v1.perfil        | Implementado y probado |
| GET    | /v1/trabajos                                    | Sí            | Trabajos del usuario con su código QR             | app.api.v1.trabajos      | Implementado y probado |
| POST   | /v1/trabajos                                    | Sí            | Abre un trabajo con un proveedor                  | app.api.v1.trabajos      | Implementado y probado |
| DELETE | /v1/trabajos/{id}                               | Sí            | Cancela un trabajo propio abierto                 | app.api.v1.trabajos      | Implementado y probado |
| DELETE | /v1/auth/yo                                     | Sí            | Elimina la cuenta con confirmación por contraseña | app.api.v1.autenticacion | Implementado y probado |
| GET    | /v1/businesses                                  | No            | Marketplace público                               | app.api.v1.negocios      | Implementado y probado |
| POST   | /v1/businesses                                  | Sí, proveedor | Crea empresa                                      | app.api.v1.negocios      | Implementado y probado |
| GET    | /v1/businesses/mias                             | Sí            | Empresas del titular                              | app.api.v1.negocios      | Implementado y probado |
| POST   | /v1/businesses/{id}/rater-refresh               | Sí, titular   | Re-evalúa evaluador e índice                      | app.api.v1.negocios      | Implementado y probado |
| POST   | /v1/businesses/{id}/trabajos/concretar          | Sí, titular   | Marca trabajo concretado con QR                   | app.api.v1.trabajos      | Implementado y probado |
| POST   | /v1/businesses/{id}/trabajos/{id}/no-concretado | Sí, titular   | Marca no concretado                               | app.api.v1.trabajos      | Implementado y probado |
| GET    | /v1/businesses/{id}/reputation                  | No            | Índice de Transparencia                           | app.api.v1.negocios      | Implementado y probado |
| DELETE | /v1/businesses/{id}                             | Sí, creador   | Elimina la empresa                                | app.api.v1.negocios      | Implementado y probado |

## Levantar en local
Requisitos previos:
Python 3.12
Docker y psql instalado y en ejecución
Puertos libres: 5432, 6379, 8000, 5500

Requisitos: Python 3.12 y PostgreSQL. Ejemplo con Docker:

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

Luego:

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"

psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql

uvicorn app.principal:app --reload
```

Pegue el valor generado en JWT_SECRET del .env.

## Pruebas

```bash
pytest
```

Las pruebas unitarias usan SQLite en memoria. No necesitan PostgreSQL.

# Cómo levantar

## Backend

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegue el token en JWT_SECRET del .env.

### Postgres

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

### Redis

```bash
docker run -d --name servichile-redis -p 6379:6379 redis:7-alpine
```

En .env: REDIS_URL=redis://localhost:6379/0

### Mailhog

```bash
docker run -d --name servichile-mailhog -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

### Base nueva

```bash
psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
python -m scripts.cargar_db_demo
uvicorn app.principal:app --reload
```

### Base ya existente

```bash
python -m scripts.cargar_db_demo
```

Refrescar seed:

```bash
python -m scripts.cargar_db_demo --reset-seed
```

### Arranque diario

```bash
cd ~/Desktop/pwa2/servichile-backend
source .venv/bin/activate
uvicorn app.principal:app --reload --port 8000
```

### Migraciones de compras (VPS / production)

```bash
cd ~/servichile-backend
source .venv/bin/activate
python -m scripts.aplicar_migraciones_compras
```

## Frontend

```bash
cd servichile-frontend
python3 serve.py 5500
```

## Tests

```bash
cd servichile-backend
source .venv/bin/activate
pytest
lint-imports
```
