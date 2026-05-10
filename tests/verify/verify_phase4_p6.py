#!/usr/bin/env python3
"""
Verification script for Phase 4 Prompt #6 — Tier 2 Dramatic Press Conferences.

Checks against saves/phase4_v6.db after a 3-season stress test:
1. Schema: tier2_press_event, tier2_press_response, tier2_trigger_guard tables exist
2. Events generated: at least 3 Tier 2 events across 3 seasons
3. Per-season cap: no season exceeds TIER2_MAX_PER_SEASON
4. All events resolved: resolved_at IS NOT NULL for all events
5. Response count matches: each event has num_questions response rows
6. Effect deltas match TIER2_EFFECTS constants
7. Trigger diversity: at least 2 distinct trigger types fired
8. Tier 1 suppression: no press_event row exists for any (season, week, team)
   where a tier2_press_event row also exists
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.connection import get_connection
from src.utils.constants import TIER2_MAX_PER_SEASON, TIER2_EFFECTS, TIER2_VALID_CHOICES

DB_PATH = "saves/phase4_v6.db"


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} does not exist.")
        print("Run: python generate.py saves/phase4_v6.db --season 2024")
        print("Then: python run_stress_test.py saves/phase4_v6.db --invariants --seasons 3")
        sys.exit(1)

    conn = get_connection(DB_PATH)
    all_pass = True

    print("\nPhase 4 Prompt #6 — Tier 2 Dramatic Press Conference Verification")
    print("=" * 70)

    # 1. Schema check
    tables = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table'
        AND name IN ('tier2_press_event', 'tier2_press_response', 'tier2_trigger_guard')
    """).fetchall()
    table_names = {t['name'] for t in tables}
    ok = check(
        "Schema: all 3 Tier 2 tables exist",
        len(table_names) == 3,
        f"found: {sorted(table_names)}"
    )
    all_pass = all_pass and ok

    # 2. Events generated
    event_count = conn.execute("""
        SELECT COUNT(*) as cnt FROM tier2_press_event
    """).fetchone()['cnt']
    ok = check(
        "Events generated: at least 3 across all seasons",
        event_count >= 3,
        f"found {event_count} events"
    )
    all_pass = all_pass and ok

    # 3. Per-season cap
    season_counts = conn.execute("""
        SELECT season_year, COUNT(*) as cnt FROM tier2_press_event
        GROUP BY season_year
    """).fetchall()
    max_in_season = max((r['cnt'] for r in season_counts), default=0)
    ok = check(
        f"Per-season cap: no season exceeds {TIER2_MAX_PER_SEASON}",
        max_in_season <= TIER2_MAX_PER_SEASON,
        f"max in one season: {max_in_season}"
    )
    all_pass = all_pass and ok

    # 4. All events resolved
    unresolved = conn.execute("""
        SELECT COUNT(*) as cnt FROM tier2_press_event WHERE resolved_at IS NULL
    """).fetchone()['cnt']
    ok = check(
        "All events resolved",
        unresolved == 0,
        f"unresolved: {unresolved}"
    )
    all_pass = all_pass and ok

    # 5. Response count matches num_questions
    mismatched = conn.execute("""
        SELECT e.id, e.num_questions, COUNT(r.id) as actual
        FROM tier2_press_event e
        LEFT JOIN tier2_press_response r ON r.event_id = e.id
        GROUP BY e.id
        HAVING actual != e.num_questions
    """).fetchall()
    ok = check(
        "Response count matches num_questions for all events",
        len(mismatched) == 0,
        f"mismatched events: {len(mismatched)}"
    )
    all_pass = all_pass and ok

    # 6. Effect deltas match constants
    responses = conn.execute("""
        SELECT selected_response, delta_owner, delta_fan, delta_locker_room
        FROM tier2_press_response
        WHERE selected_response IS NOT NULL
    """).fetchall()
    bad_deltas = 0
    for r in responses:
        choice = r['selected_response']
        if choice not in TIER2_VALID_CHOICES:
            bad_deltas += 1
            continue
        expected = TIER2_EFFECTS[choice]
        if (r['delta_owner'] != expected['owner'] or
                r['delta_fan'] != expected['fan'] or
                r['delta_locker_room'] != expected['locker_room']):
            bad_deltas += 1
    ok = check(
        "Effect deltas match TIER2_EFFECTS constants",
        bad_deltas == 0,
        f"mismatched responses: {bad_deltas}/{len(responses)}"
    )
    all_pass = all_pass and ok

    # 7. Trigger diversity
    distinct_triggers = conn.execute("""
        SELECT COUNT(DISTINCT trigger_type) as cnt FROM tier2_press_event
    """).fetchone()['cnt']
    ok = check(
        "Trigger diversity: at least 2 distinct trigger types",
        distinct_triggers >= 2,
        f"distinct triggers: {distinct_triggers}"
    )
    all_pass = all_pass and ok

    # 8. Tier 1 suppression
    overlaps = conn.execute("""
        SELECT COUNT(*) as cnt FROM tier2_press_event t2
        JOIN press_event t1
          ON t1.season_year = t2.season_year
         AND t1.week_number = t2.week_number
         AND t1.team_id = t2.team_id
    """).fetchone()['cnt']
    ok = check(
        "Tier 1 suppression: no overlapping (season, week, team)",
        overlaps == 0,
        f"overlaps: {overlaps}"
    )
    all_pass = all_pass and ok

    # Summary
    print("\n" + "=" * 70)
    if all_pass:
        print("  ALL CHECKS PASSED")
        conn.close()
        sys.exit(0)
    else:
        print("  SOME CHECKS FAILED")
        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
