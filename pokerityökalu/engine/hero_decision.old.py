# -*- coding: utf-8 -*-

from engine.player_profile import PlayerProfile


class HeroDecisionModel:
    """
    Vastaa heron päätöksenteosta street-kohtaisesti.
    Tämä on V1-stub: EI vielä vaikuta lopputulokseen.
    """

    def __init__(self, profile: PlayerProfile | None = None):
        self.profile = profile  # talletetaan tulevaa käyttöä varten

    def should_continue(self, street: str, pressure: float) -> bool:
        """
        Palauttaa True jos hero jatkaa (call / bet),
        False jos hero foldaa.

        V1: hero EI KOSKAAN foldata → simulaattori pysyy vakaana
        """
        # Parametrit ovat tarkoituksella käytössä:
        _ = street
        _ = pressure

        return True
