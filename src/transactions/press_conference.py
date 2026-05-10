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
)
from src.utils.press_templates import get_templates_by_context, get_template_by_id
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

    Priority order:
    1. Losing streak (3+ consecutive losses)
    2. Winning streak (3+ consecutive wins)
    3. Blowout win (14+ point margin)
    4. Blowout loss (14+ point margin)
    5. Division loss
    6. Simple post_win
    7. Simple post_loss
    8. Routine (fallback)

    Args:
        conn: Database connection
        team_id: Team ID
        season_year: Season year
        week_number: Week number (1-17)

    Returns:
        Context type string
    """
    # Phase 5 P5: lineup controversy takes highest priority
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
        return 'routine'  # No game this week (shouldn't happen in regular season)

    # Determine if team won and margin
    is_home = game['home_team_id'] == team_id
    team_score = game['home_score'] if is_home else game['away_score']
    opp_score = game['away_score'] if is_home else game['home_score']
    margin = abs(team_score - opp_score)
    won = team_score > opp_score
    opp_division = game['away_division'] if is_home else game['home_division']
    team_division = game['home_division'] if is_home else game['away_division']
    is_division_game = opp_division == team_division

    # Check for streaks (last 3 games including this one)
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

    if len(last_3_games) >= 3:
        results = [g['won'] for g in last_3_games]
        if all(r == 0 for r in results):
            return 'losing_streak'
        if all(r == 1 for r in results):
            return 'winning_streak'

    # Check for blowout
    if margin >= PRESS_BLOWOUT_MARGIN:
        return 'post_blowout_win' if won else 'post_blowout_loss'

    # Check for division loss
    if not won and is_division_game:
        return 'post_division_loss'

    # Simple win/loss
    return 'post_win' if won else 'post_loss'


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

    # Detect context and pick random template
    context = detect_context(conn, team_id, season_year, week_number)
    templates = get_templates_by_context(context)
    template = random.choice(templates)

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

    # Update press_event
    with conn:
        conn.execute("""
            UPDATE press_event
            SET selected_response = ?,
                autopilot_used = ?,
                delta_owner = ?,
                delta_fan = ?,
                delta_locker_room = ?,
                resolved_at = ?
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
