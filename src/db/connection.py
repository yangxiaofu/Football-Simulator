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
    conn = sqlite3.connect(save_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # Allows dict-style column access

    # Ensure tables exist (for migrating existing saves)
    ensure_satisfaction_tables(conn)
    ensure_fa_tables(conn)
    ensure_franchise_tag_table(conn)
    ensure_scouting_tables(conn)
    ensure_draft_tables(conn)
    ensure_offseason_state_table(conn)
    ensure_coach_tables(conn)
    ensure_team_phase_column(conn)
    ensure_owner_sentiment_tables(conn)
    ensure_coach_legacy_tables(conn)
    ensure_league_record_table(conn)
    ensure_press_tables(conn)
    ensure_tier2_press_tables(conn)
    ensure_narrative_moment_table(conn)
    ensure_in_season_stats_tables(conn)
    ensure_depth_chart_table(conn)
    ensure_player_watchlist_column(conn)

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

    # Phase 5 P8 — add reason_code column to satisfaction_event
    try:
        conn.execute("ALTER TABLE satisfaction_event ADD COLUMN reason_code TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Backfill existing rows so the explainer never sees NULL reason_code
    conn.execute(
        "UPDATE satisfaction_event SET reason_code = 'legacy_unknown' WHERE reason_code IS NULL"
    )
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

    # Phase 5 P7 — add outcome columns idempotently
    for col_def in [
        "ALTER TABLE fa_interest ADD COLUMN outcome_narrative TEXT",
        "ALTER TABLE fa_interest ADD COLUMN reason_code TEXT",
    ]:
        try:
            conn.execute(col_def)
        except Exception:
            pass  # column already exists
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


def ensure_coach_tables(conn: sqlite3.Connection) -> None:
    """
    Create coach identity tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the coach identity system was added (Phase 4).

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_career (
            id                    INTEGER PRIMARY KEY,
            first_name            TEXT NOT NULL,
            last_name             TEXT NOT NULL,
            age                   INTEGER NOT NULL,
            personality_archetype TEXT NOT NULL,
            career_start_year     INTEGER NOT NULL,
            current_team_id       INTEGER,
            is_player             INTEGER NOT NULL DEFAULT 0,
            is_active             INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (current_team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_career_active
        ON coach_career(is_active, is_player)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_career_team
        ON coach_career(current_team_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_tenure (
            id              INTEGER PRIMARY KEY,
            coach_id        INTEGER NOT NULL,
            team_id         INTEGER NOT NULL,
            start_year      INTEGER NOT NULL,
            end_year        INTEGER,
            end_reason      TEXT,
            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            FOREIGN KEY (team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_tenure_coach
        ON coach_tenure(coach_id, end_year)
    """)

    # Add coach_id column to legacy_score and hall_of_fame for existing saves
    _safe_add_column(conn, 'legacy_score', 'coach_id', 'INTEGER REFERENCES coach_career(id)')
    _safe_add_column(conn, 'hall_of_fame', 'coach_id', 'INTEGER REFERENCES coach_career(id)')

    conn.commit()


def ensure_team_phase_column(conn: sqlite3.Connection) -> None:
    """Add team_phase column to team table if it doesn't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the AI GM behavior system was added (Phase 4).

    Args:
        conn: Database connection
    """
    _safe_add_column(conn, 'team', 'team_phase', "TEXT NOT NULL DEFAULT 'bridge'")
    conn.commit()


def ensure_player_watchlist_column(conn: sqlite3.Connection) -> None:
    """Add is_watchlisted column to player for the GUI FA watchlist (Phase 6 P7b).

    Safe to call multiple times. Forward-migrates saves created before the
    watchlist flag existed.

    Args:
        conn: Database connection
    """
    _safe_add_column(conn, 'player', 'is_watchlisted', "INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def ensure_owner_sentiment_tables(conn: sqlite3.Connection) -> None:
    """
    Create owner_sentiment and coach_job_offer tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the owner sentiment system was added (Phase 4 Prompt #4).

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS owner_sentiment (
            id                      INTEGER PRIMARY KEY,
            team_id                 INTEGER NOT NULL,
            season_year             INTEGER NOT NULL,
            sentiment_score         INTEGER NOT NULL DEFAULT 70,
            preseason_expectation   TEXT,
            hot_seat_tier           TEXT NOT NULL DEFAULT 'stable',

            -- Driver breakdowns
            wins_vs_expectation     INTEGER NOT NULL DEFAULT 0,
            cap_management_score    INTEGER NOT NULL DEFAULT 0,
            star_holdout_penalty    INTEGER NOT NULL DEFAULT 0,
            playoff_bonus           INTEGER NOT NULL DEFAULT 0,
            championship_bonus      INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(team_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_owner_sentiment_team
        ON owner_sentiment(team_id, season_year)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_job_offer (
            id                  INTEGER PRIMARY KEY,
            coach_id            INTEGER NOT NULL,
            team_id             INTEGER NOT NULL,
            season_year         INTEGER NOT NULL,
            week_offered        INTEGER NOT NULL,
            offer_quality_tier  TEXT NOT NULL,
            is_accepted         INTEGER NOT NULL DEFAULT 0,
            is_declined         INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            FOREIGN KEY (team_id) REFERENCES team(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_job_offer_coach
        ON coach_job_offer(coach_id)
    """)

    # Add presser_delta column to owner_sentiment (Phase 4 Prompt #5)
    try:
        conn.execute("""
            ALTER TABLE owner_sentiment
            ADD COLUMN presser_delta INTEGER NOT NULL DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Phase 5 P8 — add sentiment reason columns idempotently
    for col_def in [
        "ALTER TABLE owner_sentiment ADD COLUMN reason_code TEXT",
        "ALTER TABLE owner_sentiment ADD COLUMN reason_detail TEXT",
    ]:
        try:
            conn.execute(col_def)
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()

    # Backfill existing rows so the explainer never sees NULL reason_code
    conn.execute(
        "UPDATE owner_sentiment SET reason_code = 'legacy_unknown' WHERE reason_code IS NULL"
    )
    conn.commit()


def ensure_coach_legacy_tables(conn: sqlite3.Connection) -> None:
    """Create coach legacy expansion tables (Phase 4 Prompt #7)."""
    # Create coach_legacy_score table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_legacy_score (
            id                              INTEGER PRIMARY KEY,
            coach_id                        INTEGER NOT NULL,
            season_year                     INTEGER NOT NULL,
            team_id                         INTEGER NOT NULL,

            championships                   INTEGER NOT NULL DEFAULT 0,
            conference_titles               INTEGER NOT NULL DEFAULT 0,
            season_win_pct                  REAL NOT NULL DEFAULT 0,
            stars_developed                 INTEGER NOT NULL DEFAULT 0,
            cap_efficiency_score            INTEGER NOT NULL DEFAULT 50,
            media_legacy_score              INTEGER NOT NULL DEFAULT 50,

            era_difficulty_multiplier       REAL NOT NULL DEFAULT 1.0,
            starting_condition_multiplier   REAL NOT NULL DEFAULT 1.0,

            season_legacy_score             INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(coach_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_legacy_coach
        ON coach_legacy_score(coach_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_legacy_season
        ON coach_legacy_score(season_year)
    """)

    # Create coach_narrative_beat table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_narrative_beat (
            id              INTEGER PRIMARY KEY,
            coach_id        INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            beat_type       TEXT NOT NULL,
            text            TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            UNIQUE(coach_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_coach_narrative_coach
        ON coach_narrative_beat(coach_id)
    """)

    # Create peer_ranking_snapshot table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS peer_ranking_snapshot (
            id                  INTEGER PRIMARY KEY,
            coach_id            INTEGER NOT NULL,
            season_year         INTEGER NOT NULL,
            career_legacy_total INTEGER NOT NULL,
            active_rank         INTEGER NOT NULL,
            all_time_rank       INTEGER NOT NULL,
            n_active            INTEGER NOT NULL,
            n_all_time          INTEGER NOT NULL,
            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            UNIQUE(coach_id, season_year)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_peer_ranking_season
        ON peer_ranking_snapshot(season_year, active_rank)
    """)

    # Add starting_condition_multiplier to coach_tenure (safe ALTER)
    try:
        conn.execute("""
            ALTER TABLE coach_tenure
            ADD COLUMN starting_condition_multiplier REAL NOT NULL DEFAULT 1.0
        """)
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()


def ensure_league_record_table(conn: sqlite3.Connection) -> None:
    """Create league_record table and extend season table (Phase 4 Prompt #8)."""
    # Create league_record table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS league_record (
            id                  INTEGER PRIMARY KEY,
            category            TEXT NOT NULL,
            scope               TEXT NOT NULL,
            record_value        REAL NOT NULL,
            holder_player_id    INTEGER,
            holder_team_id      INTEGER,
            holder_coach_id     INTEGER,
            holder_name         TEXT NOT NULL,
            season_year         INTEGER,
            week_number         INTEGER,
            set_at              TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (holder_player_id) REFERENCES player(id),
            FOREIGN KEY (holder_team_id) REFERENCES team(id),
            FOREIGN KEY (holder_coach_id) REFERENCES coach_career(id),
            UNIQUE(category, scope)
        )
    """)

    # Create index
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_league_record_category
        ON league_record(category, scope)
    """)

    # Alter season table (5 new columns, safe with DEFAULT/NULL)
    try:
        conn.execute("""
            ALTER TABLE season
            ADD COLUMN runner_up_team_id INTEGER REFERENCES team(id)
        """)
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("""
            ALTER TABLE season
            ADD COLUMN championship_home_score INTEGER
        """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            ALTER TABLE season
            ADD COLUMN championship_away_score INTEGER
        """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            ALTER TABLE season
            ADD COLUMN championship_mvp_player_id INTEGER REFERENCES player(id)
        """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            ALTER TABLE season
            ADD COLUMN championship_coach_id INTEGER REFERENCES coach_career(id)
        """)
    except sqlite3.OperationalError:
        pass

    conn.commit()


def ensure_press_tables(conn: sqlite3.Connection) -> None:
    """
    Create press_event table and add press_autopilot_default column to coach_career.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the Tier 1 press conference system was added (Phase 4 Prompt #5).

    Args:
        conn: Database connection
    """
    # Create press_event table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS press_event (
            id                      INTEGER PRIMARY KEY,
            season_year             INTEGER NOT NULL,
            week_number             INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            coach_id                INTEGER NOT NULL,
            context_type            TEXT NOT NULL,
            question_template_id    TEXT NOT NULL,
            selected_response       TEXT,
            autopilot_used          INTEGER NOT NULL DEFAULT 0,
            delta_owner             INTEGER NOT NULL DEFAULT 0,
            delta_fan               INTEGER NOT NULL DEFAULT 0,
            delta_locker_room       INTEGER NOT NULL DEFAULT 0,
            resolved_at             TEXT,
            created_at              TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES team(id),
            FOREIGN KEY (coach_id) REFERENCES coach_career(id),
            UNIQUE(season_year, week_number, team_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_press_event_team
        ON press_event(team_id, season_year)
    """)

    # Add press_autopilot_default column to coach_career
    try:
        conn.execute("""
            ALTER TABLE coach_career
            ADD COLUMN press_autopilot_default TEXT
        """)
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Phase 5 P9: add template_id for LRU anti-repetition guard
    try:
        conn.execute("ALTER TABLE press_event ADD COLUMN template_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()


def ensure_recap_column(conn: sqlite3.Connection) -> None:
    """Idempotently add recap_shown column to season table (Phase 5 P10)."""
    try:
        conn.execute("ALTER TABLE season ADD COLUMN recap_shown INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists


def ensure_tier2_press_tables(conn: sqlite3.Connection) -> None:
    """
    Create Tier 2 dramatic press conference tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the Tier 2 press conference system was added (Phase 4 Prompt #6).

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tier2_press_event (
            id                  INTEGER PRIMARY KEY,
            season_year         INTEGER NOT NULL,
            week_number         INTEGER NOT NULL,
            team_id             INTEGER NOT NULL,
            coach_id            INTEGER NOT NULL,
            trigger_type        TEXT NOT NULL,
            template_id         TEXT NOT NULL,
            num_questions       INTEGER NOT NULL,
            resolved_at         TEXT,
            created_at          TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES team(id),
            FOREIGN KEY (coach_id) REFERENCES coach_career(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tier2_press_event_team
        ON tier2_press_event(team_id, season_year)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tier2_press_response (
            id                  INTEGER PRIMARY KEY,
            event_id            INTEGER NOT NULL,
            question_index      INTEGER NOT NULL,
            question_text       TEXT NOT NULL,
            selected_response   TEXT,
            delta_owner         INTEGER NOT NULL DEFAULT 0,
            delta_fan           INTEGER NOT NULL DEFAULT 0,
            delta_locker_room   INTEGER NOT NULL DEFAULT 0,
            resolved_at         TEXT,
            FOREIGN KEY (event_id) REFERENCES tier2_press_event(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tier2_press_response_event
        ON tier2_press_response(event_id)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tier2_trigger_guard (
            id              INTEGER PRIMARY KEY,
            team_id         INTEGER NOT NULL,
            season_year     INTEGER NOT NULL,
            trigger_type    TEXT NOT NULL,
            guard_key       TEXT NOT NULL,
            fired_week      INTEGER NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(team_id, season_year, trigger_type, guard_key)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tier2_trigger_guard_team
        ON tier2_trigger_guard(team_id, season_year)
    """)

    conn.commit()


def ensure_narrative_moment_table(conn: sqlite3.Connection) -> None:
    """
    Create narrative_moment_shown table for Prompt #9.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the display layer was added (Phase 4 Prompt #9).

    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS narrative_moment_shown (
            coach_id        INTEGER NOT NULL,
            moment_type     TEXT NOT NULL,
            shown_season    INTEGER NOT NULL,
            PRIMARY KEY (coach_id, moment_type),
            FOREIGN KEY (coach_id) REFERENCES coach_career(id)
        )
    """)
    conn.commit()


def ensure_in_season_stats_tables(conn: sqlite3.Connection) -> None:
    """
    Create weekly stats cache tables if they don't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the weekly stats system was added (Phase 5).

    Creates 5 tables:
    - player_week_stats: per-player per-week snapshot
    - player_season_running: running season totals
    - team_week_stats: per-team per-week snapshot
    - team_season_running: running team totals
    - weekly_award: Stars of the Week awards

    Args:
        conn: Database connection
    """
    # player_week_stats
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_week_stats (
            id                      INTEGER PRIMARY KEY,
            season_year             INTEGER NOT NULL,
            week_number             INTEGER NOT NULL,
            player_id               INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            is_playoff              INTEGER NOT NULL DEFAULT 0,
            pass_attempts           INTEGER NOT NULL DEFAULT 0,
            completions             INTEGER NOT NULL DEFAULT 0,
            pass_yards              INTEGER NOT NULL DEFAULT 0,
            pass_tds                INTEGER NOT NULL DEFAULT 0,
            interceptions_thrown    INTEGER NOT NULL DEFAULT 0,
            sacks_taken             INTEGER NOT NULL DEFAULT 0,
            carries                 INTEGER NOT NULL DEFAULT 0,
            rush_yards              INTEGER NOT NULL DEFAULT 0,
            rush_tds                INTEGER NOT NULL DEFAULT 0,
            fumbles                 INTEGER NOT NULL DEFAULT 0,
            targets                 INTEGER NOT NULL DEFAULT 0,
            receptions              INTEGER NOT NULL DEFAULT 0,
            rec_yards               INTEGER NOT NULL DEFAULT 0,
            rec_tds                 INTEGER NOT NULL DEFAULT 0,
            tackles                 INTEGER NOT NULL DEFAULT 0,
            sacks                   REAL NOT NULL DEFAULT 0,
            interceptions           INTEGER NOT NULL DEFAULT 0,
            pass_deflections        INTEGER NOT NULL DEFAULT 0,
            forced_fumbles          INTEGER NOT NULL DEFAULT 0,
            fg_attempts             INTEGER NOT NULL DEFAULT 0,
            fg_made                 INTEGER NOT NULL DEFAULT 0,
            fg_long                 INTEGER NOT NULL DEFAULT 0,
            xp_attempts             INTEGER NOT NULL DEFAULT 0,
            xp_made                 INTEGER NOT NULL DEFAULT 0,
            punts                   INTEGER NOT NULL DEFAULT 0,
            punt_yards              INTEGER NOT NULL DEFAULT 0,
            punt_returns            INTEGER NOT NULL DEFAULT 0,
            punt_return_yards       INTEGER NOT NULL DEFAULT 0,
            punt_return_tds         INTEGER NOT NULL DEFAULT 0,
            kick_returns            INTEGER NOT NULL DEFAULT 0,
            kick_return_yards       INTEGER NOT NULL DEFAULT 0,
            kick_return_tds         INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(season_year, week_number, player_id, is_playoff)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_week_stats_week
        ON player_week_stats(season_year, week_number, is_playoff)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_week_stats_player
        ON player_week_stats(player_id, season_year)
    """)

    # player_season_running
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_season_running (
            id                      INTEGER PRIMARY KEY,
            season_year             INTEGER NOT NULL,
            player_id               INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            is_playoff              INTEGER NOT NULL DEFAULT 0,
            games_played            INTEGER NOT NULL DEFAULT 0,
            pass_attempts           INTEGER NOT NULL DEFAULT 0,
            completions             INTEGER NOT NULL DEFAULT 0,
            pass_yards              INTEGER NOT NULL DEFAULT 0,
            pass_tds                INTEGER NOT NULL DEFAULT 0,
            interceptions_thrown    INTEGER NOT NULL DEFAULT 0,
            sacks_taken             INTEGER NOT NULL DEFAULT 0,
            carries                 INTEGER NOT NULL DEFAULT 0,
            rush_yards              INTEGER NOT NULL DEFAULT 0,
            rush_tds                INTEGER NOT NULL DEFAULT 0,
            fumbles                 INTEGER NOT NULL DEFAULT 0,
            targets                 INTEGER NOT NULL DEFAULT 0,
            receptions              INTEGER NOT NULL DEFAULT 0,
            rec_yards               INTEGER NOT NULL DEFAULT 0,
            rec_tds                 INTEGER NOT NULL DEFAULT 0,
            tackles                 INTEGER NOT NULL DEFAULT 0,
            sacks                   REAL NOT NULL DEFAULT 0,
            interceptions           INTEGER NOT NULL DEFAULT 0,
            pass_deflections        INTEGER NOT NULL DEFAULT 0,
            forced_fumbles          INTEGER NOT NULL DEFAULT 0,
            fg_attempts             INTEGER NOT NULL DEFAULT 0,
            fg_made                 INTEGER NOT NULL DEFAULT 0,
            fg_long                 INTEGER NOT NULL DEFAULT 0,
            xp_attempts             INTEGER NOT NULL DEFAULT 0,
            xp_made                 INTEGER NOT NULL DEFAULT 0,
            punts                   INTEGER NOT NULL DEFAULT 0,
            punt_yards              INTEGER NOT NULL DEFAULT 0,
            punt_returns            INTEGER NOT NULL DEFAULT 0,
            punt_return_yards       INTEGER NOT NULL DEFAULT 0,
            punt_return_tds         INTEGER NOT NULL DEFAULT 0,
            kick_returns            INTEGER NOT NULL DEFAULT 0,
            kick_return_yards       INTEGER NOT NULL DEFAULT 0,
            kick_return_tds         INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(season_year, player_id, is_playoff)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_player
        ON player_season_running(player_id, season_year)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_pass_yards
        ON player_season_running(season_year, is_playoff, pass_yards DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_rush_yards
        ON player_season_running(season_year, is_playoff, rush_yards DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_rec_yards
        ON player_season_running(season_year, is_playoff, rec_yards DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_tackles
        ON player_season_running(season_year, is_playoff, tackles DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_running_sacks
        ON player_season_running(season_year, is_playoff, sacks DESC)
    """)

    # team_week_stats
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_week_stats (
            id                      INTEGER PRIMARY KEY,
            season_year             INTEGER NOT NULL,
            week_number             INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            is_playoff              INTEGER NOT NULL DEFAULT 0,
            points_scored           INTEGER NOT NULL DEFAULT 0,
            total_yards             INTEGER NOT NULL DEFAULT 0,
            pass_yards              INTEGER NOT NULL DEFAULT 0,
            rush_yards              INTEGER NOT NULL DEFAULT 0,
            turnovers               INTEGER NOT NULL DEFAULT 0,
            third_down_conversions  INTEGER NOT NULL DEFAULT 0,
            third_down_attempts     INTEGER NOT NULL DEFAULT 0,
            points_allowed          INTEGER NOT NULL DEFAULT 0,
            yards_allowed           INTEGER NOT NULL DEFAULT 0,
            sacks_recorded          REAL NOT NULL DEFAULT 0,
            takeaways               INTEGER NOT NULL DEFAULT 0,
            won                     INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(season_year, week_number, team_id, is_playoff)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_week_stats_week
        ON team_week_stats(season_year, week_number, is_playoff)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_week_stats_team
        ON team_week_stats(team_id, season_year)
    """)

    # team_season_running
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_season_running (
            id                      INTEGER PRIMARY KEY,
            season_year             INTEGER NOT NULL,
            team_id                 INTEGER NOT NULL,
            is_playoff              INTEGER NOT NULL DEFAULT 0,
            games_played            INTEGER NOT NULL DEFAULT 0,
            points_scored           INTEGER NOT NULL DEFAULT 0,
            total_yards             INTEGER NOT NULL DEFAULT 0,
            pass_yards              INTEGER NOT NULL DEFAULT 0,
            rush_yards              INTEGER NOT NULL DEFAULT 0,
            turnovers               INTEGER NOT NULL DEFAULT 0,
            third_down_conversions  INTEGER NOT NULL DEFAULT 0,
            third_down_attempts     INTEGER NOT NULL DEFAULT 0,
            points_allowed          INTEGER NOT NULL DEFAULT 0,
            yards_allowed           INTEGER NOT NULL DEFAULT 0,
            sacks_recorded          REAL NOT NULL DEFAULT 0,
            takeaways               INTEGER NOT NULL DEFAULT 0,
            wins                    INTEGER NOT NULL DEFAULT 0,
            losses                  INTEGER NOT NULL DEFAULT 0,
            ties                    INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(season_year, team_id, is_playoff)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_season_running_team
        ON team_season_running(team_id, season_year)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_season_running_points_scored
        ON team_season_running(season_year, is_playoff, points_scored DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_season_running_points_allowed
        ON team_season_running(season_year, is_playoff, points_allowed ASC)
    """)

    # weekly_award
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_award (
            id                  INTEGER PRIMARY KEY,
            season_year         INTEGER NOT NULL,
            week_number         INTEGER NOT NULL,
            is_playoff          INTEGER NOT NULL DEFAULT 0,
            award_type          TEXT NOT NULL,
            player_id           INTEGER NOT NULL,
            team_id             INTEGER NOT NULL,
            score               REAL NOT NULL,
            narrative_blurb     TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES player(id),
            FOREIGN KEY (team_id) REFERENCES team(id),
            UNIQUE(season_year, week_number, is_playoff, award_type)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_weekly_award_week
        ON weekly_award(season_year, week_number, is_playoff)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_weekly_award_player
        ON weekly_award(player_id, season_year)
    """)

    conn.commit()


def ensure_depth_chart_table(conn: sqlite3.Connection) -> None:
    """
    Create depth_chart table if it doesn't exist.

    Safe to call multiple times. Used for migrating existing save files
    that were created before the depth chart system was added (Phase 5 Prompt #3).

    Args:
        conn: Database connection
    """
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='depth_chart'")
    if cursor.fetchone():
        return  # Already exists

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS depth_chart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            position_slot TEXT NOT NULL,
            slot_order INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            is_user_set INTEGER NOT NULL DEFAULT 0,
            replaced_player_id INTEGER,
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES player(id) ON DELETE CASCADE,
            FOREIGN KEY (replaced_player_id) REFERENCES player(id) ON DELETE SET NULL,
            UNIQUE(team_id, season_year, position_slot, slot_order)
        );
        CREATE INDEX IF NOT EXISTS idx_depth_chart_team_season ON depth_chart(team_id, season_year);
        CREATE INDEX IF NOT EXISTS idx_depth_chart_player ON depth_chart(player_id);
        CREATE INDEX IF NOT EXISTS idx_depth_chart_position ON depth_chart(team_id, season_year, position_slot);
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
