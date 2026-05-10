"""
Play calling: offensive and defensive play selection from game plan
tendencies plus situational adjustments.

No engine dependencies — reads game state and constants only.
"""

import random

from ..utils.constants import (
    DEFAULT_GAME_PLAN,
    THIRD_DOWN_LONG_DISTANCE,
    THIRD_DOWN_LONG_PASS_BIAS,
    THIRD_DOWN_SHORT_DISTANCE,
    THIRD_DOWN_SHORT_RUN_BIAS,
    SECOND_DOWN_LONG_DISTANCE,
    SECOND_DOWN_LONG_PASS_LEAN,
    TRAILING_SCORE_DIFF,
    TRAILING_PASS_BIAS,
    LEADING_SCORE_DIFF,
    LEADING_TIME_THRESHOLD,
    LEADING_RUN_BIAS,
    CLUTCH_2MIN_THRESHOLD,
    TWO_MINUTE_PASS_BIAS,
    RED_ZONE_YARDS,
    RED_ZONE_MIN_RUN_RATE,
    GOAL_LINE_YARDS,
)
from .constants_engine import PASS_SUBTYPES, RUN_SUBTYPES


def select_offensive_play(game_state_dict: dict, game_plan: dict = None) -> dict:
    """
    Select an offensive play based on tendencies and situation.

    Args:
        game_state_dict: Dict with quarter, time_remaining, down, distance,
                         field_position, score_diff, yards_to_endzone
        game_plan: Team's game plan tendencies (or DEFAULT_GAME_PLAN)

    Returns:
        dict with:
            'play_type': 'pass' or 'run'
            'subtype': specific play subtype
            'pass_zone': 'short', 'medium', or 'deep' (pass only)
            'is_play_action': bool
    """
    plan = game_plan or DEFAULT_GAME_PLAN
    run_rate = plan['run_pass_ratio']

    # Situational adjustments
    down = game_state_dict.get('down', 1)
    distance = game_state_dict.get('distance', 10)
    time_remaining = game_state_dict.get('time_remaining', 900)
    quarter = game_state_dict.get('quarter', 1)
    score_diff = game_state_dict.get('score_diff', 0)
    yards_to_endzone = game_state_dict.get('yards_to_endzone', 75)

    # 3rd and long: more passing
    if down == 3 and distance >= THIRD_DOWN_LONG_DISTANCE:
        run_rate *= THIRD_DOWN_LONG_PASS_BIAS

    # 3rd and short: more running
    elif down == 3 and distance <= THIRD_DOWN_SHORT_DISTANCE:
        run_rate *= THIRD_DOWN_SHORT_RUN_BIAS

    # 2nd and long: slight pass lean
    elif down == 2 and distance >= SECOND_DOWN_LONG_DISTANCE:
        run_rate *= SECOND_DOWN_LONG_PASS_LEAN

    # Trailing late: pass more
    if quarter >= 4 and score_diff < TRAILING_SCORE_DIFF:
        run_rate *= TRAILING_PASS_BIAS

    # Leading late: run more
    if quarter >= 4 and score_diff > LEADING_SCORE_DIFF and time_remaining < LEADING_TIME_THRESHOLD:
        run_rate *= LEADING_RUN_BIAS

    # 2-minute drill: mostly pass
    if time_remaining <= CLUTCH_2MIN_THRESHOLD and quarter in (2, 4):
        run_rate *= TWO_MINUTE_PASS_BIAS

    # Red zone: slightly more balanced
    if yards_to_endzone <= RED_ZONE_YARDS:
        run_rate = max(run_rate, RED_ZONE_MIN_RUN_RATE)

    # Goal line: favor run
    if yards_to_endzone <= GOAL_LINE_YARDS:
        run_rate = max(run_rate, 0.55)

    # Clamp
    run_rate = max(0.1, min(0.9, run_rate))

    # Decide run or pass
    is_run = random.random() < run_rate

    if is_run:
        subtype = random.choice(RUN_SUBTYPES)
        # Special case: QB sneak on very short yardage
        if distance <= 1:
            subtype = random.choice(['qb_sneak', 'power', 'inside_zone'])
        return {
            'play_type': 'run',
            'subtype': subtype,
            'pass_zone': None,
            'is_play_action': False,
        }
    else:
        # Select pass zone
        short_pct, medium_pct, deep_pct = plan['short_medium_deep']

        # Adjust zone by distance needed
        if distance <= 5:
            short_pct *= 1.3
        elif distance >= 15:
            deep_pct *= 1.5
            medium_pct *= 1.2

        # Normalize
        total = short_pct + medium_pct + deep_pct
        zones = ['short', 'medium', 'deep']
        weights = [short_pct / total, medium_pct / total, deep_pct / total]
        zone = random.choices(zones, weights=weights, k=1)[0]

        subtype = random.choice(PASS_SUBTYPES)

        # Play action chance (more likely on early downs)
        is_play_action = False
        if down <= 2 and random.random() < 0.20:
            is_play_action = True

        return {
            'play_type': 'pass',
            'subtype': subtype,
            'pass_zone': zone,
            'is_play_action': is_play_action,
        }


