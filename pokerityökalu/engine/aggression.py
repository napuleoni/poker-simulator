# -*- coding: utf-8 -*-



import random

class AggressionModel:
    """
    Mallintaa vastustajan aggressiivisen käyttäytymisen
    mukaan lukien bluffibarrelit.
    """

    @staticmethod
    def reacts(profile, street: str):
        """
        Palauttaa: 'fold', 'call', 'raise'
        """
        aggr = profile.aggression / 100.0

        r = random.random()

        if r < aggr * 0.4:
            return "raise"
        elif r < aggr:
            return "call"
        else:
            return "fold"

    @staticmethod
    def barrel_with_bluff(profile, street: str):
        """
        Palauttaa True jos vastustaja barreloi,
        mukaan lukien bluffit.
        """

        # perus barrel-prosentti
        base = profile.aggression / 100.0

        # bluffiosuus (löysät bluffaa enemmän)
        bluff_factor = (100 - profile.vpip) / 100.0

        if street == "turn":
            prob = base * 0.6 + bluff_factor * 0.15
        elif street == "river":
            prob = base * 0.4 + bluff_factor * 0.10
        else:
            prob = base * 0.5

        return random.random() < prob
