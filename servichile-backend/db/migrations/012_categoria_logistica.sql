-- Categoría Transporte, Logística y Última Milla (flotas, courier B2B, bodegaje).
ALTER TABLE business_entities
  DROP CONSTRAINT IF EXISTS business_entities_categoria_check;

ALTER TABLE business_entities
  ADD CONSTRAINT business_entities_categoria_check
  CHECK (categoria IN (
    'tecnologia',
    'industria',
    'construccion',
    'servicios-profesionales',
    'logistica'
  ));
