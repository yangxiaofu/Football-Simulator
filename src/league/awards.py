"""
End-of-season award calculations.

MVP, OPOY, DPOY, OROY, DROY, Pro Bowl, All-Pro selections.
All stat queries go through src/db/queries.
"""

import sqlite3

from ..db.queries import (
    set_player_season_award,
    get_team_season_record,
    get_award_candidates,
    get_position_season_stats,
)
from ..utils.constants import (
    PRO_BOWL_SELECTIONS,
    ALL_PRO_SELECTIONS,
    MVP_MIN_GAMES_PLAYED,
    OPOY_MIN_GAMES_PLAYED,
    DPOY_MIN_GAMES_PLAYED,
    QB_AWARD_MIN_ATTEMPTS,
    RB_AWARD_MIN_CARRIES,
    WR_AWARD_MIN_TARGETS,
    MVP_STAT_WEIGHT,
    MVP_TEAM_SUCCESS_WEIGHT,
    QB_MVP_BIAS_MULTIPLIER,
    OFFENSE_POSITIONS,
    DEFENSE_POSITIONS,
    AWARD_PASS_YARDS_WEIGHT,
    AWARD_PASS_TDS_WEIGHT,
    AWARD_INTERCEPTIONS_PENALTY,
    AWARD_PASSER_RATING_WEIGHT,
    AWARD_RUSH_YARDS_WEIGHT,
    AWARD_RUSH_TDS_WEIGHT,
    AWARD_REC_YARDS_WEIGHT,
    AWARD_REC_TDS_WEIGHT,
    AWARD_RECEPTIONS_WEIGHT,
    AWARD_FG_MADE_WEIGHT,
    AWARD_FUMBLE_PENALTY,
    AWARD_TACKLES_WEIGHT,
    AWARD_SACKS_WEIGHT,
    AWARD_DEF_INT_WEIGHT,
    AWARD_PASS_DEFLECTIONS_WEIGHT,
)


