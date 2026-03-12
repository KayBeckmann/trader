"""
REST API – Phase 6

Endpunkte:
  GET /health                  – Healthcheck
  GET /empfehlungen            – Aktuelle Top-10-Long + Top-10-Short
  GET /statistik               – Trefferquote & Ergebnis je Aktie
  GET /statistik/gesamt        – Aggregierte KNN-Performance
  GET /kurse?aktie=AAPL        – Kursverlauf einer Aktie (letzte 24 h)
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from db import engine

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Healthcheck mit DB-Verbindungstest und Kurz-Statistik."""
    db_ok = False
    kurse_count = 0
    trades_count = 0
    try:
        with engine.connect() as conn:
            db_ok = True
            kurse_count  = conn.execute(text("SELECT COUNT(*) FROM kurse")).scalar() or 0
            trades_count = conn.execute(text("SELECT COUNT(*) FROM trades")).scalar() or 0
    except Exception as exc:
        logger.warning("Health-DB-Fehler: %s", exc)
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "kurse": kurse_count,
        "trades": trades_count,
    }


# ── Empfehlungen ──────────────────────────────────────────────────────────────
@app.get("/empfehlungen")
def get_empfehlungen():
    """
    Gibt die aktuellsten KNN-Empfehlungen zurück (letzter Inferenz-Zeitpunkt).
    Antwort: {"timestamp": "...", "long": [...], "short": [...]}
    """
    with engine.connect() as conn:
        # Neuesten Zeitstempel ermitteln
        ts_row = conn.execute(
            text("SELECT MAX(timestamp) FROM empfehlungen")
        ).fetchone()
        if not ts_row or ts_row[0] is None:
            return {"timestamp": None, "long": [], "short": []}

        ts = ts_row[0]
        rows = conn.execute(
            text("""
                SELECT aktie, richtung, knn_wert
                FROM empfehlungen
                WHERE timestamp = :ts
                ORDER BY richtung, knn_wert DESC
            """),
            {"ts": ts},
        ).fetchall()

    long_list = [
        {"aktie": r[0], "knn_wert": float(r[2])}
        for r in rows if r[1] == "long"
    ]
    short_list = [
        {"aktie": r[0], "knn_wert": float(r[2])}
        for r in rows if r[1] == "short"
    ]
    return {"timestamp": ts.isoformat(), "long": long_list, "short": short_list}


# ── Statistik je Aktie ────────────────────────────────────────────────────────
@app.get("/statistik")
def get_statistik():
    """Trefferquote und Ergebnis je Aktie aus der aggregierten View."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT aktie, trades_gesamt, trades_gewinn, trades_verlust,
                       gesamtergebnis_eur, trefferquote_pct, durchschnitt_eur
                FROM statistik
                ORDER BY gesamtergebnis_eur DESC
            """)
        ).fetchall()

    return [
        {
            "aktie": r[0],
            "trades_gesamt": r[1],
            "trades_gewinn": r[2],
            "trades_verlust": r[3],
            "gesamtergebnis_eur": float(r[4]) if r[4] is not None else 0.0,
            "trefferquote_pct": float(r[5]) if r[5] is not None else 0.0,
            "durchschnitt_eur": float(r[6]) if r[6] is not None else 0.0,
        }
        for r in rows
    ]


# ── Gesamtstatistik ───────────────────────────────────────────────────────────
@app.get("/statistik/gesamt")
def get_statistik_gesamt():
    """Aggregierte KNN-Performance über alle Aktien."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    SUM(trades_gesamt)                                          AS trades_gesamt,
                    SUM(trades_gewinn)                                          AS trades_gewinn,
                    SUM(trades_verlust)                                         AS trades_verlust,
                    ROUND(SUM(gesamtergebnis_eur), 2)                          AS gesamtergebnis_eur,
                    ROUND(
                        100.0 * SUM(trades_gewinn)
                        / NULLIF(SUM(trades_gesamt), 0), 2
                    )                                                           AS trefferquote_pct,
                    ROUND(AVG(durchschnitt_eur), 4)                            AS durchschnitt_eur
                FROM statistik
            """)
        ).fetchone()

    if not row or row[0] is None:
        return {
            "trades_gesamt": 0, "trades_gewinn": 0, "trades_verlust": 0,
            "gesamtergebnis_eur": 0.0, "trefferquote_pct": 0.0, "durchschnitt_eur": 0.0,
        }
    return {
        "trades_gesamt": int(row[0]),
        "trades_gewinn": int(row[1]),
        "trades_verlust": int(row[2]),
        "gesamtergebnis_eur": float(row[3]),
        "trefferquote_pct": float(row[4]),
        "durchschnitt_eur": float(row[5]),
    }


# ── Kursverlauf ───────────────────────────────────────────────────────────────
@app.get("/kurse")
def get_kurse(
    aktie: str = Query(..., description="Ticker-Symbol, z. B. AAPL"),
    stunden: int = Query(24, ge=1, le=336, description="Anzahl Stunden zurück (max. 336 = 2 Wochen)"),
):
    """Kursverlauf einer Aktie für den Chart (5-Minuten-Auflösung)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT timestamp, wert
                FROM kurse
                WHERE aktie = :aktie
                  AND timestamp >= NOW() - INTERVAL '1 hour' * :stunden
                ORDER BY timestamp ASC
            """),
            {"aktie": aktie.upper(), "stunden": stunden},
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Keine Kurse für {aktie} gefunden.")

    return {
        "aktie": aktie.upper(),
        "kurse": [
            {"timestamp": r[0].isoformat(), "wert": float(r[1])}
            for r in rows
        ],
    }
