CREATE TABLE IF NOT EXISTS correo_oauth (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    email          varchar(254) NOT NULL,
    refresh_token  text NOT NULL,
    access_token   text,
    expira_en      timestamptz,
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mensajes_correo (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id   uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id  uuid REFERENCES business_entities(id) ON DELETE SET NULL,
    tipo         varchar(20) NOT NULL,
    destino      varchar(254) NOT NULL,
    asunto       varchar(200) NOT NULL,
    cuerpo       text NOT NULL,
    estado       varchar(20) NOT NULL,
    creado_en    timestamptz NOT NULL DEFAULT now()
);
