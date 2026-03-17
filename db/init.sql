-- Schema für Trader-Projekt

-- Tabelle: kurse
CREATE TABLE IF NOT EXISTS kurse (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL,
    aktie       VARCHAR(20) NOT NULL,
    wert        NUMERIC(18, 6) NOT NULL,
    CONSTRAINT uq_kurse_aktie_timestamp UNIQUE (aktie, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_kurse_aktie_timestamp ON kurse (aktie, timestamp DESC);

-- Tabelle: trades
CREATE TABLE IF NOT EXISTS trades (
    id                      BIGSERIAL PRIMARY KEY,
    aktie                   VARCHAR(20) NOT NULL,
    richtung                VARCHAR(5) NOT NULL CHECK (richtung IN ('long', 'short')),
    eroeffnet_at            TIMESTAMPTZ NOT NULL,
    einstiegskurs           NUMERIC(12, 6),
    geschlossen_at          TIMESTAMPTZ,
    schliessgrund           VARCHAR(20) CHECK (schliessgrund IN ('stop_loss', 'take_profit', 'timeout')),
    einsatz_eur             NUMERIC(10, 2) NOT NULL DEFAULT 100.00,
    gebuehr_eroeffnung_eur  NUMERIC(10, 4) NOT NULL,
    gebuehr_schliessung_eur NUMERIC(10, 4),
    ergebnis_eur            NUMERIC(10, 4),
    reward                  NUMERIC(5, 4),
    entry_features          TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_aktie ON trades (aktie);
CREATE INDEX IF NOT EXISTS idx_trades_eroeffnet_at ON trades (eroeffnet_at DESC);

-- Tabelle: empfehlungen (KNN-Ausgabe je Takt)
CREATE TABLE IF NOT EXISTS empfehlungen (
    id        BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aktie     VARCHAR(20) NOT NULL,
    richtung  VARCHAR(5)  NOT NULL CHECK (richtung IN ('long', 'short')),
    knn_wert  NUMERIC(8, 6) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_empfehlungen_timestamp ON empfehlungen (timestamp DESC);

-- Aggregierte View: statistik
CREATE OR REPLACE VIEW statistik AS
SELECT
    aktie,
    COUNT(*)                                                        AS trades_gesamt,
    COUNT(*) FILTER (WHERE ergebnis_eur > 0)                       AS trades_gewinn,
    COUNT(*) FILTER (WHERE ergebnis_eur <= 0)                      AS trades_verlust,
    ROUND(SUM(ergebnis_eur), 2)                                    AS gesamtergebnis_eur,
    ROUND(SUM(ergebnis_eur) FILTER (WHERE ergebnis_eur > 0), 2)   AS gesamtgewinn_eur,
    ROUND(SUM(ergebnis_eur) FILTER (WHERE ergebnis_eur <= 0), 2)  AS gesamtverlust_eur,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE ergebnis_eur > 0)
        / NULLIF(COUNT(*), 0),
        2
    )                                                               AS trefferquote_pct,
    ROUND(AVG(ergebnis_eur), 4)                                    AS durchschnitt_eur
FROM trades
WHERE geschlossen_at IS NOT NULL
GROUP BY aktie;
