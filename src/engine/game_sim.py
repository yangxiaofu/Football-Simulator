"""
Main game simulation loop.

Orchestrates: coin toss → kickoff → drives → quarters → halftime → OT →
final score → DB writes.

Imports from all engine modules.
"""

import random
import sqlite3
from typing import Optional

from ..utils.constants import (
    PLAY_TIME_RANGES,
    HUDDLE_TIME_NORMAL,
    HUDDLE_TIME_HURRY,
    HUDDLE_TIME_2MIN,
    STARTERS_BY_POSITION,
    DEFAULT_GAME_PLAN,
    PENALTY_RATE_PER_GAME,
    PENALTY_YARDS,
    QUARTER_LENGTH_SECONDS,
    HOME_FIELD_MODIFIER,
    STAMINA_DRAIN_PER_SNAP,
    CLUTCH_2MIN_THRESHOLD,
    MAX_PLAYS_PER_GAME,
)
from .game_state import GameState
from .weather import generate_weather
from .play_caller import (
    select_offensive_play, select_defensive_play,
    should_attempt_fg, should_go_for_it, should_punt,
)
from .play_pass import resolve_pass_play
from .play_run import resolve_run_play
from .play_special import (
    resolve_field_goal, resolve_extra_point,
    resolve_two_point, resolve_punt, resolve_kickoff,
)
from .stats import StatsAccumulator
from .fatigue import drain_stamina, should_substitute
from .injury import get_injury_status_for_db
from .narration import (
    narrate_drive_summary, narrate_coin_toss,
    narrate_penalty, narrate_injury,
)
from .constants_engine import GAME_END_TEMPLATE, HALFTIME_TEMPLATE, TWO_MINUTE_WARNING_TEMPLATE


