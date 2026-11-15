-- ServiChile: crea el esquema completo desde cero.
-- Uso:
--   createdb servichile
--   psql "postgresql://USUARIO@HOST:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql

BEGIN;

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
    -- Antecedentes: PDF validado en memoria; se guarda solo el resultado.
    antecedentes_verificados boolean NOT NULL DEFAULT false,
    antecedentes_verificados_en timestamptz,
    antecedentes_anotaciones boolean,
    antecedentes_score integer,
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
    -- persona | contratista | proveedor (onboarding). Nullable para cuentas anteriores.
    tipo_cuenta    varchar(20) CHECK (tipo_cuenta IS NULL OR tipo_cuenta IN ('persona', 'contratista', 'proveedor')),
    -- DEPRECADOS: nullable durante la transición. Se eliminan en una migración posterior.
    preocupacion   varchar(20) CHECK (preocupacion IN ('embargo', 'seguros', 'telecom', 'otro')),
    proposito      varchar(20) CHECK (proposito IN ('autoinformarse', 'asesorar', 'investigar', 'trabajo')),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

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
    rut_empresa    varchar(12),                    -- RUT para ChileCompra (claim/alta)
    creado_en      timestamptz NOT NULL DEFAULT now()
);

-- Métricas estadísticas agregadas y el Índice de Transparencia. Sin textos de reseñas.
CREATE TABLE business_reputation_metrics (
    business_id              uuid PRIMARY KEY REFERENCES business_entities(id) ON DELETE CASCADE,
    google_rating_avg        double precision CHECK (google_rating_avg BETWEEN 0 AND 5),
    google_reviews_count     integer NOT NULL DEFAULT 0 CHECK (google_reviews_count >= 0),
    google_place_nombre      varchar(200),
    sentiment_positive_ratio double precision CHECK (sentiment_positive_ratio BETWEEN 0 AND 1),
    response_time_score      double precision CHECK (response_time_score BETWEEN 0 AND 1),
    -- Índice algorítmico de 1.0 a 10.0, no un juicio de valor sobre la calidad del servicio
    final_score              double precision NOT NULL DEFAULT 1.0 CHECK (final_score BETWEEN 1 AND 10),
    is_verified_profile      boolean NOT NULL DEFAULT false,
    -- Observables ciber/operativa (0–100); null = aún no escaneados
    score_ssl_tls            double precision CHECK (score_ssl_tls IS NULL OR score_ssl_tls BETWEEN 0 AND 100),
    score_email_auth         double precision CHECK (score_email_auth IS NULL OR score_email_auth BETWEEN 0 AND 100),
    score_puertos            double precision CHECK (score_puertos IS NULL OR score_puertos BETWEEN 0 AND 100),
    score_headers_http       double precision CHECK (score_headers_http IS NULL OR score_headers_http BETWEEN 0 AND 100),
    score_stack_vulnerable   double precision CHECK (score_stack_vulnerable IS NULL OR score_stack_vulnerable BETWEEN 0 AND 100),
    score_blacklist          double precision CHECK (score_blacklist IS NULL OR score_blacklist BETWEEN 0 AND 100),
    score_dnssec             double precision CHECK (score_dnssec IS NULL OR score_dnssec BETWEEN 0 AND 100),
    score_subdominios        double precision CHECK (score_subdominios IS NULL OR score_subdominios BETWEEN 0 AND 100),
    score_whois              double precision CHECK (score_whois IS NULL OR score_whois BETWEEN 0 AND 100),
    score_uptime             double precision CHECK (score_uptime IS NULL OR score_uptime BETWEEN 0 AND 100),
    score_cookies            double precision CHECK (score_cookies IS NULL OR score_cookies BETWEEN 0 AND 100),
    score_politica_privacidad double precision CHECK (score_politica_privacidad IS NULL OR score_politica_privacidad BETWEEN 0 AND 100),
    score_terminos           double precision CHECK (score_terminos IS NULL OR score_terminos BETWEEN 0 AND 100),
    score_sla                double precision CHECK (score_sla IS NULL OR score_sla BETWEEN 0 AND 100),
    docs_legales_razones     jsonb,
    score_mercado_publico    double precision CHECK (score_mercado_publico IS NULL OR score_mercado_publico BETWEEN 0 AND 100),
    score_sii                double precision CHECK (score_sii IS NULL OR score_sii BETWEEN 0 AND 100),
    score_cmf                double precision CHECK (score_cmf IS NULL OR score_cmf BETWEEN 0 AND 100),
    score_incidentes         double precision CHECK (score_incidentes IS NULL OR score_incidentes BETWEEN 0 AND 100),
    score_domicilio          double precision CHECK (score_domicilio IS NULL OR score_domicilio BETWEEN 0 AND 100),
    score_huella_digital     double precision CHECK (score_huella_digital IS NULL OR score_huella_digital BETWEEN 0 AND 100),
    score_persona_juridica   double precision CHECK (score_persona_juridica IS NULL OR score_persona_juridica BETWEEN 0 AND 100),
    datalux_razones          jsonb,
    ciber_escaneado_en       timestamptz,
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

-- Índice local CMF Bancos (API api.cmfchile.cl) para el observable cmf.
CREATE TABLE cmf_instituciones (
    rut         varchar(12) PRIMARY KEY,
    codigo      varchar(8) NOT NULL,
    nombre      varchar(200) NOT NULL DEFAULT '',
    direccion   varchar(300),
    web         varchar(200),
    sucursales  integer,
    empleados   integer
);

CREATE TABLE cmf_indice_meta (
    id               integer PRIMARY KEY,
    sincronizado_en  timestamptz,
    filas            integer NOT NULL DEFAULT 0,
    fuente           varchar(200)
);


COMMIT;
