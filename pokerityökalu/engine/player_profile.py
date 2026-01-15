# -*- coding: utf-8 -*-

from dataclasses import dataclass
from random import random

class PlayerProfile:
    def __init__(
        self,
        vpip=20,
        aggression=30,
        fold_flop=40,
        fold_turn=50,
        fold_river=60,
    ):
        self.vpip = vpip
        self.aggression = aggression
        self.fold_flop = fold_flop
        self.fold_turn = fold_turn
        self.fold_river = fold_river


@dataclass
class PlayerProfile:
    """
    Pelaajaprofiili:
    - VPIP: kuinka usein osallistuu jakoon
    - call_preflop_pct: kuinka usein VPIP-käsi oikeasti jatketaan
    - fold-prosentit postflop
    - aggressio
    """

    # ===== PRE-FLOP =====
    vpip: int = 25
    call_preflop_pct: int = 75   # 🔹 UUSI: jatketaanko VPIP-käsi oikeasti

    # ===== AGGRESSION =====
    aggression: float = 2.5
    barrel_turn_pct: int = 45
    barrel_river_pct: int = 30

    # ===== FOLDING =====
    fold_flop: int = 40
    fold_turn: int = 50
    fold_river: int = 60

    # ==================================================
    # HELPERIT
    # ==================================================

    def should_call_preflop(self) -> bool:
        return random() < (self.call_preflop_pct / 100.0)

    def should_barrel_turn(self) -> bool:
        return random() < (self.barrel_turn_pct / 100.0)

    def should_barrel_river(self) -> bool:
        return random() < (self.barrel_river_pct / 100.0)

    def is_aggressive(self) -> bool:
        return self.aggression >= 3.0

    def is_passive(self) -> bool:
        return self.aggression < 2.0