def simulate_game(db_path: str, game_id: int, verbose: bool = True) -> dict:
    """
    Simulate a complete game.

    This is the main public entry point for the engine.

    Args:
        db_path: Path to the franchise .db file
        game_id: ID of the game record in the `game` table
        verbose: Whether to print play-by-play narration

    Returns:
        dict with:
            'home_score': int
            'away_score': int
            'home_team': str
            'away_team': str
            'play_log': list of narration strings
            'home_stats': dict
            'away_stats': dict
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    try:
        # Load game record
        game = conn.execute("SELECT * FROM game WHERE id = ?", (game_id,)).fetchone()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        # Load teams
        home_team = conn.execute("SELECT * FROM team WHERE id = ?", (game['home_team_id'],)).fetchone()
        away_team = conn.execute("SELECT * FROM team WHERE id = ?", (game['away_team_id'],)).fetchone()

        # Load rosters
        home_players = _load_roster(conn, home_team['id'])
        away_players = _load_roster(conn, away_team['id'])

        # Load staff
        home_staff = _load_staff(conn, home_team['id'])
        away_staff = _load_staff(conn, away_team['id'])

        # Load depth chart (Phase 5 Prompt #3)
        from src.db.queries import get_depth_chart, get_league_state
        league = get_league_state(conn)
        season_year = league['current_season']
        depth_chart_home = get_depth_chart(conn, home_team['id'], season_year)
        depth_chart_away = get_depth_chart(conn, away_team['id'], season_year)

        # Convert to lookup dict: {position_slot: [(slot_order, player_id), ...]}
        def build_depth_chart_lookup(entries):
            lookup = {}
            for entry in entries:
                slot = entry['position_slot']
                if slot not in lookup:
                    lookup[slot] = []
                lookup[slot].append((entry['slot_order'], entry['player_id']))
            # Sort by slot_order
            for slot in lookup:
                lookup[slot].sort(key=lambda x: x[0])
            return lookup

        depth_lookup_home = build_depth_chart_lookup(depth_chart_home)
        depth_lookup_away = build_depth_chart_lookup(depth_chart_away)

        # Generate weather
        weather = generate_weather(
            home_team['stadium_type'],
            home_team['home_city_climate'],
            _get_week_number(conn, game['week_id']),
        )

        # Initialize game state
        state = GameState(
            home_team_id=home_team['id'],
            away_team_id=away_team['id'],
            home_team_name=f"{home_team['city']} {home_team['nickname']}",
            away_team_name=f"{away_team['city']} {away_team['nickname']}",
            home_team_abbr=home_team['abbreviation'],
            away_team_abbr=away_team['abbreviation'],
        )

        # Initialize stamina for all players
        for p in home_players + away_players:
            state.player_stamina[p['id']] = p.get('weekly_stamina', 100)

        # Initialize stats
        stats = StatsAccumulator(game_id, home_team['id'], away_team['id'])

        # Build team lineup dicts
        home_lineup = _build_lineup(home_players, home_staff, depth_lookup_home)
        away_lineup = _build_lineup(away_players, away_staff, depth_lookup_away)

        # Play log for output
        play_log = []

        def log(text: str):
            play_log.append(text)
            if verbose:
                print(text)

        # ===== COIN TOSS =====
        toss_winner_id = random.choice([home_team['id'], away_team['id']])
        toss_winner_name = state.home_team_name if toss_winner_id == home_team['id'] else state.away_team_name
        # Winner defers ~60% of the time (modern NFL)
        defers = random.random() < 0.60
        state.coin_toss_winner = toss_winner_id
        state.coin_toss_deferred = defers

        if defers:
            receiving_team = away_team['id'] if toss_winner_id == home_team['id'] else home_team['id']
            log(narrate_coin_toss(toss_winner_name, "defer to the second half"))
        else:
            receiving_team = toss_winner_id
            log(narrate_coin_toss(toss_winner_name, "receive"))

        kicking_team = home_team['id'] if receiving_team == away_team['id'] else away_team['id']
        second_half_receiver = kicking_team  # Team that kicks off first half receives second half

        # Weather report
        log(f"Weather: {weather['condition'].replace('_', ' ').title()}, "
            f"{weather['temperature']}°F, Wind: {weather['wind_speed']} mph")
        log("")

        # ===== OPENING KICKOFF =====
        log("--- Start of Q1 ---")
        _do_kickoff(state, home_lineup, away_lineup, kicking_team, weather, stats, log)

        # ===== MAIN GAME LOOP =====
        two_min_warned = {2: False, 4: False}

        while not state.is_game_over and state.total_plays < MAX_PLAYS_PER_GAME:
            # Check two-minute warning
            q = state.quarter
            if q in (2, 4) and state.time_remaining <= CLUTCH_2MIN_THRESHOLD and not two_min_warned[q]:
                two_min_warned[q] = True
                log(TWO_MINUTE_WARNING_TEMPLATE)

            # Check quarter end
            if state.time_remaining <= 0:
                quarter_ended = state.check_quarter_end()
                if state.is_halftime:
                    log("")
                    log(HALFTIME_TEMPLATE)
                    log(f"  {state.away_team_abbr} {state.away_score} - {state.home_team_abbr} {state.home_score}")
                    log("")
                    state.start_second_half()
                    log("--- Start of Q3 ---")
                    _do_kickoff(state, home_lineup, away_lineup, second_half_receiver,
                               weather, stats, log, receiving=False)
                    continue
                elif state.is_game_over:
                    break
                elif state.is_overtime:
                    log("")
                    log("--- OVERTIME ---")
                    # OT coin toss — other team gets to choose
                    ot_receiver = random.choice([home_team['id'], away_team['id']])
                    ot_kicker = home_team['id'] if ot_receiver == away_team['id'] else away_team['id']
                    _do_kickoff(state, home_lineup, away_lineup, ot_kicker, weather, stats, log)
                    continue
                else:
                    log(f"\n--- Start of Q{state.quarter} ---")
                    continue

            # ===== DRIVE LOGIC =====
            if state.is_kickoff:
                # After kickoff, start a drive
                continue

            # Determine offense/defense
            off_id = state.possession_team_id
            def_id = state.defending_team_id
            off_lineup = home_lineup if off_id == home_team['id'] else away_lineup
            def_lineup = home_lineup if def_id == home_team['id'] else away_lineup
            is_home_offense = off_id == home_team['id']
            off_staff = home_staff if is_home_offense else away_staff
            def_staff_dict = away_staff if is_home_offense else home_staff

            # Get active personnel (handle substitutions)
            offense_personnel = _get_offense_personnel(
                off_lineup, state, off_staff, is_home_offense,
            )
            defense_personnel = _get_defense_personnel(
                def_lineup, state, def_staff_dict, not is_home_offense,
            )

            gs_dict = state.get_game_state_dict()
            gs_dict['yards_to_endzone'] = state.yards_to_endzone
            gs_dict['field_position'] = state.field_position

            # ===== 4th DOWN DECISIONS =====
            if state.down > 4:
                # Turnover on downs
                log(f"Turnover on downs. {state.defending_team_name} takes over.")
                state.change_possession()
                state.field_position = 100 - state.field_position
                state.down = 1
                state.distance = 10
                state.drive_plays = 0
                state.drive_yards = 0
                state.drive_start_position = state.field_position
                continue

            if state.down == 4:
                if should_attempt_fg(gs_dict):
                    result = resolve_field_goal(
                        offense_personnel['kicker'],
                        state, weather,
                        off_staff, def_staff_dict,
                        is_home=is_home_offense,
                    )
                    _process_play_result(
                        result, state, stats, log,
                        offense_personnel, defense_personnel,
                        off_id, def_id, weather,
                    )

                    if result['result'] == 'fg_good':
                        state.score_field_goal()
                        log(f"  Score: {state.away_team_abbr} {state.away_score} - "
                            f"{state.home_team_abbr} {state.home_score}")
                        # Kickoff
                        _do_kickoff(state, home_lineup, away_lineup, off_id, weather, stats, log)
                    else:
                        # Missed/blocked FG — other team takes over
                        state.change_possession()
                        state.field_position = 100 - state.field_position
                        if state.field_position < 20:
                            state.field_position = 20
                        state.down = 1
                        state.distance = 10
                        state.drive_plays = 0
                        state.drive_yards = 0
                        state.drive_start_position = state.field_position
                    continue

                elif should_go_for_it(gs_dict):
                    pass  # Fall through to normal play
                else:
                    # Punt
                    returner = _get_returner(def_lineup)
                    result = resolve_punt(
                        offense_personnel['punter'],
                        returner,
                        state, weather, off_staff,
                    )
                    _process_play_result(
                        result, state, stats, log,
                        offense_personnel, defense_personnel,
                        off_id, def_id, weather,
                    )

                    new_pos = result.get('new_field_position', 20)
                    state.change_possession()
                    state.new_drive(state.possession_team_id, new_pos)
                    continue

            # ===== NORMAL PLAY =====
            off_call = select_offensive_play(gs_dict, DEFAULT_GAME_PLAN)
            def_call = select_defensive_play(gs_dict, DEFAULT_GAME_PLAN)

            if off_call['play_type'] == 'pass':
                offense_dict = {
                    'qb': offense_personnel['qb'],
                    'receivers': offense_personnel['receivers'],
                    'oline': offense_personnel['oline'],
                    'coordinator': off_staff.get('oc', {}),
                    'staff_dict': off_staff,
                    'team_id': off_id,
                    'team_name': state.possession_team_name,
                }
                defense_dict = {
                    'pass_rushers': defense_personnel['dline'],
                    'coverage': defense_personnel['coverage'],
                    'coordinator': def_staff_dict.get('dc', {}),
                    'staff_dict': def_staff_dict,
                    'team_id': def_id,
                    'team_name': state.defending_team_name,
                }

                # Add blitzers
                if def_call['is_blitz'] and def_call['blitz_count'] > 0:
                    blitzers = defense_personnel['linebackers'][:def_call['blitz_count']]
                    defense_dict['pass_rushers'] = defense_dict['pass_rushers'] + blitzers

                off_call['coverage_type'] = def_call['coverage_type']

                result = resolve_pass_play(
                    offense_dict, defense_dict, off_call,
                    state, weather, is_home_offense,
                )
            else:
                offense_dict = {
                    'rb': offense_personnel['rb'],
                    'oline': offense_personnel['oline'],
                    'coordinator': off_staff.get('oc', {}),
                    'staff_dict': off_staff,
                    'team_id': off_id,
                    'team_name': state.possession_team_name,
                }
                defense_dict = {
                    'dline': defense_personnel['dline'],
                    'linebackers': defense_personnel['linebackers'],
                    'safeties': defense_personnel['safeties'],
                    'coordinator': def_staff_dict.get('dc', {}),
                    'staff_dict': def_staff_dict,
                    'team_id': def_id,
                    'team_name': state.defending_team_name,
                }

                result = resolve_run_play(
                    offense_dict, defense_dict, off_call,
                    state, weather, is_home_offense,
                )

            _process_play_result(
                result, state, stats, log,
                offense_personnel, defense_personnel,
                off_id, def_id, weather,
            )

            # ===== POST-PLAY =====
            if result.get('is_touchdown'):
                state.score_touchdown()

                # PAT/2pt decision
                # Go for 2 if trailing by specific amounts late
                go_for_two = False
                if state.quarter >= 4 and state.time_remaining < 300:
                    deficit = -state.score_diff
                    if deficit in (2, 5):  # Trailing by 2 or 5 after TD
                        go_for_two = True

                if go_for_two:
                    two_pt = resolve_two_point(
                        {'qb': offense_personnel['qb'],
                         'receivers': offense_personnel['receivers'],
                         'team_id': off_id},
                        {'team_id': def_id},
                        state, weather,
                    )
                    log(f"  {two_pt['narration_text']}")
                    if two_pt['result'] == '2pt_good':
                        state.score_two_point()
                else:
                    xp = resolve_extra_point(
                        offense_personnel['kicker'], state, weather, off_staff,
                    )
                    log(f"  {xp['narration_text']}")
                    if xp['result'] == 'xp_good':
                        state.score_extra_point()
                    stats.record_xp_attempt(
                        offense_personnel['kicker']['id'], off_id,
                        xp['result'] == 'xp_good',
                    )

                log(f"  Score: {state.away_team_abbr} {state.away_score} - "
                    f"{state.home_team_abbr} {state.home_score}")

                # OT: game ends after scoring drive if both teams had possession
                if state.is_overtime:
                    state.is_game_over = True
                    continue

                # Kickoff
                _do_kickoff(state, home_lineup, away_lineup, off_id, weather, stats, log)

            elif result.get('is_turnover'):
                # Possession change on turnover
                state.change_possession()
                if result['result'] == 'int':
                    # INT return position (simplified)
                    state.field_position = random.randint(20, 45)
                else:
                    # Fumble recovery at spot
                    state.field_position = 100 - state.field_position

                state.field_position = max(1, min(99, state.field_position))
                state.down = 1
                state.distance = min(10, 100 - state.field_position)
                state.drive_plays = 0
                state.drive_yards = 0
                state.drive_start_position = state.field_position

                # OT: if defensive team scores/gets turnover
                if state.is_overtime:
                    pass  # Continue playing, defense now has the ball

            elif state.down > 4:
                # Turnover on downs — will be handled at top of loop
                pass

            # ===== CLOCK =====
            _advance_clock(state, result)

            # Inject occasional penalty
            if random.random() < (PENALTY_RATE_PER_GAME / 130.0):  # ~6 per 130 plays
                _inject_penalty(state, off_id, def_id,
                                state.possession_team_name,
                                state.defending_team_name, log)

        # ===== GAME OVER =====
        log("")
        log(GAME_END_TEMPLATE.format(
            away_team=state.away_team_abbr,
            away_score=state.away_score,
            home_team=state.home_team_abbr,
            home_score=state.home_score,
        ))

        # Write results to database
        with conn:
            # Update game record
            conn.execute("""
                UPDATE game SET
                    home_score = ?, away_score = ?, is_complete = 1,
                    weather_condition = ?, wind_speed = ?,
                    temperature = ?, precipitation = ?
                WHERE id = ?
            """, (
                state.home_score, state.away_score,
                weather['condition'], weather['wind_speed'],
                weather['temperature'], 1 if weather['precipitation'] else 0,
                game_id,
            ))

            # Write stats
            stats.write_box_scores(conn)
            stats.write_plays(conn)
            stats.write_key_plays(conn)

            # Write injuries to player table
            for player_id, inj in state.in_game_injuries.items():
                db_status = get_injury_status_for_db(inj['severity'])
                conn.execute("""
                    UPDATE player SET
                        injury_status = ?,
                        injury_weeks_remaining = ?
                    WHERE id = ?
                """, (db_status, inj['weeks_out'], player_id))

        home_stats = stats.get_team_stats_summary(home_team['id'])
        away_stats = stats.get_team_stats_summary(away_team['id'])

        return {
            'home_score': state.home_score,
            'away_score': state.away_score,
            'home_team': state.home_team_name,
            'away_team': state.away_team_name,
            'home_abbr': state.home_team_abbr,
            'away_abbr': state.away_team_abbr,
            'play_log': play_log,
            'home_stats': home_stats,
            'away_stats': away_stats,
            'total_plays': state.total_plays,
            'weather': weather,
        }

    finally:
        conn.close()


# ========== Internal helpers ==========

def _load_roster(conn: sqlite3.Connection, team_id: int) -> list[dict]:
    """Load all active players for a team."""
    rows = conn.execute("""
        SELECT * FROM player
        WHERE team_id = ? AND roster_status = 'active' AND is_active = 1
        ORDER BY true_overall DESC
    """, (team_id,)).fetchall()
    return [dict(row) for row in rows]


def _load_staff(conn: sqlite3.Connection, team_id: int) -> dict:
    """Load staff for a team as role -> staff dict."""
    rows = conn.execute("""
        SELECT * FROM staff WHERE team_id = ?
    """, (team_id,)).fetchall()

    staff = {}
    for row in rows:
        d = dict(row)
        role = d['role'].lower()
        staff[role] = d
    return staff


def _get_week_number(conn: sqlite3.Connection, week_id: int) -> int:
    """Get the week number for a game's week_id."""
    row = conn.execute("SELECT week_number FROM week WHERE id = ?", (week_id,)).fetchone()
    return row['week_number'] if row else 1


