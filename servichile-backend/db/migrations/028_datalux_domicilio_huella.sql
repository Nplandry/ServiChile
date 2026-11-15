-- Observables DataLux: domicilio y huella digital (base 50, match 100, peso 2%).
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_domicilio double precision;

ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_huella_digital double precision;

ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS datalux_razones jsonb;

ALTER TABLE business_reputation_metrics
    DROP CONSTRAINT IF EXISTS business_reputation_metrics_score_domicilio_check;

ALTER TABLE business_reputation_metrics
    ADD CONSTRAINT business_reputation_metrics_score_domicilio_check
    CHECK (score_domicilio IS NULL OR score_domicilio BETWEEN 0 AND 100);

ALTER TABLE business_reputation_metrics
    DROP CONSTRAINT IF EXISTS business_reputation_metrics_score_huella_digital_check;

ALTER TABLE business_reputation_metrics
    ADD CONSTRAINT business_reputation_metrics_score_huella_digital_check
    CHECK (score_huella_digital IS NULL OR score_huella_digital BETWEEN 0 AND 100);
