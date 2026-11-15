# ServiChile API

Backend de ServiChile: autenticación, Pasaporte de Confianza, marketplace B2B e Índice de Transparencia.

Stack: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL.

## Estructura

```
servichile-backend/
├── app/
│   ├── principal.py             # Aplicación FastAPI, CORS y routers
│   ├── configuracion.py         # Variables de entorno (Pydantic Settings)
│   ├── tiempo.py                # Reloj UTC
│   ├── domain/                  # Núcleo: entidades, reglas y puertos (sin SQLAlchemy, FastAPI ni Pydantic)
│   │   ├── entidades.py         # Usuario, Negocio, Reserva y resultados de servicio
│   │   ├── errores.py           # Excepciones de negocio
│   │   ├── puertos.py           # Contratos (repositorios y proveedores). Los servicios solo hablan esto
│   │   ├── pasaporte.py         # RUT módulo 11 y score de confiabilidad
│   │   ├── ficha_negocio.py     # Cómo se muestra un negocio en el mapa (foto, logo, botón)
│   │   └── transparencia/       # Índice: indicadores, métricas, CMF, SII, Mercado Público
│   ├── services/                # Casos de uso: reutilizables, sin ORM ni HTTP
│   │   ├── autenticacion.py     # Registro, login (Argon2id) y JWT
│   │   └── pasaporte.py, reserva.py, negocio.py, …
│   ├── infrastructure/          # Adaptadores que implementan los puertos
│   │   ├── persistencia/        # Modelos ORM y repositorios SQL
│   │   ├── cmf/                 # Cliente CMF, índice local y repositorio
│   │   ├── ciber_sonda.py       # Sonda de indicadores (fake|live)
│   │   └── limite_solicitudes.py
│   └── api/                     # Presentación REST: sin reglas de negocio ni consultas
│       ├── esquemas.py          # Contratos de entrada y salida (Pydantic)
│       ├── mapeos.py            # Entidades y resultados -> respuestas
│       ├── dependencias.py      # Ensambla servicios, repositorios y APIs externas
│       ├── autorizacion.py      # Quién puede crear o reclamar un negocio
│       └── v1/                  # Routers: autenticacion, perfil, negocios, reservas, reporte
├── db/init_script.sql           # Crea el esquema completo desde cero
├── docs/
│   ├── api_interface_table.md   # Tabla de la interfaz de programación
│   └── modelo_datos.md          # Diagrama entidad relación (Mermaid)
└── tests/                       # Pruebas pytest y colección Postman
```

Las reglas de capas se verifican con `import-linter` (`lint-imports`, ver `.importlinter`): el dominio no depende de frameworks, los servicios no importan infraestructura ni API, y los routers no acceden a la base. `app.api.dependencias` ensambla repositorios y proveedores.

## Endpoints y estado de desarrollo

Los tests de integración con PostgreSQL (`tests/integration/`) se omiten sin `TEST_DATABASE_URL`.

| Método | Ruta | Sesión | Descripción | Archivo | Estado |
|---|---|---|---|---|---|
| GET | `/salud` | No | Healthcheck → `{"estado": "ok"}` | `app/principal.py` | Implementado y probado |
| POST | `/v1/auth/registro` | No | Registra usuario (201) | `app/api/v1/autenticacion.py` | Implementado y probado |
| POST | `/v1/auth/login` | No | Login → `TokenOut` (JWT) | `app/api/v1/autenticacion.py` | Implementado y probado |
| GET | `/v1/auth/yo` | Sí | Datos del usuario autenticado | `app/api/v1/autenticacion.py` | Implementado y probado |
| GET | `/v1/perfil` | Sí | Estado del Pasaporte de Confianza (nivel, score de confiabilidad) | `app/api/v1/perfil.py` | Implementado y probado |
| PATCH | `/v1/perfil` | Sí | Actualiza edad, teléfono y verifica el RUT | `app/api/v1/perfil.py` | Implementado y probado |
| POST | `/v1/perfil/biometria` | Sí | Verificación biométrica; la foto no se almacena (201) | `app/api/v1/perfil.py` | Implementado y probado |
| GET | `/v1/reservas` | Sí | Reservas del usuario con su código QR | `app/api/v1/reservas.py` | Implementado y probado |
| POST | `/v1/reservas` | Sí | Reserva un cupo en un comercio (201) | `app/api/v1/reservas.py` | Implementado y probado |
| DELETE | `/v1/reservas/{id}` | Sí | Cancela una reserva propia que siga activa | `app/api/v1/reservas.py` | Implementado y probado |
| DELETE | `/v1/auth/yo` | Sí | Elimina la cuenta, con confirmación por contraseña (204) | `app/api/v1/autenticacion.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/checkin` | Sí (titular) | El dueño registra asistencia con el QR del usuario | `app/api/v1/negocios.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/reservas/{reserva_id}/no-show` | Sí (titular) | El dueño marca una reserva como no-show | `app/api/v1/negocios.py` | Implementado y probado |
| GET | `/v1/businesses/{id}/reputation` | No | Índice de Transparencia y métricas estadísticas | `app/api/v1/negocios.py` | Implementado y probado |
| POST | `/v1/businesses/{id}/claim` | Sí | Derecho a Réplica: el dueño reclama su perfil (201) | `app/api/v1/negocios.py` | Implementado y probado |

