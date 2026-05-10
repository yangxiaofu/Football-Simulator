"""
Tier 2 dramatic press conference system (Phase 4 Prompt #6).

Event-triggered, 2-3 questions, 3-5x effect magnitude vs Tier 1.
Cannot be autopilot-skipped. ~3-5 per season.

Uses same effect application pattern as Tier 1 (press_conference.py):
- Owner: presser_delta accumulator on owner_sentiment
- Fan: direct UPDATE to team.fan_sentiment with clamp
- Locker room: adjust_satisfaction for top N players
"""

import sqlite3
import random
from datetime import datetime
from typing import Optional

from ..utils.constants import (
    TIER2_EFFECTS,
    TIER2_HEADLESS_FALLBACK,
    TIER2_VALID_CHOICES,
    SENTIMENT_MIN,
    SENTIMENT_MAX,
    PRESS_LOCKER_ROOM_TOP_N_PLAYERS,
)
from ..utils.tier2_templates import (
    get_tier2_templates_by_trigger,
    get_tier2_template_by_id,
    format_tier2_question,
)
from .tier2_triggers import detect_tier2_trigger, insert_trigger_guard
from ..db.queries import update_sentiment_drivers, get_owner_sentiment
from ..transactions.satisfaction import adjust_satisfaction


def generate_tier2_press_event(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    team_id: int,
    coach_id: int,
    headless: bool = False,
) -> Optional[dict]:
    """
    Try to generate a Tier 2 dramatic press event.

    Returns None if no trigger fires. Otherwise:
    1. Detects trigger
    2. Picks random template for the trigger
    3. Inserts tier2_press_event row
    4. Inserts tier2_press_response rows (one per question, unresolved)
    5. Inserts trigger guard
    6. If headless: auto-resolves all questions with TIER2_HEADLESS_FALLBACK
    7. Returns event dict with questions for interactive display

    Args:
        conn: Database connection
        season_year: Current season year
        week_number: Current week number
        team_id: Team ID
        coach_id: Coach ID
        headless: If True, auto-resolve all questions (stress harness mode)

    Returns:
        Event dict with questions, or None if no trigger fires
    """
    # Check if a Tier 2 event already exists for this week/team
    existing = conn.execute("""
        SELECT id, resolved_at FROM tier2_press_event
        WHERE season_year = ? AND week_number = ? AND team_id = ?
    """, (season_year, week_number, team_id)).fetchone()

    if existing:
        # Return existing event
        return _load_existing_event(conn, existing['id'])

    # Run trigger detection
    trigger_type, context = detect_tier2_trigger(conn, team_id, season_year, week_number)

    if trigger_type is None:
        return None

    # Pick random template for this trigger
    templates = get_tier2_templates_by_trigger(trigger_type)
    if not templates:
        return None

    template = random.choice(templates)
    num_questions = len(template['questions'])

    # Insert event
    with conn:
        cursor = conn.execute("""
            INSERT INTO tier2_press_event
            (season_year, week_number, team_id, coach_id, trigger_type, template_id, num_questions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (season_year, week_number, team_id, coach_id, trigger_type,
              template['id'], num_questions, datetime.now().isoformat()))
        event_id = cursor.lastrowid

        # Insert response rows (one per question)
        response_ids = []
        for idx, q in enumerate(template['questions']):
            formatted_question = format_tier2_question(q['question'], context)
            cur = conn.execute("""
                INSERT INTO tier2_press_response
                (event_id, question_index, question_text)
                VALUES (?, ?, ?)
            """, (event_id, idx, formatted_question))
            response_ids.append(cur.lastrowid)

        # Insert trigger guard
        guard_key = context.get('guard_key', f"{trigger_type}_{week_number}")
        insert_trigger_guard(conn, team_id, season_year, trigger_type, guard_key, week_number)

    # Build return dict
    questions = []
    for idx, q in enumerate(template['questions']):
        formatted_question = format_tier2_question(q['question'], context)
        questions.append({
            'response_id': response_ids[idx],
            'question_index': idx,
            'question': formatted_question,
            'responses': q['responses'],
        })

    result = {
        'event_id': event_id,
        'trigger_type': trigger_type,
        'template_id': template['id'],
        'num_questions': num_questions,
        'questions': questions,
        'resolved': False,
        'context': context,
    }

    # If headless, auto-resolve all questions
    if headless:
        for q in questions:
            resolve_tier2_question(conn, q['response_id'], TIER2_HEADLESS_FALLBACK)
        # Mark event resolved
        with conn:
            conn.execute("""
                UPDATE tier2_press_event SET resolved_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), event_id))
        result['resolved'] = True

    return result


