# Interfaz de programación ServicIA API v1

URL base local: `http://localhost:8000`. Documentación interactiva: `/docs` (desactivada con `APP_ENV=production`).

Los endpoints marcados con "Sí" en la columna Sesión requieren la cabecera `Authorization: Bearer <access_token>`.

| Método | Ruta | Sesión | Entrada (JSON) | Respuesta exitosa | Errores |
|---|---|---|---|---|---|
| GET | `/salud` | No | n/a | 200 `{"estado": "ok"}` | n/a |
| POST | `/v1/auth/registro` | No | `email`, `nombre` (2 a 120), `password` (8 a 128), `perfil` opcional | 201 `UsuarioOut` | 409 correo registrado, 422 validación, 429 límite |
| POST | `/v1/auth/login` | No | `email`, `password` | 200 `TokenOut` | 401 credenciales, 422 validación, 429 límite |
| GET | `/v1/auth/yo` | Sí | n/a | 200 `UsuarioOut` | 401 sesión inválida |
| GET | `/v1/perfil` | Sí | n/a | 200 `PerfilOut` (Pasaporte de Confianza) | 401 |
| PATCH | `/v1/perfil` | Sí | `PerfilIn` parcial (`edad`, `rut`, `telefono`) | 200 `PerfilOut` | 401, 422 RUT inválido o no verificable, 409 RUT en uso o ya verificado |
| POST | `/v1/perfil/documentos` | Sí | multipart, campo `archivo` (PDF, máximo 1 MB) | 201 `InmobiliariaScoring` | 401, 413 archivo muy grande, 422 no es PDF o no se puede leer, 429 límite |
| GET | `/v1/reservas` | Sí | n/a | 200 lista de `ReservaOut` | 401 |
| POST | `/v1/reservas` | Sí | `business_id` | 201 `ReservaOut` (incluye `qr_token`) | 401, 404 negocio, 422 |
| POST | `/v1/businesses/{id}/checkin` | Sí (titular) | `qr_token` (10 a 64) | 200 `ReservaOut` con `estado: asistido` | 401, 403 no es titular del negocio, 404 QR no encontrado, 409 reserva ya cerrada, 422 |
| POST | `/v1/businesses/{id}/reservas/{reserva_id}/no-show` | Sí (titular) | n/a | 200 `ReservaOut` con `estado: no_show` | 401, 403, 404, 409 |
| POST | `/v1/consultas` | Sí | `pregunta` (5 a 2000), `categoria` opcional | 201 `ConsultaOut` | 401, 422, 429 |
| GET | `/v1/consultas?limite=50` | Sí | n/a | 200 lista de `ConsultaResumen` | 401, 422 |
| GET | `/v1/businesses/{id}/reputation` | No | n/a | 200 `ReputacionOut` | 404 negocio no encontrado |
| POST | `/v1/businesses/{id}/claim` | Sí | `documento_verificacion` (3 a 120), `nombre`/`telefono`/`sitio_web` opcionales | 201 `ClaimOut` | 401, 404, 409 ya reclamado, 422 |
| DELETE | `/v1/auth/yo` | Sí | `password` (confirmación de la contraseña actual) | 204 sin cuerpo | 401 sesión inválida, 403 contraseña incorrecta, 422 |
| DELETE | `/v1/reservas/{id}` | Sí | n/a | 200 `ReservaOut` con `estado: cancelada` | 401, 404 reserva ajena o inexistente, 409 ya no está activa |

## Esquemas

**UsuarioOut**: `id` (uuid), `email`, `nombre`, `creado_en` (ISO 8601), `perfil` (`PerfilOut`, nunca null; incluye el estado del Pasaporte). Nunca incluye contraseña, hash, RUT ni estado `activo`.

**PerfilIn** (PATCH): `edad` (14 a 120), `rut` (con dígito verificador, p. ej. `12.345.678-5`), `telefono` (solo dígitos y espacios, opcional `+`). Campos desconocidos dan 422. Un campo enviado como `null` se borra, salvo el RUT, que no se puede borrar. `preocupacion` y `proposito` se aceptan solo durante la transición.

**PerfilOut** (GET, PATCH y `inmobiliaria_scoring` de `/v1/auth/yo`):

- `rut_verificado` (bool): `true` cuando el RUT pasó la validación del dígito verificador y la consulta al verificador.
- `telefono` (texto o null).
- `nivel_pasaporte` (1 o 2): 2 solo con un arriendo verificado. Todo usuario registrado es nivel 1.
- `estado_pasaporte`: `basico` (nunca subió documentos), `pendiente`, `verificado` o `rechazado`.
- `score_confiabilidad` (0 a 100 o null): asistencias sobre reservas cerradas (asistidas más no-show), por 100. Null si no hay reservas cerradas.
- `inmobiliaria_scoring` (objeto o null): `estado_verificacion`, `score_financiero` (0 a 1000) y `actualizado_en`. Null si nunca subió documentos.
- `edad`.
- `preocupacion` y `proposito`: siempre null. Deprecados.