def _build_lineup(players: list[dict], staff: dict, depth_chart_lookup: dict) -> dict:
    """
    Build game-day lineup from roster, selecting starters by position.

    Args:
        players: List of player dicts
        staff: Staff dict
        depth_chart_lookup: {position_slot: [(slot_order, player_id), ...]}

    Returns dict with position -> list of player dicts (starters first, then backups).
    """
    lineup = {}
    by_position = {}

    for p in players:
        pos = p['position']
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(p)

    # Sort each position group by overall (descending)
    for pos, group in by_position.items():
        group.sort(key=lambda x: x.get('true_overall', 0), reverse=True)
        starters_count = STARTERS_BY_POSITION.get(pos, 1)
        lineup[pos] = {
            'starters': group[:starters_count],
            'backups': group[starters_count:],
            'all': group,
        }

    # Store depth chart in lineup dict for later use (Phase 5 Prompt #3)
    lineup['_depth_chart'] = depth_chart_lookup

    return lineup


def _get_offense_personnel(lineup: dict, state: GameState, staff: dict, is_home: bool) -> dict:
    """Get current offensive personnel, handling substitutions."""
    qb = _get_active_player(lineup, 'QB', state, 0, depth_slot='QB')
    rb = _get_active_player(lineup, 'RB', state, 0, depth_slot='RB')

    receivers = []
    # 3 WR (use WR1, WR2, WR3 depth slots)
    for i, slot in enumerate(['WR1', 'WR2', 'WR3']):
        wr = _get_active_player(lineup, 'WR', state, i, depth_slot=slot)
        if wr:
            receivers.append(wr)
    # 1 TE
    te = _get_active_player(lineup, 'TE', state, 0, depth_slot='TE')
    if te:
        receivers.append(te)
    # RB as receiver option
    if rb and rb not in receivers:
        receivers.append(rb)

    oline = []
    for i, slot in enumerate(['LT', 'LG', 'C', 'RG', 'RT']):
        ol = _get_active_player(lineup, 'OL', state, i, depth_slot=slot)
        if ol:
            oline.append(ol)

    kicker = _get_active_player(lineup, 'K', state, 0, depth_slot='K')
    punter = _get_active_player(lineup, 'P', state, 0, depth_slot='P')

    # Fallback: if no kicker/punter, use QB
    if not kicker:
        kicker = qb
    if not punter:
        punter = qb

    return {
        'qb': qb,
        'rb': rb,
        'receivers': receivers,
        'oline': oline,
        'kicker': kicker,
        'punter': punter,
    }


