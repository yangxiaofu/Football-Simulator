"""
Narration engine: template library and formatting for all play result types.

Pure template module with no engine dependencies.
"""

import random

from .constants_engine import (
    PASS_COMPLETE_TEMPLATES,
    PASS_COMPLETE_BIG_PLAY_TEMPLATES,
    PASS_COMPLETE_TD_TEMPLATES,
    PASS_INCOMPLETE_TEMPLATES,
    INTERCEPTION_TEMPLATES,
    SACK_TEMPLATES,
    SCRAMBLE_TEMPLATES,
    RUN_TEMPLATES,
    RUN_BIG_PLAY_TEMPLATES,
    RUN_TD_TEMPLATES,
    RUN_LOSS_TEMPLATES,
    FUMBLE_TEMPLATES,
    FG_GOOD_TEMPLATES,
    FG_MISS_TEMPLATES,
    FG_BLOCKED_TEMPLATES,
    PUNT_TEMPLATES,
    KICKOFF_TEMPLATES,
    XP_GOOD_TEMPLATES,
    XP_MISS_TEMPLATES,
    TWO_POINT_GOOD_TEMPLATES,
    TWO_POINT_FAIL_TEMPLATES,
    PENALTY_TEMPLATES,
    DRIVE_SUMMARY_TEMPLATE,
    COIN_TOSS_TEMPLATE,
    RUN_DIRECTIONS,
    ROUTE_DESCRIPTIONS,
    COVERAGE_DESCRIPTIONS,
)


def _player_name(player: dict) -> str:
    """Format a player name for narration."""
    if player is None:
        return "Unknown"
    first = player.get('first_name', '')
    last = player.get('last_name', '')
    # Use first initial + last name for conciseness
    if first:
        return f"{first[0]}. {last}"
    return last


def narrate_pass_complete(qb: dict, receiver: dict, yards: int, is_td: bool, is_big_play: bool) -> str:
    """Generate narration for a completed pass."""
    params = {
        'qb': _player_name(qb),
        'receiver': _player_name(receiver),
        'yards': abs(yards),
        'route_desc': random.choice(ROUTE_DESCRIPTIONS),
        'coverage_desc': random.choice(COVERAGE_DESCRIPTIONS),
    }

    if is_td:
        template = random.choice(PASS_COMPLETE_TD_TEMPLATES)
    elif is_big_play:
        template = random.choice(PASS_COMPLETE_BIG_PLAY_TEMPLATES)
    else:
        template = random.choice(PASS_COMPLETE_TEMPLATES)

    return template.format(**params)


def narrate_pass_incomplete(qb: dict, receiver: dict, defender: dict) -> str:
    """Generate narration for an incomplete pass."""
    params = {
        'qb': _player_name(qb),
        'receiver': _player_name(receiver),
        'defender': _player_name(defender),
    }
    template = random.choice(PASS_INCOMPLETE_TEMPLATES)
    return template.format(**params)


def narrate_interception(qb: dict, receiver: dict, defender: dict) -> str:
    """Generate narration for an interception."""
    params = {
        'qb': _player_name(qb),
        'receiver': _player_name(receiver),
        'defender': _player_name(defender),
    }
    template = random.choice(INTERCEPTION_TEMPLATES)
    return template.format(**params)


def narrate_sack(qb: dict, defender: dict, yards: int) -> str:
    """Generate narration for a sack."""
    params = {
        'qb': _player_name(qb),
        'defender': _player_name(defender),
        'yards': abs(yards),
    }
    template = random.choice(SACK_TEMPLATES)
    return template.format(**params)


def narrate_scramble(qb: dict, yards: int) -> str:
    """Generate narration for a QB scramble."""
    params = {
        'qb': _player_name(qb),
        'yards': abs(yards),
    }
    template = random.choice(SCRAMBLE_TEMPLATES)
    return template.format(**params)


