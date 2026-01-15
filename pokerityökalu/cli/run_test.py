# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))



from engine.simulator import run_simulation
from engine.config import SimulationConfig
from engine.player_profile import PlayerProfile
from engine.positional_player import PositionalPlayer


def main():
    # ================================
    # HERO
    # ================================
    hero_hand = ["Ah", "Ad"]
    board = []          # tyhjä = preflop → postflop simulaatio
    position = "BTN"
    mode = "PLAY"

    # ================================
    # VASTUSTAJAPROFIILIT
    # ================================
    tight_profile = PlayerProfile(
        vpip=18,
        fold_flop=55,
        fold_turn=65,
        fold_river=70,
        aggression=2.0,
        barrel_turn_pct=30,
        barrel_river_pct=20,
    )

    loose_profile = PlayerProfile(
        vpip=35,
        fold_flop=30,
        fold_turn=40,
        fold_river=45,
        aggression=3.5,
        barrel_turn_pct=55,
        barrel_river_pct=40,
    )

    # ================================
    # POSITIONAL PLAYERS
    # ================================
    villain1 = PositionalPlayer(
        name="Villain-Tight",
        profiles_by_position={
            "BTN": tight_profile,
            "SB": tight_profile,
            "BB": tight_profile,
        },
    )

    villain2 = PositionalPlayer(
        name="Villain-Loose",
        profiles_by_position={
            "BTN": loose_profile,
            "SB": loose_profile,
            "BB": loose_profile,
        },
    )

    opponents = [villain1, villain2]

    # ================================
    # SIMULAATIOKONFIG
    # ================================
    config = SimulationConfig(
        hero_hand=hero_hand,
        position=position,
        board=board,
        mode=mode,
        iterations=1000,
        random_seed=42,
        opponent_profiles=opponents,
    )

    # ================================
    # AJA SIMULAATIO
    # ================================
    results = run_simulation(config)

    print("\n=== SIMULAATIOTULOKSET ===")
    for r in results:
        print(
            f"Vastustajia: {r.opponents} | "
            f"Equity: {r.equity:.2f}% | "
            f"Non-SD: {r.non_showdown_win_pct:.2f}%"
        )


if __name__ == "__main__":
    main()
