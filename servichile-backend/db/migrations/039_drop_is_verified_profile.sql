-- Verificacion de empresa eliminada del producto.
ALTER TABLE business_reputation_metrics
    DROP COLUMN IF EXISTS is_verified_profile;
