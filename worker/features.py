"""
Feature Engineering – Phase 3

Für jeden 5-Minuten-Takt werden drei normalisierte Deltas je Aktie berechnet:
  delta_5m  – Kursveränderung der letzten  5 Minuten
  delta_20m – Kursveränderung der letzten 20 Minuten
  delta_60m – Kursveränderung der letzten 60 Minuten

Normalisierung: Min-Max auf [-1, 1] über ein rollendes 7-Tage-Fenster.
  +1 → stärkstes Steigen im Fenster
  -1 → stärkstes Fallen im Fenster
   0 → keine Veränderung

Ausgabe: NumPy-Tensor shape (N_tickers, 3), dtype float32 – direkt als
         PyTorch-Eingabe verwendbar (Phase 4).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import text

from db import engine
from tickers import TICKERS

logger = logging.getLogger(__name__)

WINDOW_DAYS = 7  # Länge des Normalisierungsfensters


@dataclass
class FeatureVector:
    aktie: str
    delta_5m: float
    delta_20m: float
    delta_60m: float


def _load_prices(tickers: list[str], days: int = WINDOW_DAYS + 1) -> dict[str, pd.Series]:
    """Lädt alle Kurse der letzten `days` Tage je Ticker aus der DB."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = text("""
        SELECT aktie, timestamp, wert
        FROM kurse
        WHERE aktie = ANY(:tickers)
          AND timestamp >= :since
        ORDER BY aktie, timestamp
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"tickers": list(tickers), "since": since}).fetchall()

    grouped: dict[str, list[tuple]] = {}
    for aktie, ts, wert in rows:
        grouped.setdefault(aktie, []).append((ts, float(wert)))

    return {
        aktie: pd.Series(
            [w for _, w in vals],
            index=pd.DatetimeIndex([t for t, _ in vals], tz="UTC"),
            name=aktie,
        )
        for aktie, vals in grouped.items()
    }


def _delta_normalized(prices: pd.Series, periods: int) -> pd.Series:
    """
    Berechnet (price_now - price_N_periods_ago) für alle Zeitpunkte
    und normalisiert das Ergebnis per Min-Max auf [-1, 1].

    `periods` entspricht der Anzahl 5-Min-Schritte:
      1 → 5 min, 4 → 20 min, 12 → 60 min
    """
    raw = (prices - prices.shift(periods)).dropna()
    if len(raw) == 0:
        return pd.Series(dtype=float)
    mn, mx = raw.min(), raw.max()
    if mx == mn:
        # Alle Deltas identisch → kein Trend erkennbar → 0
        return pd.Series(0.0, index=raw.index)
    return 2.0 * (raw - mn) / (mx - mn) - 1.0


def compute_features(tickers: list[str] = TICKERS) -> list[FeatureVector]:
    """
    Berechnet den normalisierten Feature-Vektor [delta_5m, delta_20m, delta_60m]
    für jeden Ticker auf Basis der letzten 7 Tage.

    Ticker ohne ausreichende Datenlage erhalten einen Nullvektor [0, 0, 0].
    """
    prices_map = _load_prices(tickers)
    vectors: list[FeatureVector] = []

    for ticker in tickers:
        series = prices_map.get(ticker)

        # Mindestens 13 Datenpunkte nötig: 12 Perioden Shift + 1 aktueller Wert
        if series is None or len(series) < 13:
            logger.debug("Zu wenig Daten für %s – Nullvektor.", ticker)
            vectors.append(FeatureVector(ticker, 0.0, 0.0, 0.0))
            continue

        try:
            n5 = _delta_normalized(series, periods=1)   #  1 × 5 min =  5 min
            n20 = _delta_normalized(series, periods=4)  #  4 × 5 min = 20 min
            n60 = _delta_normalized(series, periods=12) # 12 × 5 min = 60 min

            vectors.append(FeatureVector(
                aktie=ticker,
                delta_5m=float(n5.iloc[-1]) if len(n5) > 0 else 0.0,
                delta_20m=float(n20.iloc[-1]) if len(n20) > 0 else 0.0,
                delta_60m=float(n60.iloc[-1]) if len(n60) > 0 else 0.0,
            ))
        except Exception as exc:
            logger.warning("Feature-Fehler für %s: %s", ticker, exc)
            vectors.append(FeatureVector(ticker, 0.0, 0.0, 0.0))

    valid = sum(1 for v in vectors if v.delta_5m != 0.0 or v.delta_20m != 0.0)
    logger.info("Features berechnet: %d/%d Ticker mit Daten.", valid, len(tickers))
    return vectors


def build_tensor(vectors: list[FeatureVector]) -> np.ndarray:
    """
    Baut den Eingabe-Tensor shape (N_tickers, 3) aus den Feature-Vektoren.
    Reihenfolge entspricht der TICKERS-Liste.
    dtype float32 – direkt als PyTorch-Input verwendbar.
    """
    return np.array(
        [[v.delta_5m, v.delta_20m, v.delta_60m] for v in vectors],
        dtype=np.float32,
    )