def _get_defense_personnel(lineup: dict, state: GameState, staff: dict, is_home: bool) -> dict:
    """Get current defensive personnel."""
    dline = []
    for i, slot in enumerate(['LE', 'DT1', 'DT2', 'RE']):
        dl = _get_active_player(lineup, 'DL', state, i, depth_slot=slot)
        if dl:
            dline.append(dl)

    linebackers = []
    for i, slot in enumerate(['LOLB', 'MLB', 'ROLB']):
        lb = _get_active_player(lineup, 'LB', state, i, depth_slot=slot)
        if lb:
            linebackers.append(lb)

    corners = []
    for i, slot in enumerate(['CB1', 'CB2']):
        cb = _get_active_player(lineup, 'CB', state, i, depth_slot=slot)
        if cb:
            corners.append(cb)

    safeties = []
    for i, slot in enumerate(['FS', 'SS']):
        s = _get_active_player(lineup, 'S', state, i, depth_slot=slot)
        if s:
            safeties.append(s)

    coverage = corners + safeties

    return {
        'dline': dline,
        'linebackers': linebackers,
        'corners': corners,
        'safeties': safeties,
        'coverage': coverage,
    }


def _get_active_player(lineup: dict, position: str, state: GameState, index: int, depth_slot: Optional[str] = None) -> dict:
    """
    Get the active player at a position/index, handling injuries and fatigue subs.

    Args:
        lineup: Team lineup dict
        position: Generic position (QB, RB, WR, etc.)
        state: Game state
        index: Position index (0 for starter, 1+ for backups)
        depth_slot: Optional depth chart position slot (e.g., 'WR1', 'LT', 'CB1')

    Returns:
        Player dict or None
    """
    # Phase 5 Prompt #3: Check depth chart first if depth_slot provided
    if depth_slot and '_depth_chart' in lineup:
        depth_entries = lineup['_depth_chart'].get(depth_slot, [])
        for slot_order, player_id in depth_entries:
            # Find player in roster
            pos_data = lineup.get(position, {})
            all_players = pos_data.get('all', [])
            player = next((p for p in all_players if p['id'] == player_id), None)
            if not player:
                continue
            # Skip if injured
            if player_id in state.in_game_injuries:
                continue
            # Check fatigue substitution
            stamina = state.player_stamina.get(player_id, 100)
            if should_substitute(stamina, position):
                continue
            # Found healthy depth chart player — attach depth_slot for SAR penalty calculation
            player['_depth_slot'] = depth_slot
            return player

    # Fallback to rating-based selection (existing code)
    pos_data = lineup.get(position, {})
    all_players = pos_data.get('all', [])

    if not all_players:
        return None

    # Try starters first, then backups
    for p in all_players[index:]:
        pid = p['id']
        # Skip injured players
        if pid in state.in_game_injuries:
            continue
        # Check fatigue substitution
        stamina = state.player_stamina.get(pid, 100)
        if should_substitute(stamina, position) and len(all_players) > index + 1:
            continue
        # Attach depth_slot for SAR penalty calculation (Phase 5 Prompt #3 Cleanup Round 2)
        if depth_slot:
            p['_depth_slot'] = depth_slot
        return p

    # If all are fatigued/injured, return the best available
    for p in all_players:
        if p['id'] not in state.in_game_injuries:
            if depth_slot:
                p['_depth_slot'] = depth_slot
            return p

    # Last resort: return first player
    if all_players:
        if depth_slot:
            all_players[0]['_depth_slot'] = depth_slot
        return all_players[0]
    return None


