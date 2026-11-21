
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS incidentes_razones jsonb;
