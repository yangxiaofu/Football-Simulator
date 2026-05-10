"""
Franchise Tag system for Football Simulator.

Handles franchise and transition tag application, salary calculation,
consecutive tag tracking, and tag removal.

All database access goes through src/db/queries.py — no raw SQL here.
All tuning constants come from src/utils/constants.py.
"""

import sqlite3
from typing import Optional

from ..db.cap import recalculate_cap_space
from ..db.queries import (
    get_franchise_tags_for_team,
    get_active_tag_for_player,
    get_tag_history_for_player,
    count_active_tags_for_team,
    get_consecutive_tag_count,
    insert_franchise_tag,
    update_tag_status,
    get_top_n_cap_hits_at_position,
    get_player_contract_status,
    get_tag_by_id,
    get_all_tagged_players,
    count_position_tagged_players,
    get_league_state,
    get_active_contract,
    update_contract_status,
    get_player_for_contract,
    get_player_basic_info,
    mark_contract_as_franchise_tag,
    get_team_basic_info,
)
from ..db.transactions import log_transaction
from .contracts import offer_contract, release_player
from .satisfaction import adjust_satisfaction
from ..utils.constants import (
    FRANCHISE_TAGS_PER_TEAM,
    FRANCHISE_TAG_TOP_N,
    TRANSITION_TAG_TOP_N,
    CONSECUTIVE_TAG_SALARY_MULTIPLIER,
    FRANCHISE_TAG_SATISFACTION_PENALTY_1,
    FRANCHISE_TAG_SATISFACTION_PENALTY_2,
    FRANCHISE_TAG_SATISFACTION_PENALTY_3,
)


# Position-based minimum salary fallbacks (in millions)
# Used when insufficient market data exists
POSITION_MIN_SALARY = {
    'QB': 10_000_000, 'WR': 8_000_000, 'CB': 8_000_000,
    'DE': 8_000_000, 'LT': 8_000_000, 'DT': 7_000_000,
    'LB': 7_000_000, 'S': 6_000_000, 'RB': 5_000_000,
    'TE': 5_000_000, 'OL': 5_000_000, 'DL': 5_000_000,
    'K': 3_000_000, 'P': 2_000_000,
}


def calculate_tag_salary(
    position: str,
    tag_type: str,
    season_year: int,
    conn: sqlite3.Connection,
) -> int:
    """
    Calculate the franchise tag salary for a position and tag type.

    Franchise tag salary = average of top-N cap hits at position.
    - Exclusive tag: top-5 average
    - Transition tag: top-10 average

    This function calculates the BASE salary before any consecutive tag multiplier.
    The multiplier is applied in apply_franchise_tag().

    Args:
        position: Player position ('QB', 'WR', etc.)
        tag_type: 'exclusive' or 'transition'
        season_year: Season to calculate for (uses prior season cap hits)
        conn: Database connection

    Returns:
        Tag salary in dollars

    Raises:
        ValueError: On invalid tag_type or insufficient market data
    """
    if tag_type not in ('exclusive', 'transition'):
        raise ValueError(f"Invalid tag_type: {tag_type}. Must be 'exclusive' or 'transition'.")

    # Determine how many cap hits to average
    top_n = FRANCHISE_TAG_TOP_N if tag_type == 'exclusive' else TRANSITION_TAG_TOP_N

    # Get top-N cap hits at position from prior season
    prior_season = season_year - 1
    cap_hits = get_top_n_cap_hits_at_position(conn, position, prior_season, top_n)

    if len(cap_hits) >= top_n:
        # Sufficient data: average the top-N
        return int(sum(cap_hits) / len(cap_hits))
    elif len(cap_hits) > 0:
        # Some data but not enough: average what we have
        return int(sum(cap_hits) / len(cap_hits))
    else:
        # No market data: fall back to position minimum
        fallback = POSITION_MIN_SALARY.get(position, 5_000_000)
        return fallback


