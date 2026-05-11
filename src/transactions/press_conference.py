"""
Tier 1 weekly press conference system (Phase 4 Prompt #5).

Generates one press event per team per regular season week (weeks 1-17).
Player coach gets interactive prompt; AI coaches auto-resolve.
Effects: small deltas to owner sentiment, fan sentiment, and locker room satisfaction.

Autopilot: Player coach can set a default response to auto-resolve future pressers.
"""

import sqlite3
import random
from datetime import datetime
from typing import Optional

from src.utils.constants import (
    PRESS_AUTOPILOT_VALID_CHOICES,
    PRESS_AUTOPILOT_HARNESS_FALLBACK,
    PRESS_EFFECTS,
    PRESS_BLOWOUT_MARGIN,
    PRESS_LOSING_STREAK_THRESHOLD,
    PRESS_WINNING_STREAK_THRESHOLD,
    PRESS_LOCKER_ROOM_TOP_N_PLAYERS,
    SENTIMENT_MIN,
    SENTIMENT_MAX,
    FAN_SENTIMENT_DEFAULT,
    # Phase 5 P9 — new context/LRU constants
    PRESS_BLOWOUT_MARGIN_THRESHOLD,
    PRESS_UPSET_WIN_DELTA,
    PRESS_CLINCH_WIN_THRESHOLD,
    PRESS_ELIMINATE_WIN_THRESHOLD,
    PRESS_STARTER_INJURY_MIN_WEEKS,
    PRESS_LRU_EXCLUDE_COUNT,
    PRESS_MIN_POOL_FALLBACK,
    PRESS_CONTEXT_POST_WIN_BLOWOUT,
    PRESS_CONTEXT_POST_WIN_NARROW,
    PRESS_CONTEXT_POST_WIN_VS_RIVAL,
    PRESS_CONTEXT_POST_LOSS_BLOWOUT,
    PRESS_CONTEXT_POST_LOSS_CLOSE,
    PRESS_CONTEXT_POST_LOSS_UPSET,
    PRESS_CONTEXT_POST_STARTER_INJURY,
    PRESS_CONTEXT_MID_SEASON_GRIND,
    PRESS_CONTEXT_PRE_DIVISION_GAME,
    PRESS_CONTEXT_POST_INJURY_CRITICAL,
    PRESS_CONTEXT_PRE_PLAYOFF_GAME,
    PRESS_CONTEXT_POST_CLINCHING,
    PRESS_CONTEXT_POST_ELIMINATED,
)
from src.utils.press_templates import get_templates_by_context, get_template_by_id
from src.db import queries
from src.db.queries import update_sentiment_drivers, get_owner_sentiment
from src.transactions.satisfaction import adjust_satisfaction


