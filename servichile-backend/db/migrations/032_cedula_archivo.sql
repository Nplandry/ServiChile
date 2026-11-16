-- Foto frontal de cédula: metadata en Postgres; bytes en filesystem local.
BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS cedula_verificada boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS cedula_verificada_en timestamptz,
    ADD COLUMN IF NOT EXISTS cedula_ruta varchar(260),
    ADD COLUMN IF NOT EXISTS cedula_sha256 varchar(64),
    ADD COLUMN IF NOT EXISTS cedula_bytes integer,
    ADD COLUMN IF NOT EXISTS cedula_ancho integer,
    ADD COLUMN IF NOT EXISTS cedula_alto integer,
    ADD COLUMN IF NOT EXISTS cedula_content_type varchar(40),
    ADD COLUMN IF NOT EXISTS cedula_retener_hasta timestamptz,
    ADD COLUMN IF NOT EXISTS cedula_score integer,
    ADD COLUMN IF NOT EXISTS cedula_rut_ocr varchar(12);

COMMIT;
