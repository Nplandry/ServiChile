# Validaciones, seguridad, mantenimiento y pruebas

Documento de apoyo al informe técnico del backend ServiChile.

---

## 1. Validaciones y manejo de errores

### 1.1 Validadores de entrada (Pydantic)

La capa API define contratos de entrada y salida en `app/api/esquemas/` con **Pydantic v2**. FastAPI valida automáticamente el cuerpo JSON, query params y path params antes de ejecutar el caso de uso.

Ejemplos de reglas aplicadas:

1. Longitudes y rangos (`Field(min_length=…)`, `ge` / `le`): contraseña 8–128, nombre 2–120, edad 14–120, pregunta 5–2000.
2. Tipos estrictos: `EmailStr`, `UUID`, literales de categoría / tipo de cuenta.
3. Patrones (`pattern`) para teléfono.
4. Validadores custom (`@field_validator`) para normalizar o rechazar valores (p. ej. nombre vacío tras `strip`).
5. Campos desconocidos en modelos estrictos → **422**.
6. Uploads (biometría): tipo y tamaño validados en el servicio de reporte además del borde HTTP.

Si la validación falla, FastAPI responde **422** con `detail` como lista de errores por campo (formato estándar de validación).

### 1.2 Estructura de respuestas de error (`detail`)

Los errores de aplicación usan el formato FastAPI:

```json
{"detail": "mensaje claro para el cliente"}
```

En validación de esquema, `detail` es una **lista** de objetos con ubicación del campo (`loc`), mensaje (`msg`) y tipo. La API no expone stack traces ni detalles internos de base de datos al cliente.

Mensajes de borde habituales:

1. **401** — `Sesión inválida o expirada.` (con cabecera `WWW-Authenticate: Bearer`).
2. **429** — `Demasiados intentos. Espere un minuto e intente de nuevo.` (con `Retry-After: 60`).
3. Mensajes de dominio traducidos en el router (correo ya registrado, nivel insuficiente, RUT inválido, no titular, etc.).

### 1.3 Mapeo de errores de dominio → HTTP

Las excepciones de negocio viven en `app/dominio/errores.py` **sin conocer FastAPI**. La capa API las captura y las traduce a `HTTPException` con código semántico:

| Ámbito | Ejemplos de error de dominio | HTTP típico |
|---|---|---|
| Auth | Credenciales inválidas; correo duplicado; contraseña de baja incorrecta | 401 / 409 / 403 |
| Perfil / reporte | RUT inválido; RUT en uso; RUT ya verificado; biometría inválida o muy grande | 422 / 409 / 413 |
| Autorización de cuenta | Solo proveedor puede crear una empresa | 403 (`autorizacion.py`) |
| Negocios / trabajos | No encontrado; ya reclamado; no titular; nivel insuficiente; trabajo cerrado | 404 / 409 / 403 |
| Reporte (QR) | Payload inválido o expirado | 422 |

Principio: **el servicio lanza error de negocio; el router decide el status code**. Así no hay lógica HTTP dentro de la capa de casos de uso.

### 1.4 Rate limits (control de límites de peticiones)

Implementación en `app/infraestructura/limite_solicitudes.py`, inyectada vía `dependencias.py`:

1. Con `REDIS_URL` (obligatorio fuera de `APP_ENV=test`): límite compartido entre instancias.
2. En `APP_ENV=test` sin Redis: contador **en memoria** del proceso.

Límites configurables en `.env` (`app/configuracion.py`):

| Límite | Variable | Uso |
|---|---|---|
| Login/registro por correo | `LOGIN_RATE_PER_MINUTE` (default 5) | Mitiga fuerza bruta por cuenta |
| Login/registro por IP | `LOGIN_IP_RATE_PER_MINUTE` (default 20) | Mitiga abuso desde una misma red |
| Reporte validar | rate limit en el router correspondiente | Evita barrido de validaciones |

