"""
Season-end archival.

Aggregates box_score data into player_season_stats and player_career_stats,
preserves key plays, deletes play logs, finalizes records and draft order.
"""

import sqlite3

from ..db.queries import (
    get_all_box_scores_for_season,
    insert_player_season_stats,
    upsert_player_career_stats,
    delete_play_logs_for_season,
    mark_season_complete,
    get_all_active_players,
    update_player_age,
    increment_player_experience,
    get_season_stats_for_career_update,
)
from ..utils.constants import RATING_MIN, RATING_MAX
from .standings import get_draft_order, update_all_standings


def archive_season(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Run the full season archive job.

    Steps:
    1. Aggregate box scores -> player_season_stats
    2. Update player_career_stats
    3. Delete play logs (keep key_play table, box_score table)
    4. Finalize team records and draft order
    5. Age players and increment experience
    6. Mark season complete

    Returns dict with counts of records processed.
    """
    print("  Archiving season stats...")

    # Step 1: Aggregate player season stats
    season_stats_count = aggregate_player_season_stats(conn, season_year)
    print(f"    {season_stats_count} player season stat records created")

    # Step 2: Update career stats
    career_count = update_player_career_stats(conn, season_year)
    print(f"    {career_count} player career stat records updated")

    # Step 3: Delete play logs
    plays_deleted = delete_play_logs_for_season(conn, season_year)
    print(f"    {plays_deleted} play records deleted")

    # Step 4: Finalize records and draft order
    finalize_draft_order(conn, season_year)
    print("    Draft order finalized")

    # Step 5: Age players, increment experience
    age_and_advance_players(conn)
    print("    Players aged and experience incremented")

    # Step 6: Mark season complete
    mark_season_complete(conn, season_year)
    print(f"    Season {season_year} marked complete")

    return {
        'season_stats_count': season_stats_count,
        'career_count': career_count,
        'plays_deleted': plays_deleted,
    }


def aggregate_player_season_stats(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Compute season totals from box_score records and write to player_season_stats.

    Returns count of records written.
    """
    box_scores = get_all_box_scores_for_season(conn, season_year)

    # Aggregate by player
    player_agg = {}
    for bs in box_scores:
        pid = bs['player_id']
        if pid not in player_agg:
            player_agg[pid] = {
                'player_id': pid,
                'team_id': bs['team_id'],
                'season_year': season_year,
                'games_played': 0,
                'games_started': 0,
                'pass_attempts': 0,
                'completions': 0,
                'pass_yards': 0,
                'pass_tds': 0,
                'interceptions_thrown': 0,
                'carries': 0,
                'rush_yards': 0,
                'rush_tds': 0,
                'targets': 0,
                'receptions': 0,
                'rec_yards': 0,
                'rec_tds': 0,
                'tackles': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'pass_deflections': 0,
                'fg_made': 0,
                'fg_attempts': 0,
                'fg_long': 0,
                'sacks_taken': 0,
                'fumbles': 0,
                'punts': 0,
                'punt_yards': 0,
                'xp_attempts': 0,
                'xp_made': 0,
                'punt_returns': 0,
                'punt_return_yards': 0,
                'punt_return_tds': 0,
                'kick_returns': 0,
                'kick_return_yards': 0,
                'kick_return_tds': 0,
            }

        agg = player_agg[pid]
        agg['games_played'] += 1
        # Count as started if player had significant involvement
        has_significant_stats = (
            bs['pass_attempts'] > 0 or bs['carries'] > 0 or
            bs['targets'] > 0 or bs['tackles'] > 0
        )
        if has_significant_stats:
            agg['games_started'] += 1

        agg['pass_attempts'] += bs['pass_attempts']
        agg['completions'] += bs['completions']
        agg['pass_yards'] += bs['pass_yards']
        agg['pass_tds'] += bs['pass_tds']
        agg['interceptions_thrown'] += bs['interceptions_thrown']
        agg['carries'] += bs['carries']
        agg['rush_yards'] += bs['rush_yards']
        agg['rush_tds'] += bs['rush_tds']
        agg['targets'] += bs['targets']
        agg['receptions'] += bs['receptions']
        agg['rec_yards'] += bs['rec_yards']
        agg['rec_tds'] += bs['rec_tds']
        agg['tackles'] += bs['tackles']
        agg['sacks'] += bs['sacks']
        agg['interceptions'] += bs['interceptions']
        agg['pass_deflections'] += bs['pass_deflections']
        agg['fg_made'] += bs['fg_made']
        agg['fg_attempts'] += bs['fg_attempts']
        if bs['fg_long'] > agg['fg_long']:
            agg['fg_long'] = bs['fg_long']
        agg['sacks_taken'] += bs['sacks_taken']
        agg['fumbles'] += bs['fumbles']
        agg['punts'] += bs['punts']
        agg['punt_yards'] += bs['punt_yards']
        agg['xp_attempts'] += bs['xp_attempts']
        agg['xp_made'] += bs['xp_made']
        agg['punt_returns'] += bs['punt_returns'] or 0
        agg['punt_return_yards'] += bs['punt_return_yards'] or 0
        agg['punt_return_tds'] += bs['punt_return_tds'] or 0
        agg['kick_returns'] += bs['kick_returns'] or 0
        agg['kick_return_yards'] += bs['kick_return_yards'] or 0
        agg['kick_return_tds'] += bs['kick_return_tds'] or 0

    # Compute derived stats and write
    count = 0
    for pid, agg in player_agg.items():
        # Passer rating (simplified NFL formula)
        agg['passer_rating'] = _compute_passer_rating(agg)

        # Yards per carry
        if agg['carries'] > 0:
            agg['yards_per_carry'] = round(agg['rush_yards'] / agg['carries'], 1)
        else:
            agg['yards_per_carry'] = 0.0

        # Catch percentage
        if agg['targets'] > 0:
            agg['catch_percentage'] = round(agg['receptions'] / agg['targets'], 3)
        else:
            agg['catch_percentage'] = 0.0

        # FG percentage
        if agg['fg_attempts'] > 0:
            agg['fg_percentage'] = round(agg['fg_made'] / agg['fg_attempts'], 3)
        else:
            agg['fg_percentage'] = 0.0

        # Awards default to 0 (set by awards module)
        agg['made_pro_bowl'] = 0
        agg['made_all_pro'] = 0
        agg['won_mvp'] = 0

        insert_player_season_stats(conn, agg)
        count += 1

    return count


def update_player_career_stats(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Add this season's stats to career totals for each player.

    Returns count of players updated.
    """
    rows = get_season_stats_for_career_update(conn, season_year)

    count = 0
    for row in rows:
        stats = dict(row)
        stats['current_overall'] = row['true_overall']
        upsert_player_career_stats(conn, row['player_id'], stats)
        count += 1

    return count


def finalize_draft_order(
    conn: sqlite3.Connection, season_year: int,
) -> None:
    """Set draft_position for all 32 teams based on final standings."""
    from ..db.queries import set_team_draft_position

    draft_order = get_draft_order(conn, season_year)
    for pick, team_id in enumerate(draft_order, 1):
        set_team_draft_position(conn, team_id, season_year, pick)


def age_and_advance_players(conn: sqlite3.Connection) -> None:
    """Age all active players by 1 year and increment experience."""
    players = get_all_active_players(conn)
    for p in players:
        update_player_age(conn, p['id'])
        increment_player_experience(conn, p['id'])


def _compute_passer_rating(stats: dict) -> float:
    """Compute NFL passer rating from season stats.

    Uses the standard NFL passer rating formula.
    """
    att = stats.get('pass_attempts', 0)
    if att == 0:
        return 0.0

    comp = stats.get('completions', 0)
    yards = stats.get('pass_yards', 0)
    td = stats.get('pass_tds', 0)
    ints = stats.get('interceptions_thrown', 0)

    # Component a: completion percentage
    a = max(0, min(2.375, ((comp / att) - 0.3) * 5))
    # Component b: yards per attempt
    b = max(0, min(2.375, ((yards / att) - 3) * 0.25))
    # Component c: TD percentage
    c = max(0, min(2.375, (td / att) * 20))
    # Component d: INT percentage
    d = max(0, min(2.375, 2.375 - ((ints / att) * 25)))

    rating = ((a + b + c + d) / 6) * 100
    return round(rating, 1)
