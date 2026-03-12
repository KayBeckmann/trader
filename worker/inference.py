"""
Inferenz-Modul – Phase 4

Lädt das TraderNet, führt den Forward-Pass durch und liefert:
  - Top-10-Long-Kandidaten  (höchste positive KNN-Ausgabe)
  - Top-10-Short-Kandidaten (stärkste negative KNN-Ausgabe)

Checkpoint und letzte Empfehlungen werden im Docker-Volume /app/models
persistiert, sodass der Backend-Container sie lesen kann (Phase 6).
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sqlalchemy import text

from db import engine
from model import TraderNet
from tickers import TICKERS

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app/models"))
CHECKPOINT_PATH = _MODEL_DIR / "trader_net.pt"
LATEST_PATH = _MODEL_DIR / "latest_empfehlungen.json"

# Singleton – einmal laden, danach wiederverwenden
_model: TraderNet | None = None


def get_model() -> TraderNet:
    """Gibt das Singleton-Modell zurück; lädt Checkpoint falls vorhanden."""
    global _model
    if _model is None:
        _model = TraderNet()
        if CHECKPOINT_PATH.exists():
            _model.load_state_dict(
                torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
            )
            logger.info("Checkpoint geladen: %s", CHECKPOINT_PATH)
        else:
            logger.info("Kein Checkpoint – starte mit zufälligen Gewichten (Bootstrap).")
    return _model


def save_checkpoint() -> None:
    """Speichert den aktuellen Modellzustand als Checkpoint."""
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(get_model().state_dict(), CHECKPOINT_PATH)
    logger.info("Checkpoint gespeichert: %s", CHECKPOINT_PATH)


@dataclass
class Empfehlung:
    aktie: str
    wert: float  # KNN-Ausgabe in [-1, +1]


@dataclass
class Inferenzresultat:
    long_top10: list[Empfehlung]
    short_top10: list[Empfehlung]
    raw_output: np.ndarray  # shape (90,) – wird für RL in Phase 5 benötigt


def run_inference(tensor: np.ndarray) -> Inferenzresultat:
    """
    Forward-Pass durch das TraderNet.

    tensor : NumPy-Array shape (90, 3) aus features.build_tensor()
    Gibt Top-10-Long- und Top-10-Short-Empfehlungen zurück.
    Alle 90 Aktien werden in einem einzigen Matrix-Multiplikations-Schritt
    verarbeitet – kein sequenzieller Loop.
    """
    model = get_model()
    model.eval()

    with torch.no_grad():
        x = torch.from_numpy(tensor.flatten()).unsqueeze(0).float()  # (1, 270)
        output: np.ndarray = model(x).squeeze(0).numpy()             # (90,)

    # Paare (ticker, wert) nach KNN-Ausgabe sortieren
    pairs = list(zip(TICKERS, output.tolist()))
    long_top10 = [
        Empfehlung(t, round(v, 6))
        for t, v in sorted(pairs, key=lambda tv: tv[1], reverse=True)[:10]
    ]
    short_top10 = [
        Empfehlung(t, round(v, 6))
        for t, v in sorted(pairs, key=lambda tv: tv[1])[:10]
    ]

    logger.info(
        "Inferenz – Long #1: %s=%.4f  Short #1: %s=%.4f",
        long_top10[0].aktie, long_top10[0].wert,
        short_top10[0].aktie, short_top10[0].wert,
    )

    result = Inferenzresultat(
        long_top10=long_top10,
        short_top10=short_top10,
        raw_output=output,
    )
    _save_latest(result)
    _save_to_db(result)
    return result


def _save_latest(result: Inferenzresultat) -> None:
    """Persistiert die letzten Empfehlungen als JSON im Modell-Volume (Backup)."""
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "long_top10": [asdict(e) for e in result.long_top10],
        "short_top10": [asdict(e) for e in result.short_top10],
    }
    LATEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _save_to_db(result: Inferenzresultat) -> None:
    """Schreibt die aktuellen Empfehlungen in die Tabelle `empfehlungen`."""
    ts = datetime.now(timezone.utc)
    rows = [
        {"timestamp": ts, "aktie": e.aktie, "richtung": "long", "knn_wert": e.wert}
        for e in result.long_top10
    ] + [
        {"timestamp": ts, "aktie": e.aktie, "richtung": "short", "knn_wert": e.wert}
        for e in result.short_top10
    ]
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO empfehlungen (timestamp, aktie, richtung, knn_wert)
                    VALUES (:timestamp, :aktie, :richtung, :knn_wert)
                """),
                rows,
            )
            conn.commit()
    except Exception as exc:
        logger.warning("Empfehlungen konnten nicht in DB geschrieben werden: %s", exc)
