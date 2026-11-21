

BEGIN;

CREATE TABLE IF NOT EXISTS perfiles (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    
    edad           smallint CHECK (edad BETWEEN 14 AND 120),
    preocupacion   varchar(20) CHECK (preocupacion IN ('embargo', 'seguros', 'telecom', 'otro')),
    proposito      varchar(20) CHECK (proposito IN ('autoinformarse', 'asesorar', 'investigar', 'trabajo')),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

COMMIT;
