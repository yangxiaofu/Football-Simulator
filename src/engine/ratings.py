"""
Rating system: SAR (Scheme-Adjusted Rating) calculation.

Integrates scheme fit, coordinator multiplier, home field advantage,
weather modifiers, fatigue penalties, and clutch bonuses.

Depends on: weather.py, fatigue.py
"""

import json


def _attr(d: dict, key: str, default: int = 50) -> int:
    """Get a dict value, returning default if None or missing."""
    val = d.get(key)
    return val if val is not None else default


from ..utils.constants import (
    HOME_FIELD_MODIFIER,
    SCHEME_ATTRIBUTE_MAP_OFFENSE,
    SCHEME_ATTRIBUTE_MAP_DEFENSE,
    SCHEME_FIT_BONUS_MIN,
    SCHEME_FIT_BONUS_MAX,
    CLUTCH_SCORE_MARGIN,
    CLUTCH_2MIN_THRESHOLD,
    CLUTCH_3RD_DOWN_DISTANCE,
    CLUTCH_PLAYOFF_BONUS,
    OL_COACH_BONUS_MAX,
    WR_COACH_SITUATIONAL_BONUS,
    QB_COACH_PRESSURE_REDUCTION,
    RB_COACH_VISION_BONUS,
    DB_COACH_COVERAGE_BONUS,
    OUT_OF_POSITION_SAR_PENALTY,
    DEPTH_CHART_TO_PLAYER_POSITION,
    FLEXIBLE_POSITION_EQUIVALENTS,
)
from .weather import get_weather_modifiers
from .fatigue import get_fatigue_penalty


def calculate_scheme_fit(player: dict, coordinator: dict, side: str = 'offense') -> float:
    """
    Calculate scheme fit bonus for a player under a coordinator.

    SAR contribution = scheme_fit_bonus * fit_multiplier
    Net swing: -8 to +8.

    Args:
        player: Player dict with true_* attributes
        coordinator: Staff dict with scheme_expertise (JSON string or dict)
        side: 'offense' or 'defense'

    Returns:
        Scheme fit SAR modifier (float, typically -5 to +8)
    """
    # Parse scheme expertise
    expertise = coordinator.get('scheme_expertise')
    if not expertise:
        return 0.0

    if isinstance(expertise, str):
        try:
            expertise = json.loads(expertise)
        except (json.JSONDecodeError, TypeError):
            return 0.0

    if not expertise:
        return 0.0

    # Find primary scheme (highest expertise)
    primary_scheme = max(expertise, key=expertise.get)

    # Get attribute map
    if side == 'offense':
        attr_map = SCHEME_ATTRIBUTE_MAP_OFFENSE
    else:
        attr_map = SCHEME_ATTRIBUTE_MAP_DEFENSE

    valued_attrs = attr_map.get(primary_scheme, [])
    if not valued_attrs:
        return 0.0

    # Calculate player's fit: average of valued attributes vs overall
    attr_values = []
    for attr in valued_attrs:
        val = player.get(attr)
        if val is not None:
            attr_values.append(val)

    if not attr_values:
        return 0.0

    valued_avg = sum(attr_values) / len(attr_values)
    overall = _attr(player, 'true_overall', 70)
    fit_delta = valued_avg - overall

    # Clamp to range
    scheme_fit_bonus = max(SCHEME_FIT_BONUS_MIN, min(SCHEME_FIT_BONUS_MAX, fit_delta))

    # Fit multiplier = coordinator expertise / 100
    fit_multiplier = expertise.get(primary_scheme, 50) / 100.0

    return scheme_fit_bonus * fit_multiplier


def calculate_coach_bonus(player: dict, staff_dict: dict) -> int:
    """
    Calculate position coach bonus for a player.

    Each position coach type provides a small bonus to relevant attributes.
    The bonus scales with the coach's teaching_ability.

    Args:
        player: Player dict
        staff_dict: Dict mapping role -> staff dict for the team

    Returns:
        Total coach bonus (0-5 typically)
    """
    position = player.get('position', '')
    bonus = 0

    # Map positions to their coach and max bonus
    coach_map = {
        'OL': ('OL_coach', OL_COACH_BONUS_MAX),
        'WR': ('WR_coach', WR_COACH_SITUATIONAL_BONUS),
        'QB': ('QB_coach', QB_COACH_PRESSURE_REDUCTION),
        'RB': ('RB_coach', RB_COACH_VISION_BONUS),
        'CB': ('DB_coach', DB_COACH_COVERAGE_BONUS),
        'S': ('DB_coach', DB_COACH_COVERAGE_BONUS),
    }

    coach_info = coach_map.get(position)
    if coach_info:
        role, max_bonus = coach_info
        coach = staff_dict.get(role)
        if coach:
            teaching = coach.get('teaching_ability', 50)
            # Scale: teaching 99 = max bonus, teaching 50 = ~half
            bonus = int(max_bonus * (teaching / 99.0))

    return bonus


