

BEGIN;

CREATE TABLE IF NOT EXISTS business_entities (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         varchar(160) NOT NULL,
    categoria      varchar(30) NOT NULL
                     CHECK (categoria IN ('gimnasio', 'clinica-dental', 'comercio', 'restaurante', 'automotriz', 'otro')),
    latitud        double precision,
    longitud       double precision,
    external_ref   varchar(200) UNIQUE,            
    is_claimed     boolean NOT NULL DEFAULT false, 
    reclamado_por  uuid REFERENCES usuarios(id) ON DELETE SET NULL,
    telefono       varchar(30),
    sitio_web      varchar(200),
    creado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_reputation_metrics (
    business_id              uuid PRIMARY KEY REFERENCES business_entities(id) ON DELETE CASCADE,
    google_rating_avg        double precision CHECK (google_rating_avg BETWEEN 0 AND 5),
    google_reviews_count     integer NOT NULL DEFAULT 0 CHECK (google_reviews_count >= 0),
    sentiment_positive_ratio double precision CHECK (sentiment_positive_ratio BETWEEN 0 AND 1),
    response_time_score      double precision CHECK (response_time_score BETWEEN 0 AND 1),
    
    final_score              double precision NOT NULL DEFAULT 1.0 CHECK (final_score BETWEEN 0 AND 10),
    actualizado_en           timestamptz NOT NULL DEFAULT now()
);

COMMIT;
