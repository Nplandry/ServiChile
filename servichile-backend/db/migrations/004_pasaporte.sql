

BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS rut varchar(12) UNIQUE CHECK (rut ~ '^[0-9]{1,8}-[0-9K]$'),
    ADD COLUMN IF NOT EXISTS rut_verificado boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS telefono varchar(30);

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
