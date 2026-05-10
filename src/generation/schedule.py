"""
Schedule generation for Phase 0.

Generates a 17-game regular season schedule for all 32 teams.
"""

import sqlite3
import random
from typing import List, Tuple

from ..utils.constants import REGULAR_SEASON_WEEKS, NUM_TEAMS, TEAMS_PER_DIVISION


def get_teams_by_division(conn: sqlite3.Connection) -> dict:
    """
    Organize teams by division.

    Returns:
        Dict of division_id -> list of team_ids
    """
    rows = conn.execute("""
        SELECT id, division_id FROM team ORDER BY division_id, id
    """).fetchall()

    divisions = {}
    for row in rows:
        team_id = row[0]
        division_id = row[1]
        if division_id not in divisions:
            divisions[division_id] = []
        divisions[division_id].append(team_id)

    return divisions


def generate_division_games(division_teams: list[int]) -> list[tuple]:
    """
    Generate home-and-away games within a division (6 games per team).

    Each team plays every other team in division twice (home/away).

    Args:
        division_teams: List of 4 team IDs in a division

    Returns:
        List of (home_team_id, away_team_id) tuples
    """
    games = []
    for i in range(len(division_teams)):
        for j in range(i + 1, len(division_teams)):
            # Home and away
            games.append((division_teams[i], division_teams[j]))
            games.append((division_teams[j], division_teams[i]))
    return games


def generate_conference_games(divisions: dict, season_id: int) -> list[tuple]:
    """
    Generate conference games (not including division games).

    Simplified for Phase 0: each team plays 6 additional conference games.

    Args:
        divisions: Dict of division_id -> team_ids
        season_id: Season ID

    Returns:
        List of (home_team_id, away_team_id) tuples
    """
    # For Phase 0, use a simplified approach:
    # Generate random conference matchups
    # In a real implementation, this would follow NFL scheduling rules
    # (rotating division matchups, etc.)

    all_teams = []
    for teams in divisions.values():
        all_teams.extend(teams)

    random.shuffle(all_teams)

    games = []
    # Create 6 conference games per team (total ~96 games)
    for i in range(0, len(all_teams) - 1, 2):
        games.append((all_teams[i], all_teams[i + 1]))

    return games


def generate_full_schedule(conn: sqlite3.Connection, season_id: int, team_ids: list[int]) -> int:
    """
    Generate a complete 17-game regular season schedule.

    Simplified for Phase 0:
    - 6 division games (home/away against 3 division opponents)
    - 11 other games (mix of conference and cross-conference)

    Args:
        conn: Database connection (must be in transaction)
        season_id: Season ID
        team_ids: List of all team IDs

    Returns:
        Number of games scheduled

    Note:
        This is a simplified schedule generator for Phase 0.
        A production version would implement full NFL scheduling rules:
        - 6 division games (home/away)
        - 4 games vs one other division in conference (rotating)
        - 4 games vs one division in other conference (rotating)
        - 2 games vs conference teams with same division standing
        - 1 game vs cross-conference team with same standing
    """
    divisions = get_teams_by_division(conn)

    # Create weeks 1-17
    for week_num in range(1, REGULAR_SEASON_WEEKS + 1):
        conn.execute("""
            INSERT INTO week (season_id, week_number, week_type, is_complete)
            VALUES (?, ?, 'regular', 0)
        """, (season_id, week_num))

    week_rows = conn.execute("""
        SELECT id, week_number FROM week WHERE season_id = ? ORDER BY week_number
    """, (season_id,)).fetchall()

    week_map = {row[1]: row[0] for row in week_rows}

    # Generate all matchups
    all_games = []

    # 1. Division games (6 per team = 48 total games)
    for division_id, division_teams in divisions.items():
        div_games = generate_division_games(division_teams)
        all_games.extend(div_games)

    # 2. Additional games to reach 17 per team (272 total games in season)
    # Simplified: generate random matchups
    # Real NFL: follow specific rotation rules

    # We need 272 total games (32 teams * 17 games / 2)
    # We have ~48 division games
    # Need ~224 more games

    random.shuffle(team_ids)
    additional_games_needed = (NUM_TEAMS * REGULAR_SEASON_WEEKS // 2) - len(all_games)

    for i in range(0, additional_games_needed * 2, 2):
        team_a = team_ids[i % len(team_ids)]
        team_b = team_ids[(i + 1) % len(team_ids)]
        all_games.append((team_a, team_b))

    # Shuffle games and distribute across weeks
    random.shuffle(all_games)

    games_per_week = len(all_games) // REGULAR_SEASON_WEEKS
    game_count = 0

    for week_num in range(1, REGULAR_SEASON_WEEKS + 1):
        week_id = week_map[week_num]
        week_games = all_games[game_count:game_count + games_per_week]

        for home_team_id, away_team_id in week_games:
            conn.execute("""
                INSERT INTO game (week_id, home_team_id, away_team_id, is_complete)
                VALUES (?, ?, ?, 0)
            """, (week_id, home_team_id, away_team_id))

        game_count += len(week_games)

    # Handle any remaining games (distribute to final weeks)
    remaining_games = all_games[game_count:]
    final_week_id = week_map[REGULAR_SEASON_WEEKS]

    for home_team_id, away_team_id in remaining_games:
        conn.execute("""
            INSERT INTO game (week_id, home_team_id, away_team_id, is_complete)
            VALUES (?, ?, ?, 0)
        """, (final_week_id, home_team_id, away_team_id))

    total_games = len(all_games)
    return total_games
