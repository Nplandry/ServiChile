
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_pades boolean NOT NULL DEFAULT false;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_entidad_emisora text;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_fecha_emision date;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_sha256 text;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_glosa text;
