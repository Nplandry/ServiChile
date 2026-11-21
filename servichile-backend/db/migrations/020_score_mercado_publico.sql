
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_mercado_publico double precision;
