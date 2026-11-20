<p align="center">
  <img src="docs/brand/banner.svg" alt="ServiChile · Universidad Mayor" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Universidad%20Mayor-%2312636B?style=for-the-badge&labelColor=3C3C3B" alt="Universidad Mayor" />
  <img src="https://img.shields.io/badge/INGT1003-Arquitectura%20de%20Desarrollo-A4222B?style=for-the-badge&labelColor=3C3C3B" alt="INGT1003" />
  <img src="https://img.shields.io/badge/Semestre-2°%202026-FEDA3F?style=for-the-badge&labelColor=3C3C3B&color=FEDA3F" alt="Segundo semestre 2026" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/stack-FastAPI-12636B?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/stack-PostgreSQL-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/cliente-PWA-A4222B" alt="PWA" />
  <img src="https://img.shields.io/badge/arquitectura-capas-3C3C3B" alt="Arquitectura por capas" />
  <img src="https://img.shields.io/badge/rama-desarrollo-12636B" alt="Rama desarrollo" />
  <a href="https://github.com/Nplandry/ServiChile/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Nplandry/ServiChile/ci.yml?branch=desarrollo&label=CI&color=12636B" alt="Estado CI" /></a>
</p>

# ServiChile

Marketplace B2B con **due diligence** de proveedores, **Reporte de Confianza** (QR + verificación) e **Índice de Transparencia**. Proyecto semestral de la Escuela de Ingeniería Civil, Universidad Mayor.

| | |
|---|---|
| **Curso** | INGT1003 · Arquitectura de Desarrollo (Móvil y Web) |
| **Unidad académica** | Facultad de Ciencias, Ingeniería y Tecnología · Escuela de Ingeniería Civil |
| **Docente** | Prof. Carlos Muñoz S. |
| **Período** | Segundo semestre 2026 |
| **Repositorio** | [github.com/Nplandry/ServiChile](https://github.com/Nplandry/ServiChile) |

---

## Propuesta de valor

| Pregunta | Respuesta |
|---|---|
| **Qué problema** | Contratar proveedores sin evidencia verificable de identidad, trayectoria y transparencia. |
| **Para quién** | Empresas y contratistas que necesitan evaluar proveedores en Chile antes de cerrar un trabajo. |
| **Qué promete** | Un flujo extremo a extremo: explorar → verificar → reportar → persistir, con API real y PWA. |

---

## Arquitectura (capas)

```
┌─────────────────────────────────────────────────────────────┐
│  Presentación · servichile-frontend (PWA)                   │
│  HTML / CSS / JS · Service Worker · JWT en sesión           │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS / REST /v1
┌────────────────────────────▼────────────────────────────────┐
│  API · FastAPI (app/api)                                    │
│  Routers · esquemas Pydantic · sin reglas de negocio        │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Negocio · app/servicios + app/dominio                      │
│  Casos de uso · puertos · entidades (sin ORM / HTTP)        │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Datos · app/infraestructura/persistencia                   │
│  SQLAlchemy · PostgreSQL · repositorios                     │
└─────────────────────────────────────────────────────────────┘
```

Las reglas de dependencia se verifican con `import-linter` en el backend.

---

## Estructura del monorepo

```
ServiChile/
├── docs/brand/                 # Identidad visual (paleta U. Mayor)
├── servichile-backend/         # API FastAPI + PostgreSQL
│   ├── COMO_LEVANTAR.md        # Instrucciones reproducibles
│   ├── README.md
│   ├── docs/                   # Contrato API y modelo de datos
│   └── tests/
└── servichile-frontend/        # PWA (explorar, reportes, verificación)
    └── README.md
```

---

## Cómo levantar (primer intento)

Requisitos: **Python 3.12**, **PostgreSQL 16** (o Docker) y un navegador moderno.

### 1. Backend

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Pegue el valor en JWT_SECRET dentro de .env
```

Postgres (si aún no hay contenedor):

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

Schema + demo + servidor:

```bash
psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
python -m scripts.cargar_db_demo
uvicorn app.principal:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Salud: http://localhost:8000/salud  

### 2. Frontend

Usar siempre **localhost** (no `127.0.0.1`) para no romper la sesión tras Webpay.

```bash
cd servichile-frontend
python3 -m http.server 5500
```

- App: http://localhost:5500/index.html  

Detalle ampliado: [`servichile-backend/COMO_LEVANTAR.md`](servichile-backend/COMO_LEVANTAR.md).

---

## Observabilidad del proyecto

| Señal | Dónde |
|---|---|
| Healthcheck | `GET /salud` → `{"estado":"ok"}` |
| Docs interactivas | `/docs` (OpenAPI) |
| Contrato de API | [`servichile-backend/docs/api_interface_table.md`](servichile-backend/docs/api_interface_table.md) |
| Modelo de datos | [`servichile-backend/docs/modelo_datos.md`](servichile-backend/docs/modelo_datos.md) |
| Pruebas | `cd servichile-backend && pytest` |
| Capas | `cd servichile-backend && lint-imports` |
| Colección HTTP | `servichile-backend/tests/servichile_api_collection.json` |

Credenciales y secretos: solo en `.env` (nunca en el repositorio). Plantilla: `.env.example`.

---

## Hitos del curso

| Hito | Enfoque | Peso |
|---|---|---|
| **H1** · Propuesta | Valor, prototipo, arquitectura de información | 30 % |
| **H2** · Back end | API viva, capas, persistencia, justificación técnica | 35 % |
| **H3** · Producto | Flujo punta a punta FE↔BE, manual, video, bitácora | 35 % |

Ramas de trabajo del monorepo: `desarrollo` · `QA` · `produccion`.

---

## Identidad visual (Universidad Mayor)

Paleta corporativa aplicada en badges y marca del proyecto ([Manual de marca U. Mayor](https://www.umayor.cl/um/santiago-manual-uso-de-marca)):

| Color | Hex | Uso |
|---|---|---|
| Verde institucional | `#12636B` | Marca principal, encabezados |
| Rojo institucional | `#A4222B` | Acentos y alertas de marca |
| Amarillo institucional | `#FEDA3F` | Destacados / contraste |
| Gris institucional | `#3C3C3B` | Texto secundario |

<p align="center">
  <img src="docs/brand/mark.svg" alt="Marca ServiChile" width="96" />
</p>

La marca ServiChile usa la paleta institucional; **no sustituye** el isologo oficial de Universidad Mayor.

---

## Documentación por componente

- Backend: [`servichile-backend/README.md`](servichile-backend/README.md)
- Frontend: [`servichile-frontend/README.md`](servichile-frontend/README.md)
- Instalación: [`servichile-backend/COMO_LEVANTAR.md`](servichile-backend/COMO_LEVANTAR.md)

---

<p align="center">
  <sub>
    Universidad Mayor · Facultad de Ciencias, Ingeniería y Tecnología · Escuela de Ingeniería Civil<br/>
    INGT1003 Arquitectura de Desarrollo (Móvil y Web) · Proyecto semestral · 2° semestre 2026 · Prof. Carlos Muñoz S.
  </sub>
</p>
