-- RUT empresa para consulta ChileCompra (claim / alta).
ALTER TABLE business_entities
    ADD COLUMN IF NOT EXISTS rut_empresa varchar(12);
