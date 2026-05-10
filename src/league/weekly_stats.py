"""
Weekly stats aggregation system (Phase 5).

Aggregates box_score data for completed weeks into:
- player_week_stats: per-player per-week snapshot
- player_season_running: running season totals (incremental updates)
- team_week_stats: per-team per-week snapshot
- team_season_running: running team totals (incremental updates)

Called from season.py after each week is marked complete.
"""

import sqlite3
from typing import Dict, List
from ..db.queries import (
    get_all_games_for_week,
    get_box_scores_for_game,
    insert_player_week_stats,
    get_player_season_running,
    insert_player_season_running,
    update_player_season_running_incremental,
    insert_team_week_stats,
    get_team_season_running,
    insert_team_season_running,
    update_team_season_running_incremental,
)
from ..utils.constants import STAT_COLUMNS_PLAYER


def aggregate_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff: bool = False
) -> None:
    """
    Aggregate box_score data for completed week into weekly caches + running totals.

    Pipeline:
    1. Sum box_score by player → player_week_stats (snapshot)
    2. Update player_season_running (incremental += this week)
    3. Sum box_score by team → team_week_stats (snapshot)
    4. Update team_season_running (incremental += this week)
    5. Calculate Stars of the Week (weekly_award table)

    Args:
        conn: Database connection
        season_year: Season year
        week_number: Week number (1-17 regular season, 18-21 playoffs)
        is_playoff: True if playoff week, False for regular season

    Transaction safety: Should be called within an existing transaction block.
    """
    is_playoff_int = 1 if is_playoff else 0

    # Step 1 & 2: Aggregate player stats
    _aggregate_player_week_stats(conn, season_year, week_number, is_playoff_int)

    # Step 3 & 4: Aggregate team stats
    _aggregate_team_week_stats(conn, season_year, week_number, is_playoff_int)


def _aggregate_player_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff_int: int
) -> None:
    """
    Aggregate player box_score data for the week.

    Creates player_week_stats snapshots and updates player_season_running totals.
    """
    # Get all games for this week
    games = get_all_games_for_week(conn, season_year, week_number)

    # Accumulate stats by player
    player_stats: Dict[int, Dict] = {}

    for game in games:
        box_scores = get_box_scores_for_game(conn, game['id'])

        for box in box_scores:
            player_id = box['player_id']
            team_id = box['team_id']

            if player_id not in player_stats:
                player_stats[player_id] = _init_player_stat_dict(player_id, team_id)

            # Accumulate all stats from this box_score
            _accumulate_player_stats(player_stats[player_id], box)

    # Write snapshots to player_week_stats (INSERT OR REPLACE for idempotency)
    for player_id, stats_dict in player_stats.items():
        # Delete existing week stats if present (idempotent)
        conn.execute("""
            DELETE FROM player_week_stats
            WHERE season_year = ? AND week_number = ? AND player_id = ? AND is_playoff = ?
        """, (season_year, week_number, player_id, is_playoff_int))

        insert_player_week_stats(conn, season_year, week_number, is_playoff_int, stats_dict)

    # Recompute running totals from SUM of all weekly stats (idempotent)
    _recompute_player_running_totals(conn, season_year, is_playoff_int)