def resolve_tier2_question(
    conn: sqlite3.Connection,
    response_id: int,
    response_choice: str,
) -> dict:
    """
    Resolve one Tier 2 question. Apply effects.

    Owner: accumulate presser_delta via update_sentiment_drivers()
    Fan: direct UPDATE team.fan_sentiment with clamp [SENTIMENT_MIN, SENTIMENT_MAX]
    Locker room: adjust_satisfaction for top N players

    If this is the last question in the event, marks event as resolved.

    Args:
        conn: Database connection
        response_id: tier2_press_response.id
        response_choice: 'deflect' | 'accountable' | 'confrontational'

    Returns:
        dict with delta_owner, delta_fan, delta_locker_room

    Raises:
        ValueError: If response_choice is invalid or response not found
    """
    if response_choice not in TIER2_VALID_CHOICES:
        raise ValueError(f"Invalid response choice: {response_choice}")

    # Get response row
    response = conn.execute("""
        SELECT r.*, e.team_id, e.season_year, e.week_number, e.id as event_id, e.num_questions
        FROM tier2_press_response r
        JOIN tier2_press_event e ON r.event_id = e.id
        WHERE r.id = ?
    """, (response_id,)).fetchone()

    if not response:
        raise ValueError(f"Tier 2 response {response_id} not found")

    # Get effect deltas
    effects = TIER2_EFFECTS[response_choice]
    delta_owner = effects['owner']
    delta_fan = effects['fan']
    delta_locker_room = effects['locker_room']

    team_id = response['team_id']
    season_year = response['season_year']

    # Apply owner sentiment (accumulate presser_delta)
    if delta_owner != 0:
        sentiment = get_owner_sentiment(conn, team_id, season_year)
        if sentiment:
            current_presser_delta = sentiment['presser_delta'] if 'presser_delta' in sentiment.keys() else 0
            new_presser_delta = current_presser_delta + delta_owner
            update_sentiment_drivers(
                conn,
                team_id,
                season_year,
                presser_delta=new_presser_delta
            )

    # Apply fan sentiment (direct update)
    if delta_fan != 0:
        team = conn.execute("""
            SELECT fan_sentiment FROM team WHERE id = ?
        """, (team_id,)).fetchone()

        current_fan = team['fan_sentiment'] if team and team['fan_sentiment'] is not None else 50
        new_fan = max(SENTIMENT_MIN, min(SENTIMENT_MAX, current_fan + delta_fan))

        with conn:
            conn.execute("""
                UPDATE team SET fan_sentiment = ? WHERE id = ?
            """, (new_fan, team_id))

    # Apply locker room (top N players by true_overall)
    if delta_locker_room != 0:
        top_players = conn.execute("""
            SELECT id FROM player
            WHERE team_id = ? AND position != 'PRAC'
            ORDER BY true_overall DESC
            LIMIT ?
        """, (team_id, PRESS_LOCKER_ROOM_TOP_N_PLAYERS)).fetchall()

        for player_row in top_players:
            adjust_satisfaction(
                player_row['id'],
                delta_locker_room,
                f"Tier 2 press: {response_choice}",
                conn
            )

    # Mark response resolved
    with conn:
        conn.execute("""
            UPDATE tier2_press_response
            SET selected_response = ?,
                delta_owner = ?,
                delta_fan = ?,
                delta_locker_room = ?,
                resolved_at = ?
            WHERE id = ?
        """, (response_choice, delta_owner, delta_fan, delta_locker_room,
              datetime.now().isoformat(), response_id))

    # Check if all questions in this event are now resolved
    event_id = response['event_id']
    unresolved_count = conn.execute("""
        SELECT COUNT(*) as cnt FROM tier2_press_response
        WHERE event_id = ? AND resolved_at IS NULL
    """, (event_id,)).fetchone()['cnt']

    if unresolved_count == 0:
        with conn:
            conn.execute("""
                UPDATE tier2_press_event SET resolved_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), event_id))

    return {
        'delta_owner': delta_owner,
        'delta_fan': delta_fan,
        'delta_locker_room': delta_locker_room,
    }


def _load_existing_event(conn: sqlite3.Connection, event_id: int) -> dict:
    """Load an existing Tier 2 event and its responses."""
    event = conn.execute("""
        SELECT * FROM tier2_press_event WHERE id = ?
    """, (event_id,)).fetchone()

    responses = conn.execute("""
        SELECT * FROM tier2_press_response
        WHERE event_id = ?
        ORDER BY question_index
    """, (event_id,)).fetchall()

    # Load template to get response options
    template = get_tier2_template_by_id(event['template_id'])

    questions = []
    for resp in responses:
        q_idx = resp['question_index']
        q_responses = {}
        if template and q_idx < len(template['questions']):
            q_responses = template['questions'][q_idx]['responses']

        questions.append({
            'response_id': resp['id'],
            'question_index': q_idx,
            'question': resp['question_text'],
            'responses': q_responses,
            'selected_response': resp['selected_response'],
            'resolved': resp['resolved_at'] is not None,
        })

    return {
        'event_id': event_id,
        'trigger_type': event['trigger_type'],
        'template_id': event['template_id'],
        'num_questions': event['num_questions'],
        'questions': questions,
        'resolved': event['resolved_at'] is not None,
        'context': {},
    }
