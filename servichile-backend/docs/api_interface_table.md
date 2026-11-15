# Interfaz de programación ServiChile API v1

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
| POST | `/v1/perfil/biometria` | Sí | multipart, campo `foto` (JPEG/PNG/WebP/GIF, máximo 5 MB) | 201 `BiometriaOut` | 401, 413 foto muy grande, 422 no es imagen, 429 límite |
| POST | `/v1/perfil/antecedentes` | Sí | multipart `archivo` (PDF) + `nombre_archivo` | 201 `AntecedentesOut` (score, anotaciones sí/no, XP +60 una vez; PDF no se guarda) | 401, 413, 422, 429 |
| GET | `/v1/reservas` | Sí | n/a | 200 lista de `ReservaOut` | 401 |
| POST | `/v1/reservas` | Sí | `business_id` | 201 `ReservaOut` (incluye `qr_token`) | 401, 404 negocio, 422 |
| POST | `/v1/businesses/{id}/checkin` | Sí (titular) | `qr_token` (10 a 64) | 200 `ReservaOut` con `estado: asistido` | 401, 403 no es titular del negocio, 404 QR no encontrado, 409 reserva ya cerrada, 422 |
| POST | `/v1/businesses/{id}/reservas/{reserva_id}/no-show` | Sí (titular) | n/a | 200 `ReservaOut` con `estado: no_show` | 401, 403, 404, 409 |
| POST | `/v1/businesses` | Sí (proveedor) | `nombre`, `categoria`, `direccion` (oficina); opcionales `descripcion`/`telefono`/`sitio_web`/`imagen_url`/`logo_url` | 201 `NegocioEnMapaOut` | 401, 403 si no es proveedor, 422 |
| GET | `/v1/businesses/mias` | Sí | n/a | 200 lista de `NegocioEnMapaOut` | 401 |
| GET | `/v1/businesses/{id}/reputation` | No | n/a | 200 `ReputacionOut` (incluye `observables_ciber`) | 404 negocio no encontrado |
| POST | `/v1/businesses/{id}/ciber-scan` | Sí (titular) | n/a | 200 `ReputacionOut` re-escaneada | 401, 403 no titular, 404 |
| POST | `/v1/businesses/{id}/claim` | Sí (proveedor) | `documento_verificacion` (3 a 120), `nombre`/`telefono`/`sitio_web` opcionales | 201 `ClaimOut` | 401, 403 si no es proveedor, 404, 409 ya reclamado, 422 |
| DELETE | `/v1/businesses/{id}/claim` | Sí (titular) | n/a | 204 sin cuerpo | 401, 403 no es titular, 404 |
| DELETE | `/v1/auth/yo` | Sí | `password` (confirmación de la contraseña actual) | 204 sin cuerpo | 401 sesión inválida, 403 contraseña incorrecta, 422 |
| DELETE | `/v1/reservas/{id}` | Sí | n/a | 200 `ReservaOut` con `estado: cancelada` | 401, 404 reserva ajena o inexistente, 409 ya no está activa |
| GET | `/v1/reporte` | Sí | n/a | 200 `ReporteOut` (payload QR del reporte) | 401 |
| POST | `/v1/reporte/validar` | Sí | `payload` (URI `servichile://reporte/...` o JWT) | 200 `ReporteValidacionOut` | 401, 422 QR inválido/expirado, 429 |

## Esquemas

**UsuarioOut**: `id` (uuid), `email`, `nombre`, `creado_en` (ISO 8601), `perfil` (`PerfilOut`, nunca null; incluye el estado del Pasaporte). Nunca incluye contraseña, hash, RUT ni estado `activo`.

**PerfilIn** (PATCH): `edad` (14 a 120), `rut` (con dígito verificador, p. ej. `12.345.678-5`), `telefono` (solo dígitos y espacios, opcional `+`). Campos desconocidos dan 422. Un campo enviado como `null` se borra, salvo el RUT, que no se puede borrar. `preocupacion` y `proposito` se aceptan solo durante la transición.

**PerfilOut** (GET, PATCH y perfil de `/v1/auth/yo`):

- `rut_verificado` (bool): `true` cuando el RUT pasó la validación del dígito verificador y la consulta al verificador.
- `telefono` (texto o null).
- `nivel_pasaporte`: siempre `1` (registrado).
- `estado_pasaporte`: `basico` o `verificado` (según RUT).
- `score_confiabilidad` (0 a 100 o null): asistencias sobre reservas cerradas (asistidas más no-show), por 100. Null si no hay reservas cerradas.
- `biometria_verificada` (bool) y `biometria_verificada_en` (ISO 8601 o null): la foto nunca se guarda.
- `xp` y `nivel_xp` (1 a 3).
- `edad`.
- `preocupacion` y `proposito`: siempre null. Deprecados.

