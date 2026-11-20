-- Cupón Webpay para publicar ficha de empresa ($8.990).
-- business_id queda NULL hasta consumir el alta (POST /v1/businesses).
CREATE TABLE IF NOT EXISTS compras_publicacion (
    id UUID PRIMARY KEY,
    usuario_id UUID NOT NULL,
    business_id UUID,
    buy_order VARCHAR(26) NOT NULL UNIQUE,
    monto INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    token VARCHAR(128),
    response_code INTEGER,
    authorization_code VARCHAR(32),
    payment_type_code VARCHAR(16),
    card_last4 VARCHAR(4),
    error_codigo VARCHAR(64),
    error_detalle TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compras_publicacion_token
  ON compras_publicacion (token);
CREATE INDEX IF NOT EXISTS idx_compras_publicacion_usuario
  ON compras_publicacion (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_compras_publicacion_cupon
  ON compras_publicacion (usuario_id, estado)
  WHERE business_id IS NULL;

-- Una sola autorizada sin consumir por usuario (cupón libre).
CREATE UNIQUE INDEX IF NOT EXISTS uq_compras_publicacion_cupon_libre
  ON compras_publicacion (usuario_id)
  WHERE estado = 'autorizado' AND business_id IS NULL;
