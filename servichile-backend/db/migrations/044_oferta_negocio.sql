-- Oferta declarada por el proveedor (no entra al índice de transparencia).

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS servicios jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS industrias jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS contrataciones jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS monto varchar(20);

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS plazo varchar(20);

ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS referencias jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE business_entities DROP CONSTRAINT IF EXISTS business_entities_monto_check;
ALTER TABLE business_entities
    ADD CONSTRAINT business_entities_monto_check
    CHECK (monto IS NULL OR monto IN ('bajo', 'medio', 'alto'));

ALTER TABLE business_entities DROP CONSTRAINT IF EXISTS business_entities_plazo_check;
ALTER TABLE business_entities
    ADD CONSTRAINT business_entities_plazo_check
    CHECK (plazo IS NULL OR plazo IN ('menos-2h', 'en-el-dia', '24-48h'));
