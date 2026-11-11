-- Migración 006: imagen y logo del negocio para el marketplace.
-- Uso en una base existente (después de 005):
--   psql "postgresql://USUARIO@HOST:5432/servichile" -v ON_ERROR_STOP=1 -f db/migrations/006_marketplace_media.sql
-- Las bases nuevas lo reciben desde db/init_script.sql.

BEGIN;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS imagen_url varchar(500),
    ADD COLUMN IF NOT EXISTS logo_url varchar(500);

COMMIT;
