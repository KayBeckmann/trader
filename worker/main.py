import logging
import os
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import text

from db import engine, run_migrations
from features import build_tensor, compute_features
from fetcher import backfill, fetch_current
from inference import CHECKPOINT_PATH, get_model, run_inference, save_checkpoint
from market_hours import is_market_open
from trader import check_and_close_trades, load_offene_trades, open_trades

# Logging-Level aus Umgebungsvariable lesen (Standard: INFO)
_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=_level,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


# ── DB-Startwartelogik ────────────────────────────────────────────────────────
def _wait_for_db(max_retries: int = 12, delay: int = 5) -> None:
    """Wartet auf die Datenbankverbindung (exponentielles Backoff)."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Datenbankverbindung hergestellt.")
            return
        except Exception as exc:
            wait = min(delay * attempt, 60)
            logger.warning(
                "DB nicht erreichbar (Versuch %d/%d): %s – Retry in %ds",
                attempt, max_retries, exc, wait,
            )
            time.sleep(wait)
    raise RuntimeError("Datenbankverbindung konnte nicht hergestellt werden.")


# ── Haupt-Job ─────────────────────────────────────────────────────────────────
def job_kurs_abruf() -> None:
    if not is_market_open():
        logger.info("Markt geschlossen – Abruf übersprungen.")
        return
    try:
        check_and_close_trades()          # 1. Offene Trades prüfen / RL-Update
        fetch_current()                   # 2. Neue Kurse laden
        vectors = compute_features()      # 3. Features berechnen
        tensor = build_tensor(vectors)
        logger.info(
            "Feature-Tensor: shape=%s  min=%.4f  max=%.4f",
            tensor.shape, float(tensor.min()), float(tensor.max()),
        )
        result = run_inference(tensor)    # 4. KNN-Inferenz
        open_trades(result, tensor)       # 5. Neue Trades eröffnen
    except Exception as exc:
        logger.error("Fehler im Job-Lauf: %s", exc, exc_info=True)


# ── Einstiegspunkt ────────────────────────────────────────────────────────────
def main() -> None:
    logger.info("Worker gestartet.")
    _wait_for_db()

    logger.info("Führe DB-Migrationen durch…")
    run_migrations()

    logger.info("Führe initialen Backfill durch…")
    backfill()

    # Bootstrap: Modell initialisieren und Checkpoint anlegen falls nicht vorhanden
    get_model()
    if not CHECKPOINT_PATH.exists():
        save_checkpoint()
        logger.info("Bootstrap-Checkpoint angelegt.")

    logger.info("Lade offene Trades aus DB…")
    load_offene_trades()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(job_kurs_abruf, "interval", minutes=5, id="kurs_abruf",
                      misfire_grace_time=60)
    logger.info("Scheduler läuft (alle 5 Minuten).")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker beendet.")


if __name__ == "__main__":
    main()
