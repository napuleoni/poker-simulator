import random
from typing import List

from treys import Card as TreysCard, Evaluator

from engine.config import SimulationConfig
from engine.models import SimulationResult
from engine.utils import assert_unique_cards, weighted_choice
from engine.ranges import FULL_DECK, generate_combos
from engine.range_generator import generate_profile_range
from engine.hero_decision import HeroDecisionModel
from engine.betting_model import opponent_call_decision
from engine.hero_strategy import HeroStrategyProfile
DEBUG = True   # ← vaihda True kun haluat tutkia




HU_RIVER_PROFILE = {
    "value_bet_thin": 0.55,   # TP / weak 2p valuebet
    "bluff_freq": 0.25,       # bluffeja riverillä
    "call_down": 0.60,        # bluff-catch
}

MW_RIVER_PROFILE = {
    "value_bet_thin": 0.25,   # vain vahva value
    "bluff_freq": 0.08,       # lähes ei bluffeja
    "call_down": 0.30,
}

HU_RIVER_CALL_PROBS = {
    0: 0.05,   # air – lähes aina fold
    1: 0.35,   # weak pair – bluffcatch joskus
    2: 0.85,   # top pair – lähes aina call
    3: 1.00,   # 2pair+ – aina call
}


# ======================================================
# APU: käden vahvuus
# ======================================================



def hand_strength_bucket(cards, board, evaluator):
    """
    0 = air
    1 = weak pair
    2 = top pair / overpair
    3 = two pair+
    """

    board_cards = [TreysCard.new(c) for c in board]
    hand_cards = [TreysCard.new(c) for c in cards]

    value = evaluator.evaluate(board_cards, hand_cards)

    
    if value <= 1600:
        bucket = 3
    elif value <= 3000:
        bucket = 2
    elif value <= 4500:
        bucket = 1
    else:
        bucket = 0

   
    return bucket

def street_bet_size(
    street: str,
    pot_size: float,
    texture: str,
    aggression: float = 1.0,
) -> float:
    """
    Palauttaa heron betin koon (absoluuttinen määrä).
    """

    # --- perus bet fraction ---
    if street == "flop":
        base = 0.33
    elif street == "turn":
        base = 0.50
    else:  # river
        base = 0.66

    # --- board texture ---
    if texture == "wet":
        base += 0.10
    elif texture == "dry":
        base -= 0.05

    # --- aggressiivisuus ---
    base *= (0.8 + aggression * 0.4)

    # --- clamp ---
    base = max(0.2, min(base, 0.9))

    return pot_size * base

# ======================================================
# APU: fold-logiikka
# ======================================================

def board_texture(board):
    """
    Palauttaa:
    "dry"  = kuiva board (A72r)
    "semi" = jonkin verran vetoja
    "wet"  = paljon vetoja (JT9, kaksivärinen)
    """
    if len(board) < 3:
        return "dry"

    ranks = [c[0] for c in board]
    suits = [c[1] for c in board]

    # samaa maata
    max_suit = max(suits.count(s) for s in set(suits))

    # peräkkäisiä rankeja
    rank_order = "23456789TJQKA"
    idx = sorted(rank_order.index(r) for r in ranks)
    gaps = max(idx) - min(idx)

    if max_suit >= 3 or gaps <= 4:
        return "wet"
    elif max_suit == 2 or gaps <= 6:
        return "semi"
    else:
        return "dry"


def detect_draws(board):
    """
    Palauttaa dict:
    {
        "flush_draw": bool,
        "straight_draw": bool
    }
    """
    if len(board) < 3:
        return {"flush_draw": False, "straight_draw": False}

    ranks = [c[0] for c in board]
    suits = [c[1] for c in board]

    # --- Flush draw ---
    flush_draw = any(suits.count(s) >= 2 for s in set(suits))

    # --- Straight draw ---
    rank_order = "23456789TJQKA"
    idx = sorted(set(rank_order.index(r) for r in ranks))
    straight_draw = False
    for i in range(len(idx) - 1):
        if idx[i + 1] - idx[i] <= 2:
            straight_draw = True
            break

    return {
        "flush_draw": flush_draw,
        "straight_draw": straight_draw,
    }

# NOTE: apply_folds is currently unused (kept for future alternative sim mode)