Los endpoints marcados con "Sí" en Sesión requieren la cabecera `Authorization: Bearer <access_token>`. El detalle de esquemas de entrada/salida y errores está en `docs/api_interface_table.md`.

### Pendientes (no implementados)

- `/v1/patrimonio`, `/v1/polizas`, `/v1/subtel`: cruce de datos, dependen de convenios con SII, Registro Civil, CMF y SUBTEL.
- Endpoints B2B y webhook de WhatsApp.
- Worker de ingesta y recálculo del Índice de Transparencia (cron/Celery): recolectar métricas de Google Maps y NLP de sentimiento, y persistir `final_score` periódicamente. Hoy la fórmula (`app/domain/transparencia/reputacion.py`) y el recálculo al reclamar/al vuelo ya existen; falta el proceso en segundo plano que alimente las métricas.
- Pasaporte de Confianza, pendientes antes de producción:
  - Verificador de RUT real (proveedor de identidad). Hoy `FakeVerificadorRut` acepta cualquier RUT con DV válido.
  - Eliminar `preocupacion` y `proposito` de la base en una migración posterior, cuando el frontend antiguo ya no los envíe.
  - Reclamo de comercios: hoy el documento de verificación no se valida ni se guarda.

## Levantar en local

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
# Edite .env: DATABASE_URL con la clave de su base y JWT_SECRET con un valor aleatorio:
python -c "import secrets; print(secrets.token_urlsafe(48))"

psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql

uvicorn app.principal:app --reload
```

Abra http://localhost:8000/docs para probar los endpoints, o importe `tests/servichile_api_collection.json` en Postman o Insomnia.

## Pruebas

```bash
pytest
```

Las pruebas unitarias usan SQLite en memoria. No necesitan PostgreSQL.

## Despliegue en Cloud Run

```bash
gcloud run deploy servichile-api \
  --source . \
  --region southamerica-west1 \
  --service-account servichile-api@PROYECTO.iam.gserviceaccount.com \
  --add-cloudsql-instances PROYECTO:REGION:servichile-db \
  --set-env-vars APP_ENV=production,CORS_ORIGINS=https://SU-FRONTEND,TRUST_PROXY=true \
  --set-secrets JWT_SECRET=jwt-secret:latest,DATABASE_URL=database-url:latest
```

- La cuenta de servicio necesita los roles `roles/cloudsql.client` y `roles/secretmanager.secretAccessor`.
- `JWT_SECRET` y `DATABASE_URL` se guardan en Secret Manager, nunca en variables de entorno en texto plano.
- Con más de una instancia, configure `REDIS_URL` (Memorystore). El límite en memoria no se comparte entre instancias.
- `TRUST_PROXY=true` solo es seguro detrás de Cloud Run. Con `true` en un servidor expuesto directamente, cualquiera puede falsear su IP y evadir el límite por IP.

## Pendiente (fases siguientes)

- Endpoints de cruce de datos (`/v1/patrimonio`, `/v1/polizas`, `/v1/subtel`): dependen de convenios con SII, Registro Civil, CMF y SUBTEL.
- Endpoints B2B y webhook de WhatsApp.
- Conectar el frontend: hoy `js/core/auth.js` guarda usuarios y contraseñas en `localStorage` y debe reemplazarse por llamadas a `/v1/auth`.
