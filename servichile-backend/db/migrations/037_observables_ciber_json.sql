

ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS observables_ciber jsonb;