def _get_returner(lineup: dict) -> dict:
    """Get the kick/punt returner (fastest WR or RB)."""
    candidates = []
    for pos in ('WR', 'RB'):
        pos_data = lineup.get(pos, {})
        for p in pos_data.get('all', []):
            candidates.append(p)

    if not candidates:
        return None

    # Pick fastest
    candidates.sort(key=lambda p: p.get('true_speed', 0), reverse=True)
    return candidates[0]


def _do_kickoff(
    state: GameState,
    home_lineup: dict,
    away_lineup: dict,
    kicking_team_id: int,
    weather: dict,
    stats: StatsAccumulator,
    log_fn,
    receiving: bool = True,
):
    """Execute a kickoff and set up the receiving team's drive."""
    kick_lineup = home_lineup if kicking_team_id == state.home_team_id else away_lineup
    recv_lineup = away_lineup if kicking_team_id == state.home_team_id else home_lineup
    recv_team_id = state.away_team_id if kicking_team_id == state.home_team_id else state.home_team_id

    kicker = _get_active_player(kick_lineup, 'K', state, 0)
    if not kicker:
        # Fallback to punter
        kicker = _get_active_player(kick_lineup, 'P', state, 0)
    if not kicker:
        kicker = {'id': 0, 'first_name': 'Unknown', 'last_name': 'Kicker', 'true_kick_power': 50}

    returner = _get_returner(recv_lineup)

    kick_staff = _load_staff_from_lineup(kick_lineup)

    result = resolve_kickoff(kicker, returner, state, weather, kick_staff)
    log_fn(result['narration_text'])

    # Record kickoff return stats
    if result.get('stats', {}).get('kick_return'):
        kick_ret_data = result['stats']['kick_return']
        if kick_ret_data['player_id']:
            stats.record_kick_return(
                kick_ret_data['player_id'],
                recv_team_id,
                kick_ret_data['yards'],
                kick_ret_data.get('is_td', False)
            )

    # Handle injuries
    for inj in result.get('injuries', []):
        state.in_game_injuries[inj['player_id']] = inj
        log_fn(f"  {narrate_injury(inj['player'], inj['severity'])}")

    # Set up receiving team's drive
    new_pos = result.get('new_field_position', 25)
    state.new_drive(recv_team_id, new_pos)
    state.is_kickoff = False

    # Advance clock for kickoff
    _advance_clock(state, result)


