-- Migración 004: Pasaporte de Confianza.
-- Agrega RUT verificado y teléfono al usuario, reservas (nivel 1) y resultados de arriendo (nivel 2).
-- Las columnas preocupacion y proposito NO se eliminan aquí: quedan nullable durante la transición.
-- Uso en una base existente (después de 003):
--   psql "postgresql://USUARIO@HOST:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/004_pasaporte.sql
-- Las bases nuevas lo reciben desde db/init_script.sql.

BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS rut varchar(12) UNIQUE CHECK (rut ~ '^[0-9]{1,8}-[0-9K]$'),
    ADD COLUMN IF NOT EXISTS rut_verificado boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS telefono varchar(30);

-- Transición: los campos del perfil antiguo siguen existiendo y pueden ser null.
ALTER TABLE perfiles ALTER COLUMN preocupacion DROP NOT NULL;
ALTER TABLE perfiles ALTER COLUMN proposito DROP NOT NULL;

CREATE TABLE IF NOT EXISTS reservas (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id    uuid NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    estado         varchar(20) NOT NULL DEFAULT 'reservada'
                     CHECK (estado IN ('reservada', 'asistido', 'no_show', 'cancelada')),
    qr_token       varchar(64) NOT NULL UNIQUE,
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reservas_usuario_idx ON reservas (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS reservas_negocio_idx ON reservas (business_id);

CREATE TABLE IF NOT EXISTS pasaporte_arriendo (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estado         varchar(20) NOT NULL
                     CHECK (estado IN ('pendiente', 'verificado', 'rechazado')),
    score          smallint CHECK (score BETWEEN 0 AND 1000),
    verificado_en  timestamptz,
    creado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS pasaporte_arriendo_usuario_idx ON pasaporte_arriendo (usuario_id, creado_en DESC);

COMMIT;
