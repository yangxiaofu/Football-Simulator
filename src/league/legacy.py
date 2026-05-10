"""
Legacy score calculation and dynasty tracking.

Updates the legacy_score table after each season to track
the user's franchise performance over time.

Phase 4 Prompt #7 additions:
- Coach-centric legacy scores with era/starting condition multipliers
- Career legacy totals with tenure stability bonus
- Dynasty and HOF trigger detection
"""

import sqlite3
from typing import Optional

from ..db.queries import (
    get_team_season_record,
    count_team_championships,
    count_team_conference_titles,
    get_team_career_totals,
    count_stars_developed,
    count_playoff_appearances,
    count_team_seasons,
    get_recent_season_records,
    count_championships_since,
    upsert_legacy_score,
    insert_coach_legacy_score,
    get_coach_legacy_scores,
    get_all_active_coaches,
    get_team_prior_season_wpct,
)
from ..utils.constants import (
    LEGACY_WEIGHTS,
    DYNASTY_CHAMPIONSHIPS_REQUIRED,
    DYNASTY_WINDOW_YEARS,
    HOF_LEGACY_THRESHOLD,
    HOF_MIN_SEASONS,
    LEGACY_CHAMP_MULTIPLIER,
    LEGACY_WIN_PCT_MULTIPLIER,
    LEGACY_PLAYOFF_MULTIPLIER,
    LEGACY_STARS_MULTIPLIER,
    LEGACY_CAP_MULTIPLIER,
    LEGACY_MEDIA_MULTIPLIER,
    LEGACY_MEDIA_RECENT_WIN_WEIGHT,
    LEGACY_MEDIA_SCORE_CAP,
    LEGACY_RECENT_SEASONS_COUNT,
    LEGACY_STAR_DEVELOPMENT_JUMP,
    STARTING_CONDITION_BUCKETS,
    TENURE_STABILITY_THRESHOLD_YEARS,
    TENURE_STABILITY_PER_YEAR,
    TENURE_STABILITY_CAP,
)
from .era_context import compute_era_difficulty_multiplier