def _load_staff_from_lineup(lineup: dict) -> dict:
    """Placeholder: in the actual game sim, staff is loaded separately."""
    return {}


def _process_play_result(
    result: dict,
    state: GameState,
    stats: StatsAccumulator,
    log_fn,
    offense_personnel: dict,
    defense_personnel: dict,
    off_team_id: int,
    def_team_id: int,
    weather: dict,
):
    """Process a play result: update stats, state, injuries, narration."""
    # Log narration
    down_str = _down_distance_str(state)
    log_fn(f"  {down_str} | {result['narration_text']}")

    # Record stats
    stat_instructions = result.get('stats', {})
    _record_stats(stats, stat_instructions, off_team_id, def_team_id)

    # Record play to stats accumulator
    play_data = {
        'play_number': state.play_number + 1,
        'quarter': state.quarter,
        'time_remaining': state.time_remaining,
        'possession_team_id': off_team_id,
        'field_position': state.field_position,
        'down': state.down,
        'distance': state.distance,
        'home_score': state.home_score,
        'away_score': state.away_score,
        'play_type': result.get('play_type', 'unknown'),
        'yards_gained': result.get('yards_gained', 0),
        'result': result.get('result', 'unknown'),
        'is_touchdown': 1 if result.get('is_touchdown') else 0,
        'is_turnover': 1 if result.get('is_turnover') else 0,
        'is_big_play': 1 if result.get('is_big_play') else 0,
        'primary_player_id': result.get('primary_player_id'),
        'target_player_id': result.get('target_player_id'),
        'defender_player_id': result.get('defender_player_id'),
        'pocket_time_grade': result.get('pocket_time_grade'),
        'separation_yards': result.get('separation_yards'),
        'clutch_activated': 1 if result.get('clutch_activated') else 0,
        'narration_text': result.get('narration_text', ''),
    }
    stats.record_play(play_data)

    # Update game state (yards, downs)
    yards = result.get('yards_gained', 0)
    if result.get('play_type') in ('pass', 'run') and not result.get('is_turnover'):
        state.advance_play(yards)
    elif result.get('play_type') in ('pass', 'run'):
        # Turnover — advance_play for tracking, possession change handled by caller
        state.play_number += 1
        state.total_plays += 1

    # Process injuries
    for inj in result.get('injuries', []):
        state.in_game_injuries[inj['player_id']] = inj
        log_fn(f"    {narrate_injury(inj['player'], inj['severity'])}")

    # Drain stamina for involved players
    _drain_play_stamina(state, offense_personnel, defense_personnel, result)


