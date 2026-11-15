-- Situación tributaria SII (ApiGateway Info. Contribuyentes).
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_sii double precision;
