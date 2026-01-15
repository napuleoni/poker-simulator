

import random
from treys import Card as TreysCard, Evaluator
MODE = "PLAY"   # "PLAY" = fold-logiikka päällä

def ask_mode():
    """
    Kysyy käyttäjältä simulaatiomoodin.
    Palauttaa: "SHOWDOWN" tai "PLAY"
    """
    while True:
        mode = input(
            "Valitse simulaatiomoodi:\n"
            "  1 = SHOWDOWN (puhdas equity)\n"
            "  2 = PLAY (fold-logiikka mukana)\n"
            "Valinta (1/2): "
        ).strip()

        if mode == "1":
            return "SHOWDOWN"
        if mode == "2":
            return "PLAY"

        print("Virheellinen valinta, anna 1 tai 2.")



def simulate_once(player_hand, fixed_board, opponent_range, players, evaluator):
    # --- Alustus ---
    deck = FULL_DECK.copy()

    # Poista heron kortit
    for c in player_hand:
        deck.remove(c)

    # Board (flop/turn/river valmiina tai tyhjä)
    board = fixed_board.copy()
    for c in board:
        deck.remove(c)

    dead_cards = set(player_hand + board)

    opponents = []

    # --- Vastustajien kädet ---
    for opp_i in range(players - 1):

        if opp_i == 0:
            range_spec = opponent_range
        elif opp_i <= 2:
            range_spec = normalize_range(top_percent_range(25))
        else:
            range_spec = normalize_range(top_percent_range(40))

        combos = []
        weights = []

        for hand_code, weight in range_spec.items():
            for combo in generate_combos(hand_code):

                if combo[0] in dead_cards or combo[1] in dead_cards:
                    continue

                bw = hand_board_weight(combo, board, hero_hand=player_hand)

                if bw <= 0:
                    continue

                final_weight = max(weight * bw, 0.001)

                combos.append(combo)
                weights.append(final_weight)

        # Failsafe
        if not combos:
            return None

        hand = weighted_choice(combos, weights)
        opponents.append(hand)

        for c in hand:
            deck.remove(c)
            dead_cards.add(c)

    # --- FLOP ---
    random.shuffle(deck)
    while len(board) < 3:
        board.append(deck.pop())

    if MODE == "PLAY":
        opponents = [
            h for h in opponents
            if opponent_survives_street(h, board, "flop")
        ]
        if not opponents:
            return "win"

    # --- TURN ---
    if len(board) < 4:
        board.append(deck.pop())

    if MODE == "PLAY":
        opponents = [
            h for h in opponents
            if opponent_survives_street(h, board, "turn")
        ]
        if not opponents:
            return "win"

    # --- RIVER ---
    if len(board) < 5:
        board.append(deck.pop())

    if MODE == "PLAY":
        opponents = [
            h for h in opponents
            if opponent_survives_street(h, board, "river")
        ]
        if not opponents:
            return "win"

    # --- Showdown ---
    assert_unique_cards(player_hand, board, *opponents)

    board_cards = [TreysCard.new(c) for c in board]
    hero_cards = [TreysCard.new(c) for c in player_hand]
    hero_value = evaluator.evaluate(board_cards, hero_cards)

    best = True
    tie = False

    for opp in opponents:
        opp_cards = [TreysCard.new(c) for c in opp]
        opp_value = evaluator.evaluate(board_cards, opp_cards)

        if opp_value < hero_value:
            best = False
            break
        elif opp_value == hero_value:
            tie = True

    if best and not tie:
        return "win"
    elif best and tie:
        return "tie"
    else:
        return "loss"


def simulate_preflop_once(player_hand, opponent_counts, position):
    """
    Simuloi yhden preflop-jaon ilman boardia.
    Palauttaa: "win", "tie" tai "loss"
    """

    # Kopioidaan pakka
    deck = FULL_DECK.copy()

    # Poista hero-kortit
    for c in player_hand:
        deck.remove(c)

    dead_cards = set(player_hand)

    # Vastustajat
    opponents = []


    # Jaetaan vastustajille kadet rangesta
    for opp_i in range(opponent_counts):
        range_spec = opponent_range_for_index(opp_i, position)
        combos = build_range_combos(range_spec, dead_cards)

        if not combos:
            return None

    # Preflop: käytetään vain rangepainoja
        combo_weights = []

        for combo in combos:
            r1 = combo[0][0]
            r2 = combo[1][0]

            if r1 == r2:
                code = r1 + r2
            elif combo[0][1] == combo[1][1]:
                code = r1 + r2 + "s"
            else:
                code = r1 + r2 + "o"

            combo_weights.append(range_spec.get(code, 1.0))

        hand = random.choices(combos, weights=combo_weights, k=1)[0]
        opponents.append(hand)

        for c in hand:
            deck.remove(c)
            dead_cards.add(c)

    # --- Preflop equitylogiikka ---
    # Jaetaan taysi board VAIN evaluointia varten
    board = random.sample(deck, 5)

    evaluator = Evaluator()

    board_cards = [TreysCard.new(c) for c in board]
    hero_cards = [TreysCard.new(c) for c in player_hand]
    hero_value = evaluator.evaluate(board_cards, hero_cards)

    best = True
    tie = False

    for opp in opponents:
        opp_cards = [TreysCard.new(c) for c in opp]
        opp_value = evaluator.evaluate(board_cards, opp_cards)

        if opp_value < hero_value:
            best = False
            break
        elif opp_value == hero_value:
            tie = True

    if best and not tie:
        return "win"
    elif best and tie:
        return "tie"
    else:
        return "loss"

