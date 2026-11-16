-- Documentos legales de empresa verificados (PDF no se retiene; solo metadata).
BEGIN;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS docs_empresa jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMIT;
