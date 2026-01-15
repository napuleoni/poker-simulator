# -*- coding: utf-8 -*-



class HeroStrategyProfile:
    def __init__(
        self,
        aggression: float = 1.0,     # bet sizing & bluff freq
        bluff_freq: float = 1.0,     # bluffien todennäköisyys
        call_down: float = 1.0,      # river call willingness
    ):
        self.aggression = aggression
        self.bluff_freq = bluff_freq
        self.call_down = call_down