def update_legacy_score(
    conn: sqlite3.Connection,
    season_year: int,
    user_team_id: int,
) -> dict:
    """Compute and insert/update the legacy score for this season.

    Factors:
    - Championships won (cumulative)
    - Conference titles (cumulative)
    - Career win percentage
    - Stars developed (players who jumped from C to A)
    - Cap efficiency (simplified)
    - Playoff appearances

    Returns dict with legacy details.
    """
    # Current season record
    current_record = get_team_season_record(conn, user_team_id, season_year)

    # Count championships
    championships = count_team_championships(conn, user_team_id)

    # Count conference titles (reached Super Bowl = conference champion)
    conf_titles = count_team_conference_titles(conn, user_team_id)

    # Career win percentage
    all_records = get_team_career_totals(conn, user_team_id)

    total_w = all_records['total_wins'] or 0
    total_l = all_records['total_losses'] or 0
    total_t = all_records['total_ties'] or 0
    total_games = total_w + total_l + total_t
    career_win_pct = (total_w + total_t * 0.5) / max(1, total_games)

    # Stars developed: players on user team who have improved significantly
    stars_developed = count_stars_developed(
        conn, user_team_id, LEGACY_STAR_DEVELOPMENT_JUMP,
    )

    # Playoff appearances
    playoff_apps = count_playoff_appearances(conn, user_team_id)

    # Seasons coached
    seasons_coached = count_team_seasons(conn, user_team_id)

    # Cap efficiency (simplified: good record = good efficiency)
    cap_efficiency = int(career_win_pct * 100)

    # Media legacy score (based on recent success)
    recent_wins = 0
    recent_records = get_recent_season_records(
        conn, user_team_id, LEGACY_RECENT_SEASONS_COUNT,
    )
    for r in recent_records:
        recent_wins += r['wins']
    media_score = min(
        LEGACY_MEDIA_SCORE_CAP,
        int(recent_wins * LEGACY_MEDIA_RECENT_WIN_WEIGHT),
    )

    # Compute weighted total
    total_legacy = int(
        championships * LEGACY_CHAMP_MULTIPLIER * LEGACY_WEIGHTS['championships'] +
        career_win_pct * LEGACY_WIN_PCT_MULTIPLIER * LEGACY_WEIGHTS['win_percentage'] +
        playoff_apps * LEGACY_PLAYOFF_MULTIPLIER * LEGACY_WEIGHTS['playoff_appearances'] +
        stars_developed * LEGACY_STARS_MULTIPLIER * LEGACY_WEIGHTS['stars_developed'] +
        cap_efficiency * LEGACY_CAP_MULTIPLIER * LEGACY_WEIGHTS['cap_efficiency'] +
        media_score * LEGACY_MEDIA_MULTIPLIER * LEGACY_WEIGHTS['media_score']
    )

    # Dynasty check
    is_dynasty = 0
    if championships >= DYNASTY_CHAMPIONSHIPS_REQUIRED:
        # Check if 3+ championships within window
        recent_champs = count_championships_since(
            conn, user_team_id, season_year - DYNASTY_WINDOW_YEARS,
        )
        if recent_champs >= DYNASTY_CHAMPIONSHIPS_REQUIRED:
            is_dynasty = 1

    # HOF eligible
    hof_eligible = (
        1 if total_legacy >= HOF_LEGACY_THRESHOLD
        and seasons_coached >= HOF_MIN_SEASONS else 0
    )

    # Upsert legacy record
    upsert_legacy_score(conn, season_year, {
        'championships': championships,
        'conference_titles': conf_titles,
        'career_win_pct': career_win_pct,
        'stars_developed': stars_developed,
        'cap_efficiency': cap_efficiency,
        'seasons_coached': seasons_coached,
        'media_score': media_score,
        'total_legacy': total_legacy,
        'is_dynasty': is_dynasty,
        'hof_eligible': hof_eligible,
    })

    return {
        'championships': championships,
        'conference_titles': conf_titles,
        'career_win_pct': career_win_pct,
        'stars_developed': stars_developed,
        'total_legacy_score': total_legacy,
        'is_dynasty': bool(is_dynasty),
        'seasons_coached': seasons_coached,
    }


# ==============================
# PHASE 4 PROMPT #7: COACH LEGACY EXPANSION
# ==============================

def lookup_starting_condition_multiplier(
    conn: sqlite3.Connection,
    coach_id: int,
    team_id: int,
    hire_season_year: int,
) -> float:
    """Look up team's prior-season W% and return multiplier from buckets.

    If hire_season_year is franchise's first season, return 1.0.
    Reads from coach_tenure.starting_condition_multiplier if already stored.

    Args:
        hire_season_year: Season when coach was hired

    Returns:
        Multiplier from STARTING_CONDITION_BUCKETS
    """
    # Check if already stored on tenure
    row = conn.execute("""
        SELECT starting_condition_multiplier FROM coach_tenure
        WHERE coach_id = ? AND team_id = ? AND start_year = ?
    """, (coach_id, team_id, hire_season_year)).fetchone()

    if row and row['starting_condition_multiplier'] != 1.0:
        return row['starting_condition_multiplier']

    # Look up prior season W%
    wpct = get_team_prior_season_wpct(conn, team_id, hire_season_year)

    if wpct is None:
        # First season of franchise or no record
        return 1.0

    # Map wpct to bucket
    for wpct_threshold, multiplier in STARTING_CONDITION_BUCKETS:
        if wpct < wpct_threshold:
            return multiplier

    # Should not reach here, but fallback to baseline
    return 1.0


