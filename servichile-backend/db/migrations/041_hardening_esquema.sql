

CREATE INDEX IF NOT EXISTS business_entities_categoria_nombre_idx
    ON business_entities (categoria, nombre);

CREATE INDEX IF NOT EXISTS business_entities_reclamado_por_idx
    ON business_entities (reclamado_por);

ALTER TABLE business_reputation_metrics
    ALTER COLUMN final_score SET DEFAULT 0.0;

ALTER TABLE business_entities
    DROP CONSTRAINT IF EXISTS business_entities_rut_empresa_check;

ALTER TABLE business_entities
    ADD CONSTRAINT business_entities_rut_empresa_check
    CHECK (rut_empresa IS NULL OR rut_empresa ~ '^[0-9]{1,8}-[0-9K]$');

CREATE UNIQUE INDEX IF NOT EXISTS business_entities_rut_empresa_uidx
    ON business_entities (rut_empresa)
    WHERE rut_empresa IS NOT NULL;

UPDATE pades_document_hashes p
SET usuario_id = NULL
WHERE usuario_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM usuarios u WHERE u.id = p.usuario_id);

UPDATE pades_document_hashes p
SET business_id = NULL
WHERE business_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM business_entities b WHERE b.id = p.business_id);

ALTER TABLE pades_document_hashes
    DROP CONSTRAINT IF EXISTS pades_document_hashes_usuario_id_fkey;

ALTER TABLE pades_document_hashes
    DROP CONSTRAINT IF EXISTS pades_document_hashes_business_id_fkey;

ALTER TABLE pades_document_hashes
    ADD CONSTRAINT pades_document_hashes_usuario_id_fkey
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;

ALTER TABLE pades_document_hashes
    ADD CONSTRAINT pades_document_hashes_business_id_fkey
    FOREIGN KEY (business_id) REFERENCES business_entities(id) ON DELETE SET NULL;