def narrate_run(runner: dict, defender: dict, yards: int, is_td: bool, is_big_play: bool) -> str:
    """Generate narration for a run play."""
    direction = random.choice(RUN_DIRECTIONS)
    params = {
        'runner': _player_name(runner),
        'defender': _player_name(defender),
        'yards': abs(yards),
        'direction': direction,
    }

    if is_td:
        template = random.choice(RUN_TD_TEMPLATES)
    elif is_big_play:
        template = random.choice(RUN_BIG_PLAY_TEMPLATES)
    elif yards < 0:
        params['loss_yards'] = abs(yards)
        template = random.choice(RUN_LOSS_TEMPLATES)
    else:
        template = random.choice(RUN_TEMPLATES)

    return template.format(**params)


def narrate_fumble(ball_carrier: dict, defender: dict) -> str:
    """Generate narration for a fumble."""
    params = {
        'runner': _player_name(ball_carrier),
        'defender': _player_name(defender),
    }
    template = random.choice(FUMBLE_TEMPLATES)
    return template.format(**params)


def narrate_fg(kicker: dict, distance: int, is_good: bool, is_blocked: bool = False) -> str:
    """Generate narration for a field goal attempt."""
    params = {
        'kicker': _player_name(kicker),
        'distance': distance,
        'direction': random.choice(['left', 'right']),
    }

    if is_blocked:
        template = random.choice(FG_BLOCKED_TEMPLATES)
    elif is_good:
        template = random.choice(FG_GOOD_TEMPLATES)
    else:
        template = random.choice(FG_MISS_TEMPLATES)

    return template.format(**params)


def narrate_punt(punter: dict, distance: int, yard_line: int) -> str:
    """Generate narration for a punt."""
    params = {
        'punter': _player_name(punter),
        'distance': distance,
        'yard_line': yard_line,
    }
    template = random.choice(PUNT_TEMPLATES)
    return template.format(**params)


def narrate_kickoff(kicker: dict, returner: dict, yard_line: int, is_touchback: bool) -> str:
    """Generate narration for a kickoff."""
    params = {
        'kicker': _player_name(kicker),
        'returner': _player_name(returner),
        'yard_line': yard_line,
    }

    if is_touchback:
        template = KICKOFF_TEMPLATES[0]  # Touchback template
    else:
        template = random.choice(KICKOFF_TEMPLATES[1:])

    return template.format(**params)


def narrate_extra_point(kicker: dict, is_good: bool) -> str:
    """Generate narration for an extra point attempt."""
    params = {'kicker': _player_name(kicker)}
    if is_good:
        template = random.choice(XP_GOOD_TEMPLATES)
    else:
        template = random.choice(XP_MISS_TEMPLATES)
    return template.format(**params)


def narrate_two_point(player: dict, is_good: bool) -> str:
    """Generate narration for a two-point conversion."""
    params = {'player': _player_name(player)}
    if is_good:
        template = random.choice(TWO_POINT_GOOD_TEMPLATES)
    else:
        template = random.choice(TWO_POINT_FAIL_TEMPLATES)
    return template.format(**params)


def narrate_penalty(penalty_type: str, team_name: str, yards: int) -> str:
    """Generate narration for a penalty."""
    params = {
        'penalty_type': penalty_type.replace('_', ' ').title(),
        'team_name': team_name,
        'yards': yards,
    }
    template = random.choice(PENALTY_TEMPLATES)
    return template.format(**params)


def narrate_drive_summary(team_name: str, plays: int, yards: int, result: str) -> str:
    """Generate a drive summary line."""
    return DRIVE_SUMMARY_TEMPLATE.format(
        team=team_name, plays=plays, yards=yards, result=result,
    )


def narrate_coin_toss(winner_name: str, choice: str) -> str:
    """Generate coin toss narration."""
    return COIN_TOSS_TEMPLATE.format(winner=winner_name, choice=choice)


def narrate_injury(player: dict, severity: str) -> str:
    """Generate injury narration."""
    name = _player_name(player)
    severity_desc = {
        'questionable': 'is shaken up and questionable to return',
        'week_to_week': 'is helped off the field. Will be week-to-week',
        'ir_short': 'is carted off the field. Headed to injured reserve',
        'ir_season_ending': 'suffers a serious injury. Season may be over',
        'career_altering': 'suffers a devastating injury. Career impact possible',
        'career_ending': 'suffers a career-ending injury',
    }
    desc = severity_desc.get(severity, 'is injured')
    return f"{name} {desc}."
