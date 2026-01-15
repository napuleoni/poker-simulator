# -*- coding: utf-8 -*-


from dataclasses import dataclass
from typing import Dict, List

# ---- Perusvakiot ----

RANKS = "23456789TJQKA"
SUITS = "shdc"

FULL_DECK = [r + s for r in RANKS for s in SUITS]


# ---- Preflop-hand ----

@dataclass(frozen=True)
class PreflopHand:
    code: str  # esim "AA", "AKs", "AKo"

    def is_pair(self) -> bool:
        return len(self.code) == 2

    def is_suited(self) -> bool:
        return self.code.endswith("s")

    def is_offsuit(self) -> bool:
        return self.code.endswith("o")

    def ranks(self):
        return self.code[0], self.code[1]


# ---- Kombinaatiogeneraattorit ----

def generate_preflop_combos(hand: PreflopHand) -> List[List[str]]:
    r1, r2 = hand.ranks()
    combos = []

    if hand.is_pair():
        for i in range(len(SUITS)):
            for j in range(i + 1, len(SUITS)):
                combos.append([r1 + SUITS[i], r2 + SUITS[j]])

    elif hand.is_suited():
        for s in SUITS:
            combos.append([r1 + s, r2 + s])

    else:
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append([r1 + s1, r2 + s2])

    return combos


def generate_combos(hand_code: str) -> List[List[str]]:
    ranks = hand_code.replace("s", "").replace("o", "")
    r1, r2 = ranks[0], ranks[1]

    combos = []

    if r1 == r2:
        for i in range(len(SUITS)):
            for j in range(i + 1, len(SUITS)):
                combos.append([r1 + SUITS[i], r2 + SUITS[j]])

    elif hand_code.endswith("s"):
        for s in SUITS:
            combos.append([r1 + s, r2 + s])

    else:
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append([r1 + s1, r2 + s2])

    return combos


def filter_dead_combos(combos: List[List[str]], dead_cards: set) -> List[List[str]]:
    return [
        combo for combo in combos
        if combo[0] not in dead_cards and combo[1] not in dead_cards
    ]


# ---- Range-maarittelyt ----

def top_percent_range(percent: int) -> List[str]:
    base_hands = (
        ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22"] +
        ["AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"] +
        ["AKo", "AQo", "AJo", "KQo"]
    )

    cutoff = int(len(base_hands) * percent / 100)
    return base_hands[:cutoff]


HAND_WEIGHTS: Dict[str, float] = {
    "premium": 1.0,
    "strong": 0.9,
    "medium": 0.6,
    "speculative": 0.35,
}


def classify_hand(hand_code: str) -> str:
    if hand_code in ["AA", "KK", "QQ", "JJ"]:
        return "premium"
    if hand_code in ["TT", "AKs", "AQs", "AKo"]:
        return "strong"
    if hand_code in ["99", "88", "AJs", "KQs", "ATs"]:
        return "medium"
    return "speculative"


def normalize_range(range_input):
    if isinstance(range_input, dict):
        return dict(range_input)

    if isinstance(range_input, list):
        return {hand: 1.0 for hand in range_input}

    raise TypeError("Tuntematon range-muoto")


def position_range(position: str) -> Dict[str, float]:
    position = position.strip().upper()

def opponent_range_for_index(i: int, hero_position: str):
    """
    Palauttaa vastustajan rangen indeksin perusteella.
    """
    if not hero_position:
        hero_position = "BTN"

    if i == 0:
        return position_range(hero_position)
    elif i <= 2:
        return normalize_range(top_percent_range(25))
    else:
        return normalize_range(top_percent_range(40))
