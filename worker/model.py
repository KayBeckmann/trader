"""
KNN-Architektur – Phase 4

TraderNet verarbeitet alle 90 Aktien parallel in einem einzigen Forward-Pass:

  Eingabe : flacher Tensor  (1, 270)  = 90 Aktien × 3 Deltas
  Schicht 1: Linear(270 → 256) + ReLU
  Schicht 2: Linear(256 → 128) + ReLU
  Ausgabe : Linear(128 →  90) + Tanh  → Werte in [-1, +1]

Ausgabewerte je Aktie:
  +1  → starkes Long-Signal
   0  → neutral
  -1  → starkes Short-Signal
"""

import os

import torch
import torch.nn as nn

from tickers import TICKERS

N_TICKERS = len(TICKERS)            # dynamisch aus tickers.py (aktuell 70)
N_FEATURES = 3
INPUT_SIZE = N_TICKERS * N_FEATURES  # 70 × 3 = 210
OUTPUT_SIZE = N_TICKERS              # 70


def _default_hidden() -> list[int]:
    """Liest KNN_HIDDEN_LAYERS aus der Umgebung (z. B. '256,128')."""
    raw = os.environ.get("KNN_HIDDEN_LAYERS", "256,128")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


class TraderNet(nn.Module):
    def __init__(self, hidden_sizes: list[int] | None = None) -> None:
        super().__init__()
        if hidden_sizes is None:
            hidden_sizes = _default_hidden()

        layers: list[nn.Module] = []
        in_size = INPUT_SIZE
        for h in hidden_sizes:
            layers.append(nn.Linear(in_size, h))
            layers.append(nn.ReLU())
            in_size = h
        layers.append(nn.Linear(in_size, OUTPUT_SIZE))
        layers.append(nn.Tanh())

        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, 270) oder (270,)
        Gibt Tensor (batch, 90) oder (90,) zurück.
        """
        return self.net(x)