def _aggregate_team_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff_int: int
) -> None:
    """
    Aggregate team-level stats for the week.

    Creates team_week_stats snapshots and updates team_season_running totals.
    """
    # Get all games for this week
    games = get_all_games_for_week(conn, season_year, week_number)

    # Accumulate stats by team
    team_stats: Dict[int, Dict] = {}

    for game in games:
        home_id = game['home_team_id']
        away_id = game['away_team_id']
        home_score = game['home_score'] or 0
        away_score = game['away_score'] or 0

        # Initialize team dicts
        if home_id not in team_stats:
            team_stats[home_id] = _init_team_stat_dict(home_id)
        if away_id not in team_stats:
            team_stats[away_id] = _init_team_stat_dict(away_id)

        # Extract team stats from player box_scores
        box_scores = get_box_scores_for_game(conn, game['id'])
        for box in box_scores:
            team_id = box['team_id']
            if team_id not in team_stats:
                continue  # Should never happen

            # Accumulate offensive stats (yards, turnovers)
            team_stats[team_id]['pass_yards'] += box['pass_yards']
            team_stats[team_id]['rush_yards'] += box['rush_yards']
            team_stats[team_id]['turnovers'] += box['interceptions_thrown'] + box['fumbles']

            # Accumulate defensive stats (sacks, takeaways)
            # Note: interceptions and fumbles are credited to the defender's team
            team_stats[team_id]['sacks_recorded'] += box['sacks']
            team_stats[team_id]['takeaways'] += box['interceptions'] + box['forced_fumbles']

        # Calculate total yards
        team_stats[home_id]['total_yards'] = team_stats[home_id]['pass_yards'] + team_stats[home_id]['rush_yards']
        team_stats[away_id]['total_yards'] = team_stats[away_id]['pass_yards'] + team_stats[away_id]['rush_yards']

        # Points scored/allowed
        team_stats[home_id]['points_scored'] = home_score
        team_stats[home_id]['points_allowed'] = away_score
        team_stats[away_id]['points_scored'] = away_score
        team_stats[away_id]['points_allowed'] = home_score

        # Win/loss
        if home_score > away_score:
            team_stats[home_id]['won'] = 1
            team_stats[home_id]['wins'] = 1
            team_stats[away_id]['losses'] = 1
        elif away_score > home_score:
            team_stats[away_id]['won'] = 1
            team_stats[away_id]['wins'] = 1
            team_stats[home_id]['losses'] = 1
        else:
            team_stats[home_id]['ties'] = 1
            team_stats[away_id]['ties'] = 1

    # Write snapshots to team_week_stats (idempotent)
    for team_id, stats_dict in team_stats.items():
        # Delete existing week stats if present
        conn.execute("""
            DELETE FROM team_week_stats
            WHERE season_year = ? AND week_number = ? AND team_id = ? AND is_playoff = ?
        """, (season_year, week_number, team_id, is_playoff_int))

        insert_team_week_stats(conn, season_year, week_number, team_id, is_playoff_int, stats_dict)

    # Recompute running totals from SUM of all weekly stats (idempotent)
    _recompute_team_running_totals(conn, season_year, is_playoff_int)


def _recompute_player_running_totals(
    conn: sqlite3.Connection, season_year: int, is_playoff_int: int
) -> None:
    """
    Recompute player_season_running from SUM of player_week_stats.

    This ensures idempotency: running totals = SUM(weekly stats) always.
    """
    # Get all players with weekly stats this season
    players = conn.execute("""
        SELECT DISTINCT player_id, team_id
        FROM player_week_stats
        WHERE season_year = ? AND is_playoff = ?
    """, (season_year, is_playoff_int)).fetchall()

    for player_row in players:
        player_id = player_row['player_id']
        team_id = player_row['team_id']

        # Sum all weekly stats for this player
        weekly_sum = conn.execute("""
            SELECT
                COUNT(*) as games_played,
                SUM(pass_attempts) as pass_attempts, SUM(completions) as completions,
                SUM(pass_yards) as pass_yards, SUM(pass_tds) as pass_tds,
                SUM(interceptions_thrown) as interceptions_thrown, SUM(sacks_taken) as sacks_taken,
                SUM(carries) as carries, SUM(rush_yards) as rush_yards,
                SUM(rush_tds) as rush_tds, SUM(fumbles) as fumbles,
                SUM(targets) as targets, SUM(receptions) as receptions,
                SUM(rec_yards) as rec_yards, SUM(rec_tds) as rec_tds,
                SUM(tackles) as tackles, SUM(sacks) as sacks,
                SUM(interceptions) as interceptions, SUM(pass_deflections) as pass_deflections,
                SUM(forced_fumbles) as forced_fumbles,
                SUM(fg_attempts) as fg_attempts, SUM(fg_made) as fg_made,
                MAX(fg_long) as fg_long,
                SUM(xp_attempts) as xp_attempts, SUM(xp_made) as xp_made,
                SUM(punts) as punts, SUM(punt_yards) as punt_yards,
                SUM(punt_returns) as punt_returns, SUM(punt_return_yards) as punt_return_yards,
                SUM(punt_return_tds) as punt_return_tds,
                SUM(kick_returns) as kick_returns, SUM(kick_return_yards) as kick_return_yards,
                SUM(kick_return_tds) as kick_return_tds
            FROM player_week_stats
            WHERE season_year = ? AND player_id = ? AND is_playoff = ?
        """, (season_year, player_id, is_playoff_int)).fetchone()

        running_totals = dict(weekly_sum)

        # Delete existing running total and insert new one (INSERT OR REPLACE pattern)
        conn.execute("""
            DELETE FROM player_season_running
            WHERE season_year = ? AND player_id = ? AND is_playoff = ?
        """, (season_year, player_id, is_playoff_int))

        insert_player_season_running(
            conn, season_year, player_id, team_id, is_playoff_int, running_totals
        )


