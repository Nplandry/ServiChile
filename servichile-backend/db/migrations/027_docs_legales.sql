
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_politica_privacidad double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_terminos double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_sla double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS docs_legales_razones jsonb;
