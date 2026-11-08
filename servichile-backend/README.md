# ServicIA API

Backend de ServicIA: autenticación de usuarios y asistente de orientación con IA que responde citando normativa oficial cargada desde PDFs (RAG con pgvector).

Stack: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16 con pgvector, Gemini en Vertex AI.

## Estructura

```
servicia-backend/
├── app/
│   ├── main.py                  # Aplicación FastAPI, CORS y routers
│   ├── config.py                # Variables de entorno (Pydantic Settings)
│   ├── domain/                  # Capa 1: entidades y reglas puras (sin SQLAlchemy, FastAPI ni Pydantic)
│   │   ├── entidades.py         # Usuario, Negocio, Reserva, Consulta y resultados de servicio
│   │   ├── reputacion.py        # Fórmula del Índice de Transparencia
│   │   ├── pasaporte.py         # RUT módulo 11, scores de confiabilidad y arriendo
│   │   └── pii.py               # Redacción de RUT, correos y teléfonos
│   ├── services/                # Capa 2: casos de uso (solo entidades, sin ORM ni schemas de API)
│   │   ├── auth_service.py      # Registro, login (Argon2id) y JWT
│   │   ├── pasaporte_service.py, reserva_service.py, negocio_service.py, consulta_service.py
│   │   └── ai_assistant.py      # Redacción, búsqueda de normativa, prompt y respuesta con citas
│   ├── infrastructure/          # Capa 3: adaptadores (convierten ORM <-> entidades)
│   │   ├── db.py                # Conexión y modelos ORM
│   │   ├── repositories.py      # Consultas SQL, mapeo a entidades y búsqueda vectorial
│   │   ├── verificacion.py      # Verificador de RUT y extractor de PDF (configurables)
│   │   ├── llm.py               # Proveedor de IA (Gemini o falso)
│   │   └── rate_limit.py        # Límite de solicitudes (Redis o memoria)
│   └── api/                     # Capa 4: endpoints REST
│       ├── schemas.py           # Schemas de entrada y salida (Pydantic)
│       ├── mapeos.py            # Entidades y resultados -> respuestas
│       ├── deps.py              # Ensamblado de dependencias (única capa que toca la base)
│       └── v1/                  # Routers: auth, perfil, consultas, negocios, reservas
├── scripts/ingest_pdfs.py       # Carga un PDF de normativa en la base de conocimiento
├── db/init_script.sql           # Crea el esquema completo desde cero
├── docs/
│   ├── api_interface_table.md   # Tabla de la interfaz de programación
│   └── modelo_datos.md          # Diagrama entidad relación (Mermaid)
└── tests/                       # Pruebas pytest y colección Postman
```

Las reglas de capas se verifican con `import-linter` (`lint-imports`, ver `.importlinter`): cada capa solo importa a las de abajo, el dominio no depende de frameworks, los servicios no conocen el ORM ni la API, y los routers no acceden a la base.

## Endpoints y estado de desarrollo

Estado verificado el 2026-11-06. La suite de pruebas pasa (`41 passed, 14 skipped`); los 14 saltados son los de integración con PostgreSQL (`tests/integration/test_postgres.py`), que requieren `TEST_DATABASE_URL`. El servidor no se ejecuta por defecto; con `LLM_PROVIDER=fake` responde sin llamar a Vertex AI.

| Método | Ruta | Sesión | Descripción | Archivo | Estado |
|---|---|---|---|---|---|
| GET | `/salud` | No | Healthcheck → `{"estado": "ok"}` | `app/main.py` | Implementado y probado |
| POST | `/v1/auth/registro` | No | Registra usuario (201) | `app/api/v1/auth.py` | Implementado y probado |
| POST | `/v1/auth/login` | No | Login → `TokenOut` (JWT) | `app/api/v1/auth.py` | Implementado y probado |
| GET | `/v1/auth/yo` | Sí | Datos del usuario autenticado | `app/api/v1/auth.py` | Implementado y probado |
| GET | `/v1/perfil` | Sí | Estado del Pasaporte de Confianza (nivel, score de confiabilidad, arriendo) | `app/api/v1/perfil.py` | Implementado y probado |
| PATCH | `/v1/perfil` | Sí | Actualiza edad, teléfono y verifica el RUT | `app/api/v1/perfil.py` | Implementado y probado |
| POST | `/v1/perfil/documentos` | Sí | Nivel 2: score de arriendo desde un PDF procesado en memoria (201) | `app/api/v1/perfil.py` | Implementado con extractor falso |
| GET | `/v1/reservas` | Sí | Reservas del usuario con su código QR | `app/api/v1/reservas.py` | Implementado y probado |
| POST | `/v1/reservas` | Sí | Reserva un cupo en un comercio (201) | `app/api/v1/reservas.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/checkin` | Sí (titular) | El dueño registra asistencia con el QR del usuario | `app/api/v1/negocios.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/reservas/{reserva_id}/no-show` | Sí (titular) | El dueño marca una reserva como no-show | `app/api/v1/negocios.py` | Implementado y probado |
| POST | `/v1/consultas` | Sí | Crea consulta IA con RAG (201) | `app/api/v1/consultas.py` | Implementado y probado |
| GET | `/v1/consultas?limite=50` | Sí | Historial de consultas | `app/api/v1/consultas.py` | Implementado y probado |
| GET | `/v1/businesses/{id}/reputation` | No | Índice de Transparencia y métricas estadísticas | `app/api/v1/negocios.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/claim` | Sí | Derecho a Réplica: el dueño reclama su perfil (201) | `app/api/v1/negocios.py` | Implementado y probado |

