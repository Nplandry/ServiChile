
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_incidentes double precision;

ALTER TABLE business_reputation_metrics
    DROP CONSTRAINT IF EXISTS business_reputation_metrics_score_incidentes_check;

ALTER TABLE business_reputation_metrics
    ADD CONSTRAINT business_reputation_metrics_score_incidentes_check
    CHECK (score_incidentes IS NULL OR score_incidentes BETWEEN 0 AND 100);
