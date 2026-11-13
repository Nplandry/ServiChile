# Validaciones, seguridad, mantenimiento y pruebas

Documento de apoyo al informe técnico del backend ServiChile.

---

## 1. Validaciones y manejo de errores

### 1.1 Validadores de entrada (Pydantic)

La capa API define contratos de entrada y salida en `app/api/schemas.py` con **Pydantic v2**. FastAPI valida automáticamente el cuerpo JSON, query params y path params antes de ejecutar el caso de uso.

Ejemplos de reglas aplicadas:

1. Longitudes y rangos (`Field(min_length=…)`, `ge` / `le`): contraseña 8–128, nombre 2–120, edad 14–120, pregunta 5–2000.
2. Tipos estrictos: `EmailStr`, `UUID`, literales de categoría / tipo de cuenta.
3. Patrones (`pattern`) para teléfono.
4. Validadores custom (`@field_validator`) para normalizar o rechazar valores (p. ej. nombre vacío tras `strip`).
5. Campos desconocidos en modelos estrictos → **422**.
6. Uploads (biometría): tipo y tamaño validados en el servicio de pasaporte además del borde HTTP.

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

Las excepciones de negocio viven en el dominio/servicios **sin conocer FastAPI** (`app/domain/errores.py`, errores de `PasaporteService`, `AuthService`, etc.). La capa API las captura y las traduce a `HTTPException` con código semántico:

| Ámbito | Ejemplos de error de dominio | HTTP típico |
|---|---|---|
| Auth | Credenciales inválidas; correo duplicado; contraseña de baja incorrecta | 401 / 409 / 403 |
| Perfil / pasaporte | RUT inválido; RUT en uso; RUT ya verificado; biometría inválida o muy grande | 422 / 409 / 413 |
| Autorización de cuenta | Solo empresa puede crear/reclamar | 403 (`authz.py`) |
| Negocios / reservas | No encontrado; ya reclamado; no titular; nivel insuficiente; reserva cerrada | 404 / 409 / 403 |
| Reporte (QR) | Payload inválido o expirado | 422 |

Principio: **el servicio lanza error de negocio; el router decide el status code**. Así no hay lógica HTTP dentro de la capa de casos de uso.

### 1.4 Rate limits (control de límites de peticiones)

Implementación en `app/infrastructure/rate_limit.py`, inyectada vía `deps.py`:

1. Sin `REDIS_URL`: contador **en memoria** del proceso (adecuado solo a desarrollo / una instancia).
2. Con `REDIS_URL`: límite compartido entre instancias.

Límites configurables en `.env` (`app/config.py`):

| Límite | Variable | Uso |
|---|---|---|
| Login/registro por correo | `LOGIN_RATE_PER_MINUTE` (default 5) | Mitiga fuerza bruta por cuenta |
| Login/registro por IP | `LOGIN_IP_RATE_PER_MINUTE` (default 20) | Mitiga abuso desde una misma red |
| Reporte validar | rate limit en el router correspondiente | Evita barrido de validaciones |

Respuesta al exceder: **429** + `Retry-After`. `TRUST_PROXY` solo debe ser `true` detrás de un proxy confiable; de lo contrario la IP puede falsearse.

---

## 2. Seguridad y mantenimiento

### 2.1 Hashing de contraseñas

`app/services/auth_service.py` usa **Argon2id** (`argon2-cffi`, `PasswordHasher` con parámetros por defecto de la librería).

1. Al registrar: se guarda solo el hash, nunca la contraseña en claro.
2. Al login o al borrar cuenta: `verify` contra el hash; fallos de verificación → credenciales inválidas / 403 según el flujo.
3. Las respuestas `UsuarioOut` **nunca** incluyen hash ni contraseña.

### 2.2 JWT

1. Emisión y verificación con **PyJWT**, firmado con `JWT_SECRET` (`SecretStr`, mínimo 32 caracteres).
2. Token de sesión: `Bearer` en `Authorization`; expiración `JWT_EXPIRES_MINUTES`.
3. **Reporte** usa un token firmado **distinto** al de sesión, con vida `REPORTE_EXPIRES_MINUTES` (corta). El QR solo valida ese reporte; el JWT de sesión no sirve.
4. Sesión inválida o expirada → 401 uniforme, sin filtrar si el usuario existe.

### 2.3 Tratamiento de datos personales

1. El RUT completo no se expone al validar un reporte ajeno (solo flags como `rut_verificado`).
2. Reputación de negocios entrega métricas agregadas, no textos de reseñas.
3. Contraseñas solo como hash Argon2id; biometría sin retención de imagen.

### 2.4 Zero-retention de biometría

`PasaporteService.procesar_biometria`:

1. Valida tamaño (máx. 5 MB) y firma de imagen (JPEG/PNG/WebP/GIF).
2. Marca `biometria_verificada` / `biometria_verificada_en`.
3. **Descarta los bytes de la foto**: no se escribe archivo ni columna de imagen.
4. Otorga XP de biometría si corresponde.

La API responde con `BiometriaOut` y un mensaje que deja explícito que la foto no se almacenó.

### 2.5 Validación de capas (linting de arquitectura)

Las reglas de dependencia se verifican con **import-linter** (`.importlinter`):

1. Capas: `api` → `services` → `infrastructure` → `domain`.
2. Dominio sin FastAPI / SQLAlchemy / Pydantic de frameworks.
3. Servicios sin ORM directo ni imports de `app.api`.
4. API sin acceso directo a `db` / `repositories` (salvo ensamblado en `deps.py`).

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

- `test_auth.py`, `test_cuenta.py`, `test_perfil.py`, `test_pasaporte.py`
- `test_biometria.py`, `test_xp.py`, `test_tipo_cuenta.py`
- `test_reservas.py`, `test_negocios.py`, `test_marketplace_presentacion.py`
- `test_reporte.py`, `test_ciber_observables.py`, `test_seguridad.py`

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
2. **Seguridad:** Argon2id, JWT de sesión + token corto de reporte, biometría zero-retention, `import-linter`, respaldos locales con `pg_dump` / scripts SQL versionados.
3. **Pruebas:** `pytest` unitario sin Postgres; integración condicional a `TEST_DATABASE_URL` (skip si no hay instancia).
