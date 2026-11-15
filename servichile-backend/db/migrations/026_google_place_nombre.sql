ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS google_place_nombre varchar(200);
