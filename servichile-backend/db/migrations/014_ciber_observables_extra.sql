
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_email_auth double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_puertos double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_stack_vulnerable double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_dnssec double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_subdominios double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_uptime double precision;
