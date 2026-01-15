# engine/hero_decision.py
# engine/hero_decision.py

class HeroDecisionModel:
    def should_continue(
        self,
        street: str,
        pressure: int,
        opp_fold: float,
        board_texture: str,
    ) -> bool:

        if street == "flop":
            base_threshold = 0.25
        elif street == "turn":
            base_threshold = 0.35
        else:
            base_threshold = 0.50

        pressure_penalty = pressure * 0.10

        if board_texture == "wet":
            texture_penalty = 0.15
        elif board_texture == "semi":
            texture_penalty = 0.07
        else:
            texture_penalty = 0.0

        required_fold = (
            base_threshold
            + pressure_penalty
            + texture_penalty
        )

        return opp_fold >= required_fold