Los endpoints marcados con "Sí" en Sesión requieren la cabecera `Authorization: Bearer <access_token>`. El detalle de esquemas de entrada/salida y errores está en `docs/api_interface_table.md`.

### Pendientes (no implementados)

- `/v1/patrimonio`, `/v1/polizas`, `/v1/subtel`: cruce de datos, dependen de convenios con SII, Registro Civil, CMF y SUBTEL.
- Endpoints B2B y webhook de WhatsApp.
- Worker de ingesta y recálculo del Índice de Transparencia (cron/Celery): recolectar métricas de Google Maps y NLP de sentimiento, y persistir `final_score` periódicamente. Hoy la fórmula (`app/domain/reputacion.py`) y el recálculo al reclamar/al vuelo ya existen; falta el proceso en segundo plano que alimente las métricas.
- Pasaporte de Confianza, pendientes antes de producción:
  - Verificador de RUT real (proveedor de identidad). Hoy `FakeVerificadorRut` acepta cualquier RUT con DV válido.
  - Extractor de PDF real con Gemini. Hoy `FakeExtractorFinanciero` devuelve métricas fijas. Antes de enviar documentos financieros a un tercero, revisar el tratamiento de datos.
  - Fórmula definitiva del score de arriendo. Hoy es provisional (`app/domain/pasaporte.py`).
  - Eliminar `preocupacion` y `proposito` de la base en una migración posterior, cuando el frontend antiguo ya no los envíe.
  - Reclamo de comercios: hoy el documento de verificación no se valida ni se guarda.

## Levantar en local

Requisitos: Python 3.12 y PostgreSQL 16 con pgvector. La forma más simple de tener la base es con Docker:

```bash
docker run -d --name servicia-db -p 5432:5432 \
  -e POSTGRES_USER=servicia -e POSTGRES_PASSWORD=servicia -e POSTGRES_DB=servicia \
  pgvector/pgvector:pg16
```

Luego:

```bash
cd servicia-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Edite .env: DATABASE_URL con la clave de su base y JWT_SECRET con un valor aleatorio:
python -c "import secrets; print(secrets.token_urlsafe(48))"

psql "postgresql://servicia:servicia@localhost:5432/servicia" -v ON_ERROR_STOP=1 -f db/init_script.sql

uvicorn app.main:app --reload
```

Abra http://localhost:8000/docs para probar los endpoints, o importe `tests/servicia_api_collection.json` en Postman o Insomnia.

Con `LLM_PROVIDER=fake` la API funciona sin Google Cloud: genera embeddings deterministas y una respuesta de prueba. Sirve para probar el flujo completo, no la calidad de las respuestas.

## Cargar normativa (PDF)

```bash
python -m scripts.ingest_pdfs data/ley_19496.pdf \
  --titulo "Ley 19.496 sobre Protección de los Derechos de los Consumidores" \
  --url "https://www.bcn.cl/leychile/navegar?idNorma=61438" \
  --categoria seguros
```

- Use el mismo `LLM_PROVIDER` al cargar y al consultar. Los vectores de `fake` y de `gemini` no son compatibles entre sí.
- Si cambia de proveedor o de `EMBEDDING_DIM`, vacíe `documentos` y vuelva a cargar los PDFs.
- Los PDFs escaneados necesitan OCR antes de cargarlos.

## Usar Gemini (Vertex AI)

```bash
gcloud auth application-default login
```

En `.env`: `LLM_PROVIDER=gemini`, `GCP_PROJECT=su-proyecto` y `GCP_LOCATION` con una región donde estén disponibles los modelos configurados en `GEMINI_MODEL` y `EMBEDDING_MODEL`. Verifique la disponibilidad en la documentación de Vertex AI antes de elegir región.

## Pruebas

```bash
pytest
```

Las pruebas usan SQLite en memoria y el proveedor falso. No necesitan PostgreSQL ni conexión a Google Cloud.

## Despliegue en Cloud Run

```bash
gcloud run deploy servicia-api \
  --source . \
  --region southamerica-west1 \
  --service-account servicia-api@PROYECTO.iam.gserviceaccount.com \
  --add-cloudsql-instances PROYECTO:REGION:serviclia-db \
  --set-env-vars APP_ENV=production,LLM_PROVIDER=gemini,GCP_PROJECT=PROYECTO,CORS_ORIGINS=https://SU-FRONTEND,TRUST_PROXY=true \
  --set-secrets JWT_SECRET=jwt-secret:latest,DATABASE_URL=database-url:latest
```

- La cuenta de servicio necesita los roles `roles/cloudsql.client`, `roles/aiplatform.user` y `roles/secretmanager.secretAccessor`, y ningún otro.
- `JWT_SECRET` y `DATABASE_URL` se guardan en Secret Manager, nunca en variables de entorno en texto plano.
- Con más de una instancia, configure `REDIS_URL` (Memorystore). El límite en memoria no se comparte entre instancias.
- `TRUST_PROXY=true` solo es seguro detrás de Cloud Run. Con `true` en un servidor expuesto directamente, cualquiera puede falsear su IP y evadir el límite por IP.

## Pendiente (fases siguientes)

- Endpoints de cruce de datos (`/v1/patrimonio`, `/v1/polizas`, `/v1/subtel`): dependen de convenios con SII, Registro Civil, CMF y SUBTEL.
- Endpoints B2B y webhook de WhatsApp.
- Conectar el frontend: hoy `js/core/auth.js` guarda usuarios y contraseñas en `localStorage` y debe reemplazarse por llamadas a `/v1/auth`.
