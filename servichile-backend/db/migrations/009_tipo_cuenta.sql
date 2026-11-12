-- Tipo de cuenta del onboarding: persona natural o empresa.
BEGIN;

ALTER TABLE perfiles
    ADD COLUMN IF NOT EXISTS tipo_cuenta varchar(20);

ALTER TABLE perfiles
    DROP CONSTRAINT IF EXISTS perfiles_tipo_cuenta_check;

ALTER TABLE perfiles
    ADD CONSTRAINT perfiles_tipo_cuenta_check
    CHECK (tipo_cuenta IS NULL OR tipo_cuenta IN ('persona', 'empresa'));

-- Permisos para el rol de la app (si existe).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'servicia') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE usuario_xp_eventos TO servicia;
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE perfiles TO servicia;
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE usuarios TO servicia;
    END IF;
END $$;

COMMIT;
