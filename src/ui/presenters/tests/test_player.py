"""Tests for the player card presenter."""
import json
from pathlib import Path
import pytest
from src.db.connection import get_connection
from src.ui.presenters import player

_SAVE_CANDIDATES = [
    Path("saves/phase5_p12_test.db"),
    Path("saves/phase5_p11_test.db"),
    Path("saves/test_franchise.db"),
]


def _has_league_table(path: Path) -> bool:
    import sqlite3
    try:
        conn = sqlite3.connect(str(path))
        r = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='league'").fetchone()
        conn.close()
        return r[0] == 1
    except Exception:
        return False


SAVE = next((p for p in _SAVE_CANDIDATES if p.exists() and _has_league_table(p)), _SAVE_CANDIDATES[0])


def _get_first_player_id(conn):
    """Get the first player on the user team."""
    from src.db import queries
    state = queries.get_league_state(conn)
    rows = queries.get_roster_with_contracts(conn, state["user_team_id"], state["current_season"])
    return rows[0]["id"] if rows else None


@pytest.mark.skipif(not SAVE.exists(), reason="save file not present")
def test_player_shape():
    conn = get_connection(str(SAVE))
    pid = _get_first_player_id(conn)
    if pid is None:
        pytest.skip("No players on user team")
    result = player.build(conn, pid)
    assert set(result.keys()) == {"header", "overview", "stats", "contract", "satisfaction", "history", "actions"}
    assert result["header"]["full_name"], "full_name must not be empty"
    assert len(result["overview"]["key_attributes"]) >= 2
    assert len(result["actions"]) == 3
    # 7b: Cut/Restructure are wired; Add to Trade Block stays disabled (5.8).
    by_key = {a["action_key"]: a for a in result["actions"]}
    assert by_key["add_to_trade_block"]["enabled"] is False
    # Cut/Restructure data sub-views live on the contract dict (key set stable).
    assert "cut" in result["contract"] and "restructure" in result["contract"]
    assert isinstance(result["contract"]["cut"]["can_cut"], bool)
    assert isinstance(result["contract"]["restructure"]["can_restructure"], bool)


@pytest.mark.skipif(not SAVE.exists(), reason="save file not present")
def test_no_raw_ratings_in_player():
    conn = get_connection(str(SAVE))
    pid = _get_first_player_id(conn)
    if pid is None:
        pytest.skip("No players on user team")
    result = player.build(conn, pid)
    dump = json.dumps(result)
    assert "true_overall" not in dump
    assert "true_speed" not in dump
