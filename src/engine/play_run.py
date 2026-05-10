"""
Run play resolution: 3-step tree producing yards/result/narrative.

Steps:
1. Gap assignment (OL blocking vs DL)
2. Second level (LB fill vs RB vision)
3. Ball carrier vs open field (elusiveness + speed vs tackler)

Depends on: ratings, matchup, fatigue, injury, narration
"""

import random


def _attr(player: dict, key: str, default: int = 50) -> int:
    """Get a player attribute, returning default if None or missing."""
    val = player.get(key)
    return val if val is not None else default


from ..utils.constants import (
    TURNOVER_BASE_RATE,
    BIG_PLAY_YARDS,
    BIG_PLAY_RATE,
    OPEN_FIELD_BONUS_RANGE,
    BIG_RUN_BONUS_RANGE,
)
from .constants_engine import (
    RUN_YARDS_BASE,
    RUN_YARDS_GOOD_BLOCK,
    RUN_YARDS_BAD_BLOCK,
)
from .ratings import calculate_sar
from .matchup import resolve_matchup, resolve_group_matchup
from .fatigue import get_fatigue_injury_multiplier
from .injury import check_injury, roll_severity
from .narration import narrate_run, narrate_fumble


def resolve_run_play(
    offense: dict,
    defense: dict,
    play_call: dict,
    game_state,
    weather: dict = None,
    is_home_offense: bool = True,
    is_playoff: bool = False,
) -> dict:
    """
    Resolve a complete run play through 3 steps.

    Args:
        offense: Dict with 'rb', 'oline', 'coordinator', 'staff_dict', 'team_id', 'team_name'
        defense: Dict with 'dline', 'linebackers', 'safeties', 'coordinator', 'staff_dict', 'team_id'
        play_call: Dict from play_caller
        game_state: GameState object
        weather: Weather dict
        is_home_offense: Whether offense is home team
        is_playoff: Whether this is playoff game

    Returns:
        Play result dict (same structure as pass play)
    """
    rb = offense['rb']
    oline = offense['oline']
    off_coord = offense.get('coordinator', {})
    off_staff = offense.get('staff_dict', {})
    off_team_id = offense['team_id']

    dline = defense['dline']
    linebackers = defense['linebackers']
    safeties = defense.get('safeties', [])
    def_coord = defense.get('coordinator', {})
    def_staff = defense.get('staff_dict', {})
    def_team_id = defense['team_id']

    gs_dict = game_state.get_game_state_dict()
    gs_dict['yards_to_endzone'] = game_state.yards_to_endzone

    injuries = []
    clutch_activated = False

    from .ratings import is_clutch_situation
    if is_clutch_situation(gs_dict):
        clutch_activated = True

    # ===== STEP 1: Gap assignment (OL vs DL) =====
    ol_sars = []
    for ol in oline:
        stamina = game_state.player_stamina.get(ol['id'], 100)
        blocking = _attr(ol, 'true_blocking', _attr(ol, 'true_overall'))
        sar = calculate_sar(
            ol, off_coord, off_staff, weather, stamina,
            is_home=is_home_offense, game_state=gs_dict,
            is_playoff=is_playoff, side='offense',
        )
        # Weight blocking attribute
        sar = sar + (blocking - _attr(ol, 'true_overall')) // 2
        sar = max(1, min(99, sar))
        ol_sars.append(sar)

    dl_sars = []
    for dl in dline:
        stamina = game_state.player_stamina.get(dl['id'], 100)
        tackling = _attr(dl, 'true_tackling', _attr(dl, 'true_overall'))
        strength = _attr(dl, 'true_strength', _attr(dl, 'true_overall'))
        sar = calculate_sar(
            dl, def_coord, def_staff, weather, stamina,
            is_home=not is_home_offense, game_state=gs_dict,
            is_playoff=is_playoff, side='defense',
        )
        sar = sar + (tackling + strength - 2 * _attr(dl, 'true_overall')) // 4
        sar = max(1, min(99, sar))
        dl_sars.append(sar)

    gap_result = resolve_group_matchup(ol_sars, dl_sars)
    ol_wins = gap_result['attacker_wins']
    total_blockers = len(ol_sars)

    # Determine initial hole quality
    if ol_wins >= total_blockers - 1:
        hole_quality = 'good'
    elif ol_wins >= total_blockers // 2:
        hole_quality = 'average'
    else:
        hole_quality = 'stuffed'

    # ===== STEP 2: Second level (LB fill vs RB vision) =====
    rb_stamina = game_state.player_stamina.get(rb['id'], 100)
    rb_vision = _attr(rb, 'true_vision', _attr(rb, 'true_football_iq'))
    rb_sar = calculate_sar(
        rb, off_coord, off_staff, weather, rb_stamina,
        is_home=is_home_offense, game_state=gs_dict,
        is_playoff=is_playoff, side='offense',
    )

    # LB reaction
    lb_defender = None
    if linebackers:
        lb_defender = random.choice(linebackers)
        lb_stamina = game_state.player_stamina.get(lb_defender['id'], 100)
        lb_tackling = _attr(lb_defender, 'true_tackling', _attr(lb_defender, 'true_overall'))
        lb_sar = calculate_sar(
            lb_defender, def_coord, def_staff, weather, lb_stamina,
            is_home=not is_home_offense, game_state=gs_dict,
            is_playoff=is_playoff, side='defense',
        )
    else:
        lb_sar = 40

    # Vision matchup determines if RB finds the right hole
    vision_win = resolve_matchup(rb_vision, lb_sar // 2 + 25)  # Vision vs LB pursuit

    if hole_quality == 'stuffed' and not vision_win:
        # Stopped at or behind the line
        yards = random.randint(RUN_YARDS_BAD_BLOCK[0], RUN_YARDS_BAD_BLOCK[1])
    elif hole_quality == 'good' and vision_win:
        # Great blocking + good vision = big gain potential
        yards = random.randint(RUN_YARDS_GOOD_BLOCK[0], RUN_YARDS_GOOD_BLOCK[1])
    else:
        # Average result
        yards = random.randint(RUN_YARDS_BASE[0], RUN_YARDS_BASE[1])

    # ===== STEP 3: Ball carrier vs open field =====
    rb_elusiveness = _attr(rb, 'true_elusiveness')
    rb_speed = _attr(rb, 'true_speed')
    open_field_rating = (rb_elusiveness + rb_speed) // 2

    # Secondary defender (safety or LB)
    secondary_defender = lb_defender
    if safeties and yards > 5:
        secondary_defender = random.choice(safeties)

    if secondary_defender:
        sec_stamina = game_state.player_stamina.get(secondary_defender['id'], 100)
        sec_tackling = _attr(secondary_defender, 'true_tackling', _attr(secondary_defender, 'true_overall'))
        sec_speed = _attr(secondary_defender, 'true_speed', _attr(secondary_defender, 'true_overall'))
        sec_sar = (sec_tackling + sec_speed) // 2
    else:
        sec_sar = 40

    # Open field matchup — if RB wins, extend the run
    if yards > 3 and resolve_matchup(open_field_rating, sec_sar):
        bonus = random.randint(*OPEN_FIELD_BONUS_RANGE)
        yards += bonus

    # Big play chance (rare explosive runs)
    if yards >= 8 and random.random() < BIG_PLAY_RATE * 0.5:
        yards += random.randint(*BIG_RUN_BONUS_RANGE)

    # Cap at yards to endzone
    yards = min(yards, game_state.yards_to_endzone)
    is_td = yards >= game_state.yards_to_endzone
    is_big_play = yards >= BIG_PLAY_YARDS

    # Goal line situation
    situation = None
    if game_state.is_goal_line:
        situation = 'goal_line'

    # Fumble check
    fumble = False
    fumble_rate = TURNOVER_BASE_RATE
    if weather:
        from .weather import get_weather_modifiers
        w_mods = get_weather_modifiers(weather)
        fumble_rate *= w_mods.get('fumble', 1.0)
    # Higher fumble risk on big hits
    if yards > 10:
        fumble_rate *= 1.3

    if random.random() < fumble_rate and not is_td:
        fumble = True

    # Injury check
    fatigue_mult = get_fatigue_injury_multiplier(rb_stamina)
    if check_injury(_attr(rb, 'true_durability'), fatigue_mult, situation):
        inj = roll_severity()
        inj['player_id'] = rb['id']
        inj['player'] = rb
        injuries.append(inj)

    # Determine primary defender for narration
    primary_defender = secondary_defender or lb_defender
    if not primary_defender and dline:
        primary_defender = dline[0]

    narration = narrate_run(rb, primary_defender, yards, is_td, is_big_play)

    if fumble:
        narration += " " + narrate_fumble(rb, primary_defender)

    result_key = 'td' if is_td else ('fumble' if fumble else 'run')

    stats_dict = {
        'carry': {'player_id': rb['id'], 'team_id': off_team_id, 'yards': yards},
        'rush_td': {'player_id': rb['id'], 'team_id': off_team_id} if is_td else None,
        'tackle': {'player_id': primary_defender['id'], 'team_id': def_team_id} if primary_defender and not is_td else None,
    }
    if fumble:
        stats_dict['fumble'] = {'player_id': rb['id'], 'team_id': off_team_id}
        if primary_defender:
            stats_dict['forced_fumble'] = {'player_id': primary_defender['id'], 'team_id': def_team_id}

    return {
        'result': result_key,
        'yards_gained': yards,
        'play_type': 'run',
        'is_touchdown': is_td,
        'is_turnover': fumble,
        'is_big_play': is_big_play,
        'narration_text': narration,
        'primary_player_id': rb.get('id'),
        'target_player_id': None,
        'defender_player_id': primary_defender.get('id') if primary_defender else None,
        'pocket_time_grade': None,
        'separation_yards': None,
        'clutch_activated': clutch_activated,
        'stats': stats_dict,
        'injuries': injuries,
    }
