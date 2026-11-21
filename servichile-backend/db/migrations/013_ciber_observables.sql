
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_ssl_tls double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_headers_http double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_blacklist double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_whois double precision;
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS ciber_escaneado_en timestamptz;
