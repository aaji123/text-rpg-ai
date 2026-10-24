"""Parse a bounded subset of tabletop dice notation without evaluating code."""

import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiceResult:
    """Keep a roll's notation and individual dice visible for transparent play."""

    notation: str
    rolls: list[int]
    modifier: int
    total: int


def roll_dice(notation: str) -> DiceResult:
    """Roll standard NdM notation with an optional signed modifier safely."""

    match = re.fullmatch(r"\s*(\d{1,2})d(\d{1,5})([+-]\d{1,5})?\s*", notation.lower())
    if not match:
        raise ValueError("Use dice notation such as 1d20 or 2d6+3.")
    count, sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3) or 0)
    if count < 1 or count > 20 or sides < 2 or sides > 10000 or abs(modifier) > 10000:
        raise ValueError("Roll limits are 1–20 dice, 2–10,000 sides, and modifiers up to 10,000.")
    rolls = [random.randint(1, sides) for _ in range(count)]
    return DiceResult(notation.strip().lower(), rolls, modifier, sum(rolls) + modifier)