def apply_folds(
    active,
    profile_attr,
    board,
    evaluator,
    pressure,
    street,
    post_d1=False,   # 🔥 UUSI
):
    remaining = []

    texture = board_texture(board)
    draws = detect_draws(board)

    for hand, profile, committed in active:
        strength = hand_strength_bucket(hand, board, evaluator)
        base_fold = getattr(profile, profile_attr, 50) / 100.0

        # --- perus fold ---
        if strength == 0:
            fold_chance = base_fold * 1.2
        elif strength == 1:
            fold_chance = base_fold * 0.7
        elif strength == 2:
            fold_chance = base_fold * 0.25
        else:
            fold_chance = 0.02

        # --- pressure ---
        fold_chance *= (1 + 0.25 * pressure)

        # --- board texture ---
        if texture == "wet":
            fold_chance *= 0.7
        elif texture == "semi":
            fold_chance *= 0.85

        # --- draw-vaikutus ---
        if draws["flush_draw"]:
            fold_chance *= 0.75
        if draws["straight_draw"]:
            fold_chance *= 0.80

        # --- committed ---
        if committed:
            fold_chance *= 0.3

        # --- river call-down ---
        if street == "river" and strength >= 1:
            fold_chance *= 0.15

        # ==================================================
        # 🔥 D1-KORJAUS: post-D1 fold on vain psykologinen
        # ==================================================
        if post_d1:
            fold_chance *= 0.25

        if random.random() > min(fold_chance, 0.75):
            new_committed = committed or street in ("turn", "river")
            remaining.append((hand, profile, new_committed))

    return remaining


# ======================================================
# YKSITTÄINEN SIMULAATIO
# ======================================================
"""
NOTE:
In heads-up simulations hero often realizes EV via fold equity.
This may result in 0% showdown equity with very high non-showdown win rate.
This is expected behavior, not a bug.
"""

