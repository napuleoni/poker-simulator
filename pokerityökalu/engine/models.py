# -*- coding: utf-8 -*-

from dataclasses import dataclass

@dataclass
class SimulationResult:
    opponents: int
    wins: int
    losses: int
    ties: int
    equity: float
    non_showdown_win_pct: float
    showdown_win_pct: float
