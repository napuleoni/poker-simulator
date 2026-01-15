# -*- coding: utf-8 -*-

import random
from typing import List, Optional


RANK_ORDER = "23456789TJQKA"


def hand_board_weight(
    hand: List[str],
    board: List[str],
    hero_hand: Optional[List[str]] = None
) -> float:
    """
    Board-aware + hero-blocker-aware painotus vastustajan k�delle.
    """

    ranks = [c[0] for c in hand]
    suits = [c[1] for c in hand]

    board_ranks = [c[0] for c in board]
    board_suits = [c[1] for c in board]

    hero_suits = [c[1] for c in hero_hand] if hero_hand else []

    weight = 1.0

    # --- 1. Flush-board tunnistus ---
    suit_counts = {}
    for s in board_suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1

    flush_suit = None
    for s, cnt in suit_counts.items():
        if cnt >= 3:
            flush_suit = s
            break

    hand_flush_cards = suits.count(flush_suit) if flush_suit else 0
    hero_flush_cards = hero_suits.count(flush_suit) if hero_hand else 0

    # --- 2. Flush-board logiikka ---
    if flush_suit:
        if hand_flush_cards >= 2:
            high_rank = max(ranks, key=lambda r: RANK_ORDER.index(r))

            if high_rank == "A":
                weight *= 3.0
            elif high_rank in ["K", "Q"]:
                weight *= 2.2
            elif high_rank in ["J", "T", "9"]:
                weight *= 1.6
            else:
                weight *= 1.2

            # HERO BLOCKER EFFECT
            if hero_flush_cards >= 1:
                weight *= 0.75
            if hero_flush_cards >= 2:
                weight *= 0.6
        else:
            weight *= 0.35

    # --- 3. Pair / set / osumat ---
    for r in ranks:
        if r in board_ranks:
            weight *= 1.3

    if ranks[0] == ranks[1]:
        weight *= 1.25

    # --- 4. T�ysin ohi ---
    if (
        not any(r in board_ranks for r in ranks)
        and not flush_suit
    ):
        weight *= 0.5

    return weight


def opponent_survives_street(
    hand: List[str],
    board: List[str],
    street: str
) -> bool:
    """
    street: "flop", "turn", "river"
    """

    w = hand_board_weight(hand, board)

    if street == "flop":
        if w >= 1.2:
            return True
        if w >= 0.5:
            return random.random() < 0.5
        return random.random() < 0.15

    if street == "turn":
        if w >= 1.4:
            return True
        if w >= 0.7:
            return random.random() < 0.4
        return random.random() < 0.15

    if street == "river":
        if w >= 1.6:
            return True
        if w >= 1.0:
            return random.random() < 0.35
        return random.random() < 0.1

    raise ValueError("Tuntematon street")


def classify_flop_texture(board):
    """
    Palauttaa flopin tekstuurin:
    DRY / WET / PAIRED / MONOTONE
    """
    assert len(board) >= 3

    flop = board[:3]

    ranks = [c[0] for c in flop]
    suits = [c[1] for c in flop]

    # MONOTONE
    if len(set(suits)) == 1:
        return "monotone"

    # PAIRED
    if len(set(ranks)) < 3:
        return "paired"

    # Suoranveto?
    rank_order = "23456789TJQKA"
    idx = sorted(rank_order.index(r) for r in ranks)

    if max(idx) - min(idx) <= 4:
        return "wet"

    # Muuten kuiva
    return "dry"

from treys import Card as TreysCard


def hand_strength_bucket(hand, board, evaluator):
    """
    Palauttaa bucketin:
    0 = air
    1 = weak
    2 = medium
    3 = strong
    """

    board_cards = [TreysCard.new(c) for c in board]
    hand_cards = [TreysCard.new(c) for c in hand]

    value = evaluator.evaluate(board_cards, hand_cards)

    # Treys: pienempi = parempi käsi
    if value <= 300:
        return 3      # erittäin vahva (full house+)
    elif value <= 1200:
        return 2      # kohtalainen (2pair / trips)
    elif value <= 3000:
        return 1      # heikko SD (pair / A-high)
    else:
        return 0      # air