def simulate_postflop_once(
    hero_hand,
    fixed_board,
    opponents,
    evaluator,
    hero_strategy=None,
    vpip_tracker=None,
):
    if hero_strategy is None:
        hero_strategy = HeroStrategyProfile()

    deck = FULL_DECK.copy()
    # --- Blindit ---
    SB = 0.5
    BB = 1.0

    hero_invested = BB
    pot_size = SB + BB
    STACK = 100.0
    hero_stack = STACK - hero_invested


    for c in hero_hand:
        deck.remove(c)

    board = fixed_board.copy()
    for c in board:
        deck.remove(c)

    dead_cards = set(hero_hand + board)
    active = []

    # ==================================================
    # PRE-FLOP
    # ==================================================
    for player, position in opponents:
        profile = player.get_profile(position)

        if vpip_tracker is not None:
            vpip_tracker["total"] += 1

        if random.random() > (profile.vpip / 100.0):
            continue

        if vpip_tracker is not None:
            vpip_tracker["played"] += 1

        range_spec = generate_profile_range(profile, position)
        combos, weights = [], []

        for hand_code, weight in range_spec.items():
            for c1, c2 in generate_combos(hand_code):
                if c1 in dead_cards or c2 in dead_cards:
                    continue
                combos.append((c1, c2))
                weights.append(weight)

        if not combos:
            continue

        hand = weighted_choice(combos, weights)

        # 🔒 turvallinen deck-poisto
        if hand[0] not in deck or hand[1] not in deck:
            continue

        deck.remove(hand[0])
        deck.remove(hand[1])
        dead_cards.update(hand)
        active.append((hand, profile, False))

    # 🔴 PRE-FLOP LOPPUTARKISTUS
    if not active:
        # Hero voittaa blindit, mutta on jo maksanut BB:n
        return "win_noshowdown", "preflop", pot_size - hero_invested

    # 🔑 Määrittele HU/MW tila kerran ja päivitä aina streetien välissä
    # 🔒 Lukitaan HU-status koko kädelle
    is_heads_up_hand = (len(opponents) == 1)


    random.shuffle(deck)

    hero_model = HeroDecisionModel()   # ✅ AINA määritelty
    pressure = 0

    # ==================================================
    # FLOP
    # ==================================================
    is_heads_up_hand = (len(active) == 1)

    
    while len(board) < 3:
        board.append(deck.pop())

    texture = board_texture(board)
    pressure = 1

    bet = street_bet_size(
        "flop",
        pot_size,
        texture,
        aggression=hero_strategy.aggression,
    )
    bet = min(bet, hero_stack)

    hero_strength = hand_strength_bucket(hero_hand, board, evaluator)

    opp_fold = sum(p.fold_flop for _, p, _ in active) / max(1, 100 * len(active))
    opp_fold = max(0.25, min(opp_fold, 0.55))

    if hero_strength == 0:
        base_continue = 0.55
        if is_heads_up_hand:
            base_continue = 0.80   # 🔥 HU: floatataan

        if not (
            random.random() < base_continue
            or hero_model.should_continue("flop", pressure, opp_fold, texture)
        ):
            return "loss_noshowdown", "flop", -hero_invested

    hero_invested += bet
    hero_stack -= bet
    pot_size += bet

    callers = []
    for hand, profile, committed in active:
        calls, _ = opponent_call_decision(
            hand, board, "flop", pot_size, bet, texture, pressure,
            aggression=profile.aggression / 100.0,
        )
        if calls:
            callers.append((hand, profile, committed))
            pot_size += bet

    active = callers
    if not active:
        return "win_noshowdown", "flop", pot_size - hero_invested

    is_heads_up_hand = (len(active) == 1)
    if is_heads_up_hand:
        print("[DEBUG FLOP HU ACTIVE]")

    # ==================================================
    # TURN
    # ==================================================
    while len(board) < 4:
        board.append(deck.pop())

    texture = board_texture(board)
    pressure += 1

    bet = street_bet_size(
        "turn",
        pot_size,
        texture,
        aggression=hero_strategy.aggression,
    )
    bet = min(bet, hero_stack)

    hero_strength = hand_strength_bucket(hero_hand, board, evaluator)

    opp_fold = sum(p.fold_turn for _, p, _ in active) / max(1, 100 * len(active))

    if hero_strength == 0:
        base_continue = 0.45
        if is_heads_up_hand:
            base_continue = 0.70   # 🔥 HU: bluffcatch

        if not (
            random.random() < base_continue
            or hero_model.should_continue("turn", pressure, opp_fold, texture)
        ):
            return "loss_noshowdown", "turn", -hero_invested

    hero_invested += bet
    hero_stack -= bet
    pot_size += bet

    callers = []
    for hand, profile, committed in active:
        calls, _ = opponent_call_decision(
            hand, board, "turn", pot_size, bet, texture, pressure,
            aggression=profile.aggression / 100.0,
        )
        if calls:
            callers.append((hand, profile, committed))
            pot_size += bet

    active = callers
    if not active:
        # DEBUG: pakota river
        pass

    is_heads_up_hand = (len(active) == 1)

    # ==================================================
    # RIVER
    # ==================================================

    # 🔹 Täydennä board ensin
    while len(board) < 5:
        board.append(deck.pop())

    hero_strength = hand_strength_bucket(hero_hand, board, evaluator)
    is_heads_up_hand = (len(active) == 1)

    # ================================
    # D1: Unified HU showdown decision
    # ================================
    force_showdown = False

    if is_heads_up_hand:
        pot_pressure = pot_size / max(1.0, pot_size + hero_stack)

        base_sd_prob = {
            0: 0.05,
            1: 0.15,
            2: 0.35,
            3: 0.65,
        }.get(hero_strength, 0.0)

        sd_prob = min(0.85, base_sd_prob + 0.4 * pot_pressure)

        if random.random() < sd_prob:
            force_showdown = True

    river_profile = HU_RIVER_PROFILE if is_heads_up_hand else MW_RIVER_PROFILE

    bet = street_bet_size(
        "river",
        pot_size,
        board_texture(board),
        aggression=hero_strategy.aggression,
    )
    bet = min(bet, hero_stack)

    # --------------------------------------------------
    # 1) OPPONENT BETS
    # --------------------------------------------------
    river_betters = []

    for hand, profile, committed in active:
        opp_strength = hand_strength_bucket(hand, board, evaluator)

        if is_heads_up_hand:
            value_prob = 0.65 if opp_strength >= 2 else 0.20
            bluff_prob = 0.35 * (0.5 + profile.aggression / 100.0)
        else:
            value_prob = 0.70 if opp_strength >= 2 else 0.0
            bluff_prob = river_profile["bluff_freq"] * (0.5 + profile.aggression / 100.0)

        if random.random() < (value_prob + bluff_prob):
            river_betters.append((hand, profile, committed))

    # --------------------------------------------------
    # 2) HERO FACES BET
    # --------------------------------------------------
    if river_betters:
        if is_heads_up_hand:
            call_cost = bet
            pot_after_call = pot_size + bet
            pot_odds = call_cost / max(1.0, pot_after_call)

            HU_EQUITY_ESTIMATE = {
                0: 0.05,
                1: 0.25,
                2: 0.55,
                3: 0.80,
            }

            est_equity = HU_EQUITY_ESTIMATE.get(hero_strength, 0.0)

            bluff_pressure = min(
                0.25,
                river_profile["bluff_freq"]
                * (0.5 + river_betters[0][1].aggression / 100.0)
            )

            effective_equity = min(0.95, est_equity + bluff_pressure)
            hero_calls = effective_equity >= pot_odds
        else:
            if hero_strength >= 2:
                hero_calls = True
            elif hero_strength == 1:
                hero_calls = random.random() < (
                    river_profile["call_down"] * hero_strategy.call_down
                )
            else:
                hero_calls = False

        if hero_calls:
            hero_invested += bet
            hero_stack -= bet
            pot_size += bet
            active = river_betters
            force_showdown = True

    # --------------------------------------------------
    # 3) EI BETTIÄ → HERO BET / CHECK
    # --------------------------------------------------
    else:
        hero_bets = False
        call_prob = 0.0

        if hero_strength >= 3:
            hero_bets = True
            call_prob = 0.75
        elif hero_strength == 2:
            hero_bets = random.random() < river_profile["value_bet_thin"]
            call_prob = 0.55
        elif hero_strength == 1:
            hero_bets = random.random() < (
                river_profile["bluff_freq"] * hero_strategy.bluff_freq
            )
            call_prob = 0.35

        if hero_bets:
            hero_invested += bet
            hero_stack -= bet
            pot_size += bet

            callers = []
            for hand, profile, committed in active:
                opp_strength = hand_strength_bucket(hand, board, evaluator)
                if opp_strength >= hero_strength and random.random() < call_prob:
                    callers.append((hand, profile, committed))
                    pot_size += bet

            if callers:
                active = callers
                force_showdown = True
            else:
                # hero bet, kaikki foldaa → EI showdownia
                return "win_noshowdown", "river", pot_size - hero_invested

        else:
            # hero check
            if is_heads_up_hand:
                # HU check–check → showdown
                force_showdown = True
            else:
                # MW check–check → non-showdown
                return "win_noshowdown", "river", pot_size - hero_invested


    

    # ==================================================
    # RIVER END: FINAL DECISION
    # ==================================================
    
    if is_heads_up_hand:
        force_showdown = True


    
    if force_showdown:
        # jatketaan showdowniin
        pass
    else:
        return "win_noshowdown", "river", pot_size - hero_invested

    # DEBUG: pakota HU aina showdowniin riverissä

    # ==================================================
    # SHOWDOWN
    # ==================================================
    assert_unique_cards(hero_hand, board, *[h for h, _, _ in active])

    board_cards = [TreysCard.new(c) for c in board]
    hero_cards = [TreysCard.new(c) for c in hero_hand]
    hero_value = evaluator.evaluate(board_cards, hero_cards)

    hero_best = hero_value
    tie = False

    for hand, _, _ in active:
        opp_cards = [TreysCard.new(c) for c in hand]
        opp_value = evaluator.evaluate(board_cards, opp_cards)

        if opp_value < hero_best:
            return "loss", None, -hero_invested
        elif opp_value == hero_best:
            tie = True

    if tie:
        return "tie", None, (pot_size / 2) - hero_invested
    else:
        return "win", None, pot_size - hero_invested


   
