import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from features import build_tensor, compute_features
from fetcher import backfill, fetch_current
from market_hours import is_market_open

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


def job_kurs_abruf() -> None:
    if not is_market_open():
        logger.info("Markt geschlossen – Abruf übersprungen.")
        return
    fetch_current()
    vectors = compute_features()
    tensor = build_tensor(vectors)
    logger.info(
        "Feature-Tensor: shape=%s  min=%.4f  max=%.4f",
        tensor.shape, float(tensor.min()), float(tensor.max()),
    )


def main() -> None:
    logger.info("Worker gestartet – führe initialen Backfill durch…")
    backfill()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(job_kurs_abruf, "interval", minutes=5, id="kurs_abruf")
    logger.info("Scheduler läuft (alle 5 Minuten).")
    scheduler.start()


if __name__ == "__main__":
    main()
