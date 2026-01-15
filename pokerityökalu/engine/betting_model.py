import random
from treys import Evaluator
from engine.board_logic import hand_strength_bucket


def opponent_call_decision(
    hand,
    board,
    street: str,
    pot_size: float,
    bet_amount: float,
    texture: str,
    pressure: int,
    aggression: float = 0.5,
):
    """
    Returns:
        (calls: bool, call_amount: float)
    """

    evaluator = Evaluator()
    strength = hand_strength_bucket(hand, board, evaluator)

    # ============================
    # POT ODDS
    # ============================
    pot_odds = bet_amount / max(1e-6, (pot_size + bet_amount))

    # ============================
    # PERUS VOITTOTODENNÄKÖISYYS
    # ============================
    if strength >= 3:          # two pair+
        win_prob = 0.85
    elif strength == 2:        # top pair / overpair
        win_prob = 0.55
    elif strength == 1:        # weak pair
        win_prob = 0.32
    else:                      # air
        win_prob = 0.08

    # ============================
    # AGGRESSION & PRESSURE
    # ============================
    win_prob += aggression * 0.12
    win_prob -= pressure * 0.06   # 🔧 hillitty (oli liian vahva)

    # ============================
    # BOARD TEXTURE
    # ============================
    if texture == "wet":
        win_prob += 0.06
    elif texture == "dry":
        win_prob -= 0.03

    # ============================
    # STREET-KOHTAINEN SÄÄTÖ
    # ============================
    if street == "flop":
        win_prob += 0.05   # floatit, backdoorit
    elif street == "river":
        win_prob -= 0.08   # riverillä ei uteliaisuusmakseja

    # Clamp
    win_prob = max(0.02, min(win_prob, 0.95))

    # ============================
    # FLOP-FLOAT AIRILLA (KRITTINEN)
    # ============================
    if strength == 0 and street == "flop":
        if random.random() < 0.10:
            return True, bet_amount

    # ============================
    # LOPULLINEN PÄÄTÖS
    # ============================
    calls = win_prob >= pot_odds

    return calls, bet_amount
