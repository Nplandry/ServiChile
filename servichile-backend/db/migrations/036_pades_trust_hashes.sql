-- Anti-replay PAdES: un mismo PDF (sha256) no puede reutilizarse.
CREATE TABLE IF NOT EXISTS pades_document_hashes (
    sha256 text PRIMARY KEY,
    scope text NOT NULL,
    tipo text,
    usuario_id uuid,
    business_id uuid,
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pades_hashes_business
    ON pades_document_hashes (business_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_antecedentes_sha256
    ON usuarios (antecedentes_sha256)
    WHERE antecedentes_sha256 IS NOT NULL;

-- Rol de la app (si existe): la tabla a menudo se crea como superusuario/peer.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'servichile') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pades_document_hashes TO servichile;
    END IF;
END $$;