def detect_context(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int
) -> str:
    """
    Detect the press conference context based on recent game results.

    Phase 5 P9 priority order:
    1. lineup_controversy (P5, highest priority)
    2. post_starter_injury (key starter went down this week)
    3. post_clinching (just clinched a playoff spot)
    4. post_eliminated (just got eliminated)
    5. losing_streak (3+ consecutive losses)
    6. winning_streak (3+ consecutive wins)
    7. Post-game sub-contexts:
       - post_win_vs_rival, post_win_blowout, post_win_narrow
       - post_loss_blowout, post_loss_upset, post_loss_close
    8. post_injury_critical (any critical 'Out' injury this week via depth chart)
    9. pre_playoff_game (week 15+, in playoff position, not clinched)
    10. pre_division_game (next week is a division game)
    11. mid_season_grind (weeks 10-14, no other trigger)
    12. routine (fallback)
    """
    # Priority 1: lineup controversy (P5)
    from ..db.queries import check_lineup_controversy_queued
    from ..utils.constants import TIER1_CONTEXT_LINEUP_CONTROVERSY
    if check_lineup_controversy_queued(conn, team_id, season_year, week_number):
        return TIER1_CONTEXT_LINEUP_CONTROVERSY

    # Get this week's game result
    game = conn.execute("""
        SELECT
            g.id,
            g.home_team_id,
            g.away_team_id,
            g.home_score,
            g.away_score,
            home_div.name as home_division,
            away_div.name as away_division
        FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        JOIN team home ON g.home_team_id = home.id
        JOIN division home_div ON home.division_id = home_div.id
        JOIN team away ON g.away_team_id = away.id
        JOIN division away_div ON away.division_id = away_div.id
        WHERE s.year = ?
          AND w.week_number = ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 1
    """, (season_year, week_number, team_id, team_id)).fetchone()

    if not game:
        # No game this week — check pre-game/bye contexts
        return _detect_no_game_context(conn, team_id, season_year, week_number)

    # Determine if team won and margin
    is_home = game['home_team_id'] == team_id
    team_score = game['home_score'] if is_home else game['away_score']
    opp_score = game['away_score'] if is_home else game['home_score']
    opp_team_id = game['away_team_id'] if is_home else game['home_team_id']
    margin = abs(team_score - opp_score)
    won = team_score > opp_score
    opp_division = game['away_division'] if is_home else game['home_division']
    team_division = game['home_division'] if is_home else game['away_division']
    is_division_game = opp_division == team_division

    # Priority 2: starter injury this week (via depth chart auto-promotion)
    if _had_starter_injury_this_week(conn, team_id, season_year):
        return PRESS_CONTEXT_POST_STARTER_INJURY

    # Priority 3: clinching
    if _just_clinched(conn, team_id, season_year, week_number):
        return PRESS_CONTEXT_POST_CLINCHING

    # Priority 4: elimination
    if _just_eliminated(conn, team_id, season_year, week_number):
        return PRESS_CONTEXT_POST_ELIMINATED

    # Priority 5–6: streaks (last 3 completed games including this one)
    last_3_games = conn.execute("""
        SELECT
            CASE
                WHEN g.home_team_id = ? THEN
                    CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END
                ELSE
                    CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END
            END as won
        FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ?
          AND w.week_number <= ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 1
        ORDER BY w.week_number DESC
        LIMIT 3
    """, (team_id, season_year, week_number, team_id, team_id)).fetchall()

    if len(last_3_games) >= PRESS_LOSING_STREAK_THRESHOLD:
        results = [g['won'] for g in last_3_games]
        if all(r == 0 for r in results):
            return 'losing_streak'
        if all(r == 1 for r in results):
            return 'winning_streak'

    # Priority 7: post-game sub-contexts (blowout check before rival — a 20-pt blowout
    # is more notable as a dominant win than as a rivalry result)
    if won:
        if margin >= PRESS_BLOWOUT_MARGIN_THRESHOLD:
            return PRESS_CONTEXT_POST_WIN_BLOWOUT
        if is_division_game:
            return PRESS_CONTEXT_POST_WIN_VS_RIVAL
        return PRESS_CONTEXT_POST_WIN_NARROW
    else:
        if margin >= PRESS_BLOWOUT_MARGIN_THRESHOLD:
            return PRESS_CONTEXT_POST_LOSS_BLOWOUT
        if _was_user_favored(conn, team_id, opp_team_id, season_year):
            return PRESS_CONTEXT_POST_LOSS_UPSET
        return PRESS_CONTEXT_POST_LOSS_CLOSE

    # Priority 8 and beyond handled by _detect_no_game_context (unreachable here)


def _had_starter_injury_this_week(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
) -> bool:
    """Return True if a depth-chart starter (slot_order=1) was auto-promoted this season,
    and the replaced player has injury_weeks_remaining >= PRESS_STARTER_INJURY_MIN_WEEKS."""
    row = conn.execute("""
        SELECT 1 FROM depth_chart dc
        JOIN player p ON p.id = dc.replaced_player_id
        WHERE dc.team_id = ?
          AND dc.season_year = ?
          AND dc.slot_order = 1
          AND dc.replaced_player_id IS NOT NULL
          AND p.injury_weeks_remaining >= ?
        LIMIT 1
    """, (team_id, season_year, PRESS_STARTER_INJURY_MIN_WEEKS)).fetchone()
    return row is not None


