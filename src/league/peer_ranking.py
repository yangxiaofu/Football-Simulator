"""
Peer ranking system for coaches.

Ranks coaches vs active peers and all-time based on career legacy totals.
"""

import sqlite3
from typing import Optional

from ..db.queries import (
    get_all_active_coaches,
    insert_peer_ranking,
    get_peer_ranking,
)
from .legacy import compute_career_legacy_total


def update_peer_rankings(
    conn: sqlite3.Connection,
    season_year: int,
) -> dict:
    """For each active coach, compute career_legacy_total and rank.

    Two ranks:
    - active_rank: position among is_active=1 coaches
    - all_time_rank: position among ALL coaches

    Writes peer_ranking_snapshot rows.

    Returns:
        Dict mapping coach_id → (active_rank, all_time_rank)
    """
    # Get all active coaches with their career totals
    active_coaches = get_all_active_coaches(conn)

    active_totals = []
    for coach in active_coaches:
        total = compute_career_legacy_total(conn, coach['id'], season_year)
        active_totals.append((coach['id'], total))

    # Sort by total descending (rank 1 = highest)
    active_totals.sort(key=lambda x: x[1], reverse=True)

    # Get all-time coaches (all coaches with at least one legacy score)
    all_time_coaches = conn.execute("""
        SELECT DISTINCT coach_id FROM coach_legacy_score
    """).fetchall()

    all_time_totals = []
    for row in all_time_coaches:
        coach_id = row['coach_id']
        total = compute_career_legacy_total(conn, coach_id, season_year)
        all_time_totals.append((coach_id, total))

    # Sort by total descending
    all_time_totals.sort(key=lambda x: x[1], reverse=True)

    # Build rank lookup dicts
    active_rank_map = {coach_id: rank + 1 for rank, (coach_id, _) in enumerate(active_totals)}
    all_time_rank_map = {coach_id: rank + 1 for rank, (coach_id, _) in enumerate(all_time_totals)}

    n_active = len(active_totals)
    n_all_time = len(all_time_totals)

    results = {}

    # Write snapshots for all active coaches
    for coach_id, total in active_totals:
        active_rank = active_rank_map[coach_id]
        all_time_rank = all_time_rank_map.get(coach_id, n_all_time + 1)  # Should always exist

        insert_peer_ranking(
            conn, coach_id, season_year, total,
            active_rank, all_time_rank, n_active, n_all_time,
        )

        results[coach_id] = (active_rank, all_time_rank)

    return results


def get_player_peer_rank(
    conn: sqlite3.Connection,
    season_year: int,
) -> Optional[dict]:
    """Convenience: return latest snapshot for player coach.

    Returns:
        Dict with keys: active_rank, n_active, all_time_rank, n_all_time, career_legacy_total
        Or None if no player coach exists
    """
    # Find player coach
    player_coach = conn.execute("""
        SELECT id FROM coach_career
        WHERE is_player = 1
        LIMIT 1
    """).fetchone()

    if not player_coach:
        return None

    coach_id = player_coach['id']
    snapshot = get_peer_ranking(conn, coach_id, season_year)

    if not snapshot:
        return None

    return {
        'active_rank': snapshot['active_rank'],
        'n_active': snapshot['n_active'],
        'all_time_rank': snapshot['all_time_rank'],
        'n_all_time': snapshot['n_all_time'],
        'career_legacy_total': snapshot['career_legacy_total'],
    }
