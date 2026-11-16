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
| POST | `/v1/perfil/biometria` | Sí | multipart, campo `foto` (JPEG/PNG/WebP/GIF, máximo 5 MB) | 201 `BiometriaOut` (guarda JPEG comprimido en `BIOMETRIA_DIR` + metadata; retención configurable) | 401, 413 foto muy grande, 422 no es imagen, 429 límite |
| POST | `/v1/perfil/cedula` | Sí | multipart, campo `foto` (frontal, máx. 8 MB) | 201 `CedulaOut` (OCR Tesseract + ROI RUN + face-match vs selfie en `BIOMETRIA_DIR`; foto carnet no retenida; puede verificar RUT) | 401, 409 RUT en uso, 413, 422 (sin selfie / OCR / face-match), 429 |
| POST | `/v1/perfil/antecedentes` | Sí | multipart `archivo` (PDF) + `nombre_archivo` | 201 `AntecedentesOut` (score, anotaciones sí/no, XP +60 una vez; PDF no se guarda) | 401, 413, 422, 429 |
| POST | `/v1/perfil/aval` | Sí | multipart `archivo` (PDF textual) + `nombre_archivo` | 201 `AvalOut` (tipo carta_aval/boleta/poliza, score por reglas; sin IA; PDF no se guarda) | 401, 413, 422 (escaneo/foto/reglas), 429 |
| POST | `/v1/businesses/{id}/documentos/{tipo}` | Sí (proveedor titular) | multipart `archivo` (PDF textual); `tipo` ∈ constitucion\|patente\|inicio_actividades\|poder_representante | 201 `DocEmpresaOut` (score, docs_empresa; sin IA; PDF no se guarda) | 401, 403, 404, 413, 422, 429 |
| GET | `/v1/reservas` | Sí | n/a | 200 lista de `ReservaOut` | 401 |
| POST | `/v1/reservas` | Sí | `business_id` | 201 `ReservaOut` (incluye `qr_token`) | 401, 404 negocio, 422 |
| POST | `/v1/businesses/{id}/checkin` | Sí (titular) | `qr_token` (10 a 64) | 200 `ReservaOut` con `estado: asistido` | 401, 403 no es titular del negocio, 404 QR no encontrado, 409 reserva ya cerrada, 422 |
| POST | `/v1/businesses/{id}/reservas/{reserva_id}/no-show` | Sí (titular) | n/a | 200 `ReservaOut` con `estado: no_show` | 401, 403, 404, 409 |
| POST | `/v1/businesses` | Sí (proveedor) | `nombre`, `categoria`, `direccion` (oficina); opcionales `descripcion`/`telefono`/`sitio_web`/`imagen_url`/`logo_url`/`rut_empresa` | 201 `NegocioTitularOut` | 401, 403 si no es proveedor, 422 |
| GET | `/v1/businesses/mias` | Sí | n/a | 200 lista de `NegocioTitularOut` | 401 |
| PATCH | `/v1/businesses/{id}` | Sí (titular) | ficha (nombre, categoría, dirección, contacto, RUT…) | 200 `NegocioTitularOut` | 401, 403, 404, 422 |
| PATCH | `/v1/businesses/{id}/rut` | Sí (titular) | `rut_empresa` | 200 `NegocioTitularOut` | 401, 403, 404, 422 |
| GET | `/v1/businesses/{id}/reputation` | No | n/a | 200 `ReputacionOut` (`observables`; `docs_empresa` solo flags públicos) | 404 negocio no encontrado |
| POST | `/v1/businesses/{id}/rater-refresh` | Sí (titular) | n/a | 200 `ReputacionOut` (Places/crawler/ChileCompra + índice) | 401, 403 no titular, 404, 429, 503 rater |
| DELETE | `/v1/businesses/{id}` | Sí (creador) | n/a | 204 sin cuerpo. Borra la empresa y sus reservas. | 401, 403 si no la creó, 404 |
| DELETE | `/v1/auth/yo` | Sí | `password` (confirmación de la contraseña actual) | 204 sin cuerpo | 401 sesión inválida, 403 contraseña incorrecta, 422 |
| DELETE | `/v1/reservas/{id}` | Sí | n/a | 200 `ReservaOut` con `estado: cancelada` | 401, 404 reserva ajena o inexistente, 409 ya no está activa |
| GET | `/v1/reporte` | Sí | n/a | 200 `ReporteOut` (payload QR del reporte) | 401 |
| POST | `/v1/reporte/validar` | Sí | `payload` (URI `servichile://reporte/...` o JWT) | 200 `ReporteValidacionOut` | 401, 422 QR inválido/expirado, 429 |

## Esquemas

**UsuarioOut**: `id` (uuid), `email`, `nombre`, `creado_en` (ISO 8601), `perfil` (`PerfilOut`, nunca null; incluye el estado del Pasaporte). Nunca incluye contraseña, hash, RUT ni estado `activo`.

