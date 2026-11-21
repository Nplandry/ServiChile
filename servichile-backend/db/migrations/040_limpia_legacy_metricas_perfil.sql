

ALTER TABLE business_reputation_metrics
    DROP COLUMN IF EXISTS google_place_nombre,
    DROP COLUMN IF EXISTS sentiment_positive_ratio,
    DROP COLUMN IF EXISTS response_time_score,
    DROP COLUMN IF EXISTS score_ssl_tls,
    DROP COLUMN IF EXISTS score_email_auth,
    DROP COLUMN IF EXISTS score_puertos,
    DROP COLUMN IF EXISTS score_headers_http,
    DROP COLUMN IF EXISTS score_stack_vulnerable,
    DROP COLUMN IF EXISTS score_blacklist,
    DROP COLUMN IF EXISTS score_dnssec,
    DROP COLUMN IF EXISTS score_subdominios,
    DROP COLUMN IF EXISTS score_whois,
    DROP COLUMN IF EXISTS score_uptime,
    DROP COLUMN IF EXISTS score_cookies,
    DROP COLUMN IF EXISTS score_politica_privacidad,
    DROP COLUMN IF EXISTS score_terminos,
    DROP COLUMN IF EXISTS score_sla,
    DROP COLUMN IF EXISTS docs_legales_razones,
    DROP COLUMN IF EXISTS score_mercado_publico,
    DROP COLUMN IF EXISTS score_sii,
    DROP COLUMN IF EXISTS score_cmf,
    DROP COLUMN IF EXISTS score_incidentes,
    DROP COLUMN IF EXISTS incidentes_razones,
    DROP COLUMN IF EXISTS score_domicilio,
    DROP COLUMN IF EXISTS score_huella_digital,
    DROP COLUMN IF EXISTS score_persona_juridica,
    DROP COLUMN IF EXISTS datalux_razones;

ALTER TABLE perfiles
    DROP COLUMN IF EXISTS preocupacion,
    DROP COLUMN IF EXISTS proposito;

ALTER TABLE usuarios
    DROP COLUMN IF EXISTS aval_gemini_usado;

DROP TABLE IF EXISTS cmf_instituciones;
DROP TABLE IF EXISTS cmf_indice_meta;
