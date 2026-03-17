import logging
import os

from sqlalchemy import BigInteger, Column, Numeric, String, UniqueConstraint, create_engine, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Fügt fehlende Spalten zur trades-Tabelle hinzu (idempotent)."""
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE trades ADD COLUMN IF NOT EXISTS einstiegskurs NUMERIC(12, 6)"
        ))
        conn.execute(text(
            "ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_features TEXT"
        ))
        conn.commit()
    logger.info("DB-Migrationen abgeschlossen.")


class Base(DeclarativeBase):
    pass


class Kurs(Base):
    __tablename__ = "kurse"
    __table_args__ = (
        UniqueConstraint("aktie", "timestamp", name="uq_kurse_aktie_timestamp"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    aktie = Column(String(20), nullable=False)
    wert = Column(Numeric(18, 6), nullable=False)


def get_session() -> Session:
    return Session(engine)
