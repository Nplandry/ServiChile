-- Una sola compra autorizada por (usuario, negocio).
-- Antes de crear el índice único parcial, conserva la más reciente.

DELETE FROM compras_informe a
USING compras_informe b
WHERE a.estado = 'autorizado'
  AND b.estado = 'autorizado'
  AND a.usuario_id = b.usuario_id
  AND a.business_id = b.business_id
  AND a.creado_en < b.creado_en;

CREATE UNIQUE INDEX IF NOT EXISTS uq_compras_informe_autorizada
  ON compras_informe (usuario_id, business_id)
  WHERE estado = 'autorizado';
