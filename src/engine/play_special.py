"""
Special teams play resolution: FG, punt, kickoff, extra point, two-point.

Depends on: ratings, matchup, injury, narration
"""

import random


def _attr(player: dict, key: str, default: int = 50) -> int:
    """Get a player attribute, returning default if None or missing."""
    val = player.get(key)
    return val if val is not None else default


from ..utils.constants import (
    BLOCKED_KICK_BASE_RATE,
    STC_MODIFIER_TABLE,
    BIG_PLAY_YARDS,
    FG_SNAP_HOLD_DISTANCE,
    FG_EXTREME_RANGE_BASE_PROB,
    FG_KICK_ACCURACY_BASELINE,
    FG_KICK_ACCURACY_DIVISOR,
    FG_PROB_MIN,
    FG_PROB_MAX,
    FG_WEATHER_DIVISOR,
    FG_STC_DIVISOR,
    FG_BLOCK_RATE_STC_DIVISOR,
    FG_BLOCK_RATE_MIN,
    FG_BLOCK_RATE_MAX,
    XP_KICK_ACCURACY_BASELINE,
    XP_KICK_ACCURACY_DIVISOR,
    XP_WEATHER_DIVISOR,
    XP_STC_DIVISOR,
    XP_PROB_MIN,
    XP_PROB_MAX,
    TWO_POINT_QB_ACCURACY_BASELINE,
    TWO_POINT_QB_ACCURACY_DIVISOR,
    TWO_POINT_PROB_MIN,
    TWO_POINT_PROB_MAX,
    PUNT_POWER_BASELINE,
    PUNT_POWER_DIVISOR,
    PUNT_WEATHER_DIVISOR,
    PUNT_DISTANCE_MIN,
    PUNT_DISTANCE_MAX,
    PUNT_TOUCHBACK_BUFFER,
    PUNT_RETURN_INJURY_THRESHOLD,
    PUNT_RETURNER_RATING_DIVISOR,
    KICKOFF_POWER_BASELINE,
    KICKOFF_POWER_DIVISOR,
    KICKOFF_WEATHER_DIVISOR,
    KICKOFF_STC_DIVISOR,
    KICKOFF_TOUCHBACK_PROB_MIN,
    KICKOFF_TOUCHBACK_PROB_MAX,
    KICKOFF_TOUCHBACK_YARD_LINE,
    KICKOFF_RETURN_MIN_YARDS,
    KICKOFF_RETURN_INJURY_THRESHOLD,
    KICKOFF_RETURNER_RATING_DIVISOR,
    FIELD_POSITION_MIN,
    FIELD_POSITION_MAX,
    FIELD_LENGTH,
    ENDZONE_THRESHOLD,
)
from .constants_engine import (
    FG_DISTANCE_MODIFIER,
    EXTRA_POINT_BASE_RATE,
    TWO_POINT_BASE_RATE,
    KICKOFF_TOUCHBACK_RATE,
    KICKOFF_RETURN_YARDS,
    PUNT_YARDS_BASE,
    PUNT_RETURN_YARDS,
    PUNT_DISTANCE_VARIANCE,
    FAIR_CATCH_PROBABILITY,
    PUNT_RETURN_BONUS_GOOD,
    PUNT_RETURN_RATING_GOOD,
    PUNT_RETURN_PENALTY,
    PUNT_RETURN_RATING_POOR,
    PUNT_BIG_RETURN_PROBABILITY,
    PUNT_BIG_RETURN_RATING_MIN,
    PUNT_BIG_RETURN_YARDS,
    KICKOFF_RETURN_BONUS_GOOD,
    KICKOFF_RETURN_RATING_GOOD,
    KICKOFF_RETURN_PENALTY,
    KICKOFF_RETURN_RATING_POOR,
    KICKOFF_BIG_RETURN_PROBABILITY,
    KICKOFF_BIG_RETURN_RATING_MIN,
    KICKOFF_BIG_RETURN_YARDS,
)
from .injury import check_injury, roll_severity
from .narration import (
    narrate_fg, narrate_punt, narrate_kickoff,
    narrate_extra_point, narrate_two_point,
)
from ..utils.constants import to_letter_grade


def _get_stc_modifier(staff_dict: dict) -> int:
    """Get special teams coordinator modifier from team staff."""
    stc = staff_dict.get('ST_coord')
    if not stc:
        return 0
    # Use teaching_ability as the STC's effectiveness rating
    rating = stc.get('teaching_ability', 50)
    grade = to_letter_grade(rating)
    # Map letter grade to STC modifier bucket
    if grade in ('A+', 'A', 'A-'):
        return STC_MODIFIER_TABLE['A']
    elif grade in ('B+', 'B', 'B-'):
        return STC_MODIFIER_TABLE['B']
    elif grade in ('C+', 'C', 'C-'):
        return STC_MODIFIER_TABLE['C']
    elif grade in ('D+', 'D'):
        return STC_MODIFIER_TABLE['D']
    else:
        return STC_MODIFIER_TABLE['F']


