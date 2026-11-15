-- Razones breves del observable de incidentes (títulos / resumen para el reporte).
ALTER TABLE business_reputation_metrics
    ADD COLUMN IF NOT EXISTS incidentes_razones jsonb;