**InmobiliariaScoring** (respuesta de POST `/v1/perfil/documentos`): `estado_verificacion`, `score_financiero`, `actualizado_en`. El PDF nunca se guarda.

**ReservaOut**: `id`, `business_id`, `estado` (`reservada`, `asistido`, `no_show`, `cancelada`), `qr_token` (lo muestra el usuario en el comercio), `creado_en`.

**TokenOut**: `access_token`, `token_type` (`"bearer"`), `expires_in` (segundos).

**ConsultaOut**: `id`, `respuesta`, `fuentes` (lista de `{n, titulo, url, pagina}`), `requiere_humano` (bool), `creado_en`.

**ConsultaResumen**: `id`, `categoria`, `pregunta_redactada`, `requiere_humano`, `creado_en`.

Valores de `categoria`: `embargo-falso`, `seguros`, `portabilidad` (los mismos `id` de `js/data/categorias.js` del frontend).

**NegocioEnMapaOut** (listado marketplace): `id`, `nombre`, `categoria`, `latitud`, `longitud`, `direccion`, `descripcion`, `imagen_url`, `logo_url` (null o URL), `logo_texto` (iniciales si no hay logo), `cta_texto` (acción por categoría), `indice_transparencia`, `is_verified_profile`, `requiere_nivel` (1 o 2).

**ReputacionOut** (Índice de Transparencia): `business_id` (uuid), `nombre`, `categoria` (`gimnasio`, `clinica-dental`, `comercio`, `restaurante`, `automotriz`, `otro`), `is_verified_profile` (bool), `estado_perfil` (`"Perfil Verificado"` o `"Perfil No Verificado / Índice Básico"`), `google_rating_avg` (0 a 5 o null), `google_reviews_count` (entero), `sentiment_positive_ratio` (0 a 1 o null), `response_time_score` (0 a 1 o null), `indice_transparencia` (1.0 a 10.0), `actualizado_en` (ISO 8601), `descargo` (texto fijo que aclara que el índice no es un juicio de valor). Nunca incluye textos de reseñas ni comentarios.

**ClaimIn**: `documento_verificacion` (3 a 120, obligatorio), `nombre` (2 a 160), `telefono` (≤30), `sitio_web` (≤200), todos opcionales salvo el documento. Campos desconocidos dan 422.

**ClaimOut**: `business_id`, `is_claimed` (bool), `is_verified_profile` (bool), `reclamado_por` (uuid del usuario), `mensaje`.

## Comportamiento

- **Redacción de datos personales:** antes de buscar o llamar al modelo, la pregunta pasa por `app/domain/pii.py`, que reemplaza RUT, correos, teléfonos móviles y números de tarjeta. En la base solo se guarda la versión redactada.
- **Sin fuentes, sin modelo:** si ningún fragmento de normativa supera el umbral `RAG_MAX_DISTANCE`, la API no llama al modelo. Responde con una derivación a SERNAC y `requiere_humano: true`.
- **Límites por minuto:** 5 intentos de login o registro por correo, 10 consultas por usuario. Se configuran en `.env`.
- **Pasaporte de Confianza:**
  - **RUT:** se valida el dígito verificador con módulo 11 y luego se consulta al verificador de RUT. Hoy el verificador es falso: acepta cualquier RUT con DV válido. No se devuelve el número de RUT, solo `rut_verificado`.
  - **Documentos de arriendo:** el PDF se lee en memoria con un límite de 1 MB, que es el umbral por encima del cual Starlette escribe a disco. El extractor es falso y devuelve métricas fijas. Solo se guardan `score_financiero` y fechas.
  - **Score de arriendo:** la fórmula es provisional (capacidad de pago, con tope de 300 si hay morosidad). Falta la definición de negocio.
  - **Reservas:** el dueño verificado de un comercio (`is_claimed` y `reclamado_por` igual a su usuario) registra asistencia o no-show. Un comercio sin reclamar no tiene quien registre asistencias.
- **Índice de Transparencia (blindaje legal):** `GET /v1/businesses/{id}/reputation` devuelve solo métricas estadísticas agregadas y el índice algorítmico (1.0 a 10.0), nunca textos de reseñas ni juicios de valor. La fórmula vive en `app/domain/reputacion.py`: `(0.4 × Google normalizado) + (0.3 × Volumen normalizado) + (0.3 × Factor de verificación)`, reescalada a 1.0–10.0. Un negocio no reclamado recibe un factor de verificación neutro (ni premia ni castiga). Reclamar el perfil (`POST /claim`, Derecho a Réplica) lo marca como verificado y recalcula el índice. El cálculo está pensado para ejecutarse en segundo plano (worker); `final_score` se lee de la base y solo se calcula al vuelo si falta.
- **Errores:** siguen el formato de FastAPI, `{"detail": "mensaje"}`. Los errores 422 traen `detail` como lista de campos inválidos.