def resolve_field_goal(
    kicker: dict,
    game_state,
    weather: dict = None,
    off_staff: dict = None,
    def_staff: dict = None,
    is_home: bool = True,
    is_playoff: bool = False,
) -> dict:
    """
    Resolve a field goal attempt.

    Args:
        kicker: Kicker player dict
        game_state: GameState object
        weather: Weather dict
        off_staff: Offensive team staff dict
        def_staff: Defensive team staff dict
        is_home: Whether kicking team is home
        is_playoff: Playoff game flag

    Returns:
        Play result dict
    """
    fg_distance = game_state.yards_to_endzone + FG_SNAP_HOLD_DISTANCE

    # Get base probability by distance
    base_prob = FG_EXTREME_RANGE_BASE_PROB  # default for extreme range
    for label, (min_d, max_d, prob) in FG_DISTANCE_MODIFIER.items():
        if min_d <= fg_distance <= max_d:
            base_prob = prob
            break

    # Kicker accuracy modifier
    kick_accuracy = _attr(kicker, 'true_kick_accuracy')
    accuracy_mod = (kick_accuracy - FG_KICK_ACCURACY_BASELINE) / FG_KICK_ACCURACY_DIVISOR
    prob = base_prob + accuracy_mod

    # Weather modifier
    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        kick_mod = w_mods.get('kick', 0)
        prob += kick_mod / FG_WEATHER_DIVISOR

    # STC modifier
    stc_mod = _get_stc_modifier(off_staff or {})
    prob += stc_mod / FG_STC_DIVISOR

    # Clutch modifier
    from .ratings import is_clutch_situation, calculate_clutch_modifier
    gs_dict = game_state.get_game_state_dict()
    clutch_activated = is_clutch_situation(gs_dict)
    if clutch_activated:
        clutch_mod = calculate_clutch_modifier(_attr(kicker, 'true_clutch'), is_playoff)
        prob += clutch_mod / FG_STC_DIVISOR

    prob = max(FG_PROB_MIN, min(FG_PROB_MAX, prob))

    # Blocked kick check
    block_rate = BLOCKED_KICK_BASE_RATE
    def_stc_mod = _get_stc_modifier(def_staff or {})
    block_rate += def_stc_mod / FG_BLOCK_RATE_STC_DIVISOR
    block_rate = max(FG_BLOCK_RATE_MIN, min(FG_BLOCK_RATE_MAX, block_rate))

    is_blocked = random.random() < block_rate
    is_good = not is_blocked and random.random() < prob

    narration = narrate_fg(kicker, fg_distance, is_good, is_blocked)

    off_team_id = game_state.possession_team_id
    def_team_id = game_state.defending_team_id

    result = 'fg_good' if is_good else ('blocked' if is_blocked else 'fg_miss')

    return {
        'result': result,
        'yards_gained': 0,
        'play_type': 'fg_attempt',
        'is_touchdown': False,
        'is_turnover': False,
        'is_big_play': False,
        'narration_text': narration,
        'primary_player_id': kicker.get('id'),
        'target_player_id': None,
        'defender_player_id': None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': clutch_activated,
        'stats': {
            'fg_attempt': {
                'player_id': kicker['id'],
                'team_id': off_team_id,
                'distance': fg_distance,
                'made': is_good,
            },
        },
        'injuries': [],
        'fg_distance': fg_distance,
    }


def resolve_extra_point(kicker: dict, game_state, weather: dict = None, staff_dict: dict = None) -> dict:
    """Resolve an extra point attempt."""
    prob = EXTRA_POINT_BASE_RATE

    kick_accuracy = _attr(kicker, 'true_kick_accuracy')
    prob += (kick_accuracy - XP_KICK_ACCURACY_BASELINE) / XP_KICK_ACCURACY_DIVISOR

    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        prob += w_mods.get('kick', 0) / XP_WEATHER_DIVISOR

    stc_mod = _get_stc_modifier(staff_dict or {})
    prob += stc_mod / XP_STC_DIVISOR

    prob = max(XP_PROB_MIN, min(XP_PROB_MAX, prob))
    is_good = random.random() < prob

    narration = narrate_extra_point(kicker, is_good)

    return {
        'result': 'xp_good' if is_good else 'xp_miss',
        'yards_gained': 0,
        'play_type': 'extra_point',
        'is_touchdown': False,
        'is_turnover': False,
        'is_big_play': False,
        'narration_text': narration,
        'primary_player_id': kicker.get('id'),
        'target_player_id': None,
        'defender_player_id': None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': False,
        'stats': {
            'xp_attempt': {
                'player_id': kicker['id'],
                'team_id': game_state.possession_team_id,
                'made': is_good,
            },
        },
        'injuries': [],
    }


