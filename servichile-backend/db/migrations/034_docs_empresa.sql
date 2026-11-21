
BEGIN;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS docs_empresa jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMIT;
