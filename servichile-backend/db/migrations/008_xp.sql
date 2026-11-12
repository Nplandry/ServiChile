-- Experiencia (XP) del Pasaporte: total en usuario + log idempotente de eventos.
BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS xp integer NOT NULL DEFAULT 0 CHECK (xp >= 0);

CREATE TABLE IF NOT EXISTS usuario_xp_eventos (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento      varchar(80) NOT NULL,
    puntos      integer NOT NULL CHECK (puntos > 0),
    creado_en   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, evento)
);

CREATE INDEX IF NOT EXISTS usuario_xp_eventos_usuario_idx
    ON usuario_xp_eventos (usuario_id, creado_en DESC);

COMMIT;
