
BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS biometria_verificada boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS biometria_verificada_en timestamptz;

COMMIT;