def resolve_two_point(offense: dict, defense: dict, game_state, weather: dict = None) -> dict:
    """Resolve a two-point conversion attempt."""
    qb = offense['qb']
    receivers = offense.get('receivers', [])
    off_team_id = offense['team_id']

    prob = TWO_POINT_BASE_RATE

    # QB accuracy bonus
    qb_acc = _attr(qb, 'true_accuracy_short')
    prob += (qb_acc - TWO_POINT_QB_ACCURACY_BASELINE) / TWO_POINT_QB_ACCURACY_DIVISOR

    prob = max(TWO_POINT_PROB_MIN, min(TWO_POINT_PROB_MAX, prob))
    is_good = random.random() < prob

    # Determine the player who scores/fails
    if receivers:
        player = random.choice(receivers)
    else:
        player = qb

    narration = narrate_two_point(player, is_good)

    return {
        'result': '2pt_good' if is_good else '2pt_fail',
        'yards_gained': 0,
        'play_type': 'two_point',
        'is_touchdown': False,
        'is_turnover': False,
        'is_big_play': False,
        'narration_text': narration,
        'primary_player_id': player.get('id'),
        'target_player_id': None,
        'defender_player_id': None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': False,
        'stats': {},
        'injuries': [],
    }


def resolve_punt(
    punter: dict,
    returner: dict,
    game_state,
    weather: dict = None,
    off_staff: dict = None,
) -> dict:
    """Resolve a punt play."""
    punt_power = _attr(punter, 'true_kick_power')

    # Base punt distance
    base_distance = random.randint(PUNT_YARDS_BASE[0], PUNT_YARDS_BASE[1])
    power_mod = (punt_power - PUNT_POWER_BASELINE) / PUNT_POWER_DIVISOR
    distance = int(base_distance + power_mod)

    # Weather modifier
    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        distance += w_mods.get('kick', 0) // PUNT_WEATHER_DIVISOR

    distance = max(PUNT_DISTANCE_MIN, min(PUNT_DISTANCE_MAX, distance))

    # Don't punt into the end zone (touchback risk)
    max_useful_distance = game_state.yards_to_endzone - PUNT_TOUCHBACK_BUFFER
    if distance > max_useful_distance and max_useful_distance > PUNT_DISTANCE_MIN:
        distance = max_useful_distance + random.randint(*PUNT_DISTANCE_VARIANCE)
        distance = max(PUNT_DISTANCE_MIN, distance)

    # Punt return
    return_yards = 0
    is_fair_catch = random.random() < FAIR_CATCH_PROBABILITY

    if not is_fair_catch and returner:
        return_yards = random.randint(PUNT_RETURN_YARDS[0], PUNT_RETURN_YARDS[1])
        returner_speed = _attr(returner, 'true_speed')
        returner_elusive = _attr(returner, 'true_elusiveness')
        ret_rating = (returner_speed + returner_elusive) // PUNT_RETURNER_RATING_DIVISOR

        if ret_rating >= PUNT_RETURN_RATING_GOOD:
            return_yards += random.randint(*PUNT_RETURN_BONUS_GOOD)
        elif ret_rating < PUNT_RETURN_RATING_POOR:
            return_yards = max(0, return_yards - PUNT_RETURN_PENALTY)

        # Big return chance
        if random.random() < PUNT_BIG_RETURN_PROBABILITY and ret_rating >= PUNT_BIG_RETURN_RATING_MIN:
            return_yards += random.randint(*PUNT_BIG_RETURN_YARDS)

    # Check if return reaches endzone
    is_return_td = False
    if return_yards > 0:
        projected_field_pos = game_state.yards_to_endzone - distance + return_yards
        is_return_td = projected_field_pos >= ENDZONE_THRESHOLD

    # Calculate resulting field position for receiving team
    new_field_pos = game_state.yards_to_endzone - distance + return_yards
    new_field_pos = max(FIELD_POSITION_MIN, min(FIELD_POSITION_MAX, FIELD_LENGTH - new_field_pos))

    # Narration uses yard line from receiver's perspective
    receiving_yard_line = FIELD_LENGTH - new_field_pos

    narration = narrate_punt(punter, distance, receiving_yard_line)

    off_team_id = game_state.possession_team_id

    # Injury check on returner
    injuries = []
    if returner and return_yards > PUNT_RETURN_INJURY_THRESHOLD:
        from .fatigue import get_fatigue_injury_multiplier
        ret_stamina = game_state.player_stamina.get(returner.get('id', 0), 100)
        fatigue_mult = get_fatigue_injury_multiplier(ret_stamina)
        if check_injury(_attr(returner, 'true_durability'), fatigue_mult, 'punt_coverage'):
            inj = roll_severity()
            inj['player_id'] = returner['id']
            inj['player'] = returner
            injuries.append(inj)

    return {
        'result': 'punt',
        'yards_gained': 0,
        'play_type': 'punt',
        'is_touchdown': is_return_td,
        'is_turnover': False,
        'is_big_play': False,
        'narration_text': narration,
        'primary_player_id': punter.get('id'),
        'target_player_id': None,
        'defender_player_id': returner.get('id') if returner else None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': False,
        'stats': {
            'punt': {'player_id': punter['id'], 'team_id': off_team_id, 'yards': distance},
            'punt_return': {'player_id': returner['id'] if returner else None, 'yards': return_yards, 'is_td': is_return_td} if returner and return_yards > 0 else None,
        },
        'injuries': injuries,
        'new_field_position': new_field_pos,
        'return_yards': return_yards,
    }


