-- Categorías del directorio B2B (transparencia / due diligence de proveedores).
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