Respuesta al exceder: **429** + `Retry-After`. `TRUST_PROXY` solo debe ser `true` detrás de un proxy confiable; de lo contrario la IP puede falsearse.

---

## 2. Seguridad y mantenimiento

### 2.1 Hashing de contraseñas

El hash vive en `app/infraestructura/seguridad/hasheador.py` (**Argon2id**, `argon2-cffi`). El servicio de autenticación solo llama al puerto `HasheadorContrasena`.

1. Al registrar: se guarda solo el hash, nunca la contraseña en claro.
2. Al login o al borrar cuenta: `verify` contra el hash; fallos de verificación → credenciales inválidas / 403 según el flujo.
3. Las respuestas `UsuarioOut` **nunca** incluyen hash ni contraseña.

### 2.2 JWT

1. Emisión y verificación en `app/infraestructura/seguridad/` (**PyJWT**), firmado con `JWT_SECRET` (`SecretStr`, mínimo 32 caracteres). Los servicios no importan `jwt`.
2. Token de sesión: `Bearer` en `Authorization`; expiración `JWT_EXPIRES_MINUTES`.
3. **Reporte** usa un token firmado **distinto** al de sesión, con vida `REPORTE_EXPIRES_MINUTES` (corta). El QR solo valida ese reporte; el JWT de sesión no sirve.
4. Sesión inválida o expirada → 401 uniforme, sin filtrar si el usuario existe.

### 2.3 Tratamiento de datos personales

1. El RUT completo no se expone al validar un reporte ajeno (solo flags como `rut_verificado`).
2. Reputación de negocios entrega métricas agregadas, no textos de reseñas.
3. Contraseñas solo como hash Argon2id; biometría sin retención de imagen.

### 2.4 Biometría en disco local + metadata

`ReporteIdentidadService.procesar_biometria` + `AlmacenamientoBiometriaLocal`:

1. Valida tamaño (máx. 5 MB) y firma de imagen (JPEG/PNG/WebP/GIF).
2. Comprime a JPEG (~máx. 640 px, calidad configurable), sin EXIF.
3. Escribe en `BIOMETRIA_DIR` (por defecto `var/biometria/<user_id>.jpg`), fuera del web root.
4. Persiste metadata en Postgres: ruta relativa, sha256, bytes, ancho/alto, `biometria_retener_hasta`.
5. Al eliminar la cuenta se borra el archivo. La API no expone la ruta ni sirve el binario.

La UI debe informar consentimiento y retención; ya no se promete zero-retention.

### 2.5 Validación de capas (linting de arquitectura)

Las reglas de dependencia se verifican con **import-linter** (`.importlinter`):

1. Capas: `api` → `servicios` → `dominio`. La infraestructura implementa puertos del dominio.
2. Dominio sin FastAPI / SQLAlchemy / Pydantic.
3. Servicios sin infraestructura, API, JWT ni Argon2.
4. API sin acceso directo a persistencia (salvo ensamblado en `dependencias.py`).

Ejecución:

```bash
lint-imports
```

Complemento habitual de calidad: `pytest` y, en el toolchain de desarrollo, cachés de Ruff si se usa localmente.

### 2.6 Respaldos locales de esquemas y datos

Enfoque del repositorio (sin depender de cloud):

1. **Esquema reproducible:** `db/init_script.sql` crea la base desde cero; `db/migrations/` aplica cambios incrementales a bases ya existentes.
2. **Seed reproducible:** `python -m scripts.cargar_db_demo` (y `sembrar_negocios`) para datos demo.
3. **Respaldo local recomendado** (operación del evaluador/desarrollador):
   ```bash
   # Solo esquema
   pg_dump -s "postgresql://servichile:servichile@localhost:5432/servichile" > backup_schema.sql
   # Esquema + datos
   pg_dump "postgresql://servichile:servichile@localhost:5432/servichile" > backup_full.sql
   ```
