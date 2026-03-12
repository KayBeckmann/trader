"""
Virtueller Trade-Manager & Reinforcement Learning – Phase 5

Ablauf je 5-Min-Takt:
  1. check_and_close_trades()  – offene Trades prüfen, ggf. schließen + RL-Update
  2. open_trades(result, tensor) – neue Trades für Top-10-Long/Short öffnen

Gebührenmodell (virtuell):
  Eröffnung : 0,5 % auf Einsatz (100 €) = 0,50 €
  Schließung : 0,5 % auf aktuellen Positionswert
  Stop-Loss  : −15 % netto → Trade schließen, reward = −1
  Take-Profit: +15 % netto → Trade schließen, reward = +1
  Timeout    : nach 1 Stunde; |ergebnis| ≥ 10 € → prop. Reward, sonst ignoriert
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
import torch
import torch.nn as nn

from db import engine
from inference import Inferenzresultat, get_model, save_checkpoint
from sqlalchemy import text
from tickers import TICKERS

logger = logging.getLogger(__name__)

# ── Handelsparameter ───────────────────────────────────────────────────────────
EINSATZ_EUR: float = 100.0
GEBUEHR_RATE: float = 0.005       # 0,5 %
STOP_LOSS_PCT: float = -0.15      # −15 % netto
TAKE_PROFIT_PCT: float = 0.15     # +15 % netto
TIMEOUT_MIN: int = 60
REWARD_SCHWELLE_EUR: float = 10.0  # unter diesem Betrag → Timeout ignoriert
LR: float = 1e-4                   # Lernrate für RL-Update


# ── Datenstruktur ─────────────────────────────────────────────────────────────
@dataclass
class OffenerTrade:
    aktie: str
    richtung: str                    # 'long' | 'short'
    eroeffnet_at: datetime
    einstiegskurs: float
    gebuehr_eroeffnung: float
    ticker_index: int                # Index in TICKERS für RL-Update
    entry_tensor: np.ndarray = field(repr=False)  # Tensor zum Öffnungszeitpunkt


_offene_trades: list[OffenerTrade] = []


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def _letzter_kurs(aktie: str) -> float | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT wert FROM kurse WHERE aktie = :a ORDER BY timestamp DESC LIMIT 1"),
            {"a": aktie},
        ).fetchone()
    return float(row[0]) if row else None


def _netto_pnl(trade: OffenerTrade, kurs: float) -> float:
    """Nettoergebnis in € nach Eröffnungs- und Schließungsgebühr."""
    ratio = kurs / trade.einstiegskurs
    brutto = EINSATZ_EUR * (ratio - 1) if trade.richtung == "long" else EINSATZ_EUR * (1 - ratio)
    exit_value = EINSATZ_EUR * ratio          # Wert des Rückkaufs (Long + Short)
    gebuehr_schliessung = abs(exit_value) * GEBUEHR_RATE
    return brutto - trade.gebuehr_eroeffnung - gebuehr_schliessung


def _reward_signal(ergebnis: float, schliessgrund: str) -> float | None:
    if schliessgrund == "take_profit":
        return 1.0
    if schliessgrund == "stop_loss":
        return -1.0
    # Timeout
    if abs(ergebnis) < REWARD_SCHWELLE_EUR:
        return None  # zu klein → ignorieren
    return max(-1.0, min(1.0, ergebnis / REWARD_SCHWELLE_EUR))


def _schreibe_trade_db(
    trade: OffenerTrade, kurs: float, schliessgrund: str,
    ergebnis: float, reward: float | None,
) -> None:
    gebuehr_s = abs(EINSATZ_EUR * (kurs / trade.einstiegskurs)) * GEBUEHR_RATE
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO trades
                  (aktie, richtung, eroeffnet_at, geschlossen_at, schliessgrund,
                   einsatz_eur, gebuehr_eroeffnung_eur, gebuehr_schliessung_eur,
                   ergebnis_eur, reward)
                VALUES
                  (:aktie, :richtung, :eroeffnet_at, :geschlossen_at, :schliessgrund,
                   :einsatz, :geb_oe, :geb_sc, :ergebnis, :reward)
            """),
            {
                "aktie": trade.aktie,
                "richtung": trade.richtung,
                "eroeffnet_at": trade.eroeffnet_at,
                "geschlossen_at": datetime.now(timezone.utc),
                "schliessgrund": schliessgrund,
                "einsatz": EINSATZ_EUR,
                "geb_oe": trade.gebuehr_eroeffnung,
                "geb_sc": gebuehr_s,
                "ergebnis": ergebnis,
                "reward": reward,
            },
        )
        conn.commit()


