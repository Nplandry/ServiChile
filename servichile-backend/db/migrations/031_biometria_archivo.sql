
BEGIN;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS biometria_ruta varchar(260),
    ADD COLUMN IF NOT EXISTS biometria_sha256 varchar(64),
    ADD COLUMN IF NOT EXISTS biometria_bytes integer,
    ADD COLUMN IF NOT EXISTS biometria_ancho integer,
    ADD COLUMN IF NOT EXISTS biometria_alto integer,
    ADD COLUMN IF NOT EXISTS biometria_content_type varchar(40),
    ADD COLUMN IF NOT EXISTS biometria_retener_hasta timestamptz;

COMMIT;