def _record_stats(stats: StatsAccumulator, instructions: dict, off_team_id: int, def_team_id: int):
    """Process stat recording instructions from a play result."""
    for stat_type, info in instructions.items():
        if info is None:
            continue

        pid = info.get('player_id')
        tid = info.get('team_id', off_team_id)

        if stat_type == 'pass_attempt':
            stats.record_pass_attempt(pid, tid)
        elif stat_type == 'completion':
            stats.record_completion(pid, info['receiver_id'], tid, info['yards'])
        elif stat_type == 'pass_td':
            stats.record_pass_td(pid, info['receiver_id'], tid)
        elif stat_type == 'target':
            stats.record_target(pid, tid)
        elif stat_type == 'interception_thrown':
            stats.record_interception_thrown(pid, tid)
        elif stat_type == 'sack_taken':
            stats.record_sack_taken(pid, tid)
        elif stat_type == 'carry':
            stats.record_carry(pid, tid, info.get('yards', 0))
        elif stat_type == 'rush_td':
            stats.record_rush_td(pid, tid)
        elif stat_type == 'fumble':
            stats.record_fumble(pid, tid)
        elif stat_type == 'tackle':
            stats.record_tackle(pid, tid)
        elif stat_type == 'sack':
            stats.record_sack(pid, tid)
        elif stat_type == 'interception':
            stats.record_interception(pid, tid)
        elif stat_type == 'pass_deflection':
            stats.record_pass_deflection(pid, tid)
        elif stat_type == 'forced_fumble':
            stats.record_forced_fumble(pid, tid)
        elif stat_type == 'fg_attempt':
            stats.record_fg_attempt(pid, tid, info.get('distance', 0), info.get('made', False))
        elif stat_type == 'punt':
            stats.record_punt(pid, tid, info.get('yards', 0))
        elif stat_type == 'punt_return':
            stats.record_punt_return(pid, tid, info.get('yards', 0), info.get('is_td', False))
        elif stat_type == 'kick_return':
            stats.record_kick_return(pid, tid, info.get('yards', 0), info.get('is_td', False))


