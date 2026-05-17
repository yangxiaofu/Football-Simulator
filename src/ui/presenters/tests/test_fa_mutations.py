"""Phase 6 P7b — FA/contract mutation tests (do_sign / do_cut / do_restructure).

A real franchise is bootstrapped once with generate.py (proper schema +
rosters + teams), then each test gets an isolated copy. Contracts are created
through the real offer_contract() business logic (a fresh generate has zero
contracts — the documented Phase 0/3 data gap), so these exercise the true
code path, not hand-rolled SQL.
"""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from src.db.connection import get_connection
from src.db import queries
from src.transactions.contracts import offer_contract

_BASE = None  # built once per session


def _base_db(tmp_path_factory) -> Path:
    global _BASE
    if _BASE is None:
        d = tmp_path_factory.mktemp("p7b_base")
        path = d / "base.db"
        subprocess.run(
            [sys.executable, "generate.py", str(path), "--season", "2024"],
            check=True, capture_output=True,
        )
        _BASE = path
    return _BASE


@pytest.fixture()
def db(tmp_path, tmp_path_factory):
    base = _base_db(tmp_path_factory)
    path = tmp_path / "save.db"
    shutil.copy(base, path)
    return str(path)


def _give_contract(db_path: str, aav: int = 5_000_000) -> int:
    """Create a real 3-year active contract for a user-team player."""
    conn = get_connection(db_path)
    state = queries.get_league_state(conn)
    tid = state["user_team_id"]
    pid = conn.execute(
        "SELECT id FROM player WHERE team_id=? LIMIT 1", (tid,)
    ).fetchone()[0]
    offer_contract(pid, tid, 3, aav, 3_000_000, 5_000_000,
                    None, None, None, conn)
    conn.close()
    return pid


def _make_free_agent(db_path: str) -> int:
    """Turn a non-user player into a Tier-1 FA interested in the user team."""
    conn = get_connection(db_path)
    state = queries.get_league_state(conn)
    tid, yr = state["user_team_id"], state["current_season"]
    pid = conn.execute(
        "SELECT id FROM player WHERE team_id != ? LIMIT 1", (tid,)
    ).fetchone()[0]
    with conn:
        conn.execute(
            "UPDATE player SET team_id=NULL, roster_status='free_agent' WHERE id=?",
            (pid,),
        )
        conn.execute(
            "INSERT INTO fa_interest (player_id, team_id, season_year, tier, "
            "preference_score) VALUES (?,?,?,1,0.9)", (pid, tid, yr),
        )
    conn.close()
    return pid


def _cap_space(db_path: str, team_id: int) -> int:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT cap_space FROM team WHERE id=?", (team_id,)
    ).fetchone()
    conn.close()
    return row[0]


def _api(db_path: str):
    from src.ui.api import Api
    return Api(db_path)


# ── do_cut_player ─────────────────────────────────────────────────────────────

def test_cut_player_releases_and_recalcs_cap(db):
    pid = _give_contract(db)
    tid = 1
    cap_before = _cap_space(db, tid)

    res = _api(db).do_cut_player(pid)
    assert res["ok"] is True
    assert res["dead_cap"] and res["new_cap_space"]

    conn = sqlite3.connect(db)
    team_id, status = conn.execute(
        "SELECT p.team_id, "
        "(SELECT status FROM contract WHERE player_id=p.id ORDER BY id DESC LIMIT 1) "
        "FROM player p WHERE p.id=?", (pid,)
    ).fetchone()
    conn.close()
    assert team_id is None                       # off the roster
    assert status == "expired"                   # contract terminated
    assert _cap_space(db, tid) != cap_before     # cap recalculated


# ── do_restructure_contract ───────────────────────────────────────────────────

def test_restructure_updates_years_and_cap(db):
    pid = _give_contract(db, aav=8_000_000)
    tid = 1
    cap_before = _cap_space(db, tid)

    conn = sqlite3.connect(db)
    base = conn.execute(
        "SELECT base_salary FROM contract_year cy JOIN contract ct "
        "ON ct.id=cy.contract_id WHERE ct.player_id=? AND cy.season_year=2024",
        (pid,),
    ).fetchone()[0]
    cap_hits_before = [r[0] for r in conn.execute(
        "SELECT cap_hit FROM contract_year cy JOIN contract ct "
        "ON ct.id=cy.contract_id WHERE ct.player_id=? ORDER BY cy.season_year",
        (pid,)).fetchall()]
    conn.close()

    res = _api(db).do_restructure_contract(
        pid, {"amount_to_convert": int(base * 0.5)})
    assert res["ok"] is True
    assert res["restructured_years"] >= 2

    conn = sqlite3.connect(db)
    cap_hits_after = [r[0] for r in conn.execute(
        "SELECT cap_hit FROM contract_year cy JOIN contract ct "
        "ON ct.id=cy.contract_id WHERE ct.player_id=? ORDER BY cy.season_year",
        (pid,)).fetchall()]
    conn.close()
    assert cap_hits_after != cap_hits_before     # schedule rewritten
    assert _cap_space(db, tid) != cap_before     # cap recalculated