4. Restauración orientativa:
   ```bash
   psql "postgresql://servichile:servichile@localhost:5432/servichile" -f backup_full.sql
   ```
5. Los dumps con datos reales **no se versionan** (PII / secretos operativos).

---

## 3. Pruebas (Tests)

### 3.1 Cómo ejecutar

Desde `servichile-backend`, con el venv activo y dependencias de `requirements-dev.txt`:

```bash
pytest
lint-imports
```

Opcional, más verboso:

```bash
pytest -v
```

### 3.2 Pruebas unitarias / de API sin PostgreSQL real

`tests/conftest.py` configura:

1. `JWT_SECRET` y `APP_ENV=test` por defecto.
2. Motor **SQLite en memoria** + tablas necesarias.
3. Overrides de dependencias: sesión de prueba y `MemoryRateLimiter`.
4. Fixtures `client`, `token` (persona) y `token_empresa`.

Cobertura representativa en `tests/`:

- `test_autenticacion.py`, `test_cuenta.py`, `test_perfil.py`, `test_rut.py`, `test_reporte_estado.py`
- `test_biometria.py`, `test_progreso_cliente.py`, `test_tipo_cuenta.py`
- `test_trabajos.py`, `test_negocios.py`, `test_ficha_negocio.py`
- `test_reporte.py`, `test_reputacion_indice.py`, `test_seguridad.py`
- `test_pago_informe.py`, `test_pago_publicacion.py` (Webpay SCI/SCP, gate `buy_order`, cupón `consumido`)

### 3.2.1 Publicación de ficha (Webpay SCP)

1. Solo cuenta **proveedor** puede iniciar/confirmar/acceder al cupón (`exige_cuenta_proveedor`).
2. `POST /v1/businesses` exige `buy_order` listo (salvo pytest/`SERVICHILE_SKIP_PAGO_PUBLICACION=1`): **una TX** (reserva+ficha+consumo) → `commit`; `rollback` si falla (sin cupón “tomado” huérfano). `IntegrityError` → 409 `alta_conflicto`.
3. Consumo atómico (`UPDATE`); borrar la ficha no reabre el cupón aunque `business_id` quede NULL.
4. Monto desde dominio `PRECIO_PUBLICACION_CLP` (sin override por env; catálogo + mensajes 402).
5. Correo «cupón listo» en `/confirmar` y en reconciliación TBK (requiere SMTP disponible).
6. Production: migraciones `050`/`051` + check de arranque (`verificar_compras_publicacion`).

Estas pruebas **no requieren** una instancia activa de PostgreSQL.

### 3.3 Pruebas de integración (PostgreSQL)

Ubicación: `tests/integration/test_postgres.py`.

1. Exigen `TEST_DATABASE_URL` apuntando a una base dedicada **`servichile_test`**.
2. Si no está definida, pytest las **omite**.

```bash
createdb -O servichile servichile_test
TEST_DATABASE_URL=postgresql+psycopg://servichile:CLAVE@localhost:5432/servichile_test \
  pytest tests/integration
```

### 3.4 Comportamiento sin base de datos activa

| Escenario | Resultado |
|---|---|
| `pytest` sin Postgres | Unitarias/API con SQLite; `tests/integration` aparece como **skipped**. |
| Servidor real (`uvicorn`) sin Postgres | Fallan las operaciones con sesión SQL; ver `COMO_LEVANTAR.md`. |

---

## 4. Resumen

1. **Validación** en el borde con Pydantic; errores claros vía `detail`; dominio → HTTP en routers; rate limits configurables (memoria o Redis).
2. **Seguridad:** Argon2id, JWT de sesión + token corto de reporte, biometría en disco local cifrado por el SO + metadata, `import-linter`, respaldos locales con `pg_dump` / scripts SQL versionados.
3. **Pruebas:** `pytest` unitario sin Postgres; integración condicional a `TEST_DATABASE_URL` (skip si no hay instancia).
