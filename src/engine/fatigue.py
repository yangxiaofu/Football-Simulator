"""
Fatigue system: per-snap stamina drain, fatigue penalty calculation,
and season wear application.

Pure math module with no engine dependencies.
"""

from ..utils.constants import (
    STAMINA_MAX,
    STAMINA_MILD_THRESHOLD,
    STAMINA_MODERATE_THRESHOLD,
    STAMINA_SEVERE_THRESHOLD,
    STAMINA_PENALTIES,
    STAMINA_DRAIN_PER_SNAP,
    HIGH_EFFORT_STAMINA_DRAIN,
    SEASON_WEAR_START_WEEK,
    SEASON_WEAR_PER_WEEK,
    FATIGUE_INJURY_MULTIPLIER,
    SUBSTITUTION_THRESHOLDS,
)


def get_fatigue_penalty(stamina: float) -> int:
    """
    Get the rating penalty based on current stamina level.

    Thresholds:
        100-60: No penalty
        59-40:  -3 (mild)
        39-20:  -8 (moderate)
        <20:    -15 (severe) + double injury rate

    Args:
        stamina: Current stamina (0-100)

    Returns:
        Negative integer to apply to all ratings (0, -3, -8, or -15)
    """
    if stamina >= STAMINA_MILD_THRESHOLD:
        return 0
    elif stamina >= STAMINA_MODERATE_THRESHOLD:
        return STAMINA_PENALTIES['mild']
    elif stamina >= STAMINA_SEVERE_THRESHOLD:
        return STAMINA_PENALTIES['moderate']
    else:
        return STAMINA_PENALTIES['severe']


def get_fatigue_injury_multiplier(stamina: float) -> float:
    """
    Get the injury rate multiplier based on stamina.

    Below moderate threshold (40%): 1.3x injury rate
    Below severe threshold (20%): 2.0x injury rate (stacks)

    Args:
        stamina: Current stamina (0-100)

    Returns:
        Injury rate multiplier (1.0 = normal)
    """
    if stamina < STAMINA_SEVERE_THRESHOLD:
        return FATIGUE_INJURY_MULTIPLIER * 1.5  # ~2.0x total
    elif stamina < STAMINA_MODERATE_THRESHOLD:
        return FATIGUE_INJURY_MULTIPLIER
    return 1.0


def drain_stamina(current_stamina: float, position: str, high_effort: bool = False) -> float:
    """
    Calculate stamina after a single snap.

    Args:
        current_stamina: Current stamina (0-100)
        position: Player position code
        high_effort: Whether this was a high-effort play (e.g., long run, sack)

    Returns:
        New stamina value (clamped to 0)
    """
    base_drain = STAMINA_DRAIN_PER_SNAP.get(position, 0.5)

    if high_effort:
        base_drain *= HIGH_EFFORT_STAMINA_DRAIN

    new_stamina = current_stamina - base_drain
    return max(0.0, new_stamina)


def should_substitute(stamina: float, position: str) -> bool:
    """
    Determine if a player should be subbed out due to fatigue.

    RBs and DL are subbed more aggressively; QBs almost never.

    Args:
        stamina: Current stamina (0-100)
        position: Player position code

    Returns:
        True if player should be substituted
    """
    threshold = SUBSTITUTION_THRESHOLDS.get(position, 40)
    return stamina < threshold


def calculate_season_wear(
    position: str,
    current_week: int,
    current_wear: float = 0.0,
) -> float:
    """
    Calculate cumulative season wear for a player. Applied after each week
    starting from SEASON_WEAR_START_WEEK.

    Season wear reduces a player's effective stamina cap for the rest of the season.

    Args:
        position: Player position code
        current_week: Current week number (1-17+)
        current_wear: Existing accumulated wear

    Returns:
        New total season wear value
    """
    if current_week < SEASON_WEAR_START_WEEK:
        return current_wear

    wear_rate = SEASON_WEAR_PER_WEEK.get(position, 0.0)
    return current_wear + wear_rate


def effective_stamina_cap(base_stamina: float, season_wear: float) -> float:
    """
    Get the effective maximum stamina after accounting for season wear.

    Args:
        base_stamina: Base max stamina (typically 100)
        season_wear: Accumulated season wear

    Returns:
        Effective stamina cap
    """
    return max(0.0, base_stamina - season_wear)
