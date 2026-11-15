-- Índice local CMF Bancos + score observable cmf.
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS score_cmf double precision;

CREATE TABLE IF NOT EXISTS cmf_instituciones (
    rut         varchar(12) PRIMARY KEY,
    codigo      varchar(8) NOT NULL,
    nombre      varchar(200) NOT NULL DEFAULT '',
    direccion   varchar(300),
    web         varchar(200),
    sucursales  integer,
    empleados   integer
);

CREATE TABLE IF NOT EXISTS cmf_indice_meta (
    id               integer PRIMARY KEY,
    sincronizado_en  timestamptz,
    filas            integer NOT NULL DEFAULT 0,
    fuente           varchar(200)
);