def apply_franchise_tag(
    player_id: int,
    team_id: int,
    tag_type: str,
    season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    Apply a franchise or transition tag to a player.

    Enforces:
    - Team has not already used their one franchise tag this offseason
    - Player's contract has expired or expires this season
    - Player is on the team's roster

    On success:
    - Calculates tag salary via calculate_tag_salary()
    - Creates a 1-year fully guaranteed contract via offer_contract()
    - Writes franchise_tag record
    - Fires satisfaction penalty via adjust_satisfaction()
    - Logs transaction

    Args:
        player_id: Player to tag
        team_id: Team applying tag
        tag_type: 'exclusive' or 'transition'
        season_year: Season tag applies to
        conn: Database connection

    Returns:
        Dict with player_id, tag_type, salary, cap_hit, satisfaction_delta,
        consecutive_tag_count, tag_id

    Raises:
        ValueError: On validation failures
    """
    # Validation 1: Check team tag limit
    active_tags = count_active_tags_for_team(conn, team_id, season_year)
    if active_tags >= FRANCHISE_TAGS_PER_TEAM:
        raise ValueError(
            f"Team {team_id} has already used their franchise tag for season {season_year}. "
            f"Only {FRANCHISE_TAGS_PER_TEAM} tag(s) allowed per team per season."
        )

    # Validation 2: Check player contract status
    status = get_player_contract_status(conn, player_id)
    if not status:
        raise ValueError(f"Player {player_id} not found.")

    if status['team_id'] != team_id:
        raise ValueError(
            f"Player {player_id} is not on team {team_id}'s roster. "
            f"Current team: {status['team_id']}"
        )

    if status['roster_status'] not in ('active', 'ir'):
        raise ValueError(
            f"Player {player_id} is not eligible for franchise tag. "
            f"Roster status: {status['roster_status']}"
        )

    # Player must have either no active contract or an expiring one
    # For simplicity, we allow tagging if there's no active contract (FA)
    # or if the contract exists (we'll terminate it and replace with tag)

    # Get player position for salary calculation
    player = get_player_basic_info(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found")
    position = player['position']

    # Calculate consecutive tag count
    consecutive_count = get_consecutive_tag_count(conn, player_id, season_year)
    if consecutive_count > 0:
        consecutive_count += 1
    else:
        consecutive_count = 1

    # Calculate base tag salary
    base_salary = calculate_tag_salary(position, tag_type, season_year, conn)

    # Apply consecutive tag multiplier
    multiplier = CONSECUTIVE_TAG_SALARY_MULTIPLIER ** (consecutive_count - 1)
    tag_salary = int(base_salary * multiplier)

    # If player has an active contract, release them first
    if status['contract_id']:
        # This will handle dead cap and recalculate cap space
        release_result = release_player(player_id, team_id, season_year, conn)

    # Create 1-year fully guaranteed franchise tag contract
    contract_result = offer_contract(
        player_id=player_id,
        team_id=team_id,
        years=1,
        aav=tag_salary,
        signing_bonus=0,
        guaranteed_money=tag_salary,  # Fully guaranteed
        roster_bonuses=None,
        escalators=None,
        void_years=0,
        conn=conn,
    )

    # Mark the contract as a franchise tag
    mark_contract_as_franchise_tag(conn, contract_result['contract_id'])

    # Insert franchise_tag record
    tag_id = insert_franchise_tag(
        conn, player_id, team_id, season_year, tag_type, tag_salary, consecutive_count
    )

    # Apply satisfaction penalty based on consecutive count
    if consecutive_count == 1:
        satisfaction_delta = FRANCHISE_TAG_SATISFACTION_PENALTY_1
    elif consecutive_count == 2:
        satisfaction_delta = FRANCHISE_TAG_SATISFACTION_PENALTY_2
    else:  # 3+
        satisfaction_delta = FRANCHISE_TAG_SATISFACTION_PENALTY_3

    adjust_satisfaction(
        player_id, satisfaction_delta, 'franchise_tag', conn
    )

    league = get_league_state(conn)
    current_week = league['current_week']

    # Log transaction
    log_transaction(
        conn,
        season_year,
        current_week,
        'franchise_tagged',
        team_id,
        player_id,
        f"{player['first_name']} {player['last_name']} ({position}) franchise tagged "
        f"({tag_type}) for ${tag_salary:,} (consecutive tag #{consecutive_count})",
        cap_impact=-tag_salary,
    )

    # Commit the transaction
    conn.commit()

    return {
        'player_id': player_id,
        'tag_type': tag_type,
        'salary': tag_salary,
        'cap_hit': tag_salary,  # Tag contracts are fully guaranteed, so cap_hit = salary
        'satisfaction_delta': satisfaction_delta,
        'consecutive_tag_count': consecutive_count,
        'tag_id': tag_id,
    }


def get_tagged_players(
    team_id: int,
    season_year: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Get all players currently under franchise or transition tag for a team.

    Read-only. Used by trade system to block or flag tagged player trades.

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        List of dicts with player_id, player_name, position, tag_type,
        salary, consecutive_count
    """
    tags = get_franchise_tags_for_team(conn, team_id, season_year, status='active')

    result = []
    for tag in tags:
        result.append({
            'player_id': tag['player_id'],
            'player_name': f"{tag['first_name']} {tag['last_name']}",
            'position': tag['position'],
            'tag_type': tag['tag_type'],
            'salary': tag['salary'],
            'consecutive_count': tag['consecutive_count'],
        })

    return result


def is_tagged(
    player_id: int,
    season_year: int,
    conn: sqlite3.Connection,
) -> bool:
    """
    Check if a player currently has an active franchise or transition tag.

    Read-only. The trade system calls this before processing any deal.

    Args:
        player_id: Player ID
        season_year: Season year
        conn: Database connection

    Returns:
        True if player has an active tag in the given season
    """
    tag = get_active_tag_for_player(conn, player_id, season_year)
    return tag is not None


def remove_franchise_tag(
    player_id: int,
    team_id: int,
    season_year: int,
    reason: str,
    conn: sqlite3.Connection,
) -> dict:
    """
    Remove a franchise tag from a player.

    Called when:
    - Player signs a long-term extension before the tag year begins (reason='signed_extension')
    - Tag is rescinded by the team (reason='rescinded')

    Releases the 1-year tag contract via release_player(), updates the
    franchise_tag record status, recalculates cap space, and logs the transaction.

    Args:
        player_id: Player ID
        team_id: Team ID
        season_year: Season year
        reason: 'signed_extension' or 'rescinded'
        conn: Database connection

    Returns:
        Dict with dead_cap (should be 0), new_cap_space, tag_status

    Raises:
        ValueError: If no active tag exists or invalid reason
    """
    if reason not in ('signed_extension', 'rescinded'):
        raise ValueError(f"Invalid reason: {reason}. Must be 'signed_extension' or 'rescinded'.")

    # Find active tag
    tag = get_active_tag_for_player(conn, player_id, season_year)
    if not tag:
        raise ValueError(
            f"No active franchise tag found for player {player_id} in season {season_year}."
        )

    if tag['team_id'] != team_id:
        raise ValueError(
            f"Tag mismatch: Player {player_id} is tagged by team {tag['team_id']}, "
            f"not team {team_id}."
        )

    # Get player info for logging
    player = get_player_basic_info(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found")

    # Release the tag contract
    # This should result in 0 dead cap since tag contracts are fully guaranteed
    # and we're removing pre-season
    release_result = release_player(player_id, team_id, season_year, conn)

    # Update tag status
    update_tag_status(conn, tag['id'], reason)

    # Recalculate cap space
    recalculate_cap_space(team_id, season_year, conn)

    # Get updated cap space
    team = get_team_basic_info(conn, team_id)
    if not team:
        raise ValueError(f"Team {team_id} not found")

    # Log transaction
    league = get_league_state(conn)
    current_week = league['current_week']

    log_transaction(
        conn,
        season_year,
        current_week,
        'franchise_tag_removed',
        team_id,
        player_id,
        f"{player['first_name']} {player['last_name']} ({player['position']}) "
        f"franchise tag removed ({reason})",
        cap_impact=tag['salary'],  # Cap space recovered
    )

    # Commit the transaction
    conn.commit()

    return {
        'dead_cap': release_result.get('dead_cap', 0),
        'new_cap_space': team['cap_space'],
        'tag_status': reason,
    }


def get_tag_history(
    player_id: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Get all franchise tag records for a player across all seasons.

    Read-only. Used by calculate_tag_salary() to determine consecutive tag
    count, and surfaced to UI as player history signal.

    Args:
        player_id: Player ID
        conn: Database connection

    Returns:
        List of dicts with season_year, tag_type, salary, status,
        consecutive_count, team_name
    """
    tags = get_tag_history_for_player(conn, player_id)

    result = []
    for tag in tags:
        # Get team name
        team = get_team_basic_info(conn, tag['team_id'])
        if not team:
            continue

        result.append({
            'season_year': tag['season_year'],
            'tag_type': tag['tag_type'],
            'salary': tag['salary'],
            'status': tag['status'],
            'consecutive_count': tag['consecutive_count'],
            'team_name': f"{team['city']} {team['nickname']}",
        })

    return result
