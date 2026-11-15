-- Consentimiento de cookies / CMP detectado en HTML del sitio.
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_cookies double precision;
