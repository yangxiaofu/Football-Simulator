"""Tests for free_agency presenter (F-41 FA Market + F-42 FA Player Card)."""
import sqlite3
from pathlib import Path

import pytest

from src.ui.presenters import free_agency

_SAVE_CANDIDATES = [
    Path("saves/phase6_p7a_test.db"),
    Path("saves/phase6_p6_fo_test.db"),
    Path("saves/phase6_p5_test.db"),
]
SAVE = next((p for p in _SAVE_CANDIDATES if p.exists()), _SAVE_CANDIDATES[0])

MARKET_KEYS  = {"available_players", "columns", "your_team_needs",
                "cap_available", "active_negotiations", "watchlist_count"}
PLAYER_KEYS  = {"header", "overview", "stats", "history",
                "market_interest", "contract_history", "is_watchlisted", "actions"}
ROW_KEYS     = {"id", "pos", "name_short", "age", "overall", "asking_salary",
                "interest_label", "interest_tier", "status_icons", "is_watchlisted",
                "_pos_filter_value", "_age_filter_value"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_db(with_fa_players: int = 3) -> sqlite3.Connection:
    """Minimal in-memory DB for unit tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE league (
            id INTEGER PRIMARY KEY, current_season INTEGER NOT NULL,
            current_week INTEGER NOT NULL, current_phase TEXT NOT NULL,
            user_team_id INTEGER NOT NULL, name TEXT NOT NULL DEFAULT 'NFL',
            salary_cap INTEGER NOT NULL DEFAULT 255000000,
            created_at TEXT NOT NULL DEFAULT '2024-01-01'
        );
        INSERT INTO league VALUES (1, 2024, 1, 'offseason', 1, 'NFL', 255000000, '2024-01-01');

        CREATE TABLE team (
            id INTEGER PRIMARY KEY, division_id INTEGER NOT NULL DEFAULT 1,
            city TEXT NOT NULL DEFAULT 'Chicago', nickname TEXT NOT NULL DEFAULT 'Bears',
            abbreviation TEXT NOT NULL DEFAULT 'CHI', gm_personality TEXT NOT NULL DEFAULT 'analytics',
            prestige INTEGER NOT NULL DEFAULT 70, market_size INTEGER NOT NULL DEFAULT 80,
            stadium_type TEXT NOT NULL DEFAULT 'outdoor', home_city_climate TEXT NOT NULL DEFAULT 'cold',
            cap_space INTEGER NOT NULL DEFAULT 25000000, waiver_priority INTEGER NOT NULL DEFAULT 16,
            fan_sentiment INTEGER NOT NULL DEFAULT 50, team_phase TEXT NOT NULL DEFAULT 'bridge'
        );
        INSERT INTO team (id) VALUES (1);

        CREATE TABLE player (
            id INTEGER PRIMARY KEY, team_id INTEGER, first_name TEXT DEFAULT 'John',
            last_name TEXT DEFAULT 'Smith', position TEXT DEFAULT 'WR',
            roster_status TEXT DEFAULT 'active', is_active INTEGER DEFAULT 1,
            true_overall INTEGER DEFAULT 75, age INTEGER DEFAULT 28,
            years_experience INTEGER DEFAULT 4, draft_year INTEGER DEFAULT 2020,
            draft_round INTEGER DEFAULT 2, draft_pick INTEGER DEFAULT 45,
            college TEXT DEFAULT 'Ohio State',
            true_speed INTEGER DEFAULT 75, true_catching INTEGER DEFAULT 75,
            true_route_running INTEGER DEFAULT 75,
            true_strength INTEGER DEFAULT 75, true_pass_block INTEGER DEFAULT 75,
            true_run_block INTEGER DEFAULT 75,
            true_pass_rush INTEGER DEFAULT 75, true_run_stop INTEGER DEFAULT 75,
            true_coverage INTEGER DEFAULT 75, true_tackling INTEGER DEFAULT 75,
            true_throw_power INTEGER DEFAULT 75, true_accuracy INTEGER DEFAULT 75,
            true_elusiveness INTEGER DEFAULT 75, true_blocking INTEGER DEFAULT 75,
            true_kick_power INTEGER DEFAULT 75, true_kick_accuracy INTEGER DEFAULT 75,
            true_clutch INTEGER DEFAULT 70, injury_status TEXT DEFAULT NULL,
            satisfaction INTEGER DEFAULT 75, is_watchlisted INTEGER DEFAULT 0
        );

        CREATE TABLE fa_interest (
            id INTEGER PRIMARY KEY, player_id INTEGER, team_id INTEGER,
            season_year INTEGER, tier INTEGER DEFAULT 2, preference_score REAL DEFAULT 0.5
        );

        CREATE TABLE contract (
            id INTEGER PRIMARY KEY, player_id INTEGER, team_id INTEGER,
            status TEXT DEFAULT 'active', total_years INTEGER DEFAULT 3,
            total_value INTEGER DEFAULT 15000000, aav INTEGER DEFAULT 5000000,
            is_rookie_contract INTEGER DEFAULT 0, is_franchise_tag INTEGER DEFAULT 0,
            signed_season INTEGER DEFAULT 2022
        );

        CREATE TABLE contract_year (
            id INTEGER PRIMARY KEY, contract_id INTEGER, season_year INTEGER,
            cap_hit INTEGER DEFAULT 5000000, base_salary INTEGER DEFAULT 4000000,
            dead_cap_value INTEGER DEFAULT 2000000
        );

        CREATE TABLE player_season_stats (
            id INTEGER PRIMARY KEY, player_id INTEGER, team_id INTEGER DEFAULT 1,
            season_year INTEGER, games_played INTEGER DEFAULT 0,
            pass_yards INTEGER DEFAULT 0, pass_tds INTEGER DEFAULT 0,
            interceptions INTEGER DEFAULT 0, rush_yards INTEGER DEFAULT 0,
            rush_tds INTEGER DEFAULT 0, receptions INTEGER DEFAULT 0,
            rec_yards INTEGER DEFAULT 0, rec_tds INTEGER DEFAULT 0,
            won_mvp INTEGER DEFAULT 0, made_all_pro INTEGER DEFAULT 0,
            made_pro_bowl INTEGER DEFAULT 0
        );

        CREATE TABLE player_career_stats (
            id INTEGER PRIMARY KEY, player_id INTEGER, seasons_played INTEGER DEFAULT 0,
            career_pro_bowls INTEGER DEFAULT 0, career_all_pro INTEGER DEFAULT 0,
            peak_overall INTEGER DEFAULT 75,
            career_pass_yards INTEGER DEFAULT 0, career_pass_tds INTEGER DEFAULT 0,
            career_rush_yards INTEGER DEFAULT 0, career_rush_tds INTEGER DEFAULT 0,
            career_rec_yards INTEGER DEFAULT 0, career_rec_tds INTEGER DEFAULT 0,
            career_sacks REAL DEFAULT 0, career_interceptions INTEGER DEFAULT 0,
            career_tackles INTEGER DEFAULT 0, career_forced_fumbles INTEGER DEFAULT 0,
            career_field_goals INTEGER DEFAULT 0, career_punts INTEGER DEFAULT 0
        );

        CREATE TABLE weekly_award (
            id INTEGER PRIMARY KEY, player_id INTEGER, season_year INTEGER,
            week_number INTEGER, award_type TEXT DEFAULT 'star', narrative_blurb TEXT DEFAULT ''
        );
    """)

    # Insert user's active roster
    conn.execute(
        "INSERT INTO player (id, team_id, roster_status, position) VALUES (100, 1, 'active', 'QB')"
    )

    # Insert free agent players
    for i in range(with_fa_players):
        pid = i + 1
        pos = ["WR", "CB", "LB"][i % 3]
        conn.execute(
            "INSERT INTO player (id, team_id, roster_status, position, true_overall, age) VALUES (?, NULL, 'free_agent', ?, ?, ?)",
            (pid, pos, 70 + i * 5, 25 + i)
        )
        conn.execute(
            "INSERT INTO player_season_stats (player_id, season_year, games_played) VALUES (?, 2024, 0)",
            (pid,)
        )
        conn.execute(
            "INSERT INTO player_career_stats (player_id, seasons_played) VALUES (?, 3)",
            (pid,)
        )

    conn.commit()
    return conn


