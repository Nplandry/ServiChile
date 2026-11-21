
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_persona_juridica double precision;

ALTER TABLE business_reputation_metrics
    DROP CONSTRAINT IF EXISTS business_reputation_metrics_score_persona_juridica_check;

ALTER TABLE business_reputation_metrics
    ADD CONSTRAINT business_reputation_metrics_score_persona_juridica_check
    CHECK (score_persona_juridica IS NULL OR score_persona_juridica BETWEEN 0 AND 100);
