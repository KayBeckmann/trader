import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Worker gestartet – wartet auf weitere Implementierung.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