# ── FA Market shape tests ─────────────────────────────────────────────────────

def test_fa_market_shape():
    conn = _make_db()
    result = free_agency.build_market(conn)
    assert set(result.keys()) == MARKET_KEYS
    assert isinstance(result["available_players"], list)
    assert isinstance(result["columns"], list)
    assert isinstance(result["your_team_needs"], list)
    assert isinstance(result["cap_available"], str)
    assert isinstance(result["active_negotiations"], list)
    assert isinstance(result["watchlist_count"], int)


def test_fa_market_only_free_agents():
    conn = _make_db(with_fa_players=3)
    result = free_agency.build_market(conn)
    assert len(result["available_players"]) == 3
    for row in result["available_players"]:
        assert set(row.keys()) == ROW_KEYS


def test_fa_market_no_active_players():
    conn = _make_db(with_fa_players=0)
    result = free_agency.build_market(conn)
    assert result["available_players"] == []


def test_fa_market_cap_available_formatted():
    conn = _make_db()
    result = free_agency.build_market(conn)
    assert result["cap_available"].startswith("$")
    assert "M" in result["cap_available"] or result["cap_available"] == "$0"


def test_fa_market_row_overall_is_letter_grade():
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_market(conn)
    row = result["available_players"][0]
    assert any(row["overall"].startswith(g) for g in ["A", "B", "C", "D", "F"])


