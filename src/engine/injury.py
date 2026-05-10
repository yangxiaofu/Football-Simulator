"""
Injury system: per-play injury check, severity roll, attribute reduction
for career-altering injuries.

Pure math module with no engine dependencies.
"""

import random

from ..utils.constants import (
    BASE_INJURY_RATE,
    INJURY_MULTIPLIERS,
    INJURY_SEVERITY_WEIGHTS,
    INJURY_DURATION,
    DURABILITY_MODIFIER_TABLE,
    CAREER_ALTERING_REDUCTION,
)


def get_durability_modifier(durability_rating: int) -> float:
    """
    Map a player's durability rating to an injury rate multiplier.

    Higher durability = lower injury chance.

    Args:
        durability_rating: Player's true_durability (1-99)

    Returns:
        Multiplier (0.5 for elite, up to 1.8 for fragile)
    """
    for threshold, modifier in DURABILITY_MODIFIER_TABLE:
        if durability_rating >= threshold:
            return modifier
    return 1.8  # Worst case


def check_injury(
    durability_rating: int,
    fatigue_multiplier: float = 1.0,
    situation: str = None,
) -> bool:
    """
    Roll whether an injury occurs on this play.

    P(injury) = BASE_RATE * durability_mod * fatigue_mod * situation_mod

    Args:
        durability_rating: Player's true_durability
        fatigue_multiplier: From fatigue system (1.0 = normal, up to 2.0)
        situation: Optional situation key (e.g., 'sack', 'goal_line')

    Returns:
        True if injury occurs
    """
    dur_mod = get_durability_modifier(durability_rating)
    sit_mod = INJURY_MULTIPLIERS.get(situation, 1.0) if situation else 1.0

    injury_prob = BASE_INJURY_RATE * dur_mod * fatigue_multiplier * sit_mod
    return random.random() < injury_prob


def roll_severity() -> dict:
    """
    Determine injury severity when an injury occurs.

    Uses weighted random selection from 6 severity tiers.

    Returns:
        dict with:
            'severity': str (e.g., 'questionable', 'ir_season_ending')
            'weeks_out': int (duration in weeks)
            'is_career_altering': bool
            'is_career_ending': bool
            'attribute_reduction': int (0 unless career-altering)
    """
    # Weighted selection
    severities = list(INJURY_SEVERITY_WEIGHTS.keys())
    weights = list(INJURY_SEVERITY_WEIGHTS.values())
    severity = random.choices(severities, weights=weights, k=1)[0]

    # Duration
    min_weeks, max_weeks = INJURY_DURATION[severity]
    weeks_out = random.randint(min_weeks, max_weeks)

    # Career impact
    is_career_altering = severity == 'career_altering'
    is_career_ending = severity == 'career_ending'
    attribute_reduction = 0

    if is_career_altering:
        attribute_reduction = random.randint(
            CAREER_ALTERING_REDUCTION[0],
            CAREER_ALTERING_REDUCTION[1],
        )

    return {
        'severity': severity,
        'weeks_out': weeks_out,
        'is_career_altering': is_career_altering,
        'is_career_ending': is_career_ending,
        'attribute_reduction': attribute_reduction,
    }


def apply_injury(player_data: dict, injury_result: dict) -> dict:
    """
    Apply injury effects to a player's in-game state.

    Args:
        player_data: Mutable player dict (in-game representation)
        injury_result: Result from roll_severity()

    Returns:
        Updated player_data with injury flags set
    """
    player_data['is_injured'] = True
    player_data['injury_severity'] = injury_result['severity']
    player_data['injury_weeks_remaining'] = injury_result['weeks_out']

    if injury_result['is_career_ending']:
        player_data['is_active'] = False
        player_data['roster_status'] = 'retired'

    return player_data


def get_injury_status_for_db(severity: str) -> str:
    """
    Map internal severity to the DB injury_status column value.

    Args:
        severity: Internal severity key

    Returns:
        DB-compatible injury_status string
    """
    status_map = {
        'questionable': 'questionable',
        'week_to_week': 'out',
        'ir_short': 'out',
        'ir_season_ending': 'out',
        'career_altering': 'out',
        'career_ending': 'out',
    }
    return status_map.get(severity, 'questionable')
