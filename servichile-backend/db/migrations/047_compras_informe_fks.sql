

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compras_informe_usuario_id_fkey'
  ) THEN
    ALTER TABLE compras_informe
      ADD CONSTRAINT compras_informe_usuario_id_fkey
      FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
  END IF;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para FK usuario_id en compras_informe';
  WHEN undefined_table THEN
    RAISE NOTICE 'Tabla referenciada ausente (usuarios)';
  WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compras_informe_business_id_fkey'
  ) THEN
    ALTER TABLE compras_informe
      ADD CONSTRAINT compras_informe_business_id_fkey
      FOREIGN KEY (business_id) REFERENCES business_entities(id) ON DELETE CASCADE;
  END IF;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para FK business_id en compras_informe';
  WHEN undefined_table THEN
    RAISE NOTICE 'Tabla referenciada ausente (business_entities)';
  WHEN duplicate_object THEN
    NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_compras_informe_autorizada
  ON compras_informe (usuario_id, business_id, estado);
