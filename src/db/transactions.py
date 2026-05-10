"""
Transaction logging utilities.

CRITICAL: Every roster or contract action MUST call log_transaction().
This creates an immutable audit trail for the franchise history.
"""

import sqlite3
from typing import Optional


def log_transaction(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    transaction_type: str,
    team_id: int,
    player_id: Optional[int],
    description: str,
    cap_impact: int = 0
) -> int:
    """
    Write a transaction to the immutable audit log.

    This function MUST be called for every roster or contract action:
    - Signing a player
    - Releasing a player
    - Trading a player
    - Drafting a player
    - IR placement/return
    - Waiver claims
    - Practice squad moves
    - Franchise tags
    - Retirements
    - Contract restructures

    Args:
        conn: Database connection
        season_year: Current season year
        week_number: Current week (0 = offseason)
        transaction_type: One of: 'signed' | 'released' | 'traded' | 'drafted'
                         | 'ir_placed' | 'ir_returned' | 'waiver_claimed'
                         | 'practice_squad_signed' | 'practice_squad_released'
                         | 'franchise_tagged' | 'retired' | 'restructured'
        team_id: Team ID performing the transaction
        player_id: Player ID (None for trades involving only picks)
        description: Human-readable log line (shown in UI transaction ticker)
        cap_impact: Dollar amount of cap impact (positive = cap hit, negative = cap savings)

    Returns:
        Transaction log ID

    Usage:
        with conn:
            # Sign a free agent
            log_transaction(
                conn,
                season_year=2024,
                week_number=0,
                transaction_type='signed',
                team_id=team_id,
                player_id=player_id,
                description=f"Signed QB John Smith to a 3-year, $45M contract",
                cap_impact=15000000  # Year 1 cap hit
            )

            # Release a player
            log_transaction(
                conn,
                season_year=2024,
                week_number=0,
                transaction_type='released',
                team_id=team_id,
                player_id=player_id,
                description=f"Released RB Mike Jones",
                cap_impact=2500000  # Dead cap hit
            )
    """
    cursor = conn.execute("""
        INSERT INTO transaction_log
        (season_year, week_number, transaction_type, team_id, player_id, description, cap_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (season_year, week_number, transaction_type, team_id, player_id, description, cap_impact))

    return cursor.lastrowid


def get_team_transactions(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: Optional[int] = None,
    limit: int = 50
) -> list[sqlite3.Row]:
    """
    Retrieve transaction history for a team.

    Args:
        conn: Database connection
        team_id: Team ID
        season_year: Filter by season (None = all seasons)
        limit: Max number of transactions to return (most recent first)

    Returns:
        List of transaction log rows

    Usage:
        # Get all transactions for current season
        recent = get_team_transactions(conn, team_id, season_year=2024, limit=20)
        for txn in recent:
            print(f"Week {txn['week_number']}: {txn['description']}")
    """
    if season_year is not None:
        return conn.execute("""
            SELECT * FROM transaction_log
            WHERE team_id = ? AND season_year = ?
            ORDER BY season_year DESC, week_number DESC, id DESC
            LIMIT ?
        """, (team_id, season_year, limit)).fetchall()
    else:
        return conn.execute("""
            SELECT * FROM transaction_log
            WHERE team_id = ?
            ORDER BY season_year DESC, week_number DESC, id DESC
            LIMIT ?
        """, (team_id, limit)).fetchall()


def get_player_transaction_history(
    conn: sqlite3.Connection,
    player_id: int
) -> list[sqlite3.Row]:
    """
    Get full transaction history for a specific player.

    Useful for player career timeline display.

    Args:
        conn: Database connection
        player_id: Player ID

    Returns:
        List of transaction log rows (chronological order)

    Usage:
        history = get_player_transaction_history(conn, player_id)
        print(f"Career timeline for {player['first_name']} {player['last_name']}:")
        for txn in history:
            print(f"  {txn['season_year']} Week {txn['week_number']}: {txn['description']}")
    """
    return conn.execute("""
        SELECT * FROM transaction_log
        WHERE player_id = ?
        ORDER BY season_year ASC, week_number ASC, id ASC
    """, (player_id,)).fetchall()


def get_recent_league_transactions(
    conn: sqlite3.Connection,
    limit: int = 100,
    transaction_types: Optional[list[str]] = None
) -> list[sqlite3.Row]:
    """
    Get recent transactions across the entire league.

    Useful for "league news feed" or "transaction wire" UI displays.

    Args:
        conn: Database connection
        limit: Max number of transactions to return
        transaction_types: Filter by types (None = all types)
                          e.g., ['signed', 'traded', 'released']

    Returns:
        List of transaction log rows with team info joined

    Usage:
        # Get all recent signings and trades
        wire = get_recent_league_transactions(
            conn,
            limit=50,
            transaction_types=['signed', 'traded']
        )
        for txn in wire:
            print(f"{txn['team_abbr']}: {txn['description']}")
    """
    if transaction_types:
        placeholders = ','.join('?' * len(transaction_types))
        query = f"""
            SELECT
                tl.*,
                t.abbreviation as team_abbr,
                t.city as team_city,
                t.nickname as team_nickname
            FROM transaction_log tl
            JOIN team t ON t.id = tl.team_id
            WHERE tl.transaction_type IN ({placeholders})
            ORDER BY tl.season_year DESC, tl.week_number DESC, tl.id DESC
            LIMIT ?
        """
        params = tuple(transaction_types) + (limit,)
        return conn.execute(query, params).fetchall()
    else:
        return conn.execute("""
            SELECT
                tl.*,
                t.abbreviation as team_abbr,
                t.city as team_city,
                t.nickname as team_nickname
            FROM transaction_log tl
            JOIN team t ON t.id = tl.team_id
            ORDER BY tl.season_year DESC, tl.week_number DESC, tl.id DESC
            LIMIT ?
        """, (limit,)).fetchall()


def get_week_transactions(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int
) -> list[sqlite3.Row]:
    """
    Get all transactions that occurred in a specific week.

    Args:
        conn: Database connection
        season_year: Season year
        week_number: Week number (0 = offseason)

    Returns:
        List of transaction log rows with team info

    Usage:
        # Get all transactions from Week 1 of 2024 season
        week1_moves = get_week_transactions(conn, 2024, 1)
        print(f"{len(week1_moves)} transactions occurred in Week 1")
    """
    return conn.execute("""
        SELECT
            tl.*,
            t.abbreviation as team_abbr,
            t.city as team_city,
            t.nickname as team_nickname
        FROM transaction_log tl
        JOIN team t ON t.id = tl.team_id
        WHERE tl.season_year = ? AND tl.week_number = ?
        ORDER BY tl.id ASC
    """, (season_year, week_number)).fetchall()


def get_transaction_stats_by_type(
    conn: sqlite3.Connection,
    season_year: Optional[int] = None
) -> list[sqlite3.Row]:
    """
    Get counts of transactions by type.

    Useful for analytics and debugging.

    Args:
        conn: Database connection
        season_year: Filter by season (None = all time)

    Returns:
        List of rows with transaction_type and count

    Usage:
        stats = get_transaction_stats_by_type(conn, season_year=2024)
        for row in stats:
            print(f"{row['transaction_type']}: {row['count']} transactions")
    """
    if season_year is not None:
        return conn.execute("""
            SELECT transaction_type, COUNT(*) as count
            FROM transaction_log
            WHERE season_year = ?
            GROUP BY transaction_type
            ORDER BY count DESC
        """, (season_year,)).fetchall()
    else:
        return conn.execute("""
            SELECT transaction_type, COUNT(*) as count
            FROM transaction_log
            GROUP BY transaction_type
            ORDER BY count DESC
        """).fetchall()


def get_total_cap_impact_by_team(
    conn: sqlite3.Connection,
    season_year: int
) -> list[sqlite3.Row]:
    """
    Get total cap impact of all transactions by team for a season.

    Useful for seeing which teams were most active in free agency or trades.

    Args:
        conn: Database connection
        season_year: Season year

    Returns:
        List of rows with team_id, team_abbr, total_cap_impact

    Usage:
        impact = get_total_cap_impact_by_team(conn, 2024)
        for row in impact:
            print(f"{row['team_abbr']}: ${row['total_cap_impact']:,} in transactions")
    """
    return conn.execute("""
        SELECT
            t.id as team_id,
            t.abbreviation as team_abbr,
            t.city as team_city,
            t.nickname as team_nickname,
            COALESCE(SUM(tl.cap_impact), 0) as total_cap_impact
        FROM team t
        LEFT JOIN transaction_log tl ON tl.team_id = t.id AND tl.season_year = ?
        GROUP BY t.id, t.abbreviation, t.city, t.nickname
        ORDER BY total_cap_impact DESC
    """, (season_year,)).fetchall()
