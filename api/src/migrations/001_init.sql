CREATE TABLE IF NOT EXISTS predictions (
  id SERIAL PRIMARY KEY,
  original_filename   TEXT NOT NULL,
  image_path           TEXT NOT NULL,
  heatmap_path          TEXT,
  boxed_path             TEXT,
  status                  TEXT NOT NULL,           -- 'ok' | 'rejected'
  message                 TEXT,
  predicted_class        TEXT,
  confidence               REAL,
  top2_class              TEXT,
  top2_confidence          REAL,
  is_low_confidence        BOOLEAN NOT NULL DEFAULT FALSE,
  diagnosis_note           TEXT,
  uncertainty_warning       TEXT,
  all_confidences           JSONB,
  lesions                    JSONB,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);
