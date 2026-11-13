# Modelo de datos

Fuente: `db/init_script.sql`. Para exportar el diagrama a `db/schema_diagram.png`, pegue el bloque en https://mermaid.live y descargue la imagen.

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
        timestamptz creado_en
    }
    perfiles {
        uuid usuario_id PK, FK
        smallint edad
        varchar tipo_cuenta
        varchar preocupacion
        varchar proposito
        timestamptz actualizado_en
    }
    business_entities {
        uuid id PK
        varchar nombre
        varchar categoria
        boolean is_claimed
        uuid reclamado_por FK
    }
    business_reputation_metrics {
        uuid business_id PK, FK
        float final_score
        float score_ssl_tls
    }
    reservas {
        uuid id PK
        uuid usuario_id FK
        uuid business_id FK
        varchar estado
        varchar qr_token UK
    }
```

`perfiles` guarda los datos del onboarding aparte de las credenciales, en relación uno a uno con `usuarios`. Al borrar un usuario se borra su perfil (`ON DELETE CASCADE`). La edad mínima es 14 porque la Ley 21.719 exige consentimiento de los padres para menores de esa edad, y la app no lo gestiona.

## Migraciones

Las bases nuevas se crean con `db/init_script.sql`, que ya incluye todas las tablas. Las bases existentes se actualizan aplicando en orden los archivos de `db/migrations/`:

| Archivo | Cambio |
|---|---|
| `002_perfiles.sql` | Crea la tabla `perfiles`. Se puede ejecutar más de una vez. |
| `015_drop_consultas_rag.sql` | Elimina `consultas`, `fragmentos` y `documentos` (stack IA/RAG retirado). |
| `016_drop_pgvector.sql` | Elimina la extensión `vector` (pgvector). |
