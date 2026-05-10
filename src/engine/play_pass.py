"""
Pass play resolution: 5-step tree producing yards/result/narrative.

Steps:
1. Pre-snap read (QB Football IQ vs DC disguise)
2. Pass rush (OL vs DL/blitz) → pocket time grade
3. Route vs coverage (WR route running vs DB coverage)
4. The throw (QB accuracy + pocket time + separation)
5. After catch (YAC)

Depends on: ratings, matchup, fatigue, injury, narration
"""

import random


def _attr(player: dict, key: str, default: int = 50) -> int:
    """Get a player attribute, returning default if None or missing."""
    val = player.get(key)
    return val if val is not None else default


from ..utils.constants import (
    POCKET_PENALTY,
    SACK_PROBABILITY_BY_POCKET,
    PASS_ZONE_SHORT,
    PASS_ZONE_MEDIUM,
    PASS_ZONE_DEEP,
    TURNOVER_BASE_RATE,
    BIG_PLAY_YARDS,
    PRE_SNAP_BONUS_RANGE,
    SEPARATION_BONUS_RANGE,
    SEPARATION_PENALTY_RANGE,
)
from .constants_engine import (
    PASS_YARDS_BY_ZONE,
    SACK_YARDS,
    SCRAMBLE_YARDS,
    YAC_RANGES,
)
from .ratings import calculate_sar, get_accuracy_for_zone
from .matchup import resolve_matchup, resolve_group_matchup
from .fatigue import get_fatigue_injury_multiplier
from .injury import check_injury, roll_severity
from .narration import (
    narrate_pass_complete, narrate_pass_incomplete,
    narrate_interception, narrate_sack, narrate_scramble,
    narrate_injury,
)


