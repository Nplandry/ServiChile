-- Migración 005: campos de marketplace geolocalizado en los comercios.
-- Agrega dirección, descripción, nivel requerido y amplía las categorías.
-- Uso en una base existente (después de 004):
--   psql "postgresql://USUARIO@HOST:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/005_marketplace.sql
-- Las bases nuevas lo reciben desde db/init_script.sql.

BEGIN;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS direccion varchar(200),
    ADD COLUMN IF NOT EXISTS descripcion text,
    ADD COLUMN IF NOT EXISTS requiere_nivel smallint NOT NULL DEFAULT 1;

ALTER TABLE business_entities DROP CONSTRAINT IF EXISTS business_entities_requiere_nivel_check;
ALTER TABLE business_entities
    ADD CONSTRAINT business_entities_requiere_nivel_check CHECK (requiere_nivel IN (1, 2));

-- Ampliar las categorías permitidas (agrega 'arriendo' y 'evento').
ALTER TABLE business_entities DROP CONSTRAINT IF EXISTS business_entities_categoria_check;
ALTER TABLE business_entities
    ADD CONSTRAINT business_entities_categoria_check
    CHECK (categoria IN ('gimnasio', 'clinica-dental', 'comercio', 'restaurante',
                         'automotriz', 'arriendo', 'evento', 'otro'));

COMMIT;
