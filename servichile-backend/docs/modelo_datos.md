# Modelo de datos

Fuente: `db/init_script.sql` (esquema vivo). Bases existentes: migraciones `002`–`042` en `db/migrations/`.

```mermaid
erDiagram
    usuarios ||--o| perfiles : tiene
    usuarios ||--o{ usuario_xp_eventos : acumula
    usuarios ||--o{ reservas : hace
    usuarios ||--o{ business_entities : reclama
    business_entities ||--o| business_reputation_metrics : mide

    usuarios {
        uuid id PK
        varchar email UK
        varchar nombre
        text password_hash
        boolean activo
        varchar rut UK
        boolean rut_verificado
        integer xp
        timestamptz creado_en
    }
    perfiles {
        uuid usuario_id PK_FK
        smallint edad
        varchar tipo_cuenta
        timestamptz actualizado_en
    }
    business_entities {
        uuid id PK
        varchar nombre
        varchar categoria
        varchar rut_empresa
        jsonb docs_empresa
        boolean is_claimed
        uuid reclamado_por FK
    }
    business_reputation_metrics {
        uuid business_id PK_FK
        float final_score
        jsonb observables
        timestamptz rater_escaneado_en
    }
    reservas {
        uuid id PK
        uuid usuario_id FK
        uuid business_id FK
        varchar estado
        varchar qr_token UK
    }
    pades_document_hashes {
        text sha256 PK
        text scope
        uuid usuario_id
        uuid business_id
    }
```

## Separación persona / empresa

| Persona (`usuarios` + `perfiles`) | Empresa (`business_entities` + métricas) |
|---|---|
| RUT, cédula, biometría, antecedentes, aval, XP | `rut_empresa`, `docs_empresa`, índice rater |
| Onboarding: `tipo_cuenta`, edad, teléfono | Claim: `reclamado_por` / `is_claimed` |

El índice público de empresa vive en `observables` + `final_score` (0–10). No hay columnas `score_*` legacy ni sello `is_verified_profile`.

`perfiles` es 1:1 con `usuarios` (`ON DELETE CASCADE`). Edad mínima 14 (Ley 21.719).

## Migraciones relevantes (bases existentes)

| Archivo | Cambio |
|---|---|
| `002`–`004` | Perfiles y pasaporte (RUT) |
| `017` | Tipos `persona` / `contratista` / `proveedor` |
| `021` | `rut_empresa` |
| `031`–`033` | Biometría archivo, cédula, aval |
| `034` | `docs_empresa` JSONB |
| `037` | `observables_ciber` (luego renombrado) |
| `038` | `final_score` permite 0 |
| `039` | Drop `is_verified_profile` |
| `040` | Drop scores legacy, CMF, `preocupacion`/`proposito`, `aval_gemini_usado` |
| `041` | Índices listado, `final_score` default 0, CHECK+UNIQUE `rut_empresa`, FKs PAdES |
| `042` | Renombra `observables_ciber`→`observables`, `ciber_escaneado_en`→`rater_escaneado_en` |

`GET /reputation` expone `docs_empresa` solo con flags públicos (`verificado`, `verificado_en`). El titular ve el detalle completo al subir o vía sus endpoints.

Para levantar demo: `python -m scripts.cargar_db_demo` (aplica migraciones en orden).