def resolve_pass_play(
    offense: dict,
    defense: dict,
    play_call: dict,
    game_state,
    weather: dict = None,
    is_home_offense: bool = True,
    is_playoff: bool = False,
) -> dict:
    """
    Resolve a complete pass play through 5 steps.

    Args:
        offense: Dict with keys:
            'qb': player dict
            'receivers': list of player dicts (WR/TE/RB targets)
            'oline': list of player dicts (5 OL)
            'coordinator': OC staff dict
            'staff_dict': dict of role -> staff
            'team_id': int
            'team_name': str
        defense: Dict with keys:
            'pass_rushers': list of player dicts (DL + blitzers)
            'coverage': list of player dicts (CB/S/LB in coverage)
            'coordinator': DC staff dict
            'staff_dict': dict of role -> staff
            'team_id': int
            'team_name': str
        play_call: Dict from play_caller (play_type, pass_zone, etc.)
        game_state: GameState object
        weather: Weather dict
        is_home_offense: Whether offense is the home team
        is_playoff: Whether this is a playoff game

    Returns:
        dict with:
            'result': str ('complete', 'incomplete', 'sack', 'int', 'scramble', 'td')
            'yards_gained': int
            'play_type': 'pass'
            'is_touchdown': bool
            'is_turnover': bool
            'is_big_play': bool
            'narration_text': str
            'primary_player_id': int (QB)
            'target_player_id': int (receiver)
            'defender_player_id': int
            'pocket_time_grade': str
            'separation_yards': float
            'clutch_activated': bool
            'stats': dict (stat recording instructions)
            'injuries': list (any injuries that occurred)
    """
    qb = offense['qb']
    receivers = offense['receivers']
    oline = offense['oline']
    off_coord = offense.get('coordinator', {})
    off_staff = offense.get('staff_dict', {})
    off_team_id = offense['team_id']

    pass_rushers = defense['pass_rushers']
    coverage_dbs = defense['coverage']
    def_coord = defense.get('coordinator', {})
    def_staff = defense.get('staff_dict', {})
    def_team_id = defense['team_id']

    zone = play_call.get('pass_zone', 'medium')
    gs_dict = game_state.get_game_state_dict()
    gs_dict['yards_to_endzone'] = game_state.yards_to_endzone

    injuries = []
    clutch_activated = False

    # Check clutch
    from .ratings import is_clutch_situation
    if is_clutch_situation(gs_dict):
        clutch_activated = True

    # ===== STEP 1: Pre-snap read =====
    qb_iq = _attr(qb, 'true_football_iq')
    dc_disguise = _attr(def_coord, 'disguise_rating')
    pre_snap_bonus = 0
    if resolve_matchup(qb_iq, dc_disguise):
        pre_snap_bonus = random.randint(*PRE_SNAP_BONUS_RANGE)

    # ===== STEP 2: Pass rush (OL vs DL/blitz) =====
    # Get SAR for each OL
    ol_sars = []
    for ol in oline:
        stamina = game_state.player_stamina.get(ol['id'], 100)
        sar = calculate_sar(
            ol, off_coord, off_staff, weather, stamina,
            is_home=is_home_offense, game_state=gs_dict,
            is_playoff=is_playoff, side='offense',
        )
        ol_sars.append(sar)

    # Get SAR for each pass rusher
    rusher_sars = []
    for rusher in pass_rushers:
        stamina = game_state.player_stamina.get(rusher['id'], 100)
        pr_rating = _attr(rusher, 'true_pass_rush', _attr(rusher, 'true_overall'))
        sar = calculate_sar(
            rusher, def_coord, def_staff, weather, stamina,
            is_home=not is_home_offense, game_state=gs_dict,
            is_playoff=is_playoff, side='defense',
        )
        # Use pass rush rating as the matchup base
        sar = sar + (pr_rating - _attr(rusher, 'true_overall')) // 2
        sar = max(1, min(99, sar))
        rusher_sars.append(sar)

    # Resolve OL vs pass rush
    rush_result = resolve_group_matchup(ol_sars, rusher_sars)
    ol_wins = rush_result['attacker_wins']

    # Determine pocket time grade
    total_ol = len(ol_sars)
    if ol_wins >= total_ol - 1:  # 4-5 OL wins
        pocket_grade = 'clean'
    elif ol_wins >= total_ol - 3:  # 2-3 OL wins
        pocket_grade = 'disrupted'
    else:
        pocket_grade = 'collapsed'

    # ===== STEP 2b: Sack check =====
    sack_prob = SACK_PROBABILITY_BY_POCKET[pocket_grade]
    if random.random() < sack_prob:
        # SACK
        sack_yards = random.randint(SACK_YARDS[0], SACK_YARDS[1])
        main_rusher = pass_rushers[0] if pass_rushers else None

        # Injury check on QB (sack situation)
        qb_stamina = game_state.player_stamina.get(qb['id'], 100)
        fatigue_mult = get_fatigue_injury_multiplier(qb_stamina)
        if check_injury(_attr(qb, 'true_durability'), fatigue_mult, 'sack'):
            inj = roll_severity()
            inj['player_id'] = qb['id']
            inj['player'] = qb
            injuries.append(inj)

        narration = narrate_sack(qb, main_rusher, sack_yards)

        return {
            'result': 'sack',
            'yards_gained': sack_yards,
            'play_type': 'pass',
            'is_touchdown': False,
            'is_turnover': False,
            'is_big_play': False,
            'narration_text': narration,
            'primary_player_id': qb.get('id'),
            'target_player_id': None,
            'defender_player_id': main_rusher.get('id') if main_rusher else None,
            'pocket_time_grade': pocket_grade,
            'separation_yards': None,
            'clutch_activated': clutch_activated,
            'stats': {
                'sack_taken': {'player_id': qb['id'], 'team_id': off_team_id},
                'sack': {'player_id': main_rusher['id'], 'team_id': def_team_id} if main_rusher else None,
                'tackle': {'player_id': main_rusher['id'], 'team_id': def_team_id} if main_rusher else None,
            },
            'injuries': injuries,
        }

    # ===== STEP 2c: Scramble check =====
    # If pocket collapsed and QB is mobile, scramble
    if pocket_grade == 'collapsed' and random.random() < 0.35:
        qb_speed = _attr(qb, 'true_speed')
        qb_elusive = _attr(qb, 'true_elusiveness')
        mobility = (qb_speed + qb_elusive) // 2

        if mobility > 55 or random.random() < 0.3:
            scramble_yards = random.randint(SCRAMBLE_YARDS[0], SCRAMBLE_YARDS[1])
            # Weighted by mobility
            if mobility >= 75:
                scramble_yards = max(scramble_yards, random.randint(2, 15))
            elif mobility < 45:
                scramble_yards = min(scramble_yards, random.randint(-2, 5))

            # Cap at yards to endzone
            scramble_yards = min(scramble_yards, game_state.yards_to_endzone)
            is_td = scramble_yards >= game_state.yards_to_endzone

            # Injury check (scramble)
            qb_stamina = game_state.player_stamina.get(qb['id'], 100)
            fatigue_mult = get_fatigue_injury_multiplier(qb_stamina)
            if check_injury(_attr(qb, 'true_durability'), fatigue_mult, 'scramble'):
                inj = roll_severity()
                inj['player_id'] = qb['id']
                inj['player'] = qb
                injuries.append(inj)

            narration = narrate_scramble(qb, scramble_yards)
            if is_td:
                narration += " TOUCHDOWN!"

            return {
                'result': 'scramble' if not is_td else 'td',
                'yards_gained': scramble_yards,
                'play_type': 'pass',
                'is_touchdown': is_td,
                'is_turnover': False,
                'is_big_play': scramble_yards >= BIG_PLAY_YARDS,
                'narration_text': narration,
                'primary_player_id': qb.get('id'),
                'target_player_id': None,
                'defender_player_id': None,
                'pocket_time_grade': pocket_grade,
                'separation_yards': None,
                'clutch_activated': clutch_activated,
                'stats': {
                    'carry': {'player_id': qb['id'], 'team_id': off_team_id, 'yards': scramble_yards},
                    'rush_td': {'player_id': qb['id'], 'team_id': off_team_id} if is_td else None,
                },
                'injuries': injuries,
            }

    # ===== STEP 3: Route vs coverage =====
    # Select target receiver
    if not receivers:
        # Emergency: no receivers, incomplete
        narration = narrate_pass_incomplete(qb, {'first_name': '', 'last_name': 'nobody'}, {})
        return _incomplete_result(qb, None, None, pocket_grade, clutch_activated, narration, off_team_id)

    # Weight target selection by route running + scheme fit
    target_weights = []
    for rec in receivers:
        route = rec.get('true_route_running') or rec.get('true_overall') or 50
        weight = max(10, route)
        # Primary targets get bonus weight
        if rec.get('position') == 'WR':
            weight *= 1.2
        target_weights.append(weight)

    target = random.choices(receivers, weights=target_weights, k=1)[0]

    # Get the defender covering the target
    defender = None
    if coverage_dbs:
        defender = random.choice(coverage_dbs)

    # Calculate separation
    rec_route = _attr(target, 'true_route_running')
    rec_speed = _attr(target, 'true_speed')
    rec_sar = (rec_route + rec_speed) // 2

    if defender:
        cov_attr = 'true_coverage_man' if play_call.get('coverage_type', 'man') == 'man' else 'true_coverage_zone'
        def_cov = _attr(defender, cov_attr, _attr(defender, 'true_overall'))
        def_speed = _attr(defender, 'true_speed')
        def_sar = (def_cov + def_speed) // 2
    else:
        def_sar = 40  # No defender = wide open

    separation = (rec_sar - def_sar) / 10.0  # Positive = open, negative = tight
    separation = max(-3.0, min(5.0, separation))

    # ===== STEP 4: The throw =====
    accuracy = get_accuracy_for_zone(qb, zone, weather)

    # Apply pocket penalty
    pocket_pen = POCKET_PENALTY[pocket_grade]
    accuracy += pocket_pen

    # Apply pre-snap bonus
    accuracy += pre_snap_bonus

    # Clutch modifier
    if clutch_activated:
        from .ratings import calculate_clutch_modifier
        clutch_mod = calculate_clutch_modifier(_attr(qb, 'true_clutch'), is_playoff)
        accuracy += clutch_mod

    # Catch difficulty based on separation
    catch_rating = _attr(target, 'true_catch', _attr(target, 'true_overall'))

    # Combined throw quality: accuracy + separation + catch
    throw_quality = accuracy + separation * 4 + catch_rating * 0.2

    # Determine outcome: completion, incompletion, or interception
    # Base completion rate varies by zone
    zone_base_rates = {
        'short': 0.68,
        'medium': 0.53,
        'deep': 0.33,
    }
    base_comp_rate = zone_base_rates.get(zone, 0.58)

    # Modify by throw quality (centered around 72)
    quality_mod = (throw_quality - 72) / 220.0  # ±13% swing
    comp_rate = base_comp_rate + quality_mod
    comp_rate = max(0.15, min(0.90, comp_rate))

    # Interception chance
    int_chance = TURNOVER_BASE_RATE * 2.5  # ~3% base
    if pocket_grade == 'collapsed':
        int_chance *= 2.0
    if separation < -1.0:
        int_chance *= 1.5
    if accuracy < 50:
        int_chance *= 1.5

    roll = random.random()

    if roll < int_chance:
        # INTERCEPTION
        narration = narrate_interception(qb, target, defender)

        return {
            'result': 'int',
            'yards_gained': 0,
            'play_type': 'pass',
            'is_touchdown': False,
            'is_turnover': True,
            'is_big_play': False,
            'narration_text': narration,
            'primary_player_id': qb.get('id'),
            'target_player_id': target.get('id'),
            'defender_player_id': defender.get('id') if defender else None,
            'pocket_time_grade': pocket_grade,
            'separation_yards': separation,
            'clutch_activated': clutch_activated,
            'stats': {
                'pass_attempt': {'player_id': qb['id'], 'team_id': off_team_id},
                'target': {'player_id': target['id'], 'team_id': off_team_id},
                'interception_thrown': {'player_id': qb['id'], 'team_id': off_team_id},
                'interception': {'player_id': defender['id'], 'team_id': def_team_id} if defender else None,
            },
            'injuries': injuries,
        }

    if roll < int_chance + (1.0 - comp_rate):
        # INCOMPLETE
        narration = narrate_pass_incomplete(qb, target, defender)

        return _incomplete_result(
            qb, target, defender, pocket_grade, clutch_activated,
            narration, off_team_id, def_team_id,
        )

    # ===== COMPLETION =====
    # Calculate yards gained
    yard_range = PASS_YARDS_BY_ZONE.get(zone, (5, 15))
    base_yards = random.randint(yard_range[0], yard_range[1])

    # Modify by separation
    if separation > 2.0:
        base_yards += random.randint(*SEPARATION_BONUS_RANGE)
    elif separation < -1.0:
        base_yards -= random.randint(*SEPARATION_PENALTY_RANGE)

    # ===== STEP 5: After catch (YAC) =====
    yac_rating = _attr(target, 'true_yac', _attr(target, 'true_speed'))
    if yac_rating >= 85:
        yac_range = YAC_RANGES['elite']
    elif yac_rating >= 70:
        yac_range = YAC_RANGES['good']
    elif yac_rating >= 55:
        yac_range = YAC_RANGES['average']
    else:
        yac_range = YAC_RANGES['poor']

    yac = random.randint(yac_range[0], yac_range[1])
    total_yards = base_yards + yac

    # Cap at yards to endzone
    total_yards = min(total_yards, game_state.yards_to_endzone)
    is_td = total_yards >= game_state.yards_to_endzone
    is_big_play = total_yards >= BIG_PLAY_YARDS

    # Fumble check after catch
    fumble = False
    fumble_rate = TURNOVER_BASE_RATE
    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        fumble_rate *= w_mods.get('fumble', 1.0)
    if random.random() < fumble_rate and not is_td:
        fumble = True

    # Injury check on receiver
    rec_stamina = game_state.player_stamina.get(target['id'], 100)
    fatigue_mult = get_fatigue_injury_multiplier(rec_stamina)
    if yac > 10 and check_injury(_attr(target, 'true_durability'), fatigue_mult, 'high_speed_collision'):
        inj = roll_severity()
        inj['player_id'] = target['id']
        inj['player'] = target
        injuries.append(inj)

    narration = narrate_pass_complete(qb, target, total_yards, is_td, is_big_play)

    if fumble:
        from .narration import narrate_fumble
        narration += " " + narrate_fumble(target, defender)

    result_key = 'td' if is_td else ('fumble' if fumble else 'complete')

    stats_dict = {
        'pass_attempt': {'player_id': qb['id'], 'team_id': off_team_id},
        'target': {'player_id': target['id'], 'team_id': off_team_id},
        'completion': {'player_id': qb['id'], 'receiver_id': target['id'], 'team_id': off_team_id, 'yards': total_yards},
        'pass_td': {'player_id': qb['id'], 'receiver_id': target['id'], 'team_id': off_team_id} if is_td else None,
        'tackle': {'player_id': defender['id'], 'team_id': def_team_id} if defender and not is_td else None,
    }
    if fumble:
        stats_dict['fumble'] = {'player_id': target['id'], 'team_id': off_team_id}
        if defender:
            stats_dict['forced_fumble'] = {'player_id': defender['id'], 'team_id': def_team_id}

    return {
        'result': result_key,
        'yards_gained': total_yards,
        'play_type': 'pass',
        'is_touchdown': is_td,
        'is_turnover': fumble,
        'is_big_play': is_big_play,
        'narration_text': narration,
        'primary_player_id': qb.get('id'),
        'target_player_id': target.get('id'),
        'defender_player_id': defender.get('id') if defender else None,
        'pocket_time_grade': pocket_grade,
        'separation_yards': separation,
        'clutch_activated': clutch_activated,
        'stats': stats_dict,
        'injuries': injuries,
    }


def _incomplete_result(
    qb, target, defender, pocket_grade, clutch_activated,
    narration, off_team_id, def_team_id=None,
) -> dict:
    """Helper to build an incomplete pass result."""
    stats_dict = {
        'pass_attempt': {'player_id': qb['id'], 'team_id': off_team_id},
    }
    if target:
        stats_dict['target'] = {'player_id': target['id'], 'team_id': off_team_id}
    if defender and def_team_id:
        stats_dict['pass_deflection'] = {'player_id': defender['id'], 'team_id': def_team_id}

    return {
        'result': 'incomplete',
        'yards_gained': 0,
        'play_type': 'pass',
        'is_touchdown': False,
        'is_turnover': False,
        'is_big_play': False,
        'narration_text': narration,
        'primary_player_id': qb.get('id'),
        'target_player_id': target.get('id') if target else None,
        'defender_player_id': defender.get('id') if defender else None,
        'pocket_time_grade': pocket_grade,
        'separation_yards': None,
        'clutch_activated': clutch_activated,
        'stats': stats_dict,
        'injuries': [],
    }
