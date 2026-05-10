"""
Salary cap calculation and management utilities.

CRITICAL: team.cap_space is a CACHED VALUE, not computed live.
Call recalculate_cap_space() after EVERY contract or roster action that affects the cap.
"""

import sqlite3
from typing import Optional


def recalculate_cap_space(team_id: int, season_year: int, conn: sqlite3.Connection) -> int:
    """
    Recalculate and update a team's cap space for the given season.

    This function:
    1. Sums all active contract cap hits for the team in the season
    2. Subtracts from the league salary cap
    3. Updates team.cap_space with the result
    4. Returns the calculated cap space

    CRITICAL: Call this after every transaction that affects contracts:
    - Signing a player
    - Releasing a player
    - Trading a player
    - Restructuring a contract
    - Adding void years

    Args:
        team_id: Team ID
        season_year: Season year to calculate for
        conn: Database connection

    Returns:
        Calculated cap space (in dollars)

    Usage:
        with conn:
            # ... perform contract action ...
            new_cap = recalculate_cap_space(team_id, season_year, conn)
            print(f"Team now has ${new_cap:,} in cap space")
    """
    # Get the league salary cap
    league_row = conn.execute("SELECT salary_cap FROM league WHERE id = 1").fetchone()
    if not league_row:
        raise ValueError("League not initialized in database")

    salary_cap = league_row[0]

    # Sum all active contract cap hits for this team and season
    result = conn.execute("""
        SELECT COALESCE(SUM(cy.cap_hit), 0) as total_cap_hit
        FROM contract c
        JOIN contract_year cy ON cy.contract_id = c.id
        WHERE c.team_id = ?
          AND cy.season_year = ?
          AND c.status = 'active'
    """, (team_id, season_year)).fetchone()

    total_cap_hit = result[0] if result else 0
    cap_space = salary_cap - total_cap_hit

    # Update the cached cap_space value
    conn.execute(
        "UPDATE team SET cap_space = ? WHERE id = ?",
        (cap_space, team_id)
    )

    return cap_space


def recalculate_all_teams_cap_space(season_year: int, conn: sqlite3.Connection) -> None:
    """
    Recalculate cap space for all 32 teams.

    Useful for:
    - End of season processing
    - After league-wide salary cap changes
    - Data validation/repair

    Args:
        season_year: Season year to calculate for
        conn: Database connection

    Usage:
        with conn:
            recalculate_all_teams_cap_space(2024, conn)
    """
    teams = conn.execute("SELECT id FROM team").fetchall()
    for team_row in teams:
        recalculate_cap_space(team_row[0], season_year, conn)


def get_contract_cap_hit(contract_id: int, season_year: int, conn: sqlite3.Connection) -> int:
    """
    Get the cap hit for a specific contract in a specific season.

    Args:
        contract_id: Contract ID
        season_year: Season year
        conn: Database connection

    Returns:
        Cap hit in dollars (0 if contract doesn't exist or isn't active in that year)
    """
    result = conn.execute("""
        SELECT cap_hit
        FROM contract_year
        WHERE contract_id = ? AND season_year = ?
    """, (contract_id, season_year)).fetchone()

    return result[0] if result else 0


def get_player_cap_hit(player_id: int, season_year: int, conn: sqlite3.Connection) -> int:
    """
    Get the cap hit for a specific player in a specific season.

    Args:
        player_id: Player ID
        season_year: Season year
        conn: Database connection

    Returns:
        Cap hit in dollars (0 if player has no active contract)
    """
    result = conn.execute("""
        SELECT cy.cap_hit
        FROM contract c
        JOIN contract_year cy ON cy.contract_id = c.id
        WHERE c.player_id = ?
          AND cy.season_year = ?
          AND c.status = 'active'
    """, (player_id, season_year)).fetchone()

    return result[0] if result else 0


def get_dead_cap_value(contract_id: int, season_year: int, conn: sqlite3.Connection) -> int:
    """
    Get the dead cap value if a contract were cut in a specific season.

    This is the cap penalty that would be incurred if the player is released.

    Args:
        contract_id: Contract ID
        season_year: Season year
        conn: Database connection

    Returns:
        Dead cap value in dollars (0 if contract doesn't exist)
    """
    result = conn.execute("""
        SELECT dead_cap_value
        FROM contract_year
        WHERE contract_id = ? AND season_year = ?
    """, (contract_id, season_year)).fetchone()

    return result[0] if result else 0