# ── do_sign_free_agent ────────────────────────────────────────────────────────

def test_sign_free_agent_creates_contract(db):
    pid = _make_free_agent(db)
    tid = 1
    cap_before = _cap_space(db, tid)

    res = _api(db).do_sign_free_agent(pid, {
        "years": 3, "aav": 40_000_000,
        "signing_bonus": 10_000_000, "guaranteed_money": 20_000_000,
    })
    assert res["ok"] is True
    assert res["accepted"] is True
    assert res["outcome"] == "accepted"

    conn = sqlite3.connect(db)
    team_id = conn.execute(
        "SELECT team_id FROM player WHERE id=?", (pid,)).fetchone()[0]
    ncontract = conn.execute(
        "SELECT COUNT(*) FROM contract WHERE player_id=? AND status='active'",
        (pid,)).fetchone()[0]
    nyears = conn.execute(
        "SELECT COUNT(*) FROM contract_year cy JOIN contract ct "
        "ON ct.id=cy.contract_id WHERE ct.player_id=?", (pid,)).fetchone()[0]
    conn.close()
    assert team_id == tid
    assert ncontract == 1
    assert nyears >= 1
    assert _cap_space(db, tid) != cap_before


# ── cap-recalc regression guard ───────────────────────────────────────────────

def test_every_mutation_changes_cap_space(db):
    tid = 1
    pid_a = _give_contract(db, aav=6_000_000)
    c0 = _cap_space(db, tid)
    assert _api(db).do_restructure_contract(
        pid_a, {"amount_to_convert": 1_000_000})["ok"] is True
    c1 = _cap_space(db, tid)
    assert c1 != c0
    assert _api(db).do_cut_player(pid_a)["ok"] is True
    c2 = _cap_space(db, tid)
    assert c2 != c1


# ── rollback on exception ─────────────────────────────────────────────────────

def test_rollback_on_exception_leaves_db_unchanged(db):
    pid = _give_contract(db, aav=7_000_000)
    tid = 1
    cap_before = _cap_space(db, tid)
    conn = sqlite3.connect(db)
    rows_before = [tuple(r) for r in conn.execute(
        "SELECT season_year, base_salary, cap_hit FROM contract_year cy "
        "JOIN contract ct ON ct.id=cy.contract_id WHERE ct.player_id=? "
        "ORDER BY cy.season_year", (pid,)).fetchall()]
    conn.close()

    # Convert far more than base salary → business layer raises ValueError.
    res = _api(db).do_restructure_contract(
        pid, {"amount_to_convert": 999_000_000})
    assert res["ok"] is False
    assert res["error"]

    conn = sqlite3.connect(db)
    rows_after = [tuple(r) for r in conn.execute(
        "SELECT season_year, base_salary, cap_hit FROM contract_year cy "
        "JOIN contract ct ON ct.id=cy.contract_id WHERE ct.player_id=? "
        "ORDER BY cy.season_year", (pid,)).fetchall()]
    conn.close()
    assert rows_after == rows_before                 # no partial write
    assert _cap_space(db, tid) == cap_before          # cap unchanged


# ── single-flight concurrency guard ───────────────────────────────────────────

def test_single_flight_returns_busy(db):
    pid = _give_contract(db)
    import src.ui.api as api_mod
    api_mod._MUTATION_LOCK.acquire()
    try:
        res = _api(db).do_cut_player(pid)
    finally:
        api_mod._MUTATION_LOCK.release()
    assert res["ok"] is False
    assert "progress" in res["error"].lower()


# ── watchlist toggle ──────────────────────────────────────────────────────────

def test_add_to_watchlist_toggles(db):
    pid = _make_free_agent(db)
    a = _api(db)
    r1 = a.do_add_to_watchlist(pid)
    assert r1["ok"] is True and r1["is_watchlisted"] is True
    r2 = _api(db).do_add_to_watchlist(pid)
    assert r2["is_watchlisted"] is False