**PerfilIn** (PATCH): `edad` (14 a 120), `rut` (con dígito verificador, p. ej. `12.345.678-5`), `telefono` (solo dígitos y espacios, opcional `+`), `tipo_cuenta`. Campos desconocidos dan 422. Un campo enviado como `null` se borra, salvo el RUT, que no se puede borrar.

**PerfilOut** (GET, PATCH y perfil de `/v1/auth/yo`):

- `rut_verificado` (bool): `true` cuando el RUT pasó la validación del dígito verificador y la consulta al verificador.
- `telefono` (texto o null).
- `nivel_pasaporte`: siempre `1` (registrado).
- `estado_pasaporte`: `basico` o `verificado` (según RUT).
- `score_confiabilidad` (0 a 100 o null): asistencias sobre reservas cerradas (asistidas más no-show), por 100. Null si no hay reservas cerradas.
- `biometria_verificada` (bool), `biometria_verificada_en`, `biometria_retener_hasta`, `biometria_bytes`: selfie comprimida en disco local; no se expone la ruta ni el archivo.
- `xp` y `nivel_xp` (1 a 3).
- `edad`.
**BiometriaOut**: `biometria_verificada`, `biometria_verificada_en`, `biometria_retener_hasta`, `biometria_bytes`, `xp`, `nivel_xp`, `mensaje` (aclara retención limitada y borrado al eliminar cuenta).

**ReservaOut**: `id`, `business_id`, `estado` (`reservada`, `asistido`, `no_show`, `cancelada`), `qr_token` (lo muestra el usuario en el comercio), `creado_en`.

**TokenOut**: `access_token`, `token_type` (`"bearer"`), `expires_in` (segundos).

**NegocioEnMapaOut** (listado público): `id`, `nombre`, `categoria`, `latitud`, `longitud`, `direccion`, `descripcion`, `imagen_url`, `logo_url`, `logo_texto`, `cta_texto`, `indice_transparencia`, `indice_pct`, `requiere_nivel` (1 o 2), `is_claimed`. Sin RUT, teléfono, sitio ni docs.

**NegocioTitularOut** (alta, `/mias`, PATCH): campos de `NegocioEnMapaOut` + `rut_empresa`, `telefono`, `sitio_web`, `docs_empresa` (detalle completo del titular).

**ReputacionOut** (Índice de Transparencia): `business_id` (uuid), `nombre`, `categoria`, `google_rating_avg`, `google_reviews_count`, `indice_transparencia` (0.0 a 10.0), `indice_pct` (0–100), `docs_verificados`/`docs_total`, `docs_empresa` (meta tipada; en público solo flags), `actualizado_en`, `observables` (lista de `{id, etiqueta, detalle, score 0–100, peso, grupo}`), `descargo`. Nunca incluye textos de reseñas. El rater **no** corre en el GET: se calcula al crear/actualizar y se refresca en background o con `POST …/rater-refresh`.

**ReporteOut** (GET `/v1/reporte`): `payload` (URI `servichile://reporte/<jwt>` para dibujar el QR del reporte), `token`, `expires_in`, `expires_at`, `nombre`, `email`, `nivel_pasaporte`, `estado_pasaporte`, `score_confiabilidad`, `rut_verificado`. El token es distinto del JWT de sesión y dura `REPORTE_EXPIRES_MINUTES` (por defecto 15).

**ReporteValidarIn**: `payload` (10 a 2048). Acepta la URI completa o el JWT crudo.

**ReporteValidacionOut**: `es_propio`, `nombre`, `nivel_pasaporte`, `estado_pasaporte`, `score_confiabilidad`, `rut_verificado`, `expires_at`. Nunca incluye correo ni RUT.

## Comportamiento

- **Límites por minuto:** login/registro por correo e IP (`.env`).
- **Pasaporte de Confianza:**
  - **RUT:** se valida el dígito verificador con módulo 11 y luego se consulta al verificador de RUT. Hoy el verificador es falso: acepta cualquier RUT con DV válido. No se devuelve el número de RUT, solo `rut_verificado`.
  - **Reservas:** quien creó la empresa (`reclamado_por` igual a su usuario) registra asistencia o no-show.
  - **Reporte verificable:** cada usuario autenticado obtiene un reporte firmado de corta vida (`GET /v1/reporte`). El QR solo transporta ese token; al escanearlo (`POST /v1/reporte/validar`) se confirma la validez del reporte (datos públicos de confianza). El JWT de sesión no sirve como reporte.

- **Índice de Transparencia (blindaje legal):** `GET /v1/businesses/{id}/reputation` expone el índice unificado (señales del rater + documentos) en `final_score`/`indice_transparencia` (0.0–10.0) y `observables`. No hay reseñas ni juicios de valor. El score se persiste al crear/actualizar y se refresca en background o con `rater-refresh`; el GET solo lee.
- **Errores:** siguen el formato de FastAPI, `{"detail": "mensaje"}`. Los errores 422 traen `detail` como lista de campos inválidos.
