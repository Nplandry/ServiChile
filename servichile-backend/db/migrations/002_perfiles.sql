-- Migración 002: perfil del usuario (datos del onboarding).
-- Uso en una base existente:
--   psql "postgresql://USUARIO@HOST:5432/servicia" -v ON_ERROR_STOP=1 -f db/migrations/002_perfiles.sql
-- Las bases nuevas lo reciben desde db/init_script.sql.

BEGIN;

-- Separado de usuarios: credenciales en una tabla, datos personales del perfil en otra.
CREATE TABLE IF NOT EXISTS perfiles (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Ley 21.719: menores de 14 requieren consentimiento de sus padres, que la app no gestiona
    edad           smallint CHECK (edad BETWEEN 14 AND 120),
    preocupacion   varchar(20) CHECK (preocupacion IN ('embargo', 'seguros', 'telecom', 'otro')),
    proposito      varchar(20) CHECK (proposito IN ('autoinformarse', 'asesorar', 'investigar', 'trabajo')),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

COMMIT;
