from dataclasses import dataclass
from typing import List, Optional

from engine.positional_player import PositionalPlayer


@dataclass
class SimulationConfig:
    hero_hand: list
    position: str
    board: list
    mode: str

    iterations: int = 5000
    random_seed: Optional[int] = None

    # 🔴 TÄMÄ PUUTTUI → nyt lisätty
    opponent_profiles: Optional[List[PositionalPlayer]] = None
