# -*- coding: utf-8 -*-
from typing import Dict, Optional
from engine.player_profile import PlayerProfile


class PositionalPlayer:
    """
    Vastustaja, jolla voi olla eri profiili eri positioissa.
    """

    def __init__(
        self,
        name: str,
        profiles_by_position: Dict[str, PlayerProfile],
        default_profile: Optional[PlayerProfile] = None,
    ):
        self.name = name
        self.profiles_by_position = profiles_by_position
        self.default_profile = default_profile or PlayerProfile()

    def get_profile(self, position: str) -> PlayerProfile:
        return self.profiles_by_position.get(position, self.default_profile)

    def summary(self) -> str:
        lines = [f"Player: {self.name}"]
        for pos, profile in self.profiles_by_position.items():
            lines.append(f"  {pos}: {profile}")
        return "\n".join(lines)