def _rl_update(ticker_index: int, reward: float, tensor: np.ndarray) -> None:
    """
    Policy-Gradient-ähnliches RL-Update (MSE-Verlust auf einem Ausgabe-Knoten).
    Ziel: output[ticker_index] soll sich Richtung `reward` bewegen.
    Alle anderen Ausgabe-Knoten bleiben unberührt (target = output.detach()).
    """
    model = get_model()
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    optimizer.zero_grad()

    x = torch.from_numpy(tensor.flatten()).unsqueeze(0).float()  # (1, 270)
    output = model(x)                                            # (1,  90)

    target = output.detach().clone()
    target[0, ticker_index] = float(reward)

    loss = nn.MSELoss()(output, target)
    loss.backward()
    optimizer.step()
    model.eval()
    save_checkpoint()

    logger.debug(
        "RL-Update: %s  reward=%.3f  loss=%.6f",
        TICKERS[ticker_index], reward, loss.item(),
    )


# ── Öffentliche API ───────────────────────────────────────────────────────────
def open_trades(result: Inferenzresultat, tensor: np.ndarray) -> None:
    """Öffnet virtuelle Trades für Top-10-Long und Top-10-Short."""
    aktive = {t.aktie for t in _offene_trades}
    neu = 0
    for emp in result.long_top10 + result.short_top10:
        if emp.aktie in aktive:
            continue   # kein Doppel-Trade
        richtung = "long" if emp in result.long_top10 else "short"
        kurs = _letzter_kurs(emp.aktie)
        if kurs is None:
            logger.warning("Kein Kurs für %s – Trade übersprungen.", emp.aktie)
            continue
        _offene_trades.append(OffenerTrade(
            aktie=emp.aktie,
            richtung=richtung,
            eroeffnet_at=datetime.now(timezone.utc),
            einstiegskurs=kurs,
            gebuehr_eroeffnung=EINSATZ_EUR * GEBUEHR_RATE,
            ticker_index=TICKERS.index(emp.aktie),
            entry_tensor=tensor.copy(),
        ))
        aktive.add(emp.aktie)
        neu += 1
    if neu:
        logger.info("%d neue Trades eröffnet (gesamt offen: %d).", neu, len(_offene_trades))


def check_and_close_trades() -> None:
    """Überprüft alle offenen Trades; schließt und trainiert bei Bedarf."""
    if not _offene_trades:
        return
    jetzt = datetime.now(timezone.utc)
    to_close: list[OffenerTrade] = []

    for trade in _offene_trades:
        kurs = _letzter_kurs(trade.aktie)
        if kurs is None:
            continue
        ergebnis = _netto_pnl(trade, kurs)
        pct = ergebnis / EINSATZ_EUR
        abgelaufen = (jetzt - trade.eroeffnet_at) >= timedelta(minutes=TIMEOUT_MIN)

        if pct <= STOP_LOSS_PCT:
            schliessgrund = "stop_loss"
        elif pct >= TAKE_PROFIT_PCT:
            schliessgrund = "take_profit"
        elif abgelaufen:
            schliessgrund = "timeout"
        else:
            continue

        reward = _reward_signal(ergebnis, schliessgrund)
        _schreibe_trade_db(trade, kurs, schliessgrund, ergebnis, reward)
        to_close.append(trade)

        if reward is not None:
            _rl_update(trade.ticker_index, reward, trade.entry_tensor)

        logger.info(
            "Trade geschlossen: %s %s → %s  Ergebnis=%.2f €  reward=%s",
            trade.richtung.upper(), trade.aktie, schliessgrund,
            ergebnis, f"{reward:.3f}" if reward is not None else "None",
        )

    for t in to_close:
        _offene_trades.remove(t)