def opponent_action(weight):
    """
    Palauttaa True jos vastustaja jatkaa (call),
    False jos foldaa.
    """

    # Vahva osuma
    if weight >= 1.4:
        return True

    # Keskitaso: satunnainen jatko
    if weight >= 0.9:
        return random.random() < 0.6

    # Heikko: harvoin jatkaa
    if weight >= 0.6:
        return random.random() < 0.25

    # Täysin ohi
    return False


# ---------- CARD ENGINE ----------
from dataclasses import dataclass

@dataclass(frozen=True)
class PreflopHand:
    code: str  # esim "AA", "AKs", "AKo"

    def is_pair(self):
        return len(self.code) == 2

    def is_suited(self):
        return self.code.endswith("s")

    def is_offsuit(self):
        return self.code.endswith("o")

    def ranks(self):
        return self.code[0], self.code[1]

def generate_preflop_combos(hand: PreflopHand):
    r1, r2 = hand.ranks()
    combos = []

    if hand.is_pair():
        # AA = 6 kombinaatiota
        for i in range(len(SUITS)):
            for j in range(i + 1, len(SUITS)):
                combos.append((r1 + SUITS[i], r2 + SUITS[j]))

    elif hand.is_suited():
        # AKs = 4 kombinaatiota
        for s in SUITS:
            combos.append((r1 + s, r2 + s))

    else:
        # AKo = 12 kombinaatiota
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append((r1 + s1, r2 + s2))

    return combos

def filter_dead_combos(combos, dead_cards):
    dead = set(dead_cards)
    return [
        combo for combo in combos
        if combo[0] not in dead and combo[1] not in dead
    ]


RANKS = "23456789TJQKA"
SUITS = "shdc"

FULL_DECK = [r + s for r in RANKS for s in SUITS]


def precompute_range_combos():
    """
    Rakentaa kaikki ranget valmiiksi ilman dead cardeja
    """
    cache = {}

    positions = ["UTG", "MP", "CO", "BTN", "SB", "BB"]

    for pos in positions:
        range_codes = position_range(pos)
        combos = []
        for code in range_codes:
            combos.extend(generate_combos(code))
        cache[pos] = combos

    # yleiset ranget vastustajille
    cache["MID"] = []
    for code in top_percent_range(25):
        cache["MID"].extend(generate_combos(code))

    cache["LOOSE"] = []
    for code in top_percent_range(40):
        cache["LOOSE"].extend(generate_combos(code))

    return cache


RANGE_COMBO_CACHE = {}

def compute_preflop_equity(hero_hand, opp_count, hero_position, boards_per_matchup=20):
    """
    Laskee preflop-equityn combinatoriikalla.
    Ei Monte Carloa vastustajan käsille.
    """

    evaluator = Evaluator()

    hero_cards = [TreysCard.new(c) for c in hero_hand]

    wins = losses = ties = 0

    # Hero ei blokkaa itseään
    dead_cards_base = set(hero_hand)

    # Rakennetaan vastustajien ranget combinatoriikkana
    opponent_ranges = []

    for i in range(opp_count):
        range_codes = opponent_range_for_index(i, hero_position)

        combos = []
        for code in range_codes:
            hand = PreflopHand(code)
            combos.extend(generate_preflop_combos(hand))

        # filtteri hero-blokkereille
        combos = filter_dead_combos(combos, dead_cards_base)

        if not combos:
            return None

        opponent_ranges.append(combos)

    # 🔁 Kaydaan LAPI KAIKKI vastustajan kasiyhdistelmat
    from itertools import product

    for opp_hands in product(*opponent_ranges):

        # tarkista ettei vastustajat blokkaa toisiaan
        flat = [c for h in opp_hands for c in h]
        if len(flat) != len(set(flat)):
            continue

        dead_cards = dead_cards_base.union(flat)

        # 🎲 boardit vain evaluointia varten
        deck = [c for c in FULL_DECK if c not in dead_cards]

        for _ in range(boards_per_matchup):
            board = random.sample(deck, 5)

            board_cards = [TreysCard.new(c) for c in board]
            hero_value = evaluator.evaluate(board_cards, hero_cards)

            best = True
            tie = False

            for opp in opp_hands:
                opp_cards = [TreysCard.new(c) for c in opp]
                opp_value = evaluator.evaluate(board_cards, opp_cards)

                if opp_value < hero_value:
                    best = False
                    break
                elif opp_value == hero_value:
                    tie = True

            if best and not tie:
                wins += 1
            elif best and tie:
                ties += 1
            else:
                losses += 1

    total = wins + losses + ties
    if total == 0:
        return None

    return (wins + ties * 0.5) / total * 100


