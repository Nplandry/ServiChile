# RAG / Consultas IA (inventario)

Stack del asistente de orientación con RAG. El frontend ya no lo usa (se quitó el Asistente de la PWA); el backend **sigue exponiendo** estos endpoints y tablas.

> No confundir con `categoria` de **negocios** del marketplace (`gimnasio`, `arriendo`, etc.). Esas no forman parte de este stack.

## API

| Método | Ruta | Sesión | Función |
|---|---|---|---|
| POST | `/v1/consultas` | Sí | Crea consulta IA con RAG (201) |
| GET | `/v1/consultas?limite=50` | Sí | Historial de consultas del usuario |

Router: `app/api/v1/consultas.py` (montado en `app/main.py`).

### Schemas (`app/api/schemas.py`)

- **ConsultaIn**: `pregunta` (5–2000), `categoria` opcional
- **ConsultaOut**: `id`, `respuesta`, `fuentes` (`titulo`, `url`, `pagina`), `requiere_humano`, `creado_en`
- **ConsultaResumen**: `id`, `categoria`, `pregunta_redactada`, `requiere_humano`, `creado_en`

Categorías de consulta (tema legal, no marketplace):

- `embargo-falso`
- `seguros`
- `portabilidad`

## Flujo

1. El usuario envía una pregunta (y opcionalmente una categoría).
2. Se redactan datos personales de la pregunta (PII).
3. Se genera el embedding de la pregunta.
4. Se buscan fragmentos de normativa en pgvector (`FragmentoRepository`), filtrando por categoría si viene.
5. Si ningún fragmento supera el umbral `RAG_MAX_DISTANCE`, no se llama al modelo: se responde con derivación (p. ej. SERNAC) y `requiere_humano: true`.
6. Si hay fragmentos, se arma el prompt, se llama al LLM y se guardan pregunta redactada, respuesta y fuentes en `consultas`.

Límite: `consulta_rate_per_minute` (por defecto 10/min por usuario).

## Archivos del stack

| Pieza | Rol |
|---|---|
| `app/api/v1/consultas.py` | Endpoints POST/GET |
| `app/services/ai_assistant.py` | Redacción PII, recuperación, prompt, LLM, persistencia |
| `app/services/consulta_service.py` | Historial de consultas |
| `app/infrastructure/llm.py` | Embeddings y generación (`fake` / `gemini`) |
| `app/infrastructure/repositories.py` | `FragmentoRepository`, `ConsultaRepository` |
| `app/domain/entidades.py` | `Consulta`, `Fuente`, `ResultadoConsulta` |
| `app/domain/pii.py` | Redacción de datos personales |
| `app/api/deps.py` | Wiring de `AiAssistant` y `ConsultaService` |
| `app/api/schemas.py` | `ConsultaIn`, `ConsultaOut`, `ConsultaResumen`, `Categoria` |
| `app/config.py` | `rag_top_k`, `rag_max_distance`, `consulta_rate_per_minute` |
| `scripts/ingest_pdfs.py` | Carga PDFs de normativa a `documentos` / `fragmentos` |
| `tests/test_consultas.py` | Pruebas del flujo de consultas |
| `tests/test_llm.py` | Pruebas del adaptador LLM |
| `tests/conftest.py` | `FakeFragmentos` y overrides de deps |
| `tests/integration/test_postgres.py` | Integración con pgvector |
| `docs/api_interface_table.md` | Contrato de la API (sección consultas) |

## Base de datos (`db/init_script.sql`)

### `documentos`

Normativa oficial (leyes, circulares, guías). Campos relevantes: `titulo`, `url_fuente`, `categoria` (`embargo-falso` \| `seguros` \| `portabilidad`), `hash_sha256`.

### `fragmentos`

Chunks con embedding (`vector(768)`), índice HNSW por distancia coseno. Relacionados a `documentos` con `ON DELETE CASCADE`.

### `consultas`

Historial por usuario. Solo se guarda la **pregunta ya redactada** (sin RUT, correo ni teléfono), más `respuesta`, `fuentes` (jsonb) y `requiere_humano`.

Al borrar un usuario, sus consultas se eliminan en cascada.

## Configuración (`.env`)

- `LLM_PROVIDER` — `fake` (dev) o `gemini`
- `EMBEDDING_DIM` — debe coincidir con la dimensión de los vectores en `fragmentos`
- `RAG_TOP_K` — cuántos fragmentos recuperar
- `RAG_MAX_DISTANCE` — umbral de distancia coseno; si nada entra, no se llama al modelo
- `CONSULTA_RATE_PER_MINUTE` — rate limit por usuario

Usar el **mismo** `LLM_PROVIDER` al ingerir PDFs y al consultar: los vectores de `fake` y `gemini` no son compatibles. Si se cambia de proveedor o de dimensión, hay que vaciar `documentos`/`fragmentos` y volver a cargar.

## Cargar normativa

```bash
python -m scripts.ingest_pdfs data/ley_19496.pdf \
  --titulo "Ley 19.496 sobre Protección de los Derechos de los Consumidores" \
  --url "https://www.bcn.cl/leychile/navegar?idNorma=61438" \
  --categoria seguros
```

Los PDFs escaneados necesitan OCR antes de cargarlos.

## Estado respecto al frontend

La PWA ya no tiene Asistente, chat, auditoría por tema ni llamadas a `/v1/consultas`. Este documento sirve de mapa si más adelante se elimina o se reactiva el stack en el backend.