# ======================================================
# KOKONAISSIMULAATIO
# ======================================================

def run_simulation(config: SimulationConfig) -> List[SimulationResult]:

    if config.random_seed is not None:
        random.seed(config.random_seed)

    assert_unique_cards(config.hero_hand, config.board)

    evaluator = Evaluator()
    results = []

    hero_position = config.position or "BTN"
    max_opps = min(6, len(config.opponent_profiles))

    for opp_count in range(1, max_opps + 1):

        # =========================
        # INIT
        # =========================
        wins = losses = 0
        non_sd_wins = 0
        showdown_wins = showdown_losses = showdown_hands = 0

        total_net_bb = 0.0
        non_sd_net_bb = 0.0
        showdown_net_bb = 0.0
        hands_played = 0   # 🔥 UUSI: oikea käsilaskuri


        vpip_tracker = {"total": 0, "played": 0}

        opponents = [
            (player, hero_position)
            for player in config.opponent_profiles[:opp_count]
        ]

        # =========================
        # SIM LOOP
        # =========================
        for _ in range(config.iterations):
            hands_played += 1   # 🔥 LISÄTTY

            result, street, net_bb = simulate_postflop_once(
                hero_hand=config.hero_hand,
                fixed_board=config.board,
                opponents=opponents,
                evaluator=evaluator,
                vpip_tracker=vpip_tracker,
            )

            total_net_bb += net_bb

            # --- showdown vs non-SD ---
            if result in ("win", "loss", "tie"):
                showdown_hands += 1
                showdown_net_bb += net_bb

                if result == "win":
                    showdown_wins += 1
                    wins += 1
                elif result == "loss":
                    showdown_losses += 1
                    losses += 1
                elif result == "tie":
                    showdown_wins += 0.5
                    showdown_losses += 0.5
                    wins += 1
                    losses += 1

            else:
                non_sd_net_bb += net_bb

                if result == "win_noshowdown":
                    wins += 1
                    non_sd_wins += 1
                elif result == "loss_noshowdown":
                    losses += 1

        # =========================
        # METRICS
        # =========================
        total_hands = hands_played   # ✅ OIKEA käsimäärä
        showdown_total = showdown_wins + showdown_losses


        showdown_equity = (
            showdown_wins / showdown_total * 100
            if showdown_total else 0.0
        )

        non_sd_pct = (
            non_sd_wins / total_hands * 100
            if total_hands else 0.0
        )

        ev_per_hand = total_net_bb / total_hands
        bb_per_100 = ev_per_hand * 100

        mode = "HU" if opp_count == 1 else "MW"

        # =========================
        # OUTPUT
        # =========================
        print(
            f"[{mode}] Opponents: {opp_count} | "
            f"EV/hand: {ev_per_hand:.3f} bb | "
            f"bb/100: {bb_per_100:.2f} | "
            f"SD EQ: {showdown_equity:.2f}% | "
            f"SD freq: {showdown_hands / max(1, total_hands) * 100:.2f}%"
        )

        results.append(
            SimulationResult(
                opponents=opp_count,
                wins=wins,
                losses=losses,
                ties=0,
                equity=round(showdown_equity, 2),
                non_showdown_win_pct=round(non_sd_pct, 2),
                showdown_win_pct=round(showdown_equity, 2),
            )
        )

    return results