def _just_clinched(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> bool:
    """Heuristic: wins >= PRESS_CLINCH_WIN_THRESHOLD at week >= 15 and not already clinched this week."""
    if week_number < 15:
        return False
    row = conn.execute("""
        SELECT wins FROM team_season_running
        WHERE team_id = ? AND season_year = ? AND is_playoff = 0
    """, (team_id, season_year)).fetchone()
    if not row:
        return False
    # Only fire once: clinch threshold exactly crossed (wins == threshold at this week)
    return row['wins'] == PRESS_CLINCH_WIN_THRESHOLD


def _just_eliminated(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> bool:
    """Heuristic: wins <= PRESS_ELIMINATE_WIN_THRESHOLD at week >= 14."""
    if week_number < 14:
        return False
    row = conn.execute("""
        SELECT wins FROM team_season_running
        WHERE team_id = ? AND season_year = ? AND is_playoff = 0
    """, (team_id, season_year)).fetchone()
    if not row:
        return False
    return row['wins'] <= PRESS_ELIMINATE_WIN_THRESHOLD


def _was_user_favored(
    conn: sqlite3.Connection,
    team_id: int,
    opp_team_id: int,
    season_year: int,
) -> bool:
    """Proxy: return True if user team has more wins than opponent this season."""
    user_row = conn.execute("""
        SELECT wins FROM team_season_running
        WHERE team_id = ? AND season_year = ? AND is_playoff = 0
    """, (team_id, season_year)).fetchone()
    opp_row = conn.execute("""
        SELECT wins FROM team_season_running
        WHERE team_id = ? AND season_year = ? AND is_playoff = 0
    """, (opp_team_id, season_year)).fetchone()
    if not user_row or not opp_row:
        return False
    return user_row['wins'] > opp_row['wins'] + PRESS_UPSET_WIN_DELTA - 1


def _detect_no_game_context(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> str:
    """Detect context when no game was played this week (bye, pre-season, etc.)."""
    # post_injury_critical: any player with 'Out' status on the roster
    critical_injury = conn.execute("""
        SELECT 1 FROM player
        WHERE team_id = ? AND injury_status = 'Out' AND is_active = 1
        LIMIT 1
    """, (team_id,)).fetchone()
    if critical_injury:
        return PRESS_CONTEXT_POST_INJURY_CRITICAL

    # pre_playoff_game: week 15+ and team is in playoff position (winning record)
    if week_number >= 15:
        record = conn.execute("""
            SELECT wins, losses FROM team_season_running
            WHERE team_id = ? AND season_year = ? AND is_playoff = 0
        """, (team_id, season_year)).fetchone()
        if record and record['wins'] >= PRESS_CLINCH_WIN_THRESHOLD - 2:
            return PRESS_CONTEXT_PRE_PLAYOFF_GAME

    # pre_division_game: next week's game is vs a division opponent
    next_game = conn.execute("""
        SELECT
            g.home_team_id,
            g.away_team_id,
            home_div.name as home_division,
            away_div.name as away_division
        FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        JOIN team home ON g.home_team_id = home.id
        JOIN division home_div ON home.division_id = home_div.id
        JOIN team away ON g.away_team_id = away.id
        JOIN division away_div ON away.division_id = away_div.id
        WHERE s.year = ?
          AND w.week_number = ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 0
        LIMIT 1
    """, (season_year, week_number + 1, team_id, team_id)).fetchone()

    if next_game:
        is_home = next_game['home_team_id'] == team_id
        team_div = next_game['home_division'] if is_home else next_game['away_division']
        opp_div = next_game['away_division'] if is_home else next_game['home_division']
        if team_div == opp_div:
            return PRESS_CONTEXT_PRE_DIVISION_GAME

    # mid_season_grind: weeks 10-14
    if 10 <= week_number <= 14:
        return PRESS_CONTEXT_MID_SEASON_GRIND

    return 'routine'


def select_template_for_context(
    conn: sqlite3.Connection,
    context: str,
    coach_id: int,
) -> dict:
    """Phase 5 P9: LRU anti-repetition guard.

    Excludes the last PRESS_LRU_EXCLUDE_COUNT templates used by this coach in this context.
    Falls back to least-recently-used if the candidate pool drops below PRESS_MIN_POOL_FALLBACK.
    """
    all_templates = get_templates_by_context(context)
    if not all_templates:
        return random.choice(get_templates_by_context('routine'))

    recent_ids = queries.get_recent_template_ids_for_coach_context(
        conn, coach_id, context, limit=PRESS_LRU_EXCLUDE_COUNT
    )

    candidate_pool = [t for t in all_templates if t['id'] not in recent_ids]

    if len(candidate_pool) >= PRESS_MIN_POOL_FALLBACK:
        return random.choice(candidate_pool)

    # Pool too thin — pick the template used LONGEST ago (last item in recent_ids)
    if recent_ids:
        lru_id = recent_ids[-1]
        for t in all_templates:
            if t['id'] == lru_id:
                return t

    return random.choice(all_templates)


def generate_weekly_press_event(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    team_id: int,
    coach_id: int,
    headless: bool = False
) -> dict:
    """
    Generate a weekly press conference event for a team.

    Args:
        conn: Database connection
        season_year: Season year
        week_number: Week number (1-17)
        team_id: Team ID
        coach_id: Coach ID
        headless: If True, auto-resolve with autopilot default (stress harness mode)

    Returns:
        dict with:
            - press_event_id: int
            - context_type: str
            - question: str
            - responses: dict (only if not resolved)
            - selected_response: str (only if resolved)
            - resolved: bool
            - delta_owner: int (only if resolved)
            - delta_fan: int (only if resolved)
            - delta_locker_room: int (only if resolved)
    """
    # Check if event already exists
    existing = conn.execute("""
        SELECT id FROM press_event
        WHERE season_year = ? AND week_number = ? AND team_id = ?
    """, (season_year, week_number, team_id)).fetchone()

    if existing:
        # Return existing event
        event = conn.execute("""
            SELECT * FROM press_event WHERE id = ?
        """, (existing['id'],)).fetchone()
        template = get_template_by_id(event['question_template_id'])
        return {
            'press_event_id': event['id'],
            'context_type': event['context_type'],
            'question': template['question'],
            'selected_response': event['selected_response'],
            'resolved': event['resolved_at'] is not None,
            'delta_owner': event['delta_owner'],
            'delta_fan': event['delta_fan'],
            'delta_locker_room': event['delta_locker_room'],
        }

    # Detect context and pick template (LRU anti-repetition guard)
    context = detect_context(conn, team_id, season_year, week_number)
    template = select_template_for_context(conn, context, coach_id)

    # Create press_event row
    with conn:
        cursor = conn.execute("""
            INSERT INTO press_event
            (season_year, week_number, team_id, coach_id, context_type, question_template_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (season_year, week_number, team_id, coach_id, context, template['id'], datetime.now().isoformat()))
        press_event_id = cursor.lastrowid

    # Check for autopilot or headless mode
    coach = conn.execute("""
        SELECT press_autopilot_default FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    autopilot_default = coach['press_autopilot_default'] if coach else None

    if headless:
        # Stress harness: always auto-resolve
        choice = autopilot_default if autopilot_default else PRESS_AUTOPILOT_HARNESS_FALLBACK
        result = resolve_press_event(conn, press_event_id, choice, is_autopilot=True)
        return {
            'press_event_id': press_event_id,
            'context_type': context,
            'question': template['question'],
            'responses': template['responses'],
            'selected_response': choice,
            'resolved': True,
            'delta_owner': result['delta_owner'],
            'delta_fan': result['delta_fan'],
            'delta_locker_room': result['delta_locker_room'],
        }
    elif autopilot_default:
        # Interactive mode but autopilot is set
        result = resolve_press_event(conn, press_event_id, autopilot_default, is_autopilot=True)
        return {
            'press_event_id': press_event_id,
            'context_type': context,
            'question': template['question'],
            'responses': template['responses'],
            'selected_response': autopilot_default,
            'resolved': True,
            'delta_owner': result['delta_owner'],
            'delta_fan': result['delta_fan'],
            'delta_locker_room': result['delta_locker_room'],
        }
    else:
        # Interactive prompt needed
        return {
            'press_event_id': press_event_id,
            'context_type': context,
            'question': template['question'],
            'responses': template['responses'],
            'resolved': False,
        }


def resolve_press_event(
    conn: sqlite3.Connection,
    press_event_id: int,
    response_choice: str,
    is_autopilot: bool = False
) -> dict:
    """
    Resolve a press event by applying effects and updating the database.

    Single mutation point for all press conference effects.

    Args:
        conn: Database connection
        press_event_id: Press event ID
        response_choice: 'deflect' | 'accountable' | 'confrontational'
        is_autopilot: Whether this was auto-resolved

    Returns:
        dict with delta_owner, delta_fan, delta_locker_room, new sentiment values

    Raises:
        ValueError: If response_choice is invalid
    """
    if response_choice not in PRESS_AUTOPILOT_VALID_CHOICES:
        raise ValueError(f"Invalid response choice: {response_choice}")

    # Get event details
    event = conn.execute("""
        SELECT * FROM press_event WHERE id = ?
    """, (press_event_id,)).fetchone()

    if not event:
        raise ValueError(f"Press event {press_event_id} not found")

    # Get effect deltas
    effects = PRESS_EFFECTS[response_choice]
    delta_owner = effects['owner']
    delta_fan = effects['fan']
    delta_locker_room = effects['locker_room']

    # Apply owner sentiment (accumulate presser_delta)
    if delta_owner != 0:
        sentiment = get_owner_sentiment(conn, event['team_id'], event['season_year'])
        if sentiment:
            current_presser_delta = sentiment['presser_delta'] if 'presser_delta' in sentiment.keys() else 0
            new_presser_delta = current_presser_delta + delta_owner
            update_sentiment_drivers(
                conn,
                event['team_id'],
                event['season_year'],
                presser_delta=new_presser_delta
            )

    # Apply fan sentiment (direct update)
    if delta_fan != 0:
        team = conn.execute("""
            SELECT fan_sentiment FROM team WHERE id = ?
        """, (event['team_id'],)).fetchone()

        current_fan = team['fan_sentiment'] if team['fan_sentiment'] is not None else FAN_SENTIMENT_DEFAULT
        new_fan = max(SENTIMENT_MIN, min(SENTIMENT_MAX, current_fan + delta_fan))

        with conn:
            conn.execute("""
                UPDATE team SET fan_sentiment = ? WHERE id = ?
            """, (new_fan, event['team_id']))

    # Apply locker room (top 10 players by true_overall)
    if delta_locker_room != 0:
        top_players = conn.execute("""
            SELECT id FROM player
            WHERE team_id = ? AND position != 'PRAC'
            ORDER BY true_overall DESC
            LIMIT ?
        """, (event['team_id'], PRESS_LOCKER_ROOM_TOP_N_PLAYERS)).fetchall()

        for player_row in top_players:
            adjust_satisfaction(
                player_row['id'],
                delta_locker_room,
                f"Week {event['week_number']} press: {response_choice}",
                conn
            )

    # Update press_event — also copy question_template_id → template_id for LRU guard
    with conn:
        conn.execute("""
            UPDATE press_event
            SET selected_response = ?,
                autopilot_used = ?,
                delta_owner = ?,
                delta_fan = ?,
                delta_locker_room = ?,
                resolved_at = ?,
                template_id = question_template_id
            WHERE id = ?
        """, (response_choice, 1 if is_autopilot else 0, delta_owner, delta_fan,
              delta_locker_room, datetime.now().isoformat(), press_event_id))

    # Get new sentiment values for return
    owner_sentiment_row = conn.execute("""
        SELECT sentiment_score FROM owner_sentiment
        WHERE team_id = ? AND season_year = ?
    """, (event['team_id'], event['season_year'])).fetchone()

    team_row = conn.execute("""
        SELECT fan_sentiment FROM team WHERE id = ?
    """, (event['team_id'],)).fetchone()

    return {
        'delta_owner': delta_owner,
        'delta_fan': delta_fan,
        'delta_locker_room': delta_locker_room,
        'owner_sentiment': owner_sentiment_row['sentiment_score'] if owner_sentiment_row else None,
        'fan_sentiment': team_row['fan_sentiment'] if team_row else None,
    }


def set_autopilot_default(
    conn: sqlite3.Connection,
    coach_id: int,
    choice: Optional[str]
) -> None:
    """
    Set or clear the autopilot default for a coach's press conferences.

    Args:
        conn: Database connection
        coach_id: Coach ID
        choice: 'deflect' | 'accountable' | 'confrontational' | None (to clear)

    Raises:
        ValueError: If choice is not valid
    """
    if choice is not None and choice not in PRESS_AUTOPILOT_VALID_CHOICES:
        raise ValueError(f"Invalid autopilot choice: {choice}")

    with conn:
        conn.execute("""
            UPDATE coach_career
            SET press_autopilot_default = ?
            WHERE id = ?
        """, (choice, coach_id))


def get_unresolved_press_events(conn: sqlite3.Connection, coach_id: int) -> list:
    """
    Get all unresolved press events for a coach.

    Defensive check - shouldn't happen in normal flow.

    Args:
        conn: Database connection
        coach_id: Coach ID

    Returns:
        List of unresolved press event rows
    """
    return conn.execute("""
        SELECT * FROM press_event
        WHERE coach_id = ? AND resolved_at IS NULL
        ORDER BY season_year DESC, week_number DESC
    """, (coach_id,)).fetchall()
