# -*- coding: utf-8 -*-

import random
from engine.player_profile import PlayerProfile

# =====================================================
# KÄSIEN VAHVUUSJÄRJESTYS (positionaalinen)
# =====================================================

POSITIONAL_HAND_ORDER = {
    "UTG": [
        "AA","KK","QQ","JJ","TT",
        "AKs","AQs","AJs","KQs",
        "AKo","99","88","AQo",
    ],
    "MP": [
        "AA","KK","QQ","JJ","TT","99","88",
        "AKs","AQs","AJs","ATs","KQs",
        "AKo","AQo","AJo","KQo","77","66",
    ],
    "CO": [
        "AA","KK","QQ","JJ","TT","99","88","77","66","55",
        "AKs","AQs","AJs","ATs","A9s","KQs","KJs","QJs",
        "AKo","AQo","AJo","KQo","QJo",
    ],
    "BTN": [
        "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
        "AKs","AQs","AJs","ATs","A9s","A8s","A7s",
        "KQs","KJs","KTs","QJs","QTs","JTs","T9s","98s",
        "AKo","AQo","AJo","ATo","KQo","KJo","QJo","JTo",
    ],
    "SB": [
        "AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
        "AKs","AQs","AJs","ATs","A9s","KQs","KJs","QJs",
        "AKo","AQo","AJo","KQo","QJo","JTo",
    ],
    "BB": [
        "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
        "AKs","AQs","AJs","ATs","A9s","A8s","A7s",
        "KQs","KJs","KTs","QJs","QTs","JTs","T9s","98s","87s","76s",
        "AKo","AQo","AJo","ATo","KQo","KJo","QJo","JTo",
    ],
}

# =====================================================
# RANGE GENERAATTORI (EI VPIP LOGIIKKAA)
# =====================================================

def generate_profile_range(profile: PlayerProfile, position: str) -> dict:
    """
    Palauttaa rangemäärityksen (painotetut kädet).
    VPIP päätetään simulatorissa, EI täällä.
    """

    ordered = POSITIONAL_HAND_ORDER.get(position, POSITIONAL_HAND_ORDER["BTN"])

    # Rangelaajuus sidotaan VPIPiin
    take_n = max(1, int(len(ordered) * profile.vpip / 100))
    selected = ordered[:take_n]

    weights = {}
    for i, hand in enumerate(selected):
        strength_factor = 1.0 - (i / len(selected)) * 0.5
        noise = random.uniform(0.9, 1.1)
        weights[hand] = round(strength_factor * noise, 3)

    return weights
