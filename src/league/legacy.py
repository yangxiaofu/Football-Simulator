"""
Legacy score calculation and dynasty tracking.

Updates the legacy_score table after each season to track
the user's franchise performance over time.
"""

import sqlite3

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
)


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
