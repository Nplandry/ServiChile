

BEGIN;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS imagen_url varchar(500),
    ADD COLUMN IF NOT EXISTS logo_url varchar(500);

COMMIT;
