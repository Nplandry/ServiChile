

CREATE TABLE IF NOT EXISTS compras_informe (
    id UUID PRIMARY KEY,
    usuario_id UUID NOT NULL,
    business_id UUID NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_compras_informe_token ON compras_informe (token);
CREATE INDEX IF NOT EXISTS idx_compras_informe_usuario ON compras_informe (usuario_id, creado_en DESC);