def select_defensive_play(game_state_dict: dict, game_plan: dict = None) -> dict:
    """
    Select a defensive play/alignment based on tendencies and situation.

    Args:
        game_state_dict: Current game state
        game_plan: Team's defensive game plan

    Returns:
        dict with:
            'is_blitz': bool
            'coverage_type': 'man' or 'zone'
            'blitz_count': int (extra rushers beyond 4)
    """
    plan = game_plan or DEFAULT_GAME_PLAN
    blitz_rate = plan['blitz_frequency']
    man_rate = plan['coverage_man_zone']

    down = game_state_dict.get('down', 1)
    distance = game_state_dict.get('distance', 10)
    yards_to_endzone = game_state_dict.get('yards_to_endzone', 75)

    # 3rd and long: increase blitz
    if down == 3 and distance >= 7:
        blitz_rate *= 1.5

    # Red zone: more man coverage
    if yards_to_endzone <= 20:
        man_rate *= 1.3

    # Short yardage: less blitz, more stacked box
    if distance <= 3:
        blitz_rate *= 0.6

    # Clamp
    blitz_rate = min(0.60, blitz_rate)
    man_rate = max(0.15, min(0.85, man_rate))

    is_blitz = random.random() < blitz_rate
    coverage_type = 'man' if random.random() < man_rate else 'zone'

    blitz_count = 0
    if is_blitz:
        blitz_count = random.choices([1, 2, 3], weights=[0.50, 0.35, 0.15], k=1)[0]

    return {
        'is_blitz': is_blitz,
        'coverage_type': coverage_type,
        'blitz_count': blitz_count,
    }


def should_attempt_fg(game_state_dict: dict) -> bool:
    """
    Decide whether to attempt a field goal on 4th down.

    Args:
        game_state_dict: Current game state

    Returns:
        True if a FG attempt is recommended
    """
    yards_to_endzone = game_state_dict.get('yards_to_endzone', 75)
    distance = game_state_dict.get('distance', 10)
    fg_distance = yards_to_endzone + 17  # snap + hold distance

    # Always attempt if within reasonable range and not ultra-short
    if fg_distance <= 55 and distance > 1:
        return True

    return False


def should_go_for_it(game_state_dict: dict) -> bool:
    """
    Decide whether to go for it on 4th down (instead of punt/FG).

    Args:
        game_state_dict: Current game state

    Returns:
        True if going for it is recommended
    """
    distance = game_state_dict.get('distance', 10)
    yards_to_endzone = game_state_dict.get('yards_to_endzone', 75)
    quarter = game_state_dict.get('quarter', 1)
    score_diff = game_state_dict.get('score_diff', 0)
    time_remaining = game_state_dict.get('time_remaining', 900)

    # Very short yardage: often go for it
    if distance <= 1 and yards_to_endzone <= 40:
        return True

    # 4th and short in opponent territory
    if distance <= 3 and yards_to_endzone <= 35:
        if random.random() < 0.40:
            return True

    # Trailing in 4th quarter
    if quarter == 4 and score_diff < 0:
        if time_remaining < 300:  # Under 5 min
            return True
        if score_diff < -14 and time_remaining < 600:
            return True

    # Overtime — always more aggressive
    if quarter >= 5 and distance <= 5:
        return True

    return False


def should_punt(game_state_dict: dict) -> bool:
    """
    Decide whether to punt on 4th down.

    Returns True if punting is the recommended choice.
    """
    if should_go_for_it(game_state_dict):
        return False
    if should_attempt_fg(game_state_dict):
        return False
    return True
