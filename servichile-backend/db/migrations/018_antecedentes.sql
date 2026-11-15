ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_verificados boolean NOT NULL DEFAULT false;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_verificados_en timestamptz;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_anotaciones boolean;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS antecedentes_score integer;
