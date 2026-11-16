-- Indice documental: final_score puede ser 0.0 (antes el check exigia >= 1).
ALTER TABLE business_reputation_metrics
    DROP CONSTRAINT IF EXISTS business_reputation_metrics_final_score_check;

ALTER TABLE business_reputation_metrics
    ADD CONSTRAINT business_reputation_metrics_final_score_check
    CHECK (final_score BETWEEN 0 AND 10);