def _advance_clock(state: GameState, result: dict):
    """Advance the game clock based on play result."""
    play_type = result.get('play_type', 'run')
    play_result = result.get('result', 'run')

    # Determine time consumed
    if play_result in ('incomplete', 'spike'):
        # Clock stops on incomplete pass
        time_key = 'pass_incomplete'
    elif play_result == 'sack':
        time_key = 'sack'
    elif play_result == 'scramble':
        time_key = 'scramble'
    elif play_type == 'pass' and play_result in ('complete', 'td'):
        time_key = 'pass_complete'
    elif play_type == 'run':
        time_key = 'run'
    elif play_type == 'fg_attempt':
        time_key = 'fg_attempt'
    elif play_type == 'punt':
        time_key = 'punt'
    elif play_type == 'kickoff':
        time_key = 'kickoff'
    elif play_result == 'kneel':
        time_key = 'kneel'
    else:
        time_key = 'run'

    time_range = PLAY_TIME_RANGES.get(time_key, (5, 8))
    play_time = random.randint(time_range[0], time_range[1])

    # Add huddle time
    if state.is_two_minute_drill:
        huddle = random.randint(HUDDLE_TIME_2MIN[0], HUDDLE_TIME_2MIN[1])
    elif state.quarter >= 4 and abs(state.score_diff) <= 7:
        huddle = random.randint(HUDDLE_TIME_HURRY[0], HUDDLE_TIME_HURRY[1])
    else:
        huddle = random.randint(HUDDLE_TIME_NORMAL[0], HUDDLE_TIME_NORMAL[1])

    total_time = play_time + huddle
    state.advance_clock(total_time)


def _drain_play_stamina(
    state: GameState,
    offense_personnel: dict,
    defense_personnel: dict,
    result: dict,
):
    """Drain stamina for all players involved in a play."""
    # Offense
    high_effort_players = set()
    primary_id = result.get('primary_player_id')
    target_id = result.get('target_player_id')
    if primary_id:
        high_effort_players.add(primary_id)
    if target_id:
        high_effort_players.add(target_id)

    for key in ('qb', 'rb'):
        p = offense_personnel.get(key)
        if p:
            is_high = p['id'] in high_effort_players
            new_stam = drain_stamina(
                state.player_stamina.get(p['id'], 100),
                p['position'],
                high_effort=is_high,
            )
            state.player_stamina[p['id']] = new_stam

    for p in offense_personnel.get('receivers', []):
        is_high = p['id'] in high_effort_players
        new_stam = drain_stamina(
            state.player_stamina.get(p['id'], 100),
            p['position'],
            high_effort=is_high,
        )
        state.player_stamina[p['id']] = new_stam

    for p in offense_personnel.get('oline', []):
        new_stam = drain_stamina(
            state.player_stamina.get(p['id'], 100),
            p['position'],
        )
        state.player_stamina[p['id']] = new_stam

    # Defense
    for key in ('dline', 'linebackers', 'corners', 'safeties'):
        for p in defense_personnel.get(key, []):
            defender_id = result.get('defender_player_id')
            is_high = (p['id'] == defender_id)
            new_stam = drain_stamina(
                state.player_stamina.get(p['id'], 100),
                p['position'],
                high_effort=is_high,
            )
            state.player_stamina[p['id']] = new_stam


def _down_distance_str(state: GameState) -> str:
    """Format current down and distance."""
    down_names = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}
    down = down_names.get(state.down, f'{state.down}th')

    if state.yards_to_endzone <= state.distance:
        return f"{down} & Goal at {state.possession_team_abbr} {state.field_position}"

    return f"{down} & {state.distance} at {state.possession_team_abbr} {state.field_position}"


def _inject_penalty(
    state: GameState,
    off_team_id: int,
    def_team_id: int,
    off_name: str,
    def_name: str,
    log_fn,
):
    """Inject a procedural penalty."""
    penalty_types = list(PENALTY_YARDS.keys())
    penalty_type = random.choice(penalty_types)
    yards = PENALTY_YARDS[penalty_type]

    # Random team (slight bias toward offense)
    if random.random() < 0.55:
        team_name = off_name
        # Offensive penalty: move backward
        state.field_position = max(1, state.field_position - yards)
        if penalty_type == 'false_start':
            state.distance += yards
    else:
        team_name = def_name
        # Defensive penalty: move forward, automatic first down on some
        state.field_position = min(99, state.field_position + yards)
        if penalty_type in ('pass_interference', 'roughing_passer'):
            state.down = 1
            state.distance = min(10, state.yards_to_endzone)

    narration = narrate_penalty(penalty_type, team_name, yards)
    log_fn(f"  {narration}")
