import random


def assert_unique_cards(*card_lists):
    all_cards = []
    for lst in card_lists:
        all_cards.extend(lst)

    if len(all_cards) != len(set(all_cards)):
        raise ValueError(f"Duplikaattikortti havaittu: {all_cards}")

def weighted_choice(items, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for item, w in zip(items, weights):
        upto += w
        if upto >= r:
            return item
