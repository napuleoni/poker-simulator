# -*- coding: utf-8 -*-


# engine/pressure_model.py

class PressureModel:
    """
    Mallintaa panostuksen aiheuttamaa painetta eri streeteill�.
    Arvot ovat 0.0�1.0 (lis� fold-todenn�k�isyyteen).
    """

    FLOP_PRESSURE = 0.10
    TURN_PRESSURE = 0.20
    RIVER_PRESSURE = 0.35

    @classmethod
    def for_street(cls, street: str) -> float:
        if street == "flop":
            return cls.FLOP_PRESSURE
        elif street == "turn":
            return cls.TURN_PRESSURE
        elif street == "river":
            return cls.RIVER_PRESSURE
        return 0.0