def _recompute_team_running_totals(
    conn: sqlite3.Connection, season_year: int, is_playoff_int: int
) -> None:
    """
    Recompute team_season_running from SUM of team_week_stats.

    This ensures idempotency: running totals = SUM(weekly stats) always.
    """
    # Get all teams with weekly stats this season
    teams = conn.execute("""
        SELECT DISTINCT team_id
        FROM team_week_stats
        WHERE season_year = ? AND is_playoff = ?
    """, (season_year, is_playoff_int)).fetchall()

    for team_row in teams:
        team_id = team_row['team_id']

        # Sum all weekly stats for this team
        weekly_sum = conn.execute("""
            SELECT
                COUNT(*) as games_played,
                SUM(points_scored) as points_scored, SUM(total_yards) as total_yards,
                SUM(pass_yards) as pass_yards, SUM(rush_yards) as rush_yards,
                SUM(turnovers) as turnovers,
                SUM(third_down_conversions) as third_down_conversions,
                SUM(third_down_attempts) as third_down_attempts,
                SUM(points_allowed) as points_allowed, SUM(yards_allowed) as yards_allowed,
                SUM(sacks_recorded) as sacks_recorded, SUM(takeaways) as takeaways,
                SUM(won) as wins,
                SUM(CASE WHEN won = 0 AND (points_scored < points_allowed) THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN won = 0 AND (points_scored = points_allowed) THEN 1 ELSE 0 END) as ties
            FROM team_week_stats
            WHERE season_year = ? AND team_id = ? AND is_playoff = ?
        """, (season_year, team_id, is_playoff_int)).fetchone()

        running_totals = dict(weekly_sum)

        # Delete existing running total and insert new one
        conn.execute("""
            DELETE FROM team_season_running
            WHERE season_year = ? AND team_id = ? AND is_playoff = ?
        """, (season_year, team_id, is_playoff_int))

        insert_team_season_running(
            conn, season_year, team_id, is_playoff_int, running_totals
        )


def _init_player_stat_dict(player_id: int, team_id: int) -> Dict:
    """Initialize a player stat dict with all columns set to 0."""
    stat_dict = {
        'player_id': player_id,
        'team_id': team_id,
    }
    for col in STAT_COLUMNS_PLAYER:
        stat_dict[col] = 0 if col != 'sacks' else 0.0

    return stat_dict


def _init_team_stat_dict(team_id: int) -> Dict:
    """Initialize a team stat dict with all columns set to 0."""
    return {
        'team_id': team_id,
        'points_scored': 0,
        'total_yards': 0,
        'pass_yards': 0,
        'rush_yards': 0,
        'turnovers': 0,
        'third_down_conversions': 0,
        'third_down_attempts': 0,
        'points_allowed': 0,
        'yards_allowed': 0,
        'sacks_recorded': 0.0,
        'takeaways': 0,
        'won': 0,
        'wins': 0,
        'losses': 0,
        'ties': 0,
    }


def _accumulate_player_stats(target_dict: Dict, box_score_row: sqlite3.Row) -> None:
    """Add box_score stats to target dict (in-place accumulation)."""
    for col in STAT_COLUMNS_PLAYER:
        if col in box_score_row.keys():
            target_dict[col] += box_score_row[col]
