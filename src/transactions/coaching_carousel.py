"""
AI coaching carousel (Phase 4 Prompt #4).

Evaluates all teams (AI + player) for coaching changes at the start of each offseason.
Fires underperforming coaches based on owner sentiment and hires replacements with
archetypes weighted by team phase.

Player coaches enter vacancy state and receive job offers. AI coaches are replaced
immediately.

Preserves Invariant 8 (coach count = 32), Invariant 11 (player coach alignment),
and Invariant 12 (gm_personality sync) by pre-closing fired coach tenure and
routing hires through assign_coach_to_team().
"""

import random
import sqlite3

from ..db.queries import (
    get_all_teams,
    get_coach_tenure_length,
    get_consecutive_losing_seasons,
    get_consecutive_seasons_no_playoffs,
    get_league_state,
    get_team,
    get_team_coach,
    get_owner_sentiment,
    get_coach_by_id,
    create_ai_coach,
)
from ..league.owner_sentiment import get_firing_probability
from ..utils.constants import (
    CAROUSEL_CONSECUTIVE_LOSING_THRESHOLD,
    CAROUSEL_FIRE_PROBABILITY_LOSING,
    CAROUSEL_FIRE_PROBABILITY_NO_PLAYOFFS,
    CAROUSEL_HIRE_WEIGHTS_BY_PHASE,
    CAROUSEL_MIN_TENURE_SEASONS,
    CAROUSEL_NO_PLAYOFFS_CONTENDER_THRESHOLD,
    COACH_MAX_AGE,
    COACH_MIN_AGE,
    GM_PERSONALITIES_TUPLE,
    TEAM_PHASE_DEFAULT,
    MID_SEASON_FIRING_START_WEEK,
    MID_SEASON_FIRING_END_WEEK,
)
from .coaching import assign_coach_to_team


def run_coaching_carousel(
    conn: sqlite3.Connection, season_year: int,
) -> list:
    """Evaluate all AI teams for coaching changes.

    For each non-user team with an active non-player coach:
    1. Check firing triggers (consecutive losing, contender missing playoffs)
    2. If fired, pre-close tenure with 'fired' reason
    3. Hire replacement with archetype weighted by team phase

    Args:
        conn: Database connection.
        season_year: The season that just ended.

    Returns:
        List of dicts with team_id, fired_coach_id, hired_coach_id,
        old_archetype, new_archetype.
    """
    league = get_league_state(conn)
    user_team_id = league['user_team_id'] if league else None

    teams = get_all_teams(conn)
    results = []

    for team in teams:
        tid = team['id']

        # Never touch user's team
        if tid == user_team_id:
            continue

        coach = get_team_coach(conn, tid)
        if not coach:
            continue

        # Check tenure length — never fire before minimum
        tenure_length = get_coach_tenure_length(conn, coach['id'], season_year)
        if tenure_length < CAROUSEL_MIN_TENURE_SEASONS:
            continue

        # --- Firing Trigger: Owner Sentiment ---
        sentiment_row = get_owner_sentiment(conn, tid, season_year)
        if not sentiment_row:
            continue

        hot_seat_tier = sentiment_row['hot_seat_tier']
        fire_prob = get_firing_probability(hot_seat_tier, is_mid_season=False)

        if random.random() >= fire_prob:
            continue

        # --- Fire ---
        old_archetype = coach['personality_archetype']
        fired_coach_id = coach['id']

        firing_result = _handle_coach_firing(conn, fired_coach_id, tid, season_year, end_reason='fired')

        results.append({
            'team_id': tid,
            'fired_coach_id': fired_coach_id,
            'old_archetype': old_archetype,
            'vacancy': firing_result.get('vacancy', False),
            'hired_coach_id': firing_result.get('replacement_id'),
            'new_archetype': firing_result.get('new_archetype'),
        })

    return results


def _select_replacement_archetype(
    conn: sqlite3.Connection, team_id: int,
) -> str:
    """Select a replacement coach archetype weighted by team phase.

    Args:
        conn: Database connection.
        team_id: Team hiring a new coach.

    Returns:
        Personality archetype string.
    """
    team = get_team(conn, team_id)
    if team:
        try:
            phase = team['team_phase'] or TEAM_PHASE_DEFAULT
        except (IndexError, KeyError):
            phase = TEAM_PHASE_DEFAULT
    else:
        phase = TEAM_PHASE_DEFAULT

    weights = CAROUSEL_HIRE_WEIGHTS_BY_PHASE.get(
        phase, CAROUSEL_HIRE_WEIGHTS_BY_PHASE[TEAM_PHASE_DEFAULT],
    )

    archetypes = list(weights.keys())
    probs = [weights[a] for a in archetypes]
    return random.choices(archetypes, weights=probs, k=1)[0]


