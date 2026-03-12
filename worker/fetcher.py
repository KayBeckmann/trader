import logging
import time

import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db import Kurs, engine
from tickers import TICKERS

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # Sekunden (exponentielles Backoff: 2, 4, 8)


def _download_with_retry(tickers: list[str], interval: str, period: str) -> object:
    """yfinance-Download mit exponentiellem Retry bei Fehlern."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            data = yf.download(
                tickers=tickers,
                interval=interval,
                period=period,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            return data
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY ** (attempt + 1)
                logger.warning(
                    "Download-Fehler (Versuch %d/%d): %s – Retry in %ds",
                    attempt + 1, _MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error("Alle %d Versuche fehlgeschlagen: %s", _MAX_RETRIES, exc)
    raise last_exc


def _parse(data, tickers: list[str]) -> list[dict]:
    """Extrahiert Kurs-Zeilen aus einem yfinance-DataFrame."""
    rows = []
    is_multi = len(tickers) > 1
    for ticker in tickers:
        try:
            df = data[ticker] if is_multi else data
            df = df.dropna(subset=["Close"])
            if df.empty:
                logger.debug("Keine Daten für %s.", ticker)
                continue
            for ts, row in df.iterrows():
                rows.append({
                    "timestamp": ts.to_pydatetime(),
                    "aktie": ticker,
                    "wert": float(row["Close"]),
                })
        except Exception as exc:
            logger.warning("Parse-Fehler für %s: %s", ticker, exc)
    return rows


def _store(rows: list[dict]) -> int:
    """Speichert Kurs-Zeilen per INSERT … ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    with engine.connect() as conn:
        stmt = pg_insert(Kurs.__table__).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["aktie", "timestamp"]
        )
        result = conn.execute(stmt)
        conn.commit()
    saved = result.rowcount if result.rowcount >= 0 else len(rows)
    logger.info("%d Kurs-Einträge gespeichert (von %d).", saved, len(rows))
    return saved


def fetch_current(tickers: list[str] = TICKERS) -> int:
    """Aktuellsten 5-Minuten-Schlusskurs je Ticker abrufen und speichern."""
    logger.info("Kursabruf für %d Ticker (interval=5m, period=1d)…", len(tickers))
    try:
        data = _download_with_retry(tickers, interval="5m", period="1d")
    except Exception:
        return 0

    rows: list[dict] = []
    is_multi = len(tickers) > 1
    for ticker in tickers:
        try:
            df = data[ticker] if is_multi else data
            df = df.dropna(subset=["Close"])
            if df.empty:
                continue
            last_ts = df.index[-1]
            last_close = float(df["Close"].iloc[-1])
            rows.append({
                "timestamp": last_ts.to_pydatetime(),
                "aktie": ticker,
                "wert": last_close,
            })
        except Exception as exc:
            logger.warning("Kein Kurs für %s: %s", ticker, exc)

    return _store(rows)


def backfill(tickers: list[str] = TICKERS) -> int:
    """Historische 5-Minuten-Kurse der letzten 60 Tage initial laden."""
    logger.info("Backfill für %d Ticker (interval=5m, period=60d)…", len(tickers))
    try:
        data = _download_with_retry(tickers, interval="5m", period="60d")
    except Exception:
        return 0
    rows = _parse(data, tickers)
    return _store(rows)
