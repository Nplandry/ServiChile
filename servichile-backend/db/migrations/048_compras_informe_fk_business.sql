

DO $$
BEGIN
  BEGIN
    EXECUTE 'GRANT REFERENCES ON TABLE business_entities TO servichile';
  EXCEPTION
    WHEN insufficient_privilege THEN
      RAISE NOTICE 'No se pudo GRANT REFERENCES a servichile (continúa si ya tiene)';
    WHEN undefined_object THEN
      RAISE NOTICE 'Rol servichile ausente';
  END;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compras_informe_business_id_fkey'
  ) THEN
    ALTER TABLE compras_informe
      ADD CONSTRAINT compras_informe_business_id_fkey
      FOREIGN KEY (business_id) REFERENCES business_entities(id) ON DELETE CASCADE;
  END IF;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para FK business_id; ejecute como owner de business_entities';
  WHEN duplicate_object THEN
    NULL;
END $$;