def compute_tenure_stability_bonus(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Return +5 per year after Year 5 at current franchise, capped at +25.

    Returns:
        Bonus points (0-25)
    """
    # Get current tenure
    row = conn.execute("""
        SELECT start_year FROM coach_tenure
        WHERE coach_id = ? AND end_year IS NULL
    """, (coach_id,)).fetchone()

    if not row:
        return 0

    years_at_franchise = season_year - row['start_year'] + 1

    if years_at_franchise <= TENURE_STABILITY_THRESHOLD_YEARS:
        return 0

    years_beyond_threshold = years_at_franchise - TENURE_STABILITY_THRESHOLD_YEARS
    bonus = years_beyond_threshold * TENURE_STABILITY_PER_YEAR

    return min(bonus, TENURE_STABILITY_CAP)


def update_coach_legacy_score(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Compute and store one coach's legacy for given season.

    Steps:
    1. Get coach's team from coach_tenure
    2. Compute base 6 factors (same logic as existing update_legacy_score)
    3. Get era_difficulty_multiplier
    4. Get starting_condition_multiplier from tenure
    5. season_legacy_score = (weighted base factors) × era × starting
    6. Write coach_legacy_score row
    7. Return season_legacy_score

    Coaches between jobs get row with zeros.

    Returns:
        season_legacy_score computed
    """
    # Get coach's current team
    coach_row = conn.execute("""
        SELECT current_team_id FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach_row or coach_row['current_team_id'] is None:
        # Coach between jobs - write zeros
        team_id = 0  # Placeholder
        factors = {
            'championships': 0,
            'conference_titles': 0,
            'season_win_pct': 0.0,
            'stars_developed': 0,
            'cap_efficiency_score': 50,
            'media_legacy_score': 50,
        }
        multipliers = {
            'era_difficulty_multiplier': 1.0,
            'starting_condition_multiplier': 1.0,
        }
        season_score = 0
    else:
        team_id = coach_row['current_team_id']

        # Compute base 6 factors (same as update_legacy_score)
        current_record = get_team_season_record(conn, team_id, season_year)

        championships = count_team_championships(conn, team_id)
        conf_titles = count_team_conference_titles(conn, team_id)

        all_records = get_team_career_totals(conn, team_id)
        total_w = all_records['total_wins'] or 0
        total_l = all_records['total_losses'] or 0
        total_t = all_records['total_ties'] or 0
        total_games = total_w + total_l + total_t
        career_win_pct = (total_w + total_t * 0.5) / max(1, total_games)

        # Season win pct
        if current_record:
            season_w = current_record['wins']
            season_l = current_record['losses']
            season_t = current_record['ties']
            season_games = season_w + season_l + season_t
            season_win_pct = (season_w + season_t * 0.5) / max(1, season_games)
        else:
            season_win_pct = 0.0

        stars_developed = count_stars_developed(
            conn, team_id, LEGACY_STAR_DEVELOPMENT_JUMP,
        )

        playoff_apps = count_playoff_appearances(conn, team_id)

        cap_efficiency = int(career_win_pct * 100)

        recent_wins = 0
        recent_records = get_recent_season_records(
            conn, team_id, LEGACY_RECENT_SEASONS_COUNT,
        )
        for r in recent_records:
            recent_wins += r['wins']
        media_score = min(
            LEGACY_MEDIA_SCORE_CAP,
            int(recent_wins * LEGACY_MEDIA_RECENT_WIN_WEIGHT),
        )

        factors = {
            'championships': championships,
            'conference_titles': conf_titles,
            'season_win_pct': season_win_pct,
            'stars_developed': stars_developed,
            'cap_efficiency_score': cap_efficiency,
            'media_legacy_score': media_score,
        }

        # Get multipliers
        era_mult = compute_era_difficulty_multiplier(conn, season_year)

        # Get starting condition multiplier from tenure
        tenure_row = conn.execute("""
            SELECT starting_condition_multiplier, start_year
            FROM coach_tenure
            WHERE coach_id = ? AND end_year IS NULL
        """, (coach_id,)).fetchone()

        if tenure_row:
            starting_mult = tenure_row['starting_condition_multiplier']
        else:
            starting_mult = 1.0

        multipliers = {
            'era_difficulty_multiplier': era_mult,
            'starting_condition_multiplier': starting_mult,
        }

        # Compute season legacy score (same weighted sum as update_legacy_score)
        base_score = int(
            championships * LEGACY_CHAMP_MULTIPLIER * LEGACY_WEIGHTS['championships'] +
            career_win_pct * LEGACY_WIN_PCT_MULTIPLIER * LEGACY_WEIGHTS['win_percentage'] +
            playoff_apps * LEGACY_PLAYOFF_MULTIPLIER * LEGACY_WEIGHTS['playoff_appearances'] +
            stars_developed * LEGACY_STARS_MULTIPLIER * LEGACY_WEIGHTS['stars_developed'] +
            cap_efficiency * LEGACY_CAP_MULTIPLIER * LEGACY_WEIGHTS['cap_efficiency'] +
            media_score * LEGACY_MEDIA_MULTIPLIER * LEGACY_WEIGHTS['media_score']
        )

        # Apply multipliers
        season_score = int(base_score * era_mult * starting_mult)

    # Write coach_legacy_score row
    insert_coach_legacy_score(
        conn, coach_id, season_year, team_id, factors, multipliers, season_score,
    )

    return season_score


def update_all_coach_legacy_scores(
    conn: sqlite3.Connection,
    season_year: int,
) -> dict:
    """Run update_coach_legacy_score for every active coach.

    Returns:
        Dict mapping coach_id → season_legacy_score
    """
    coaches = get_all_active_coaches(conn)
    results = {}

    for coach in coaches:
        score = update_coach_legacy_score(conn, coach['id'], season_year)
        results[coach['id']] = score

    return results


def compute_career_legacy_total(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Sum of all season_legacy_score + tenure_stability_bonus.

    Returns:
        Total career legacy points
    """
    # Sum all season scores
    rows = get_coach_legacy_scores(conn, coach_id)
    season_total = sum(row['season_legacy_score'] for row in rows)

    # Add tenure stability bonus
    stability_bonus = compute_tenure_stability_bonus(conn, coach_id, season_year)

    return season_total + stability_bonus


def evaluate_dynasty_and_hof(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> list:
    """Check if dynasty (3 in 10 years) or HOF threshold crossed for FIRST time.

    Returns:
        List of newly activated trigger names:
        - 'dynasty_flag_activated'
        - 'hof_eligible_first_time'
    """
    triggers = []

    # Get coach's team
    coach_row = conn.execute("""
        SELECT current_team_id FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach_row or coach_row['current_team_id'] is None:
        return triggers

    team_id = coach_row['current_team_id']

    # Dynasty check (3+ championships in 10-year window)
    championships = count_team_championships(conn, team_id)
    if championships >= DYNASTY_CHAMPIONSHIPS_REQUIRED:
        recent_champs = count_championships_since(
            conn, team_id, season_year - DYNASTY_WINDOW_YEARS,
        )
        if recent_champs >= DYNASTY_CHAMPIONSHIPS_REQUIRED:
            # Check if this is FIRST time
            # Look for existing legacy_score with is_dynasty=1
            prior_dynasty = conn.execute("""
                SELECT 1 FROM legacy_score
                WHERE coach_id = ? AND is_dynasty = 1 AND season_year < ?
                LIMIT 1
            """, (coach_id, season_year)).fetchone()

            if not prior_dynasty:
                triggers.append('dynasty_flag_activated')

    # HOF eligible check
    career_total = compute_career_legacy_total(conn, coach_id, season_year)
    seasons_coached = count_team_seasons(conn, team_id)

    if career_total >= HOF_LEGACY_THRESHOLD and seasons_coached >= HOF_MIN_SEASONS:
        # Check if this is FIRST time
        prior_hof = conn.execute("""
            SELECT 1 FROM legacy_score
            WHERE coach_id = ? AND hof_eligible = 1 AND season_year < ?
            LIMIT 1
        """, (coach_id, season_year)).fetchone()

        if not prior_hof:
            triggers.append('hof_eligible_first_time')

    return triggers