def assign_awards(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Run all award calculations for a season.

    Returns dict with award winners.
    """
    results = {}

    # Pro Bowl
    pro_bowl = select_pro_bowl_players(conn, season_year)
    results['pro_bowl_count'] = len(pro_bowl)

    # All-Pro
    all_pro = select_all_pro_players(conn, season_year)
    results['all_pro_count'] = len(all_pro)

    # MVP
    mvp_id = calculate_mvp(conn, season_year)
    if mvp_id:
        set_player_season_award(conn, mvp_id, season_year, 'won_mvp')
        results['mvp'] = mvp_id

    # OPOY
    opoy_id = calculate_offensive_poy(conn, season_year)
    results['opoy'] = opoy_id

    # DPOY
    dpoy_id = calculate_defensive_poy(conn, season_year)
    results['dpoy'] = dpoy_id

    # OROY
    oroy_id = calculate_rookie_of_year(conn, season_year, 'offense')
    results['oroy'] = oroy_id

    # DROY
    droy_id = calculate_rookie_of_year(conn, season_year, 'defense')
    results['droy'] = droy_id

    return results


def calculate_mvp(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Calculate MVP. Weighted combination of stats + team success.

    Returns player_id of MVP.
    """
    candidates = get_award_candidates(conn, season_year, MVP_MIN_GAMES_PLAYED)

    if not candidates:
        return None

    best_score = -1
    best_id = None

    for c in candidates:
        stat_score = _compute_offensive_score(c)

        # Team success bonus
        record = get_team_season_record(conn, c['team_id'], season_year)
        if record:
            total_games = record['wins'] + record['losses'] + record['ties']
            win_pct = (record['wins'] + record['ties'] * 0.5) / max(1, total_games)
        else:
            win_pct = 0.5

        total_score = (
            stat_score * MVP_STAT_WEIGHT +
            win_pct * 100 * MVP_TEAM_SUCCESS_WEIGHT
        )

        # QB bias (QBs win MVP ~80% of the time in the NFL)
        if c['position'] == 'QB':
            total_score *= QB_MVP_BIAS_MULTIPLIER

        if total_score > best_score:
            best_score = total_score
            best_id = c['player_id']

    return best_id


def calculate_offensive_poy(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Calculate Offensive Player of the Year.

    Returns player_id.
    """
    candidates = get_award_candidates(
        conn, season_year, OPOY_MIN_GAMES_PLAYED,
        positions=['QB', 'RB', 'WR', 'TE'],
    )

    if not candidates:
        return None

    best_score = -1
    best_id = None

    for c in candidates:
        score = _compute_offensive_score(c)
        if score > best_score:
            best_score = score
            best_id = c['player_id']

    return best_id


def calculate_defensive_poy(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Calculate Defensive Player of the Year.

    Returns player_id.
    """
    candidates = get_award_candidates(
        conn, season_year, DPOY_MIN_GAMES_PLAYED,
        positions=['DL', 'LB', 'CB', 'S'],
    )

    if not candidates:
        return None

    best_score = -1
    best_id = None

    for c in candidates:
        score = _compute_defensive_score(c)
        if score > best_score:
            best_score = score
            best_id = c['player_id']

    return best_id


def calculate_rookie_of_year(
    conn: sqlite3.Connection,
    season_year: int,
    unit: str = 'offense',
) -> int:
    """Calculate Offensive/Defensive Rookie of the Year.

    Args:
        unit: 'offense' or 'defense'

    Returns player_id.
    """
    if unit == 'offense':
        pos_list = ['QB', 'RB', 'WR', 'TE', 'OL']
    else:
        pos_list = ['DL', 'LB', 'CB', 'S']

    candidates = get_award_candidates(
        conn, season_year, 0,
        positions=pos_list, max_experience=1,
    )

    if not candidates:
        return None

    best_score = -1
    best_id = None

    for c in candidates:
        if unit == 'offense':
            score = _compute_offensive_score(c)
        else:
            score = _compute_defensive_score(c)

        if score > best_score:
            best_score = score
            best_id = c['player_id']

    return best_id


def select_pro_bowl_players(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """Select Pro Bowl players (top N per position).

    Returns list of player_ids selected.
    """
    selected = []

    for position, count in PRO_BOWL_SELECTIONS.items():
        candidates = get_position_season_stats(conn, season_year, position)

        if position in OFFENSE_POSITIONS or position in ('K', 'P'):
            scored = []
            for c in candidates:
                score = _compute_offensive_score(c)
                scored.append((score, c['player_id']))
        else:
            scored = []
            for c in candidates:
                score = _compute_defensive_score(c)
                scored.append((score, c['player_id']))

        scored.sort(reverse=True)
        for _, pid in scored[:count]:
            set_player_season_award(conn, pid, season_year, 'made_pro_bowl')
            selected.append(pid)

    return selected


def select_all_pro_players(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """Select All-Pro First Team (top 1-2 per position).

    Returns list of player_ids selected.
    """
    selected = []

    for position, count in ALL_PRO_SELECTIONS.items():
        candidates = get_position_season_stats(conn, season_year, position)

        if position in OFFENSE_POSITIONS or position in ('K', 'P'):
            scored = []
            for c in candidates:
                score = _compute_offensive_score(c)
                scored.append((score, c['player_id']))
        else:
            scored = []
            for c in candidates:
                score = _compute_defensive_score(c)
                scored.append((score, c['player_id']))

        scored.sort(reverse=True)
        for _, pid in scored[:count]:
            set_player_season_award(conn, pid, season_year, 'made_all_pro')
            selected.append(pid)

    return selected


def _compute_offensive_score(stats) -> float:
    """Compute a composite offensive score for award comparison."""
    score = 0.0

    # Passing contribution
    score += stats['pass_yards'] * AWARD_PASS_YARDS_WEIGHT
    score += stats['pass_tds'] * AWARD_PASS_TDS_WEIGHT
    score -= stats['interceptions_thrown'] * AWARD_INTERCEPTIONS_PENALTY
    passer_rating = stats['passer_rating'] or 0
    score += passer_rating * AWARD_PASSER_RATING_WEIGHT

    # Rushing contribution
    score += stats['rush_yards'] * AWARD_RUSH_YARDS_WEIGHT
    score += stats['rush_tds'] * AWARD_RUSH_TDS_WEIGHT

    # Receiving contribution
    score += stats['rec_yards'] * AWARD_REC_YARDS_WEIGHT
    score += stats['rec_tds'] * AWARD_REC_TDS_WEIGHT
    score += stats['receptions'] * AWARD_RECEPTIONS_WEIGHT

    # Kicking contribution
    score += stats['fg_made'] * AWARD_FG_MADE_WEIGHT

    # Penalty for turnovers
    fumbles = stats['fumbles'] or 0
    score -= fumbles * AWARD_FUMBLE_PENALTY

    return score


def _compute_defensive_score(stats) -> float:
    """Compute a composite defensive score for award comparison."""
    score = 0.0

    score += stats['tackles'] * AWARD_TACKLES_WEIGHT
    score += stats['sacks'] * AWARD_SACKS_WEIGHT
    score += stats['interceptions'] * AWARD_DEF_INT_WEIGHT
    score += stats['pass_deflections'] * AWARD_PASS_DEFLECTIONS_WEIGHT

    return score
