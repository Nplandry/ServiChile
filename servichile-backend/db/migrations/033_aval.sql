
BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS aval_verificado boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS aval_verificado_en timestamptz,
    ADD COLUMN IF NOT EXISTS aval_score integer,
    ADD COLUMN IF NOT EXISTS aval_tipo varchar(20),
    ADD COLUMN IF NOT EXISTS aval_gemini_usado boolean NOT NULL DEFAULT false;

COMMIT;
