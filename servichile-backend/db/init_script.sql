-- ServiChile: crea el esquema completo desde cero.
-- Requisitos: PostgreSQL 16 con la extensión pgvector (disponible en Cloud SQL).
-- Uso:
--   createdb servichile
--   psql "postgresql://USUARIO@HOST:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
-- La dimensión vector(768) debe coincidir con EMBEDDING_DIM en .env.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE usuarios (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email          varchar(254) NOT NULL UNIQUE CHECK (email = lower(email)),
    nombre         varchar(120) NOT NULL,
    password_hash  text NOT NULL,              -- Argon2id, nunca la contraseña
    activo         boolean NOT NULL DEFAULT true,
    -- Pasaporte de Confianza. RUT normalizado "12345678-K", sin puntos. Ver db/migrations/004_pasaporte.sql
    rut            varchar(12) UNIQUE CHECK (rut ~ '^[0-9]{1,8}-[0-9K]$'),
    rut_verificado boolean NOT NULL DEFAULT false,
    telefono       varchar(30),
    -- Biometría: solo bandera + fecha. La imagen se procesa en memoria y no se guarda.
    biometria_verificada boolean NOT NULL DEFAULT false,
    biometria_verificada_en timestamptz,
    xp             integer NOT NULL DEFAULT 0 CHECK (xp >= 0),
    creado_en      timestamptz NOT NULL DEFAULT now()
);

-- Log idempotente de XP (un evento = un premio; no duplica).
CREATE TABLE usuario_xp_eventos (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento      varchar(80) NOT NULL,
    puntos      integer NOT NULL CHECK (puntos > 0),
    creado_en   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, evento)
);

CREATE INDEX usuario_xp_eventos_usuario_idx ON usuario_xp_eventos (usuario_id, creado_en DESC);

-- Perfil del usuario, separado de las credenciales. Ver también db/migrations/002_perfiles.sql y 004_pasaporte.sql
CREATE TABLE perfiles (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Ley 21.719: menores de 14 requieren consentimiento de sus padres, que la app no gestiona
    edad           smallint CHECK (edad BETWEEN 14 AND 120),
    -- persona | empresa (onboarding). Nullable para cuentas anteriores.
    tipo_cuenta    varchar(20) CHECK (tipo_cuenta IS NULL OR tipo_cuenta IN ('persona', 'empresa')),
    -- DEPRECADOS: nullable durante la transición. Se eliminan en una migración posterior.
    preocupacion   varchar(20) CHECK (preocupacion IN ('embargo', 'seguros', 'telecom', 'otro')),
    proposito      varchar(20) CHECK (proposito IN ('autoinformarse', 'asesorar', 'investigar', 'trabajo')),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

-- Normativa oficial cargada para RAG (leyes, circulares CMF, guías SERNAC, etc.)
CREATE TABLE documentos (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo         varchar(300) NOT NULL,
    url_fuente     text,
    categoria      varchar(40) CHECK (categoria IN ('embargo-falso', 'seguros', 'portabilidad')),
    publicado_en   date,
    hash_sha256    char(64) NOT NULL UNIQUE,   -- evita cargar el mismo PDF dos veces
    cargado_en     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE fragmentos (
    id             serial PRIMARY KEY,
    documento_id   uuid NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    pagina         integer,
    orden          integer NOT NULL,
    contenido      text NOT NULL,
    embedding      vector(768) NOT NULL
);

CREATE INDEX fragmentos_documento_idx ON fragmentos (documento_id);
CREATE INDEX fragmentos_embedding_idx ON fragmentos USING hnsw (embedding vector_cosine_ops);

-- Historial de consultas. Solo se guarda la pregunta ya redactada (sin RUT, correo ni teléfono).
CREATE TABLE consultas (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id          uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria           varchar(40),
    pregunta_redactada  text NOT NULL,
    respuesta           text NOT NULL,
    fuentes             jsonb NOT NULL DEFAULT '[]'::jsonb,
    requiere_humano     boolean NOT NULL DEFAULT false,
    creado_en           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX consultas_usuario_fecha_idx ON consultas (usuario_id, creado_en DESC);

-- Directorio de transparencia de comercios. Ver también db/migrations/003_negocios.sql
-- Datos estáticos del comercio. El índice se calcula en segundo plano, no aquí.
CREATE TABLE business_entities (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         varchar(160) NOT NULL,
    categoria      varchar(30) NOT NULL
                     CHECK (categoria IN ('tecnologia', 'industria', 'construccion',
                                          'servicios-profesionales', 'logistica')),
    latitud        double precision,
    longitud       double precision,
    direccion      varchar(200),
    descripcion    text,
    imagen_url     varchar(500),
    logo_url       varchar(500),
    -- Nivel de Pasaporte requerido para la acción (1 = registrado)
    requiere_nivel smallint NOT NULL DEFAULT 1 CHECK (requiere_nivel IN (1, 2)),
    external_ref   varchar(200) UNIQUE,            -- p. ej. place_id de Google Maps (ingesta)
    is_claimed     boolean NOT NULL DEFAULT false, -- Derecho a Réplica: perfil reclamado por su dueño
    reclamado_por  uuid REFERENCES usuarios(id) ON DELETE SET NULL,
    telefono       varchar(30),
    sitio_web      varchar(200),
    creado_en      timestamptz NOT NULL DEFAULT now()
);

-- Métricas estadísticas agregadas y el Índice de Transparencia. Sin textos de reseñas.
CREATE TABLE business_reputation_metrics (
    business_id              uuid PRIMARY KEY REFERENCES business_entities(id) ON DELETE CASCADE,
    google_rating_avg        double precision CHECK (google_rating_avg BETWEEN 0 AND 5),
    google_reviews_count     integer NOT NULL DEFAULT 0 CHECK (google_reviews_count >= 0),
    sentiment_positive_ratio double precision CHECK (sentiment_positive_ratio BETWEEN 0 AND 1),
    response_time_score      double precision CHECK (response_time_score BETWEEN 0 AND 1),
    -- Índice algorítmico de 1.0 a 10.0, no un juicio de valor sobre la calidad del servicio
    final_score              double precision NOT NULL DEFAULT 1.0 CHECK (final_score BETWEEN 1 AND 10),
    is_verified_profile      boolean NOT NULL DEFAULT false,
    actualizado_en           timestamptz NOT NULL DEFAULT now()
);

-- Reservas de cupo en comercios o eventos. Nacen en la app; el dueño marca asistencia o no-show.
-- El score de confiabilidad se calcula desde esta tabla, no se guarda.
CREATE TABLE reservas (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id    uuid NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    estado         varchar(20) NOT NULL DEFAULT 'reservada'
                     CHECK (estado IN ('reservada', 'asistido', 'no_show', 'cancelada')),
    qr_token       varchar(64) NOT NULL UNIQUE,   -- contenido del código QR que muestra el usuario
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX reservas_usuario_idx ON reservas (usuario_id, creado_en DESC);
CREATE INDEX reservas_negocio_idx ON reservas (business_id);


COMMIT;
