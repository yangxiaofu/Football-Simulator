"""
Schedule generation for Phase 0.

Generates a 17-game regular season schedule for all 32 teams.
"""

import sqlite3
import random
from typing import List, Tuple

from ..utils.constants import (
    REGULAR_SEASON_WEEKS,
    NUM_TEAMS,
    TEAMS_PER_DIVISION,
    MAX_GAMES_PER_TEAM_PER_WEEK,
    EXPECTED_GAMES_PER_TEAM,
    EXPECTED_TOTAL_GAMES,
)


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
    Generate a complete 17-game regular season schedule using greedy assignment.

    Ensures no team plays multiple games in the same week.

    Simplified for Phase 0:
    - 6 division games (home/away against 3 division opponents)
    - 11 other games (mix of conference and cross-conference)

    Args:
        conn: Database connection (must be in transaction)
        season_id: Season ID
        team_ids: List of all team IDs

    Returns:
        Number of games scheduled

    Raises:
        RuntimeError: If schedule validation fails

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
    # Track games per team to ensure balanced schedule
    games_per_team = {tid: 0 for tid in team_ids}
    for home, away in all_games:
        games_per_team[home] += 1
        games_per_team[away] += 1

    # Build set of existing matchups (unordered pairs)
    existing_matchups = set()
    for home, away in all_games:
        pair = tuple(sorted([home, away]))
        existing_matchups.add(pair)

    # Generate additional matchups to reach 17 games per team
    # Repeatedly pair teams that need games most
    while min(games_per_team.values()) < EXPECTED_GAMES_PER_TEAM:
        # Find teams needing games, sorted by games needed (fewest games first)
        teams_needing_games = sorted(
            [tid for tid in team_ids if games_per_team[tid] < EXPECTED_GAMES_PER_TEAM],
            key=lambda t: games_per_team[t]
        )

        if len(teams_needing_games) < 2:
            # Should never happen with 32 teams and 17 games each
            raise RuntimeError(f"Cannot complete schedule: only {len(teams_needing_games)} team(s) need games")

        # Try to find a valid pairing starting with teams that need games most
        paired = False
        for i in range(len(teams_needing_games)):
            if paired:
                break
            team_a = teams_needing_games[i]
            for j in range(i + 1, len(teams_needing_games)):
                team_b = teams_needing_games[j]
                pair = tuple(sorted([team_a, team_b]))

                # Check if matchup already exists
                if pair not in existing_matchups:
                    all_games.append((team_a, team_b))
                    games_per_team[team_a] += 1
                    games_per_team[team_b] += 1
                    existing_matchups.add(pair)
                    paired = True
                    break

        if not paired:
            # Fallback: allow duplicate matchups if absolutely necessary
            team_a = teams_needing_games[0]
            team_b = teams_needing_games[1]
            all_games.append((team_a, team_b))
            games_per_team[team_a] += 1
            games_per_team[team_b] += 1

    # Greedy assignment with backtracking: track which teams are busy each week
    week_assignments = {week_num: set() for week_num in range(1, REGULAR_SEASON_WEEKS + 1)}

    # Sort games by difficulty (games with teams that have more other games are harder to place)
    # This heuristic helps the greedy algorithm succeed more often
    team_game_count = {}
    for home, away in all_games:
        team_game_count[home] = team_game_count.get(home, 0) + 1
        team_game_count[away] = team_game_count.get(away, 0) + 1

    # Sort by sum of both teams' game counts (descending) - place harder games first
    all_games_sorted = sorted(all_games, key=lambda g: -(team_game_count[g[0]] + team_game_count[g[1]]))

    for home_team_id, away_team_id in all_games_sorted:
        # Find first week where both teams are free
        assigned = False
        for week_num in range(1, REGULAR_SEASON_WEEKS + 1):
            if home_team_id not in week_assignments[week_num] and away_team_id not in week_assignments[week_num]:
                # Assign game to this week
                week_id = week_map[week_num]
                conn.execute("""
                    INSERT INTO game (week_id, home_team_id, away_team_id, is_complete)
                    VALUES (?, ?, ?, 0)
                """, (week_id, home_team_id, away_team_id))

                # Mark both teams as busy
                week_assignments[week_num].add(home_team_id)
                week_assignments[week_num].add(away_team_id)
                assigned = True
                break

        # If no valid week found, we have a scheduling conflict
        if not assigned:
            raise RuntimeError(
                f"Cannot assign game {home_team_id} vs {away_team_id} - no valid week found. "
                f"This indicates a scheduling algorithm failure."
            )

    # Validate schedule
    errors = _validate_schedule(conn, season_id, team_ids)
    if errors:
        raise RuntimeError(f"Schedule validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    total_games = len(all_games)
    return total_games


def _validate_schedule(conn: sqlite3.Connection, season_id: int, team_ids: list[int]) -> list[str]:
    """
    Validate schedule meets all constraints. Returns list of error messages (empty if valid).

    Checks:
    1. Total game count equals EXPECTED_TOTAL_GAMES (272)
    2. Each team plays exactly EXPECTED_GAMES_PER_TEAM (17)
    3. No team plays more than MAX_GAMES_PER_TEAM_PER_WEEK (1) per week

    Args:
        conn: Database connection
        season_id: Season ID
        team_ids: List of all team IDs

    Returns:
        List of error messages (empty list if valid)
    """
    errors = []

    # Check 1: Total game count
    total = conn.execute(
        "SELECT COUNT(*) FROM game g JOIN week w ON g.week_id=w.id WHERE w.season_id=? AND w.week_type='regular'",
        (season_id,)
    ).fetchone()[0]
    if total != EXPECTED_TOTAL_GAMES:
        errors.append(f"Total games: {total} (expected {EXPECTED_TOTAL_GAMES})")

    # Check 2: Each team plays exactly 17 games
    for tid in team_ids:
        count = conn.execute(
            """SELECT COUNT(*) FROM game g
               JOIN week w ON g.week_id=w.id
               WHERE w.season_id=? AND w.week_type='regular'
               AND (g.home_team_id=? OR g.away_team_id=?)""",
            (season_id, tid, tid)
        ).fetchone()[0]
        if count != EXPECTED_GAMES_PER_TEAM:
            abbr = conn.execute("SELECT abbreviation FROM team WHERE id=?", (tid,)).fetchone()[0]
            errors.append(f"Team {abbr}: {count} games (expected {EXPECTED_GAMES_PER_TEAM})")

    # Check 3: No team plays >1 game per week
    for week_num in range(1, REGULAR_SEASON_WEEKS + 1):
        wid = conn.execute(
            "SELECT id FROM week WHERE season_id=? AND week_number=?",
            (season_id, week_num)
        ).fetchone()[0]
        for tid in team_ids:
            wcount = conn.execute(
                "SELECT COUNT(*) FROM game WHERE week_id=? AND (home_team_id=? OR away_team_id=?)",
                (wid, tid, tid)
            ).fetchone()[0]
            if wcount > MAX_GAMES_PER_TEAM_PER_WEEK:
                abbr = conn.execute("SELECT abbreviation FROM team WHERE id=?", (tid,)).fetchone()[0]
                errors.append(f"Week {week_num}: Team {abbr} has {wcount} games (max {MAX_GAMES_PER_TEAM_PER_WEEK})")

    return errors
