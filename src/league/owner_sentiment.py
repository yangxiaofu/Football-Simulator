"""
Owner sentiment tracking and hot seat classification.

Drives coach firing decisions via a multi-factor sentiment score (0-100).
"""

import sqlite3
from typing import Optional

from ..db.queries import (
    get_owner_sentiment,
    insert_owner_sentiment,
    update_sentiment_drivers,
    update_sentiment_score_and_tier,
    get_star_holdouts_count,
    get_team_basic_info,
    get_recent_win_pct,
)
from ..db.connection import execute_one
from ..utils.constants import (
    SENTIMENT_DEFAULT,
    SENTIMENT_MIN,
    SENTIMENT_MAX,
    EXPECTATION_TIERS,
    EXPECTATION_WIN_TARGETS,
    SENTIMENT_WEIGHT_PER_WIN_ABOVE,
    SENTIMENT_WEIGHT_PER_WIN_BELOW,
    SENTIMENT_CAP_HEALTHY_THRESHOLD,
    SENTIMENT_CAP_HEALTHY_BONUS,
    SENTIMENT_CAP_OVER_PENALTY,
    SENTIMENT_STAR_HOLDOUT_PENALTY,
    SENTIMENT_PLAYOFF_BONUS,
    SENTIMENT_CHAMPIONSHIP_BONUS,
    HOT_SEAT_TIERS,
    FIRING_PROB_MID_SEASON,
    FIRING_PROB_END_SEASON,
)


def initialize_sentiment(conn: sqlite3.Connection, team_id: int, season_year: int) -> None:
    """Create default sentiment record at season start."""
    existing = get_owner_sentiment(conn, team_id, season_year)
    if existing:
        return  # Already initialized
    insert_owner_sentiment(conn, team_id, season_year, sentiment_score=SENTIMENT_DEFAULT)


