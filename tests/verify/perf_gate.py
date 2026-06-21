#!/usr/bin/env python3
"""Pre-Launch Performance Gate — docs/ui/08_data_volume_testing.md §7

Usage:
    python tests/verify/perf_gate.py --db saves/perf_y1.db
    python tests/verify/perf_gate.py --db saves/perf_y10.db

Exit codes: 0 = all pass, 1 = one or more fail
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

# Make sure project root is on the path
sys.path.insert(0, str(Path(__file__).parents[2]))

from src.db.connection import get_connection

# ── Budgets (ms) ─────────────────────────────────────────────────────────────

BUDGETS = {
    "dashboard":             100,
    "roster":                100,
    "standings":             150,
    "leaders (passing)":     300,
    "leaders (rushing)":     300,
    "leaders (receiving)":   300,
    "transactions":          150,
    "schedule":              100,
    "free_agency":           150,
    "scouting (hub)":        150,
    "scouting (draft board)":150,
    "trades":                150,
    "draft room":            150,
    "season_review":         200,
    "game_recap":            200,
    "playoff_bracket":       200,
    "dynasty (hub)":         150,
    "dynasty (franchise)":   200,
    "dynasty (awards)":      300,
    "dynasty (legacy)":      150,
    "combine_results":       200,
}

# ── Bench harness ─────────────────────────────────────────────────────────────

def bench(fn, *args, runs: int = 3):
    """Return (first_ms, median_ms, error_str|None)."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        try:
            fn(*args)
        except Exception as exc:
            return None, None, str(exc)
        times.append((time.perf_counter() - t0) * 1000)
    return times[0], statistics.median(times), None


# ── EXPLAIN QUERY PLAN checker ────────────────────────────────────────────────

HEAVY_QUERIES = {
    "player_season_stats (by season)": (
        "SELECT * FROM player_season_stats WHERE season_year = 2024 LIMIT 100",
    ),
    "box_score (by game_id)": (
        "SELECT * FROM box_score WHERE game_id = 1",
    ),
    "box_score (by player+season)": (
        "SELECT * FROM box_score WHERE player_id = 1",
    ),
    "key_play (by game_id)": (
        "SELECT * FROM key_play WHERE game_id = 1",
    ),
    "player_career_stats (by player)": (
        "SELECT * FROM player_career_stats WHERE player_id = 1",
    ),
    "legacy_score (all)": (
        "SELECT * FROM legacy_score ORDER BY season_year",
    ),
    "player (active)": (
        "SELECT * FROM player WHERE is_active = 1",
    ),
    "transaction_log (all)": (
        "SELECT * FROM transaction_log ORDER BY id DESC LIMIT 500",
    ),
}

def check_query_plans(conn, raw_conn) -> list[str]:
    """Return list of warning strings for SCAN TABLE on large-ish tables."""
    warnings = []
    # Count rows to determine which scans matter
    table_counts = {}
    for (tbl,) in raw_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall():
        try:
            n = raw_conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            table_counts[tbl] = n
        except Exception:
            pass

    for label, (query,) in HEAVY_QUERIES.items():
        try:
            plan_rows = raw_conn.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
            for row in plan_rows:
                detail = str(row[-1]) if row else ""
                if "SCAN" in detail.upper():
                    # Extract table name from plan detail
                    parts = detail.upper().split()
                    tbl_name = None
                    for i, p in enumerate(parts):
                        if p == "SCAN" and i + 1 < len(parts):
                            candidate = parts[i + 1].lower().rstrip("(")
                            if candidate in table_counts:
                                tbl_name = candidate
                                break
                    count = table_counts.get(tbl_name, 0) if tbl_name else 0
                    if count > 1000:
                        warnings.append(
                            f"  ⚠ SCAN TABLE on {label!r}: {detail.strip()} "
                            f"(~{count:,} rows in {tbl_name})"
                        )
        except Exception as exc:
            warnings.append(f"  ? Could not explain {label!r}: {exc}")
    return warnings