def test_fa_market_row_salary_formatted():
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_market(conn)
    row = result["available_players"][0]
    assert row["asking_salary"].startswith("$")
    assert "/yr" in row["asking_salary"]


def test_fa_market_interest_label_valid():
    conn = _make_db(with_fa_players=2)
    result = free_agency.build_market(conn)
    valid_labels = {"High", "Neutral", "Low", "Unknown"}
    for row in result["available_players"]:
        assert row["interest_label"] in valid_labels


def test_fa_market_age_bucket():
    conn = _make_db(with_fa_players=3)
    result = free_agency.build_market(conn)
    valid_buckets = {"Under 25", "25-29", "30+"}
    for row in result["available_players"]:
        assert row["_age_filter_value"] in valid_buckets


# ── FA Player Card tests ──────────────────────────────────────────────────────

def test_fa_player_shape():
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_player(conn, 1)
    assert set(result.keys()) == PLAYER_KEYS


def test_fa_player_team_is_free_agent():
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_player(conn, 1)
    assert result["header"]["team_name"] == "Free Agent"
    assert result["header"]["team_abbr"] == "FA"


def test_fa_player_actions_wired():
    """7b: FA actions are now enabled and carry an action_key."""
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_player(conn, 1)
    assert len(result["actions"]) == 2
    keys = {a["action_key"] for a in result["actions"]}
    assert keys == {"add_to_watchlist", "pitch_meeting"}
    for action in result["actions"]:
        assert action["enabled"] is True
        assert action["tooltip"]
    assert result["is_watchlisted"] is False


def test_fa_player_no_contract_tab_in_actions():
    conn = _make_db(with_fa_players=1)
    result = free_agency.build_player(conn, 1)
    action_labels = [a["label"] for a in result["actions"]]
    assert "Current Contract" not in action_labels


def test_fa_player_not_found():
    conn = _make_db(with_fa_players=0)
    result = free_agency.build_player(conn, 9999)
    assert result.get("ok") is False
    assert "9999" in result.get("error", "")


# ── Real save test ────────────────────────────────────────────────────────────

@pytest.mark.skipif(not SAVE.exists(), reason="save file not present")
def test_fa_market_real_save():
    from src.db.connection import get_connection
    conn = get_connection(str(SAVE))
    result = free_agency.build_market(conn)
    assert set(result.keys()) == MARKET_KEYS
    assert isinstance(result["available_players"], list)
    # p7a save has 20 FA players
    if str(SAVE).endswith("p7a_test.db"):
        assert len(result["available_players"]) >= 1
    for row in result["available_players"]:
        assert row["asking_salary"].endswith("/yr")
