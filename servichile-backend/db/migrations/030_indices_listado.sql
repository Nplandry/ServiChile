
BEGIN;

CREATE INDEX IF NOT EXISTS business_entities_categoria_nombre_idx
  ON business_entities (categoria, nombre);

CREATE INDEX IF NOT EXISTS business_entities_reclamado_por_idx
  ON business_entities (reclamado_por);

COMMIT;
