"""
Database connection and utility functions.

Provides connection management and basic CRUD helpers for the Football Simulator database.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def get_connection(save_path: str) -> sqlite3.Connection:
    """
    Create and configure a database connection.

    Args:
        save_path: Path to the .db file (relative or absolute)

    Returns:
        Configured SQLite connection with foreign keys enabled and Row factory set

    Usage:
        conn = get_connection("saves/my_franchise.db")
        # ... use connection ...
        conn.close()

        # Or with context manager:
        with get_connection("saves/my_franchise.db") as conn:
            # auto-closes on exit
    """
    conn = sqlite3.connect(save_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # Allows dict-style column access

    # Ensure tables exist (for migrating existing saves)
    ensure_satisfaction_tables(conn)
    ensure_fa_tables(conn)
    ensure_franchise_tag_table(conn)
    ensure_scouting_tables(conn)
    ensure_draft_tables(conn)
    ensure_offseason_state_table(conn)

    return conn


def init_database(save_path: str, schema_path: str = "src/db/schema.sql") -> None:
    """
    Initialize a new database from the schema file.

    Args:
        save_path: Path where the new .db file will be created
        schema_path: Path to the schema.sql file (default: src/db/schema.sql)

    Raises:
        FileNotFoundError: If schema file doesn't exist
        sqlite3.Error: If database creation fails

    Usage:
        init_database("saves/my_franchise.db")
    """
    schema_file = Path(schema_path)
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    # Create parent directory if it doesn't exist
    save_file = Path(save_path)
    save_file.parent.mkdir(parents=True, exist_ok=True)

    # Read and execute schema
    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    conn = get_connection(save_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def execute_query(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """
    Execute a SELECT query and return all results.

    Args:
        conn: Database connection
        query: SQL query string (use ? for parameters)
        params: Query parameters tuple

    Returns:
        List of Row objects (access columns by name or index)

    Usage:
        rows = execute_query(conn, "SELECT * FROM team WHERE id = ?", (team_id,))
        for row in rows:
            print(row['city'], row['nickname'])
    """
    cursor = conn.execute(query, params)
    return cursor.fetchall()


def execute_one(conn: sqlite3.Connection, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """
    Execute a SELECT query and return the first result.

    Args:
        conn: Database connection
        query: SQL query string (use ? for parameters)
        params: Query parameters tuple

    Returns:
        Single Row object or None if no results

    Usage:
        team = execute_one(conn, "SELECT * FROM team WHERE id = ?", (team_id,))
        if team:
            print(team['city'], team['nickname'])
    """
    cursor = conn.execute(query, params)
    return cursor.fetchone()


def execute_write(conn: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    """
    Execute an INSERT, UPDATE, or DELETE query.

    NOTE: Does NOT auto-commit. Wrap in a transaction context or call conn.commit().

    Args:
        conn: Database connection
        query: SQL query string (use ? for parameters)
        params: Query parameters tuple

    Returns:
        Last inserted row ID (for INSERT) or number of affected rows

    Usage:
        with conn:  # auto-commits on success, rolls back on exception
            player_id = execute_write(conn,
                "INSERT INTO player (first_name, last_name, ...) VALUES (?, ?, ...)",
                (first_name, last_name, ...))
    """
    cursor = conn.execute(query, params)
    return cursor.lastrowid if cursor.lastrowid else cursor.rowcount


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        conn: Database connection
        table_name: Name of the table to check

    Returns:
        True if table exists, False otherwise
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def get_league_state(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """
    Get the current league state (season, week, phase).

    Args:
        conn: Database connection

    Returns:
        League row with current_season, current_week, current_phase, etc.
        None if league not initialized

    Usage:
        league = get_league_state(conn)
        print(f"Season {league['current_season']}, Week {league['current_week']}")
    """
    return execute_one(conn, "SELECT * FROM league WHERE id = 1")


def get_team_by_id(conn: sqlite3.Connection, team_id: int) -> Optional[sqlite3.Row]:
    """
    Retrieve a team by ID.

    Args:
        conn: Database connection
        team_id: Team ID

    Returns:
        Team row or None if not found
    """
    return execute_one(conn, "SELECT * FROM team WHERE id = ?", (team_id,))


def get_team_by_abbreviation(conn: sqlite3.Connection, abbr: str) -> Optional[sqlite3.Row]:
    """
    Retrieve a team by abbreviation (e.g., 'CHI', 'DAL').

    Args:
        conn: Database connection
        abbr: Team abbreviation (case-insensitive)

    Returns:
        Team row or None if not found
    """
    return execute_one(
        conn,
        "SELECT * FROM team WHERE UPPER(abbreviation) = UPPER(?)",
        (abbr,)
    )


def get_roster(conn: sqlite3.Connection, team_id: int,
               roster_status: str = 'active') -> list[sqlite3.Row]:
    """
    Get all players on a team's roster.

    Args:
        conn: Database connection
        team_id: Team ID
        roster_status: Filter by status (default: 'active')
                      Use 'all' to return all players regardless of status

    Returns:
        List of player rows

    Usage:
        active_roster = get_roster(conn, team_id)
        all_players = get_roster(conn, team_id, roster_status='all')
    """
    if roster_status == 'all':
        return execute_query(
            conn,
            "SELECT * FROM player WHERE team_id = ? ORDER BY position, last_name",
            (team_id,)
        )
    else:
        return execute_query(
            conn,
            "SELECT * FROM player WHERE team_id = ? AND roster_status = ? ORDER BY position, last_name",
            (team_id, roster_status)
        )


def ensure_satisfaction_tables(conn: sqlite3.Connection) -> None:
    """
    Create satisfaction-related tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the satisfaction system was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS satisfaction_event (
            id              INTEGER PRIMARY KEY,
            player_id       INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            delta           INTEGER NOT NULL,
            reason          TEXT NOT NULL,
            new_score       INTEGER NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (player_id) REFERENCES player(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_satisfaction_event_player
        ON satisfaction_event(player_id, season_year)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_event (
            id              INTEGER PRIMARY KEY,
            player_id       INTEGER NOT NULL,
            team_id         INTEGER NOT NULL,
            event_type      TEXT NOT NULL,
            season_year     INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            resolved        INTEGER NOT NULL DEFAULT 0,
            metadata_json   TEXT,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_event_player
        ON player_event(player_id, season_year)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_event_team
        ON player_event(team_id, season_year)
    """)
    conn.commit()


def ensure_fa_tables(conn: sqlite3.Connection) -> None:
    """
    Create free-agency-related tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the free agency system was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_agent_offer (
            id              INTEGER PRIMARY KEY,
            player_id       INTEGER NOT NULL,
            offering_team_id INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            round_number    INTEGER NOT NULL DEFAULT 1,
            years_offered   INTEGER NOT NULL,
            total_value     INTEGER NOT NULL,
            signing_bonus   INTEGER NOT NULL DEFAULT 0,
            guaranteed_money INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL,
            player_tier     INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (offering_team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fa_interest (
            id                      INTEGER PRIMARY KEY,
            player_id               INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            season_year             INTEGER NOT NULL,
            preference_score        REAL NOT NULL,
            tier                    INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (team_id)   REFERENCES team(id),
            UNIQUE(player_id, team_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fa_interest_player
        ON fa_interest(player_id, season_year)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fa_interest_team
        ON fa_interest(team_id, season_year)
    """)
    conn.commit()


def ensure_franchise_tag_table(conn: sqlite3.Connection) -> None:
    """
    Create franchise_tag table if it doesn't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the franchise tag system was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS franchise_tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES player(id),
            team_id INTEGER NOT NULL REFERENCES team(id),
            season_year INTEGER NOT NULL,
            tag_type TEXT NOT NULL CHECK(tag_type IN ('exclusive', 'transition')),
            salary INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'signed_extension', 'rescinded')),
            consecutive_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(team_id, season_year, status)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_franchise_tag_player
        ON franchise_tag(player_id, season_year)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_franchise_tag_team
        ON franchise_tag(team_id, season_year, status)
    """)
    conn.commit()


def _safe_add_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    """Add a column to a table, ignoring if it already exists."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # column already exists


def ensure_scouting_tables(conn: sqlite3.Connection) -> None:
    """
    Create scouting-related tables and columns if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the scouting system was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scouting_flag (
            id              INTEGER PRIMARY KEY,
            prospect_id     INTEGER NOT NULL,
            scout_id        INTEGER NOT NULL,
            team_id         INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            flag_type       TEXT NOT NULL CHECK(flag_type IN ('green','caution','red')),
            flag_text       TEXT NOT NULL,
            is_true_flag    INTEGER NOT NULL DEFAULT 1,
            report_week     INTEGER NOT NULL,
            FOREIGN KEY (prospect_id) REFERENCES prospect(id),
            FOREIGN KEY (scout_id) REFERENCES staff(id),
            FOREIGN KEY (team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scouting_flag_prospect
        ON scouting_flag(prospect_id, team_id, season_year)
    """)

    # Phase 3B: add phase and notes columns to scouted_rating
    _safe_add_column(conn, 'scouted_rating', 'phase', 'TEXT')
    _safe_add_column(conn, 'scouted_rating', 'notes', 'TEXT')

    # Phase 3B: add narrative column to mock_draft
    _safe_add_column(conn, 'mock_draft', 'narrative', 'TEXT')

    # Phase 3B: combine_event table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS combine_event (
            id              INTEGER PRIMARY KEY,
            prospect_id     INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            event_type      TEXT NOT NULL,
            narrative       TEXT NOT NULL,
            grade_impact    INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (prospect_id) REFERENCES prospect(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_combine_event_prospect
        ON combine_event(prospect_id, season_year)
    """)

    # Phase 3B: competitor_intel table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS competitor_intel (
            id              INTEGER PRIMARY KEY,
            team_id         INTEGER NOT NULL,
            prospect_id     INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            phase           TEXT NOT NULL,
            signal_type     TEXT NOT NULL,
            narrative       TEXT NOT NULL,
            is_accurate     INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (team_id) REFERENCES team(id),
            FOREIGN KEY (prospect_id) REFERENCES prospect(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_competitor_intel_prospect
        ON competitor_intel(prospect_id, season_year)
    """)

    # Phase 3B: draft_board table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS draft_board (
            id              INTEGER PRIMARY KEY,
            team_id         INTEGER NOT NULL,
            prospect_id     INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            board_rank      REAL NOT NULL,
            board_override  INTEGER,
            phase_trend     TEXT NOT NULL DEFAULT 'stable'
                CHECK(phase_trend IN ('improving','stable','declining')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES team(id),
            FOREIGN KEY (prospect_id) REFERENCES prospect(id),
            UNIQUE(team_id, season_year, prospect_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_board_team
        ON draft_board(team_id, season_year)
    """)

    conn.commit()


def ensure_draft_tables(conn: sqlite3.Connection) -> None:
    """
    Create draft_state table if it doesn't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the draft system was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS draft_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER NOT NULL,
            pick_number_overall INTEGER NOT NULL,
            round INTEGER NOT NULL,
            pick_in_round INTEGER NOT NULL,
            team_id INTEGER NOT NULL REFERENCES team(id),
            original_team_id INTEGER NOT NULL REFERENCES team(id),
            prospect_id INTEGER REFERENCES prospect(id),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','used','traded')),
            war_room_reaction TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(season_year, pick_number_overall)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_state_season
        ON draft_state(season_year, status)
    """)
    conn.commit()


def ensure_offseason_state_table(conn: sqlite3.Connection) -> None:
    """
    Create offseason_state table if it doesn't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the offseason orchestrator was added.

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS offseason_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL REFERENCES team(id),
            season_year INTEGER NOT NULL,
            current_phase TEXT NOT NULL CHECK(current_phase IN (
                'end_of_season_review', 'staff_evaluation', 'franchise_tag_window',
                'scouting_early', 'combine', 'free_agency', 'predraft',
                'draft', 'training_camp', 'season_ready'
            )),
            end_of_season_review_complete INTEGER NOT NULL DEFAULT 0,
            staff_evaluation_complete INTEGER NOT NULL DEFAULT 0,
            franchise_tag_window_complete INTEGER NOT NULL DEFAULT 0,
            scouting_early_complete INTEGER NOT NULL DEFAULT 0,
            combine_complete INTEGER NOT NULL DEFAULT 0,
            free_agency_complete INTEGER NOT NULL DEFAULT 0,
            predraft_complete INTEGER NOT NULL DEFAULT 0,
            draft_complete INTEGER NOT NULL DEFAULT 0,
            training_camp_complete INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(team_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_offseason_state_team
        ON offseason_state(team_id, season_year)
    """)
    conn.commit()


def get_player_by_id(conn: sqlite3.Connection, player_id: int) -> Optional[sqlite3.Row]:
    """
    Retrieve a player by ID.

    Args:
        conn: Database connection
        player_id: Player ID

    Returns:
        Player row or None if not found
    """
    return execute_one(conn, "SELECT * FROM player WHERE id = ?", (player_id,))
