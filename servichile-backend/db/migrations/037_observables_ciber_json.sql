-- Snapshot del rater (cabeceras, Places, ChileCompra, etc.) persistido.
-- Se calcula al crear la empresa y se refresca en background cada ~30 min.
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS observables_ciber jsonb;