**BiometriaOut**: `biometria_verificada`, `biometria_verificada_en`, `xp`, `nivel_xp`, `mensaje` (aclara que la foto no se almacenó).

**ReservaOut**: `id`, `business_id`, `estado` (`reservada`, `asistido`, `no_show`, `cancelada`), `qr_token` (lo muestra el usuario en el comercio), `creado_en`.

**TokenOut**: `access_token`, `token_type` (`"bearer"`), `expires_in` (segundos).

**NegocioEnMapaOut** (listado marketplace): `id`, `nombre`, `categoria`, `latitud`, `longitud`, `direccion`, `descripcion`, `imagen_url`, `logo_url` (null o URL), `logo_texto` (iniciales si no hay logo), `cta_texto` (acción por categoría), `indice_transparencia`, `is_verified_profile`, `requiere_nivel` (1 o 2).

**ReputacionOut** (Índice de Transparencia): `business_id` (uuid), `nombre`, `categoria`, `is_verified_profile` (bool), `estado_perfil`, `google_rating_avg`, `google_reviews_count`, `sentiment_positive_ratio`, `response_time_score`, `indice_transparencia` (1.0 a 10.0), `actualizado_en`, `observables_ciber` (lista de `{id, etiqueta, detalle, score 0–100, peso, grupo}` para `ssl-tls`, `email-auth`, `puertos`, `headers-http`, `stack-vulnerable`, `blacklist`, `dnssec`, `subdominios`, `whois`, `uptime`, `cookies`, `mercado-publico`, `sii`, `resenas-reclamos`), `descargo`. Nunca incluye textos de reseñas ni comentarios. El primer GET sin scores dispara un escaneo (`CIBER_SONDA=fake|live`) y lo persiste.

**ClaimIn**: `documento_verificacion` (3 a 120, obligatorio), `nombre` (2 a 160), `telefono` (≤30), `sitio_web` (≤200), todos opcionales salvo el documento. Campos desconocidos dan 422.

**ClaimOut**: `business_id`, `is_claimed` (bool), `is_verified_profile` (bool), `reclamado_por` (uuid del usuario), `mensaje`.

**ReporteOut** (GET `/v1/reporte`): `payload` (URI `servichile://reporte/<jwt>` para dibujar el QR del reporte), `token`, `expires_in`, `expires_at`, `nombre`, `email`, `nivel_pasaporte`, `estado_pasaporte`, `score_confiabilidad`, `rut_verificado`. El token es distinto del JWT de sesión y dura `REPORTE_EXPIRES_MINUTES` (por defecto 15).

**ReporteValidarIn**: `payload` (10 a 2048). Acepta la URI completa o el JWT crudo.

**ReporteValidacionOut**: `es_propio`, `nombre`, `nivel_pasaporte`, `estado_pasaporte`, `score_confiabilidad`, `rut_verificado`, `expires_at`. Nunca incluye correo ni RUT.

## Comportamiento

- **Límites por minuto:** login/registro por correo e IP (`.env`).
- **Pasaporte de Confianza:**
  - **RUT:** se valida el dígito verificador con módulo 11 y luego se consulta al verificador de RUT. Hoy el verificador es falso: acepta cualquier RUT con DV válido. No se devuelve el número de RUT, solo `rut_verificado`.
  - **Reservas:** el dueño verificado de un comercio (`is_claimed` y `reclamado_por` igual a su usuario) registra asistencia o no-show. Un comercio sin reclamar no tiene quien registre asistencias.
  - **Reporte verificable:** cada usuario autenticado obtiene un reporte firmado de corta vida (`GET /v1/reporte`). El QR solo transporta ese token; al escanearlo (`POST /v1/reporte/validar`) se confirma la validez del reporte (datos públicos de confianza). El JWT de sesión no sirve como reporte.

- **Índice de Transparencia (blindaje legal):** `GET /v1/businesses/{id}/reputation` devuelve solo métricas estadísticas agregadas y el índice algorítmico (1.0 a 10.0), nunca textos de reseñas ni juicios de valor. La fórmula vive en `app/domain/reputacion.py`: `(0.4 × Google normalizado) + (0.3 × Volumen normalizado) + (0.3 × Factor de verificación)`, reescalada a 1.0–10.0. Un negocio no reclamado recibe un factor de verificación neutro (ni premia ni castiga). Reclamar el perfil (`POST /claim`, Derecho a Réplica) lo marca como verificado y recalcula el índice. El cálculo está pensado para ejecutarse en segundo plano (worker); `final_score` se lee de la base y solo se calcula al vuelo si falta.
- **Errores:** siguen el formato de FastAPI, `{"detail": "mensaje"}`. Los errores 422 traen `detail` como lista de campos inválidos.