def get_team_contract_breakdown(team_id: int, season_year: int,
                                conn: sqlite3.Connection) -> list[dict]:
    """
    Get a detailed breakdown of all contracts affecting a team's cap in a season.

    Useful for UI display and debugging cap issues.

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        List of dicts with player_id, player_name, position, cap_hit, dead_cap_value

    Usage:
        breakdown = get_team_contract_breakdown(team_id, 2024, conn)
        for contract in breakdown:
            print(f"{contract['player_name']} ({contract['position']}): ${contract['cap_hit']:,}")
    """
    rows = conn.execute("""
        SELECT
            p.id as player_id,
            p.first_name || ' ' || p.last_name as player_name,
            p.position,
            cy.cap_hit,
            cy.dead_cap_value,
            cy.base_salary,
            cy.prorated_bonus,
            cy.roster_bonus
        FROM contract c
        JOIN contract_year cy ON cy.contract_id = c.id
        JOIN player p ON p.id = c.player_id
        WHERE c.team_id = ?
          AND cy.season_year = ?
          AND c.status = 'active'
        ORDER BY cy.cap_hit DESC
    """, (team_id, season_year)).fetchall()

    return [dict(row) for row in rows]


def validate_team_cap_space(team_id: int, season_year: int, conn: sqlite3.Connection) -> dict:
    """
    Validate that a team's cached cap_space matches the calculated value.

    Returns a report with current cached value, calculated value, and whether they match.

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        Dict with 'cached_cap', 'calculated_cap', 'matches', 'difference'

    Usage:
        report = validate_team_cap_space(team_id, 2024, conn)
        if not report['matches']:
            print(f"Cap space mismatch! Difference: ${report['difference']:,}")
            # Fix it:
            with conn:
                recalculate_cap_space(team_id, season_year, conn)
    """
    # Get cached value
    team_row = conn.execute(
        "SELECT cap_space FROM team WHERE id = ?",
        (team_id,)
    ).fetchone()

    if not team_row:
        raise ValueError(f"Team {team_id} not found")

    cached_cap = team_row[0]

    # Calculate actual value (without updating the cache)
    league_row = conn.execute("SELECT salary_cap FROM league WHERE id = 1").fetchone()
    salary_cap = league_row[0]

    result = conn.execute("""
        SELECT COALESCE(SUM(cy.cap_hit), 0) as total_cap_hit
        FROM contract c
        JOIN contract_year cy ON cy.contract_id = c.id
        WHERE c.team_id = ?
          AND cy.season_year = ?
          AND c.status = 'active'
    """, (team_id, season_year)).fetchone()

    total_cap_hit = result[0] if result else 0
    calculated_cap = salary_cap - total_cap_hit

    difference = cached_cap - calculated_cap
    matches = (difference == 0)

    return {
        'cached_cap': cached_cap,
        'calculated_cap': calculated_cap,
        'matches': matches,
        'difference': difference,
        'salary_cap': salary_cap,
        'total_cap_hit': total_cap_hit
    }


def validate_all_teams_cap_space(season_year: int, conn: sqlite3.Connection) -> list[dict]:
    """
    Validate cap space for all teams and return mismatches.

    Args:
        season_year: Season year to validate
        conn: Database connection

    Returns:
        List of validation reports for teams with mismatches (empty list if all valid)

    Usage:
        mismatches = validate_all_teams_cap_space(2024, conn)
        if mismatches:
            print(f"Found {len(mismatches)} teams with cap space errors")
            for report in mismatches:
                print(f"Team {report['team_id']}: off by ${report['difference']:,}")
    """
    teams = conn.execute("SELECT id FROM team").fetchall()
    mismatches = []

    for team_row in teams:
        team_id = team_row[0]
        report = validate_team_cap_space(team_id, season_year, conn)
        if not report['matches']:
            report['team_id'] = team_id
            mismatches.append(report)

    return mismatches
