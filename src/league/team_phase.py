"""
Team phase classifier and transition logic (Phase 4 Prompt #3).

Classifies each team into one of five phases based on roster quality,
cap health, recent performance, and GM personality. The phase drives
AI behavior through the behavior matrix.

Phases: rebuild, bridge, contend, win_now, decline
"""

import random
import sqlite3

from ..db.queries import (
    get_all_teams,
    get_consecutive_losing_seasons,
    get_recent_win_pct,
    get_roster_average_age,
    get_star_count,
    get_team,
    update_team_phase,
)
from ..utils.constants import (
    PHASE_CAP_HEALTHY_THRESHOLD,
    PHASE_CAP_STRESSED_THRESHOLD,
    PHASE_CONSECUTIVE_LOSING_DECLINE,
    PHASE_LOOKBACK_SEASONS,
    PHASE_MIN_STARS_BRIDGE,
    PHASE_MIN_STARS_CONTEND,
    PHASE_ROSTER_OLD_AGE_MIN,
    PHASE_WIN_NOW_AGE_MIN,
    PHASE_STAR_THRESHOLD,
    PHASE_STRONG_RECORD_PCT,
    PHASE_TRANSITION_SPEED,
    PHASE_WINNING_RECORD_PCT,
    TEAM_PHASE_DEFAULT,
)


def compute_team_phase(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> str:
    """Classify a team into a strategic phase.

    Decision tree (evaluated in order):
    1. Decline: cap stressed AND old roster AND losing; OR 2+ consecutive losing + old
    2. Rebuild: <2 stars OR (cap stressed AND personality willing) OR (young + few stars)
    3. Win-Now: 3+ stars AND W% >= .588 AND healthy cap AND avg_age >= 26.5 AND willing
    4. Contend: 3+ stars AND W% >= .500 AND cap not stressed
    5. Bridge: default fallback

    Personality transition speed modulates willingness to enter rebuild/win_now.

    Args:
        conn: Database connection.
        team_id: Team to classify.
        season_year: Current season year.

    Returns:
        Phase string: 'rebuild', 'bridge', 'contend', 'win_now', or 'decline'.
    """
    team = get_team(conn, team_id)
    if not team:
        return TEAM_PHASE_DEFAULT

    cap_space = team['cap_space']
    personality = team['gm_personality']

    avg_age = get_roster_average_age(conn, team_id)
    stars = get_star_count(conn, team_id, PHASE_STAR_THRESHOLD)
    win_pct = get_recent_win_pct(conn, team_id, PHASE_LOOKBACK_SEASONS)
    consec_losing = get_consecutive_losing_seasons(conn, team_id)

    cap_stressed = cap_space < PHASE_CAP_STRESSED_THRESHOLD
    cap_healthy = cap_space >= PHASE_CAP_HEALTHY_THRESHOLD
    roster_old = avg_age >= PHASE_ROSTER_OLD_AGE_MIN

    # Get personality transition speed
    speed = PHASE_TRANSITION_SPEED.get(personality, {'to_rebuild': 0.5, 'to_win_now': 0.5})

    # --- 1. Decline ---
    # Cap stressed AND old AND losing
    if cap_stressed and roster_old and win_pct < PHASE_WINNING_RECORD_PCT:
        return 'decline'
    # 2+ consecutive losing seasons with old roster
    if consec_losing >= PHASE_CONSECUTIVE_LOSING_DECLINE and roster_old:
        return 'decline'

    # --- 2. Rebuild ---
    # Very few stars = rebuild (modulated by personality willingness)
    if stars < PHASE_MIN_STARS_BRIDGE:
        if random.random() < speed['to_rebuild']:
            return 'rebuild'
        return 'bridge'
    # Cap stressed and personality willing to rebuild
    if cap_stressed and stars < PHASE_MIN_STARS_CONTEND:
        if random.random() < speed['to_rebuild']:
            return 'rebuild'
        return 'bridge'

    # --- 3. Win-Now ---
    if (stars >= PHASE_MIN_STARS_CONTEND
            and win_pct >= PHASE_STRONG_RECORD_PCT
            and cap_healthy
            and avg_age >= PHASE_WIN_NOW_AGE_MIN):
        if random.random() < speed['to_win_now']:
            return 'win_now'
        return 'contend'

    # --- 4. Contend ---
    if (stars >= PHASE_MIN_STARS_CONTEND
            and win_pct >= PHASE_WINNING_RECORD_PCT
            and not cap_stressed):
        return 'contend'

    # --- 5. Bridge (default) ---
    return TEAM_PHASE_DEFAULT


def update_all_team_phases(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Classify all 32 teams and write team.team_phase.

    Args:
        conn: Database connection.
        season_year: Current season year.

    Returns:
        Dict mapping team_id -> phase string.
    """
    teams = get_all_teams(conn)
    results = {}
    for team in teams:
        phase = compute_team_phase(conn, team['id'], season_year)
        update_team_phase(conn, team['id'], phase)
        results[team['id']] = phase
    return results


def transitions_summary(before: dict, after: dict) -> str:
    """Format phase changes between two snapshots for reporting.

    Args:
        before: Dict of team_id -> old phase.
        after: Dict of team_id -> new phase.

    Returns:
        Multi-line string describing changes, or "No phase changes." if none.
    """
    changes = []
    for tid in sorted(after.keys()):
        old = before.get(tid, TEAM_PHASE_DEFAULT)
        new = after[tid]
        if old != new:
            changes.append(f"  Team {tid}: {old} -> {new}")
    if not changes:
        return "No phase changes."
    return "Phase transitions:\n" + "\n".join(changes)
