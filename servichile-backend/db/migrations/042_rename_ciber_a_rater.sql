-- Vocabulario rater (deja de llamarse "ciber").

ALTER TABLE business_reputation_metrics
    RENAME COLUMN ciber_escaneado_en TO rater_escaneado_en;

ALTER TABLE business_reputation_metrics
    RENAME COLUMN observables_ciber TO observables;