def set_preseason_expectation(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> None:
    """Set expectation tier based on team phase and prior season performance.

    Expectation tiers:
    - rebuild: 4 wins
    - competitive: 8 wins
    - playoff: 10 wins
    - championship: 12 wins
    """
    # Get team phase
    team_row = execute_one(
        conn, "SELECT team_phase FROM team WHERE id = ?", (team_id,)
    )
    if not team_row:
        return

    phase = team_row['team_phase']

    # Get prior season record
    prior_record = execute_one(
        conn,
        "SELECT wins, made_playoffs FROM team_season_record WHERE team_id = ? ORDER BY season_year DESC LIMIT 1",
        (team_id,),
    )

    # Map phase to expectation tier
    if phase == 'rebuild':
        expectation = 'rebuild'
    elif phase == 'bridge':
        expectation = 'competitive'
    elif phase == 'contend':
        expectation = 'playoff'
    elif phase == 'win_now':
        expectation = 'championship'
    elif phase == 'decline':
        expectation = 'competitive'
    else:
        expectation = 'competitive'

    # Boost expectation if prior season was strong
    if prior_record and prior_record['made_playoffs']:
        if expectation == 'rebuild':
            expectation = 'competitive'
        elif expectation == 'competitive':
            expectation = 'playoff'
        elif expectation == 'playoff':
            expectation = 'championship'

    # Write expectation to DB
    conn.execute("""
        UPDATE owner_sentiment
        SET preseason_expectation = ?
        WHERE team_id = ? AND season_year = ?
    """, (expectation, team_id, season_year))


def update_wins_delta_after_game(
    conn: sqlite3.Connection, team_id: int, season_year: int, won: bool,
) -> None:
    """Lightweight post-game update: recalc wins vs expectation."""
    sentiment_row = get_owner_sentiment(conn, team_id, season_year)
    if not sentiment_row:
        return

    # Get current season record
    record_row = execute_one(
        conn,
        "SELECT wins, losses FROM team_season_record WHERE team_id = ? AND season_year = ?",
        (team_id, season_year),
    )
    if not record_row:
        return

    wins = record_row['wins']
    expectation_tier = sentiment_row['preseason_expectation']

    if not expectation_tier or expectation_tier not in EXPECTATION_WIN_TARGETS:
        return

    target_wins = EXPECTATION_WIN_TARGETS[expectation_tier]
    delta = wins - target_wins

    if delta > 0:
        wins_score = delta * SENTIMENT_WEIGHT_PER_WIN_ABOVE
    else:
        wins_score = delta * abs(SENTIMENT_WEIGHT_PER_WIN_BELOW)

    update_sentiment_drivers(
        conn, team_id, season_year,
        wins_vs_expectation=wins_score,
    )


def update_weekly_drivers(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> None:
    """Recalc cap management and holdout penalty drivers."""
    # Cap management score
    team_info = get_team_basic_info(conn, team_id)
    if not team_info:
        return

    cap_space = team_info['cap_space']
    if cap_space >= SENTIMENT_CAP_HEALTHY_THRESHOLD:
        cap_score = SENTIMENT_CAP_HEALTHY_BONUS
    elif cap_space < 0:
        cap_score = SENTIMENT_CAP_OVER_PENALTY
    else:
        cap_score = 0

    # Star holdout penalty
    holdout_count = get_star_holdouts_count(conn, team_id)
    holdout_penalty = holdout_count * SENTIMENT_STAR_HOLDOUT_PENALTY

    update_sentiment_drivers(
        conn, team_id, season_year,
        cap_management_score=cap_score,
        star_holdout_penalty=holdout_penalty,
    )


def finalize_season_sentiment(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> None:
    """Sum all drivers, apply playoff/championship bonuses, classify hot seat tier."""
    sentiment_row = get_owner_sentiment(conn, team_id, season_year)
    if not sentiment_row:
        return

    # Get playoff/championship status
    record_row = execute_one(
        conn,
        "SELECT made_playoffs, playoff_result FROM team_season_record WHERE team_id = ? AND season_year = ?",
        (team_id, season_year),
    )

    playoff_bonus = 0
    championship_bonus = 0

    if record_row:
        if record_row['made_playoffs']:
            playoff_bonus = SENTIMENT_PLAYOFF_BONUS
        if record_row['playoff_result'] == 'champion':
            championship_bonus = SENTIMENT_CHAMPIONSHIP_BONUS

    # Sum all drivers
    total = SENTIMENT_DEFAULT
    total += sentiment_row['wins_vs_expectation']
    total += sentiment_row['cap_management_score']
    total += sentiment_row['star_holdout_penalty']
    total += playoff_bonus
    total += championship_bonus

    # Clamp to valid range
    total = max(SENTIMENT_MIN, min(SENTIMENT_MAX, total))

    # Classify hot seat tier
    tier = classify_hot_seat_tier(total)

    # Write to DB
    update_sentiment_drivers(
        conn, team_id, season_year,
        playoff_bonus=playoff_bonus,
        championship_bonus=championship_bonus,
    )
    update_sentiment_score_and_tier(conn, team_id, season_year, total, tier)


def classify_hot_seat_tier(sentiment: int) -> str:
    """Map sentiment score to hot seat tier name.

    Tiers (inclusive):
    - untouchable: 70-100
    - stable: 40-69
    - warm: 20-39
    - hot: 10-19
    - termination: 0-9
    """
    for tier_name, (low, high) in HOT_SEAT_TIERS.items():
        if low <= sentiment <= high:
            return tier_name
    return 'stable'  # fallback


def get_firing_probability(hot_seat_tier: str, is_mid_season: bool) -> float:
    """Lookup firing probability from constants.

    Args:
        hot_seat_tier: 'untouchable'|'stable'|'warm'|'hot'|'termination'
        is_mid_season: True if mid-season (week 6-16), False if end-of-season

    Returns:
        Probability (0.0-1.0) of firing occurring
    """
    if is_mid_season:
        return FIRING_PROB_MID_SEASON.get(hot_seat_tier, 0.0)
    else:
        return FIRING_PROB_END_SEASON.get(hot_seat_tier, 0.0)
