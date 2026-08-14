-- Applied automatically on first `docker compose up` via /docker-entrypoint-initdb.d

CREATE TABLE IF NOT EXISTS nifty_greeks_realtime (
    id                  BIGSERIAL PRIMARY KEY,
    type                VARCHAR(2) NOT NULL,          -- CE | PE
    strike              DOUBLE PRECISION NOT NULL,
    premium             DOUBLE PRECISION,
    oi                  BIGINT,
    underlying          DOUBLE PRECISION,
    expiry              TEXT,
    time_to_expiry      DOUBLE PRECISION,
    iv                  DOUBLE PRECISION,
    delta               DOUBLE PRECISION,
    gamma               DOUBLE PRECISION,
    theta               DOUBLE PRECISION,
    vega                DOUBLE PRECISION,
    gex                 DOUBLE PRECISION,
    ingestion_timestamp TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nifty_greeks_ts
    ON nifty_greeks_realtime (ingestion_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_nifty_greeks_strike
    ON nifty_greeks_realtime (strike);

CREATE INDEX IF NOT EXISTS idx_nifty_greeks_type_ts
    ON nifty_greeks_realtime (type, ingestion_timestamp DESC);