def resolve_kickoff(
    kicker: dict,
    returner: dict,
    game_state,
    weather: dict = None,
    kicking_staff: dict = None,
) -> dict:
    """Resolve a kickoff play."""
    kick_power = _attr(kicker, 'true_kick_power')

    # Touchback probability
    tb_prob = KICKOFF_TOUCHBACK_RATE
    tb_prob += (kick_power - KICKOFF_POWER_BASELINE) / KICKOFF_POWER_DIVISOR

    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        tb_prob += w_mods.get('kick', 0) / KICKOFF_WEATHER_DIVISOR

    stc_mod = _get_stc_modifier(kicking_staff or {})
    tb_prob += stc_mod / KICKOFF_STC_DIVISOR

    tb_prob = max(KICKOFF_TOUCHBACK_PROB_MIN, min(KICKOFF_TOUCHBACK_PROB_MAX, tb_prob))

    is_touchback = random.random() < tb_prob

    if is_touchback:
        new_field_pos = KICKOFF_TOUCHBACK_YARD_LINE
        return_yards = 0
        narration = narrate_kickoff(kicker, returner, KICKOFF_TOUCHBACK_YARD_LINE, True)
    else:
        # Return
        return_yards = random.randint(KICKOFF_RETURN_YARDS[0], KICKOFF_RETURN_YARDS[1])

        if returner:
            ret_speed = _attr(returner, 'true_speed')
            ret_elusive = _attr(returner, 'true_elusiveness')
            ret_rating = (ret_speed + ret_elusive) // KICKOFF_RETURNER_RATING_DIVISOR

            if ret_rating >= KICKOFF_RETURN_RATING_GOOD:
                return_yards += random.randint(*KICKOFF_RETURN_BONUS_GOOD)
            elif ret_rating < KICKOFF_RETURN_RATING_POOR:
                return_yards = max(KICKOFF_RETURN_MIN_YARDS, return_yards - KICKOFF_RETURN_PENALTY)

            # Big return chance
            if random.random() < KICKOFF_BIG_RETURN_PROBABILITY and ret_rating >= KICKOFF_BIG_RETURN_RATING_MIN:
                return_yards += random.randint(*KICKOFF_BIG_RETURN_YARDS)

        new_field_pos = min(FIELD_POSITION_MAX, return_yards)
        narration = narrate_kickoff(kicker, returner, new_field_pos, False)

    # Injury check on returner during returns
    injuries = []
    if not is_touchback and returner and return_yards > KICKOFF_RETURN_INJURY_THRESHOLD:
        from .fatigue import get_fatigue_injury_multiplier
        ret_stamina = game_state.player_stamina.get(returner.get('id', 0), 100)
        fatigue_mult = get_fatigue_injury_multiplier(ret_stamina)
        if check_injury(_attr(returner, 'true_durability'), fatigue_mult, 'kickoff_return'):
            inj = roll_severity()
            inj['player_id'] = returner['id']
            inj['player'] = returner
            injuries.append(inj)

    # Check for kick return TD
    is_td = new_field_pos >= ENDZONE_THRESHOLD
    if is_td:
        narration += " TOUCHDOWN on the return!"

    return {
        'result': 'touchback' if is_touchback else ('td' if is_td else 'kickoff_return'),
        'yards_gained': return_yards,
        'play_type': 'kickoff',
        'is_touchdown': is_td,
        'is_turnover': False,
        'is_big_play': return_yards >= BIG_PLAY_YARDS,
        'narration_text': narration,
        'primary_player_id': kicker.get('id'),
        'target_player_id': None,
        'defender_player_id': returner.get('id') if returner else None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': False,
        'stats': {
            'kick_return': {'player_id': returner['id'] if returner else None, 'yards': return_yards, 'is_td': is_td} if returner and not is_touchback else None,
        },
        'injuries': injuries,
        'new_field_position': new_field_pos,
    }