def is_clutch_situation(game_state: dict) -> bool:
    """
    Determine if the current game state is a clutch situation.

    Clutch activates in:
    - 4th quarter within CLUTCH_SCORE_MARGIN points
    - Under 2 minutes in 2nd or 4th quarter
    - 3rd down with CLUTCH_3RD_DOWN_DISTANCE+ yards to go
    - Any playoff game (bonus applied separately)

    Args:
        game_state: Dict with quarter, time_remaining, score_diff, down, distance

    Returns:
        True if clutch modifiers should apply
    """
    quarter = game_state.get('quarter', 1)
    time_remaining = game_state.get('time_remaining', 900)
    score_diff = abs(game_state.get('score_diff', 0))
    down = game_state.get('down', 1)
    distance = game_state.get('distance', 10)

    # 4th quarter, close game
    if quarter >= 4 and score_diff <= CLUTCH_SCORE_MARGIN:
        return True

    # 2-minute drill (end of half or game)
    if time_remaining <= CLUTCH_2MIN_THRESHOLD and quarter in (2, 4):
        return True

    # Crucial 3rd down
    if down == 3 and distance >= CLUTCH_3RD_DOWN_DISTANCE:
        return True

    return False


def calculate_clutch_modifier(clutch_rating: int, is_playoff: bool = False) -> int:
    """
    Calculate clutch modifier for a player.

    Formula: (clutch_rating - 50) / 10
    A player with Clutch 80 gets +3 in clutch situations.
    A player with Clutch 30 gets -2.

    Args:
        clutch_rating: Player's true_clutch (1-99)
        is_playoff: Whether this is a playoff game

    Returns:
        SAR modifier (can be negative)
    """
    modifier = (clutch_rating - 50) / 10.0
    if is_playoff:
        modifier += CLUTCH_PLAYOFF_BONUS
    return int(round(modifier))


def calculate_sar(
    player: dict,
    coordinator: dict = None,
    staff_dict: dict = None,
    weather: dict = None,
    stamina: float = 100.0,
    is_home: bool = False,
    game_state: dict = None,
    is_playoff: bool = False,
    side: str = 'offense',
) -> int:
    """
    Calculate the full Scheme-Adjusted Rating for a player.

    SAR = true_overall
        + scheme_fit_bonus
        + coach_bonus
        + home_field_modifier
        + weather_modifier
        + fatigue_penalty
        + clutch_modifier (if applicable)

    This is the ONLY rating the simulation engine uses for matchup resolution.

    Args:
        player: Player dict with all true_* attributes
        coordinator: OC or DC staff dict (for scheme fit)
        staff_dict: Dict mapping role -> staff dict (for coach bonuses)
        weather: Weather dict from generate_weather()
        stamina: Player's current stamina (0-100)
        is_home: Whether this player's team is the home team
        game_state: Current game state dict (for clutch detection)
        is_playoff: Whether this is a playoff game
        side: 'offense' or 'defense'

    Returns:
        Final SAR value (integer)
    """
    base = _attr(player, 'true_overall')

    # Scheme fit
    scheme_bonus = 0.0
    if coordinator:
        scheme_bonus = calculate_scheme_fit(player, coordinator, side)

    # Coach bonus
    coach_bonus = 0
    if staff_dict:
        coach_bonus = calculate_coach_bonus(player, staff_dict)

    # Home field
    home_bonus = HOME_FIELD_MODIFIER if is_home else 0

    # Weather
    weather_mod = 0
    if weather:
        mods = get_weather_modifiers(weather)
        # Apply general accuracy modifier as a proxy for overall weather impact
        weather_mod = mods.get('accuracy', 0) // 2  # Halve it for general SAR

    # Fatigue
    fatigue_mod = get_fatigue_penalty(stamina)

    # Clutch
    clutch_mod = 0
    if game_state and is_clutch_situation(game_state):
        clutch_rating = _attr(player, 'true_clutch')
        clutch_mod = calculate_clutch_modifier(clutch_rating, is_playoff)

    sar = int(base + scheme_bonus + coach_bonus + home_bonus + weather_mod + fatigue_mod + clutch_mod)

    # Phase 5 Prompt #3 Cleanup Round 2: Position mismatch penalty
    depth_slot = player.get('_depth_slot')
    if depth_slot:
        player_position = player.get('position', '')
        expected_position = DEPTH_CHART_TO_PLAYER_POSITION.get(depth_slot, depth_slot)

        # Check if position matches
        if player_position != expected_position:
            # Check flexible equivalents (e.g., OL can play any O-line slot)
            is_flexible = False
            for generic_pos, allowed_slots in FLEXIBLE_POSITION_EQUIVALENTS.items():
                if player_position == generic_pos and depth_slot in allowed_slots:
                    is_flexible = True
                    break

            # Apply penalty if not a flexible match
            if not is_flexible:
                sar -= OUT_OF_POSITION_SAR_PENALTY

    # Clamp to valid range
    return max(1, min(99, sar))


def get_accuracy_for_zone(player: dict, zone: str, weather: dict = None) -> int:
    """
    Get the QB's accuracy rating for a specific pass zone, with weather applied.

    Args:
        player: QB player dict
        zone: 'short', 'medium', or 'deep'
        weather: Weather dict

    Returns:
        Accuracy rating for this zone
    """
    zone_attr_map = {
        'short': 'true_accuracy_short',
        'medium': 'true_accuracy_mid',
        'deep': 'true_accuracy_deep',
    }
    attr = zone_attr_map.get(zone, 'true_accuracy_mid')
    accuracy = _attr(player, attr, _attr(player, 'true_overall'))

    if weather:
        mods = get_weather_modifiers(weather)
        acc_mod = mods.get('accuracy', 0)
        # Deep passes get extra wind penalty
        if zone == 'deep':
            acc_mod = mods.get('deep_pass_accuracy', acc_mod)
        accuracy += acc_mod

    return max(1, min(99, accuracy))
