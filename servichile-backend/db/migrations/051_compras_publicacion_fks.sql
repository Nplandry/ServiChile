-- FKs de compras_publicacion (espejo 047 informe).
-- Si el rol no es owner de usuarios/business_entities, el ALTER fallará:
-- ejecutar como superuser o owner de esas tablas.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compras_publicacion_usuario_id_fkey'
  ) THEN
    ALTER TABLE compras_publicacion
      ADD CONSTRAINT compras_publicacion_usuario_id_fkey
      FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
  END IF;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para FK usuario_id en compras_publicacion';
  WHEN undefined_table THEN
    RAISE NOTICE 'Tabla referenciada ausente (usuarios)';
  WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compras_publicacion_business_id_fkey'
  ) THEN
    ALTER TABLE compras_publicacion
      ADD CONSTRAINT compras_publicacion_business_id_fkey
      FOREIGN KEY (business_id) REFERENCES business_entities(id) ON DELETE SET NULL;
  END IF;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para FK business_id en compras_publicacion';
  WHEN undefined_table THEN
    RAISE NOTICE 'Tabla referenciada ausente (business_entities)';
  WHEN duplicate_object THEN
    NULL;
END $$;

-- Estado 'consumido' evita reciclar el cupón si business_id queda NULL al borrar la ficha.
CREATE INDEX IF NOT EXISTS idx_compras_publicacion_cupon
  ON compras_publicacion (usuario_id, estado)
  WHERE business_id IS NULL;
