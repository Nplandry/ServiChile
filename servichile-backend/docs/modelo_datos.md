# Modelo de datos

Fuente: `db/init_script.sql`. Para exportar el diagrama a `db/schema_diagram.png`, pegue el bloque en https://mermaid.live y descargue la imagen.

```mermaid
erDiagram
    usuarios ||--o{ consultas : realiza
    usuarios ||--o| perfiles : tiene
    documentos ||--|{ fragmentos : contiene

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
        varchar preocupacion
        varchar proposito
        timestamptz actualizado_en
    }
    consultas {
        uuid id PK
        uuid usuario_id FK
        varchar categoria
        text pregunta_redactada
        text respuesta
        jsonb fuentes
        boolean requiere_humano
        timestamptz creado_en
    }
    documentos {
        uuid id PK
        varchar titulo
        text url_fuente
        varchar categoria
        date publicado_en
        char hash_sha256 UK
        timestamptz cargado_en
    }
    fragmentos {
        serial id PK
        uuid documento_id FK
        integer pagina
        integer orden
        text contenido
        vector embedding
    }
```

`fragmentos.embedding` es `vector(768)` con índice HNSW de distancia coseno. Las tablas `documentos` y `fragmentos` guardan normativa pública; no contienen datos personales.

`perfiles` guarda los datos del onboarding aparte de las credenciales, en relación uno a uno con `usuarios`. Al borrar un usuario se borra su perfil (`ON DELETE CASCADE`). La edad mínima es 14 porque la Ley 21.719 exige consentimiento de los padres para menores de esa edad, y la app no lo gestiona.

## Migraciones

Las bases nuevas se crean con `db/init_script.sql`, que ya incluye todas las tablas. Las bases existentes se actualizan aplicando en orden los archivos de `db/migrations/`:

| Archivo | Cambio |
|---|---|
| `002_perfiles.sql` | Crea la tabla `perfiles`. Se puede ejecutar más de una vez. |
