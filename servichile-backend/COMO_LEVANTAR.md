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

`init_script.sql` incluye el esquema completo (usuarios/pasaporte, marketplace, métricas rater, docs_empresa, PAdES). Bases existentes: migraciones hasta `042`.  
`cargar_db_demo` siembra/actualiza los 6 negocios `seed:*` (fotos Unsplash, índices, niveles) y aplica migraciones pendientes (incl. biometría, XP y 041–042).

Biometría: `POST /v1/perfil/biometria` con foto; JPEG comprimido en `BIOMETRIA_DIR` (`var/biometria/`) + metadata en Postgres. No se sirve al público; se borra al eliminar la cuenta.

Cédula: primero `POST /v1/perfil/biometria` (selfie en `var/biometria`). Luego `POST /v1/perfil/cedula` con foto frontal: endereza el carnet, OCR Tesseract + ROI del RUN, y face-match OpenCV contra la selfie. Sin Paddle/LLM. La foto del carnet **no se retiene**. Requiere `brew install tesseract tesseract-lang` y `opencv-python-headless` (en `requirements.txt`). Si el RUT aún no está verificado, se adopta el del carnet.

Aval/garantía: `POST /v1/perfil/aval` con **PDF textual** (no fotos ni escaneos). Score por keywords + RUT/monto/fecha/emisor; tipo `carta_aval|boleta|poliza`. Sin IA. El PDF **no se retiene**. Migración: `db/migrations/033_aval.sql`.

Docs empresa (proveedor):
- Grupo 1 (PAdES): `POST .../documentos/{tipo}` — carpeta_tributaria, inicio_actividades, vigencia_sociedad, vigencia_poderes, poder_representante, constitucion, f30, no_quiebra, antecedentes_rl. Orden: intact → ENTIRE_FILE → trusted (`ca_chile.pem`) → emisor → texto firmado.
- Grupo 2 (híbrido PDF): patente, titularidad_cuenta.
Bóveda: `app/infraestructura/certs/ca_chile.pem`. Migraciones: `034`, `035`, `036_pades_trust_hashes.sql`.

Antecedentes (persona): PDF textual + PAdES confiable (CA Chile). Anti-replay por `sha256`.

Rater empresa (`observables` en reputation; **no** se calcula en vivo en el GET):
- Se ejecuta al **crear** la empresa (y al guardar/actualizar RUT) y se refresca en background cada `RATER_REFRESH_MINUTES` (default 30).
- Fuentes: crawler del `sitio_web` (cabeceras), Google Places, ChileCompra (RUT).
- Sin dirección / teléfono / RUT / sitio en la ficha → esos indicadores quedan en **0**.
- `RATER_MODE=muestra` / `APP_ENV=test` → valores fijos (no llama APIs). En `test` el loop background no arranca.
- Places: `GOOGLE_PLACES_API_KEY` vacío → muestra; con key → produccion.
- ChileCompra: `CHILECOMPRA_TICKET` vacío → muestra; con ticket → produccion.
- Migraciones: `037` (JSON observables) + `042` (renombre a `observables` / `rater_escaneado_en`).

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
backend diario
```bash
cd ~/Desktop/pwa2/servichile-backend
source .venv/bin/activate
uvicorn app.principal:app --reload --port 8000
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
