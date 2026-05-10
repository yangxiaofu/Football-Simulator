"""
Team generation for Phase 0.

Generates 32 fictional teams with divisions, conferences, and attributes.
"""

import sqlite3
import random
from typing import List

from ..utils.constants import (
    NUM_TEAMS, NUM_CONFERENCES, NUM_DIVISIONS, TEAMS_PER_DIVISION,
    CONFERENCE_NAMES, DIVISION_NAMES, GM_PERSONALITIES,
    STADIUM_TYPES, CLIMATE_TYPES,
    PRESTIGE_MIN, PRESTIGE_MAX, MARKET_SIZE_MIN, MARKET_SIZE_MAX,
    FAN_SENTIMENT_DEFAULT, SALARY_CAP_YEAR_ONE,
    COACH_MIN_AGE, COACH_MAX_AGE,
)
from ..transactions.coaching import assign_coach_to_team
from .names import TEAM_CITIES, TEAM_NICKNAMES, TEAM_ABBREVIATIONS, FIRST_NAMES, LAST_NAMES


def generate_conferences_and_divisions(conn: sqlite3.Connection) -> dict:
    """
    Create conferences and divisions.

    Returns:
        Dict mapping division_name -> division_id
    """
    division_map = {}

    # Create conferences
    for conf_name in CONFERENCE_NAMES:
        conn.execute("INSERT INTO conference (name) VALUES (?)", (conf_name,))

    # Create divisions (4 per conference)
    for i, div_name in enumerate(DIVISION_NAMES):
        conference_id = (i // 4) + 1  # 4 divisions per conference
        cursor = conn.execute(
            "INSERT INTO division (conference_id, name) VALUES (?, ?)",
            (conference_id, div_name)
        )
        division_map[div_name] = cursor.lastrowid

    return division_map


def generate_teams(conn: sqlite3.Connection, division_map: dict, season_year: int) -> List[int]:
    """
    Generate 32 fictional teams.

    Args:
        conn: Database connection
        division_map: Dict of division_name -> division_id
        season_year: Starting season year

    Returns:
        List of team IDs
    """
    # Shuffle cities and nicknames for random pairings
    cities = TEAM_CITIES.copy()
    nicknames = TEAM_NICKNAMES[:NUM_TEAMS].copy()  # Take exactly 32
    random.shuffle(nicknames)

    team_ids = []

    for i, (div_name, division_id) in enumerate(division_map.items()):
        # Generate 4 teams per division
        for j in range(TEAMS_PER_DIVISION):
            idx = i * TEAMS_PER_DIVISION + j
            city = cities[idx]
            nickname = nicknames[idx]
            abbreviation = TEAM_ABBREVIATIONS.get(city, city[:3].upper())

            # Random attributes
            gm_personality = random.choice(GM_PERSONALITIES)
            prestige = random.randint(40, 85)  # Spread across range
            market_size = random.randint(35, 95)  # Varies by "city size"
            stadium_type = random.choice(STADIUM_TYPES)

            # Climate based on city (simplified)
            if city in ["Green Bay", "Buffalo", "Cleveland", "Chicago", "Detroit", "Minneapolis", "Boston", "Pittsburgh"]:
                climate = "cold"
            elif city in ["Miami", "Tampa Bay", "Jacksonville", "Houston", "Phoenix", "Tucson", "Los Angeles", "San Francisco"]:
                climate = "warm"
            else:
                climate = "neutral"

            # Initial cap space = full salary cap (no contracts yet)
            cap_space = SALARY_CAP_YEAR_ONE

            # Waiver priority = reverse order of team ID (will be adjusted after first season)
            waiver_priority = NUM_TEAMS - idx

            cursor = conn.execute("""
                INSERT INTO team (
                    division_id, city, nickname, abbreviation,
                    gm_personality, prestige, market_size,
                    stadium_type, home_city_climate,
                    cap_space, waiver_priority, fan_sentiment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                division_id, city, nickname, abbreviation,
                gm_personality, prestige, market_size,
                stadium_type, climate,
                cap_space, waiver_priority, FAN_SENTIMENT_DEFAULT
            ))

            team_ids.append(cursor.lastrowid)

    return team_ids


def initialize_league(conn: sqlite3.Connection, season_year: int, user_team_id: int) -> None:
    """
    Initialize the league record.

    Args:
        conn: Database connection
        season_year: Starting season year
        user_team_id: ID of the user's team
    """
    from datetime import datetime

    conn.execute("""
        INSERT INTO league (
            id, name, current_season, current_week, current_phase,
            salary_cap, user_team_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,  # Always ID 1
        "National Football League",
        season_year,
        0,  # Offseason
        'offseason',
        SALARY_CAP_YEAR_ONE,
        user_team_id,
        datetime.now().isoformat()
    ))


def initialize_season(conn: sqlite3.Connection, season_year: int) -> int:
    """
    Create the initial season record.

    Args:
        conn: Database connection
        season_year: Starting season year

    Returns:
        Season ID
    """
    cursor = conn.execute("""
        INSERT INTO season (year, salary_cap, is_complete)
        VALUES (?, ?, 0)
    """, (season_year, SALARY_CAP_YEAR_ONE))

    return cursor.lastrowid


def generate_all_teams(conn: sqlite3.Connection, season_year: int = 2024) -> List[int]:
    """
    Generate the complete league structure: conferences, divisions, and 32 teams.

    Args:
        conn: Database connection (must be in transaction)
        season_year: Starting season year

    Returns:
        List of all team IDs

    Usage:
        with conn:
            team_ids = generate_all_teams(conn, season_year=2024)
            print(f"Generated {len(team_ids)} teams")
    """
    # Step 1: Create conferences and divisions
    division_map = generate_conferences_and_divisions(conn)

    # Step 2: Generate 32 teams
    team_ids = generate_teams(conn, division_map, season_year)

    # Step 3: Initialize league (user team = first team for now, can be changed)
    user_team_id = team_ids[0]
    initialize_league(conn, season_year, user_team_id)

    # Step 4: Initialize season
    initialize_season(conn, season_year)

    return team_ids


def generate_ai_coaches(
    conn: sqlite3.Connection,
    season_year: int,
    team_ids: List[int],
    skip_team_id: int = None,
) -> List[int]:
    """
    Generate one AI coach per team, matching each team's current gm_personality.

    Args:
        conn: Database connection (must be in transaction)
        season_year: Starting season year
        team_ids: List of team IDs to generate coaches for
        skip_team_id: Optional team ID to skip (e.g., user's team will get player coach)

    Returns:
        List of coach_career IDs created
    """
    coach_ids = []

    for team_id in team_ids:
        if skip_team_id is not None and team_id == skip_team_id:
            continue
        team = conn.execute(
            "SELECT gm_personality FROM team WHERE id = ?", (team_id,)
        ).fetchone()

        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        age = random.randint(COACH_MIN_AGE, COACH_MAX_AGE)
        archetype = team['gm_personality']

        cursor = conn.execute(
            """INSERT INTO coach_career
               (first_name, last_name, age, personality_archetype,
                career_start_year, is_player, is_active)
               VALUES (?, ?, ?, ?, ?, 0, 1)""",
            (first_name, last_name, age, archetype, season_year)
        )
        coach_id = cursor.lastrowid
        assign_coach_to_team(conn, coach_id, team_id, season_year)
        coach_ids.append(coach_id)

    return coach_ids