def run_simulation_with_strategies(config: SimulationConfig):
    strategies = {
        "PASSIVE": HeroStrategyProfile(aggression=0.7, bluff_freq=0.6),
        "BASELINE": HeroStrategyProfile(aggression=1.0, bluff_freq=1.0),
        "AGGRESSIVE": HeroStrategyProfile(aggression=1.3, bluff_freq=1.4),
    }

    for name, strategy in strategies.items():
        print("\n" + "=" * 60)
        print(f" HERO STRATEGY: {name}")
        print("=" * 60)

        run_simulation_single_strategy(config, strategy)


def run_simulation_single_strategy(
    config: SimulationConfig,
    hero_strategy: HeroStrategyProfile,
):
    evaluator = Evaluator()
    hero_position = config.position or "BTN"

    for opp_count in range(1, min(3, len(config.opponent_profiles)) + 1):

        wins = losses = 0
        showdown_wins = showdown_losses = showdown_hands = 0
        total_net_bb = 0.0

        vpip_tracker = {"total": 0, "played": 0}

        opponents = [
            (player, hero_position)
            for player in config.opponent_profiles[:opp_count]
        ]

        for _ in range(config.iterations):
            result, street, net_bb = simulate_postflop_once(
                hero_hand=config.hero_hand,
                fixed_board=config.board,
                opponents=opponents,
                evaluator=evaluator,
                hero_strategy=hero_strategy,
                vpip_tracker=vpip_tracker,
            )

            total_net_bb += net_bb

            if result in ("win", "loss", "tie"):
                showdown_hands += 1

            if result == "win":
                wins += 1
                showdown_wins += 1
            elif result == "loss":
                losses += 1
                showdown_losses += 1
            elif result == "tie":
                showdown_wins += 0.5
                showdown_losses += 0.5
                wins += 1
                losses += 1
            elif result == "win_noshowdown":
                wins += 1
            elif result == "loss_noshowdown":
                losses += 1

        total_hands = wins + losses
        ev_per_hand = total_net_bb / max(1, total_hands)
        bb_per_100 = ev_per_hand * 100

        showdown_total = showdown_wins + showdown_losses
        showdown_eq = (
            showdown_wins / showdown_total * 100
            if showdown_total else 0.0
        )

        mode = "HU" if opp_count == 1 else "MW"

        print(
            f"[{mode}] Opponents: {opp_count} | "
            f"EV/hand: {ev_per_hand:.3f} bb | "
            f"bb/100: {bb_per_100:.1f} | "
            f"SD EQ: {showdown_eq:.1f}% | "
            f"SD freq: {showdown_hands / total_hands * 100:.1f}%"
        )