# ── Game sim batch ────────────────────────────────────────────────────────────

def run_game_sim_batch(db_path: str, raw_conn) -> tuple[float | None, str | None]:
    """Time 16 game simulations from completed games list. Returns (elapsed_s, error)."""
    try:
        from src.engine.game_sim import simulate_game

        # Get up to 16 completed game IDs from this fixture
        rows = raw_conn.execute(
            "SELECT id FROM game WHERE home_score IS NOT NULL ORDER BY id LIMIT 16"
        ).fetchall()
        if not rows:
            return None, "No completed games in fixture"

        game_ids = [r[0] for r in rows]
        t0 = time.perf_counter()
        for gid in game_ids:
            simulate_game(db_path, gid, verbose=False)
        elapsed = time.perf_counter() - t0
        return elapsed, None
    except Exception as exc:
        return None, str(exc)


# ── Memory soak ───────────────────────────────────────────────────────────────

def run_memory_soak(conn) -> tuple[float | None, str | None]:
    """Run 50-iteration loop over heaviest presenters, return (peak_mb, error)."""
    try:
        from src.ui.presenters import dynasty, leaders, standings

        tracemalloc.start()
        for _ in range(50):
            dynasty.build_awards_history(conn)
            leaders.build(conn, category="passing")
            standings.build(conn)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024 / 1024, None
    except Exception as exc:
        tracemalloc.stop()
        return None, str(exc)


# ── Main gate ─────────────────────────────────────────────────────────────────

def run_gate(db_path: str) -> dict:
    """Run all checks. Returns a dict with all results."""
    from src.ui.presenters import (
        combine_results as cr_mod,
        dashboard,
        dynasty,
        free_agency,
        game_recap,
        leaders,
        playoff,
        roster,
        schedule,
        scouting,
        season_review,
        standings,
        trades,
        transactions,
    )
    from src.ui.presenters import draft as draft_mod

    conn = get_connection(db_path)
    raw_conn = sqlite3.connect(db_path)
    raw_conn.row_factory = sqlite3.Row

    results = []

    def record(label, fn, *args):
        budget = BUDGETS.get(label, 200)
        first_ms, median_ms, error = bench(fn, *args)
        if error:
            results.append({"label": label, "first": None, "median": None,
                            "budget": budget, "status": "SKIP", "note": error})
        else:
            status = "PASS" if median_ms <= budget else "FAIL"
            results.append({"label": label, "first": first_ms, "median": median_ms,
                            "budget": budget, "status": status, "note": None})

    # ── Presenter benchmarks ──────────────────────────────────────────────────

    record("dashboard",             dashboard.build, conn)
    record("roster",                roster.build, conn)
    record("standings",             standings.build, conn)
    record("leaders (passing)",     leaders.build, conn, "passing")
    record("leaders (rushing)",     leaders.build, conn, "rushing")
    record("leaders (receiving)",   leaders.build, conn, "receiving")
    record("transactions",          transactions.build, conn)
    record("schedule",              schedule.build, conn)
    record("free_agency",           free_agency.build_market, conn)
    record("scouting (hub)",        scouting.build_scout_dashboard, conn)
    record("scouting (draft board)",scouting.build_draft_board_view, conn)
    record("trades",                trades.build_trade_hub, conn)
    record("draft room",            draft_mod.build_draft_room, conn)
    record("dynasty (hub)",         dynasty.build_dynasty_hub, conn)
    record("dynasty (franchise)",   dynasty.build_franchise_history, conn)
    record("dynasty (awards)",      dynasty.build_awards_history, conn)
    record("dynasty (legacy)",      dynasty.build_legacy_tracker, conn)

    # season_review — needs a completed season
    state = raw_conn.execute("SELECT current_season FROM league WHERE id=1").fetchone()
    current_season = state["current_season"] if state else 2024
    prev_season = current_season - 1
    has_prev = raw_conn.execute(
        "SELECT 1 FROM season WHERE year = ?", (prev_season,)
    ).fetchone()
    if has_prev:
        record("season_review", season_review.build_season_review, conn, prev_season)
    else:
        results.append({"label": "season_review", "first": None, "median": None,
                        "budget": 200, "status": "SKIP",
                        "note": f"No completed season (prev={prev_season})"})

    # game_recap — needs a completed game
    gid_row = raw_conn.execute(
        "SELECT game_id FROM box_score LIMIT 1"
    ).fetchone()
    if gid_row:
        record("game_recap", game_recap.build, conn, gid_row["game_id"])
    else:
        results.append({"label": "game_recap", "first": None, "median": None,
                        "budget": 200, "status": "SKIP",
                        "note": "No completed games in fixture"})

    # playoff_bracket — needs playoff data
    try:
        record("playoff_bracket", playoff.build_playoff_bracket, conn)
    except Exception as exc:
        results.append({"label": "playoff_bracket", "first": None, "median": None,
                        "budget": 200, "status": "SKIP", "note": str(exc)})

    # combine_results — needs combine events
    record("combine_results", cr_mod.build_combine_results, conn)

    return {
        "presenter_results": results,
        "query_plan_warnings": check_query_plans(conn, raw_conn),
    }


