
CREATE TABLE IF NOT EXISTS records (
    id UUID PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE records ADD COLUMN name TEXT;
UPDATE records SET name = data ->> 'name' WHERE name IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS records_name_idx ON records (name);