# ---------- RANGE-APUFUNKTIOT ----------

def weighted_choice(items, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for item, w in zip(items, weights):
        upto += w
        if upto >= r:
            return item


def normalize_range(range_input):
    """
    Muuntaa ranget yhtenäiseen RangeSpec-muotoon.
    Hyväksyy:
    - list[str]
    - dict[str, float]
    """
    if isinstance(range_input, dict):
        return dict(range_input)

    if isinstance(range_input, list):
        return {hand: 1.0 for hand in range_input}

    raise TypeError("Tuntematon range-muoto")


def generate_combos(hand_code):
    ranks = hand_code.replace("s", "").replace("o", "")
    r1, r2 = ranks[0], ranks[1]
    suits = ["s", "h", "d", "c"]

    combos = []

    if r1 == r2:
        # Parit: 6 kombinaatiota
        for i in range(len(suits)):
            for j in range(i + 1, len(suits)):
                combos.append([r1 + suits[i], r2 + suits[j]])

    elif hand_code.endswith("s"):
        # Suited: 4 kombinaatiota
        for s in suits:
            combos.append([r1 + s, r2 + s])

    else:
        # Offsuit: 12 kombinaatiota
        for s1 in suits:
            for s2 in suits:
                if s1 != s2:
                    combos.append([r1 + s1, r2 + s2])

    return combos



def top_percent_range(percent):
    base_hands = (
        ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22"] +
        ["AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"] +
        ["AKo", "AQo", "AJo", "KQo"]
    )

    cutoff = int(len(base_hands) * percent / 100)
    return base_hands[:cutoff]



def assert_unique_cards(*card_lists):
    all_cards = []
    for lst in card_lists:
        all_cards.extend(lst)

    if len(all_cards) != len(set(all_cards)):
        raise ValueError(f"Duplikaattikortti havaittu: {all_cards}")


   

def position_range(position):
    position = position.strip().upper()
    base = []

    if position == "UTG":
        base = top_percent_range(12)
    elif position == "MP":
        base = top_percent_range(18)
    elif position == "CO":
        base = top_percent_range(25)
    elif position == "BTN":
        base = top_percent_range(45)
    elif position == "SB":
        base = top_percent_range(35)
    elif position == "BB":
        base = top_percent_range(30)
    else:
        raise ValueError("Tuntematon positio")

    weighted = {}
    for hand in base:
        category = classify_hand(hand)
        weighted[hand] = HAND_WEIGHTS[category]

    return weighted


def opponent_range_for_index(i, hero_position):
    """
    Palauttaa vastustajan rangen indeksin perusteella.
    i = 0 on lähin vastustaja.
    """
    if i == 0:
        # Lähin vastustaja: sama positiorange kuin hero
        return position_range(hero_position)

    elif i <= 2:
        # Seuraavat: keskirange
        return normalize_range(top_percent_range(25))

    else:
        # Kauempana olevat: löysempi range
        return normalize_range(top_percent_range(40))


def build_range_combos(range_codes, dead_cards):
    key = (tuple(range_codes), tuple(sorted(dead_cards)))
    if key in RANGE_COMBO_CACHE:
        return RANGE_COMBO_CACHE[key]

    suits = ["s", "h", "d", "c"]
    combos = []
    dead = set(dead_cards)

    for code in range_codes:
        r1, r2 = code[0], code[1]

        # Parit
        if len(code) == 2 and r1 == r2:
            for i in range(len(suits)):
                for j in range(i + 1, len(suits)):
                    c1 = r1 + suits[i]
                    c2 = r2 + suits[j]
                    if c1 not in dead and c2 not in dead:
                        combos.append([c1, c2])

        # Suited
        elif code.endswith("s"):
            for s in suits:
                c1 = r1 + s
                c2 = r2 + s
                if c1 not in dead and c2 not in dead:
                    combos.append([c1, c2])

        # Offsuit
        else:
            for s1 in suits:
                for s2 in suits:
                    if s1 != s2:
                        c1 = r1 + s1
                        c2 = r2 + s2
                        if c1 not in dead and c2 not in dead:
                            combos.append([c1, c2])

    RANGE_COMBO_CACHE[key] = combos
    return combos


HAND_WEIGHTS = {
    "premium": 1.0,
    "strong": 0.9,
    "medium": 0.6,
    "speculative": 0.35,
}

def classify_hand(hand_code):
    if hand_code in ["AA", "KK", "QQ", "JJ"]:
        return "premium"
    if hand_code in ["TT", "AKs", "AQs", "AKo"]:
        return "strong"
    if hand_code in ["99", "88", "AJs", "KQs", "ATs"]:
        return "medium"
    return "speculative"

def hand_board_weight(hand, board, hero_hand=None):
    """
    Board-aware + hero-blocker-aware painotus vastustajan kädelle.
    Erityisesti flush-boardeilla.
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
            # Vastustajalla väri
            high_rank = max(ranks, key=lambda r: "23456789TJQKA".index(r))

            # Nut-luokitus
            if high_rank == "A":
                weight *= 3.0
            elif high_rank in ["K", "Q"]:
                weight *= 2.2
            elif high_rank in ["J", "T", "9"]:
                weight *= 1.6
            else:
                weight *= 1.2

            # --- HERO BLOCKER EFFECT ---
            if hero_flush_cards >= 1:
                weight *= 0.75
            if hero_flush_cards >= 2:
                weight *= 0.6

        else:
            # Ei väriä flush-boardilla → heikko, muttei kuollut
            weight *= 0.35


    # --- 3. Pair / set / osumat ---
    for r in ranks:
        if r in board_ranks:
            weight *= 1.3

    if ranks[0] == ranks[1]:
        weight *= 1.25

    # --- 4. Täysin ohi ---
    if (
        not any(r in board_ranks for r in ranks)
        and not flush_suit
    ):
        weight *= 0.5

    return weight

def opponent_survives_street(hand, board, street):
    """
    street: "flop", "turn", "river"
    Palauttaa True jos vastustaja jatkaa
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



# ---------- SYOTTEET ----------

MODE = ask_mode()
print(f"\nSimulaatiomoodi: {MODE}")


player_hand = input("Anna pelaajan kasi (esim. Ah Ad): ").split()
position = input("Anna positio (UTG, MP, CO, BTN, SB, BB): ")
raw_board = input("Anna board (ENTER = preflop): ").strip()
fixed_board = raw_board.split() if raw_board else []
# INVARIANTTI: ei paallekkaisia kortteja syotteissa
assert_unique_cards(player_hand, fixed_board)


# ---------- ASETUKSET ----------





iterations = 5000
opponent_counts = range(1, 7)  # 1-6 vastustajaa


evaluator = Evaluator()
opponent_range = position_range(position)


print("Vastustajan range-koko:", len(opponent_range))

if not fixed_board:
    print("\n--- PREFLOP EQUITY SIMULAATIO ---")
else:
    print("\n--- POSTFLOP EQUITY SIMULAATIO ---")



RANGE_CACHE = precompute_range_combos()



# ---------- SIMULAATIO ----------
MAX_COMBO_OPPONENTS = 2




# ---------- SIMULAATIO ----------

for opp_count in opponent_counts:

    players = opp_count + 1

    # ===== PREFLOP =====
    if not fixed_board:

        MAX_COMBO_OPPONENTS = 2

        if opp_count > MAX_COMBO_OPPONENTS:
            print(
                f"\nVastustajia: {opp_count}"
                f"\n  ⚠️ Preflop combinatoriikka rajattu {MAX_COMBO_OPPONENTS} vastustajaan"
            )
            continue

        equity = compute_preflop_equity(
            player_hand,
            opp_count,
            position,
            boards_per_matchup=20
        )

        print(f"\nVastustajia: {opp_count}")
        if equity is None:
            print("  Ei yhtään kelvollista jakoa")
        else:
            print(f"  Equity: {round(equity, 2)} %")

    # ===== POSTFLOP =====
    else:
        wins = losses = ties = 0

        for _ in range(iterations):
            result = simulate_once(
                player_hand,
                fixed_board,
                opponent_range,
                players,
                evaluator
            )

            if result is None:
                continue

            if result == "win":
                wins += 1
            elif result == "tie":
                ties += 1
            else:
                losses += 1

        total = wins + losses + ties
        if total == 0:
            print(f"\nVastustajia: {opp_count}")
            print("  Ei yhtään kelvollista jakoa")
            continue

        equity = (wins + ties * 0.5) / total * 100

        print(f"\nVastustajia: {opp_count}")
        print(f"  Voitot: {wins}")
        print(f"  Häviöt: {losses}")
        print(f"  Tasapelit: {ties}")
        print(f"  Equity: {round(equity, 2)} %")


