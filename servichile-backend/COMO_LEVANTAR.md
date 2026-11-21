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

Redis (obligatorio en `local` / `production`; caché, rate limits, estado `/salud`):

```bash
docker run -d --name servichile-redis -p 6379:6379 redis:7-alpine
```

En `.env`: `REDIS_URL=redis://localhost:6379/0` (como en `.env.example`). El arranque hace ping; sin Redis no sube.

Mailhog (correo local de comprobantes; UI en `:8025`):

```bash
docker run -d --name servichile-mailhog -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

En `.env`: `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_DESDE=noreply@servichile.local`, `SMTP_STARTTLS=false`.

### Base nueva (schema completo + datos demo)

```bash
psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
python -m scripts.cargar_db_demo
uvicorn app.principal:app --reload
```

`init_script.sql` incluye el esquema completo (usuarios/reporte, marketplace, métricas rater, docs_empresa, PAdES). Bases existentes: migraciones hasta `043`.  
`cargar_db_demo` siembra/actualiza los 6 negocios `seed:*` (fotos Unsplash, índices, niveles) y aplica migraciones pendientes (incl. biometría, XP y 041–042).

Biometría: `POST /v1/perfil/biometria` con foto; JPEG comprimido en `BIOMETRIA_DIR` (`var/biometria/`) + metadata en Postgres. No se sirve al público; se borra al eliminar la cuenta.

Cédula: primero `POST /v1/perfil/biometria` (selfie en `var/biometria`). Luego `POST /v1/perfil/cedula` con foto frontal: endereza el carnet, OCR Tesseract + ROI del RUN, y face-match OpenCV contra la selfie. Sin Paddle/LLM. La foto del carnet **no se retiene**. Requiere `brew install tesseract tesseract-lang` y `opencv-python-headless` (en `requirements.txt`). Si el RUT aún no está verificado, se adopta el del carnet.

Aval/garantía: `POST /v1/perfil/aval` con **PDF textual** (no fotos ni escaneos). Score por keywords + RUT/monto/fecha/emisor; tipo `carta_aval|boleta|poliza`. Sin IA. El PDF **no se retiene**. Migración: `db/migrations/033_aval.sql`.

Docs empresa (proveedor):
- Grupo 1 (PAdES): `POST .../documentos/{tipo}` — carpeta_tributaria, inicio_actividades, vigencia_sociedad, vigencia_poderes, poder_representante, constitucion, f30, no_quiebra, antecedentes_rl. Orden: intact → ENTIRE_FILE → trusted (`ca_chile.pem`) → emisor → texto firmado.
- Grupo 2 (híbrido PDF): patente, titularidad_cuenta.
Bóveda: `app/infraestructura/certs/ca_chile.pem`. Migraciones: `034`, `035`, `036_pades_trust_hashes.sql`.

Antecedentes (persona): PDF textual + PAdES confiable (CA Chile). Anti-replay por `sha256`.

Evaluador de empresa (`observables` en reputation; **no** se calcula en vivo en el GET):
- Al **crear** / **actualizar** ficha o RUT: responde altiro (`rater_listo=false`); el índice corre en background. El loop cada `RATER_REFRESH_MINUTES` (default 30) prioriza pendientes sin `rater_escaneado_en`.
- El FE / clientes deben usar `rater_listo` y no mostrar ★ hasta que sea true (o `POST .../rater-refresh`).
- Fuentes: `rastreador_web` del `sitio_web`, Google Places (nombre y/o dominio), ChileCompra (RUT).
- Sin dirección / teléfono / RUT / sitio → esos indicadores medidos quedan en **0**; si el rastreador falla no se pisan señales previas.
- Places: sin `GOOGLE_PLACES_API_KEY` → simula; con key → red (+ caché local ante 429).
- ChileCompra: sin ticket → simula; con ticket → red. `RUT_VERIFIER` se deriva (no va en `.env`).
- `APP_ENV=test` → evaluador síncrono en el request; fijos en rastreador; sin loop background.
- Migraciones: `037` (JSON observables) + `042` (`observables` / `rater_escaneado_en`).

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

Use siempre **localhost** (no `127.0.0.1`): la PWA redirige a localhost para no perder la sesión tras Webpay.

```bash
cd servichile-frontend
python3 serve.py 5500
# (alternativa sin 404 propio: python3 -m http.server 5500)
```

```
API:       http://localhost:8000/docs
Frontend:  http://localhost:5500/index.html
Salud:     http://localhost:8000/salud
```

### VPS / production — migraciones compras_informe (antes del deploy)

El arranque con `APP_ENV=production` **falla** si faltan FKs o el índice único. En el VPS, con la misma `DATABASE_URL` del `.env`:

```bash
cd ~/servichile-backend   # o la ruta del deploy
source .venv/bin/activate
python -m scripts.aplicar_migraciones_compras
# o solo desde FKs si 046 ya está:
# python -m scripts.aplicar_migraciones_compras --desde 047
```

Si `047`/`048`/`051` fallan por privilegios: `GRANT REFERENCES ON usuarios, business_entities TO rol_app;` (o correr el `psql -f` como owner). Luego reinicie uvicorn.

Pagos Webpay — informe `$9.990` (`SCI…`, `PRECIO_INFORME_CLP`) y publicación de ficha `$8.990` (`SCP…`, `PRECIO_PUBLICACION_CLP`). Sin override por env.
`POST /v1/businesses` (salvo pytest con `APP_ENV=test` + `PYTEST_CURRENT_TEST`, o `SERVICHILE_SKIP_PAGO_PUBLICACION=1`) hace **una sola TX**: reserva + ficha + consumo → `commit`. Si falla, `rollback` (el pago vuelve a quedar usable). Reservas `reservado` huérfanas de deploys viejos se limpian a ~180 s. No se recicla al borrar la ficha.
Un servidor con solo `APP_ENV=test` (sin pytest) **sí** exige pago.
Migraciones `050` + `051` (tabla + FKs publicación; script arriba). Tras 051, confirme FKs en `pg_constraint` si hubo `NOTICE` por privilegios.
Aviso de cupón listo: requiere SMTP (`SMTP_HOST`/`SMTP_DESDE`); sin buzón no hay correo (el FE/retorno sigue siendo la vía principal).

`APP_ENV=local` y `production` exigen `REDIS_URL` (ping al arrancar). Solo `APP_ENV=test` puede omitirlo.

`APP_ENV=production` exige además:
- Transbank real (no `webpay3gint` / commerce TEST)
- `PUBLIC_FRONTEND_URL` + `CORS_ORIGINS` sin localhost
- `PRINT_TOKEN_SECRET` ≠ `JWT_SECRET` (≥32 chars)
- Arranque verifica FKs/índices informe (046–049) y publicación (`uq_compras_publicacion_cupon_libre` + FKs 051)
- Loop de reconciliación TBK (`PAGOS_RECONCILIAR_SECONDS`, default 120; min edad 180 s; `0` = off): commit + correo informe + aviso cupón publicación; estado en `GET /salud` → `pagos_reconciliar`
- Cloud (Render/Fly/K8s/…), `SERVICHILE_DEPLOY=1` / `SERVICHILE_REQUIRE_PRODUCTION=1`, o `DATABASE_URL` remota → obliga `APP_ENV=production`
- `APP_ENV=test` fuera de pytest: sin pasarela memoria (salvo `SERVICHILE_ALLOW_MEMORIA_PASARELA=1`; prohibido en production)

GET `/reputation` público oculta `observables`/`docs_empresa`; con Bearer y compra/titular vienen completos.

Front: `SERVICHILE_API_BASE` / meta; `SERVICHILE_APP_VERSION`; JWT y pago en `sessionStorage`.

Integración Postgres (opcional): `TEST_DATABASE_URL=...servichile_test... pytest tests/integration`.

## Caché y Redis

- `GET /v1/businesses` cachea en Redis (TTL 45 s). `reputation` cachea **solo el teaser público**; compra/titular hace bypass (`X-Cache: BYPASS`) y `Cache-Control: private, no-store`.
- Se invalida al crear/editar/borrar ficha, docs, rater-refresh, trabajos concretados y al terminar un lote del evaluador en background.
- Rate limits de login y estado de workers también van por Redis. `GET /salud` hace ping a Redis y `SELECT 1` a Postgres.
- Varias réplicas uvicorn: deje los bucles en una sola (`RUN_BACKGROUND_JOBS=true`) y en el resto `RUN_BACKGROUND_JOBS=false`.
- En `APP_ENV=test` la caché queda off y el rate limit usa memoria.

## Tests

```bash
pytest
lint-imports
```
