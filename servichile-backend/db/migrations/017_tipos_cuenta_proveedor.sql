-- Tipos de cuenta: persona | contratista | proveedor
-- proveedor = antigua empresa; contratista y persona comparten funcionalidad.

ALTER TABLE perfiles
    DROP CONSTRAINT IF EXISTS perfiles_tipo_cuenta_check;

UPDATE perfiles
SET tipo_cuenta = 'proveedor'
WHERE tipo_cuenta = 'empresa';

ALTER TABLE perfiles
    ADD CONSTRAINT perfiles_tipo_cuenta_check
    CHECK (tipo_cuenta IS NULL OR tipo_cuenta IN ('persona', 'contratista', 'proveedor'));