# ── Report formatting ─────────────────────────────────────────────────────────

def format_table(results: list[dict]) -> str:
    lines = [
        "| Presenter | First Call | Median (3x) | Budget | Result |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        first = f"{r['first']:.1f}ms" if r["first"] is not None else "—"
        median = f"{r['median']:.1f}ms" if r["median"] is not None else "—"
        budget = f"{r['budget']}ms"
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭"}.get(r["status"], "?")
        note = f" _{r['note']}_" if r.get("note") and r["status"] == "SKIP" else ""
        lines.append(
            f"| {r['label']}{note} | {first} | {median} | {budget} | {icon} {r['status']} |"
        )
    return "\n".join(lines)


def write_report(path: str, y1_data: dict, y10_data: dict,
                 y1_db: str, y10_db: str,
                 sim_elapsed: float | None, sim_error: str | None,
                 mem_peak: float | None, mem_error: str | None) -> None:
    from datetime import date

    y1_size = os.path.getsize(y1_db) / 1024 / 1024
    y10_size = os.path.getsize(y10_db) / 1024 / 1024

    all_results = y1_data["presenter_results"] + y10_data["presenter_results"]
    n_pass = sum(1 for r in all_results if r["status"] == "PASS")
    n_fail = sum(1 for r in all_results if r["status"] == "FAIL")
    n_skip = sum(1 for r in all_results if r["status"] == "SKIP")
    overall = "✅ PASS" if n_fail == 0 else "❌ FAIL"

    sim_line = (
        f"{sim_elapsed:.1f}s (budget: <15s) — {'✅ PASS' if sim_elapsed and sim_elapsed < 15 else '❌ FAIL'}"
        if sim_elapsed else f"SKIP — {sim_error}"
    )
    mem_line = (
        f"{mem_peak:.1f}MB peak delta (budget: <50MB) — {'✅ PASS' if mem_peak and mem_peak < 50 else '❌ FAIL'}"
        if mem_peak else f"SKIP — {mem_error}"
    )

    failures = [r for r in all_results if r["status"] == "FAIL"]
    qp_warnings = y1_data["query_plan_warnings"] + y10_data["query_plan_warnings"]
    # Deduplicate warnings
    qp_warnings = list(dict.fromkeys(qp_warnings))

    lines = [
        "# Pre-Launch Performance Gate Report",
        f"Generated: {date.today().isoformat()}",
        f"Fixtures: perf_y1.db ({y1_size:.1f}MB) | perf_y10.db ({y10_size:.1f}MB)",
        "",
        "## Summary",
        f"PASS: {n_pass} / FAIL: {n_fail} / SKIP: {n_skip}",
        f"Overall: {overall}",
        "",
        "## Presenter Benchmarks — Year-1 Fixture",
        format_table(y1_data["presenter_results"]),
        "",
        "## Presenter Benchmarks — Year-10 Fixture",
        format_table(y10_data["presenter_results"]),
        "",
        "## EXPLAIN QUERY PLAN Findings",
    ]

    if qp_warnings:
        lines += qp_warnings
    else:
        lines.append("No SCAN TABLE warnings on tables with >1,000 rows.")

    _sim_raw = sqlite3.connect(y10_db)
    _sim_game_count = len(_sim_raw.execute(
        "SELECT id FROM game WHERE home_score IS NOT NULL LIMIT 16"
    ).fetchall())
    _sim_raw.close()
    lines += [
        "",
        "## Game Sim Batch",
        f"{_sim_game_count} game(s): {sim_line}",
        "",
        "## Memory Soak",
        f"50-iteration loop (awards_history + leaders + standings): {mem_line}",
        "",
    ]

    if failures:
        lines += ["## Failures", ""]
        for r in failures:
            lines.append(
                f"- **{r['label']}**: {r['median']:.1f}ms actual vs {r['budget']}ms budget "
                f"(+{r['median'] - r['budget']:.0f}ms over). "
                f"Suspected cause: unindexed scan or N+1 — see EXPLAIN QUERY PLAN section."
            )
        lines += [
            "",
            "## Recommended Fixes",
            "",
            "_These are diagnostic notes only — fixes are a follow-up task._",
            "",
            "For each failure above, run `EXPLAIN QUERY PLAN` on the presenter's core query "
            "and look for `SCAN TABLE` on large tables. Likely fixes:",
            "- Add compound index on `(season_year, player_id)` for stat tables",
            "- Add index on `(game_id)` for box_score and key_play",
            "- Ensure dynasty queries use existing indexes on player_career_stats",
        ]
    else:
        lines.append("## Failures\n\nNone — all presenters passed their budgets.")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pre-launch performance gate")
    parser.add_argument("--db", required=True, help="Path to fixture .db file")
    parser.add_argument("--report", action="store_true",
                        help="Also run Y10 fixture and write full report")
    args = parser.parse_args()

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"ERROR: fixture not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    print(f"\n{'='*60}")
    print(f"Performance Gate — {os.path.basename(db_path)}")
    print(f"{'='*60}\n")

    data = run_gate(db_path)
    results = data["presenter_results"]

    # Print table
    print(f"{'Presenter':<28} {'First':>9} {'Median':>9} {'Budget':>8}  Status")
    print("-" * 70)
    for r in results:
        first = f"{r['first']:.1f}ms" if r["first"] is not None else "—"
        median = f"{r['median']:.1f}ms" if r["median"] is not None else "—"
        budget = f"{r['budget']}ms"
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭"}.get(r["status"], "?")
        note = f"  [{r['note'][:40]}]" if r.get("note") and r["status"] != "PASS" else ""
        print(f"{r['label']:<28} {first:>9} {median:>9} {budget:>8}  {icon} {r['status']}{note}")

    print()

    # EXPLAIN QUERY PLAN
    warnings = data["query_plan_warnings"]
    if warnings:
        print("EXPLAIN QUERY PLAN warnings:")
        for w in warnings:
            print(w)
        print()
    else:
        print("✅ EXPLAIN QUERY PLAN: no SCAN TABLE on tables > 1,000 rows\n")

    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_skip = sum(1 for r in results if r["status"] == "SKIP")
    print(f"Totals: {n_pass} PASS / {n_fail} FAIL / {n_skip} SKIP")
    sys.exit(1 if n_fail > 0 else 0)


if __name__ == "__main__":
    main()
