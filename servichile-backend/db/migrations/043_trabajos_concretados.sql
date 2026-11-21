

ALTER TABLE reservas RENAME TO trabajos;

ALTER TABLE trabajos RENAME CONSTRAINT reservas_pkey TO trabajos_pkey;
ALTER TABLE trabajos RENAME CONSTRAINT reservas_usuario_id_fkey TO trabajos_usuario_id_fkey;
ALTER TABLE trabajos RENAME CONSTRAINT reservas_business_id_fkey TO trabajos_business_id_fkey;
ALTER INDEX IF EXISTS reservas_usuario_idx RENAME TO trabajos_usuario_idx;
ALTER INDEX IF EXISTS reservas_negocio_idx RENAME TO trabajos_negocio_idx;
ALTER INDEX IF EXISTS reservas_qr_token_key RENAME TO trabajos_qr_token_key;

ALTER TABLE trabajos DROP CONSTRAINT IF EXISTS reservas_estado_check;
ALTER TABLE trabajos DROP CONSTRAINT IF EXISTS trabajos_estado_check;

UPDATE trabajos SET estado = 'abierto' WHERE estado = 'reservada';
UPDATE trabajos SET estado = 'concretado' WHERE estado = 'asistido';
UPDATE trabajos SET estado = 'no_concretado' WHERE estado = 'no_show';
UPDATE trabajos SET estado = 'cancelado' WHERE estado = 'cancelada';

ALTER TABLE trabajos ALTER COLUMN estado SET DEFAULT 'abierto';
ALTER TABLE trabajos
    ADD CONSTRAINT trabajos_estado_check
    CHECK (estado IN ('abierto', 'concretado', 'no_concretado', 'cancelado'));