def _create_new_coach(
    conn: sqlite3.Connection, archetype: str, season_year: int,
) -> int:
    """Create a new AI coach record.

    Args:
        conn: Database connection.
        archetype: Personality archetype for the new coach.
        season_year: Year the coach is being hired.

    Returns:
        New coach_career ID.
    """
    first_names = [
        "Mike", "John", "Bill", "Steve", "Dan", "Tom", "Jim", "Bob",
        "Kevin", "Brian", "Matt", "Sean", "Todd", "Ron", "Pete",
        "Andy", "Doug", "Gary", "Frank", "Joe", "Chris", "Dave",
        "Mark", "Pat", "Jack", "Bruce", "Ray", "Rick", "Eric", "Greg",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Davis",
        "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas",
        "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia",
        "Robinson", "Clark", "Lewis", "Lee", "Walker", "Hall", "Allen",
        "Young", "King", "Wright", "Scott", "Hill", "Baker", "Adams",
    ]

    first = random.choice(first_names)
    last = random.choice(last_names)
    age = random.randint(COACH_MIN_AGE, COACH_MAX_AGE)

    return create_ai_coach(conn, first, last, age, archetype, season_year)


def _handle_coach_firing(
    conn: sqlite3.Connection, coach_id: int, team_id: int,
    season_year: int, end_reason: str = 'fired',
) -> dict:
    """Fire a coach and handle replacement (AI) or vacancy (player).

    Args:
        conn: Database connection.
        coach_id: Coach being fired.
        team_id: Team the coach was on.
        season_year: Season of firing.
        end_reason: Reason code ('fired', 'mutual_parting', etc.)

    Returns:
        Dict with 'vacancy' bool and either 'replacement_id' (AI) or 'offers_generated' (player).
    """
    # Pre-close tenure
    conn.execute(
        "UPDATE coach_tenure SET end_year=?, end_reason=? WHERE coach_id=? AND end_year IS NULL",
        (season_year, end_reason, coach_id)
    )
    conn.execute(
        "UPDATE coach_career SET current_team_id=NULL WHERE id=?",
        (coach_id,)
    )

    # Check if player coach
    coach_row = get_coach_by_id(conn, coach_id)
    if coach_row and coach_row['is_player']:
        # Generate job offers (player enters vacancy)
        from .coach_offers import generate_offers_for_vacant_coach
        generate_offers_for_vacant_coach(conn, coach_id, season_year, week=0)
        return {'vacancy': True, 'offers_generated': True}
    else:
        # Hire AI replacement immediately
        new_archetype = _select_replacement_archetype(conn, team_id)
        new_coach_id = _create_new_coach(conn, new_archetype, season_year)
        assign_coach_to_team(conn, new_coach_id, team_id, season_year)
        return {'vacancy': False, 'replacement_id': new_coach_id, 'new_archetype': new_archetype}


def check_mid_season_firing(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    week_num: int, is_loss: bool,
) -> bool:
    """Check if mid-season firing should occur after a loss.

    Only fires during weeks 6-16, and only if sentiment is hot/termination tier.

    Args:
        conn: Database connection.
        team_id: Team to check.
        season_year: Current season.
        week_num: Week number (1-17).
        is_loss: True if the team just lost.

    Returns:
        True if coach was fired, False otherwise.
    """
    if not is_loss:
        return False
    if week_num < MID_SEASON_FIRING_START_WEEK or week_num > MID_SEASON_FIRING_END_WEEK:
        return False

    sentiment_row = get_owner_sentiment(conn, team_id, season_year)
    if not sentiment_row:
        return False

    hot_seat_tier = sentiment_row['hot_seat_tier']
    fire_prob = get_firing_probability(hot_seat_tier, is_mid_season=True)

    if random.random() < fire_prob:
        coach = get_team_coach(conn, team_id)
        if coach:
            _handle_coach_firing(conn, coach['id'], team_id, season_year, end_reason='fired')
            return True
    return False
