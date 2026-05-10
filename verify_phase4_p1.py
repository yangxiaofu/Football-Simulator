#!/usr/bin/env python3
"""
Phase 4 Prompt #1 Verification Script.

Tests:
1. Schema: coach_career and coach_tenure tables exist with correct columns
2. 33 coaches total (32 AI + 1 player)
3. Personality sync invariant: team.gm_personality == coach_career.personality_archetype
4. Player team pointer: league.user_team_id == player coach's current_team_id
5. Open tenures: every active coach has exactly one open tenure (end_year IS NULL)
6. Reassignment: assign_coach_to_team correctly closes old tenure and opens new
7. Vacancy: removing a coach (team_id=None) does NOT touch league.user_team_id for player coach

Exit criteria: prints "Phase 4 prompt #1 verification passed." and exits 0.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

SAVE_PATH = "saves/phase4_test.db"


def generate_fresh_db():
    """Generate a fresh franchise database for testing."""
    if Path(SAVE_PATH).exists():
        Path(SAVE_PATH).unlink()

    result = subprocess.run(
        [
            sys.executable, "generate.py", SAVE_PATH,
            "--season", "2024",
            "--coach-first-name", "Bill",
            "--coach-last-name", "Walsh",
            "--coach-archetype", "analytics",
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAIL: generate.py failed:\n{result.stdout}\n{result.stderr}")
        sys.exit(1)
    print("Generated fresh database.")


def run_tests():
    from src.db import get_connection
    from src.transactions.coaching import assign_coach_to_team

    conn = get_connection(SAVE_PATH)
    errors = []

    # -------------------------------------------------------
    # Test 1: Schema — tables exist with expected columns
    # -------------------------------------------------------
    print("Test 1: Schema validation...")
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for tbl in ('coach_career', 'coach_tenure'):
        if tbl not in tables:
            errors.append(f"Table {tbl} missing from schema")

    # Check coach_career columns
    cc_cols = {row[1] for row in conn.execute("PRAGMA table_info(coach_career)").fetchall()}
    for col in ('id', 'first_name', 'last_name', 'age', 'personality_archetype',
                'career_start_year', 'current_team_id', 'is_player', 'is_active'):
        if col not in cc_cols:
            errors.append(f"coach_career missing column: {col}")

    # Check coach_tenure columns
    ct_cols = {row[1] for row in conn.execute("PRAGMA table_info(coach_tenure)").fetchall()}
    for col in ('id', 'coach_id', 'team_id', 'start_year', 'end_year', 'end_reason'):
        if col not in ct_cols:
            errors.append(f"coach_tenure missing column: {col}")

    # Check legacy_score has coach_id
    ls_cols = {row[1] for row in conn.execute("PRAGMA table_info(legacy_score)").fetchall()}
    if 'coach_id' not in ls_cols:
        errors.append("legacy_score missing column: coach_id")

    # Check hall_of_fame has coach_id
    hof_cols = {row[1] for row in conn.execute("PRAGMA table_info(hall_of_fame)").fetchall()}
    if 'coach_id' not in hof_cols:
        errors.append("hall_of_fame missing column: coach_id")

    if not errors:
        print("  PASS")
    else:
        for e in errors:
            print(f"  FAIL: {e}")

    # -------------------------------------------------------
    # Test 2: 33 coaches (32 AI + 1 player)
    # -------------------------------------------------------
    print("Test 2: Coach count...")
    total = conn.execute("SELECT COUNT(*) FROM coach_career").fetchone()[0]
    ai_count = conn.execute(
        "SELECT COUNT(*) FROM coach_career WHERE is_player = 0"
    ).fetchone()[0]
    player_count = conn.execute(
        "SELECT COUNT(*) FROM coach_career WHERE is_player = 1"
    ).fetchone()[0]

    if total != 33:
        errors.append(f"Expected 33 coaches, got {total}")
    if ai_count != 32:
        errors.append(f"Expected 32 AI coaches, got {ai_count}")
    if player_count != 1:
        errors.append(f"Expected 1 player coach, got {player_count}")
    if not errors:
        print("  PASS")
    else:
        for e in errors[-3:]:
            print(f"  FAIL: {e}")

    # -------------------------------------------------------
    # Test 3: Personality sync invariant
    # -------------------------------------------------------
    print("Test 3: Personality sync (Invariant #12)...")
    mismatches = conn.execute("""
        SELECT t.id, t.gm_personality, c.personality_archetype
        FROM team t
        JOIN coach_career c ON c.current_team_id = t.id
        WHERE t.gm_personality != c.personality_archetype
    """).fetchall()
    if mismatches:
        for m in mismatches:
            errors.append(
                f"Team {m[0]}: gm_personality={m[1]}, coach archetype={m[2]}"
            )
        print(f"  FAIL: {len(mismatches)} mismatches")
    else:
        print("  PASS")

    # -------------------------------------------------------
    # Test 4: Player team pointer (Invariant #11)
    # -------------------------------------------------------
    print("Test 4: Player team pointer (Invariant #11)...")
    league = conn.execute("SELECT user_team_id FROM league WHERE id = 1").fetchone()
    player_coach = conn.execute(
        "SELECT current_team_id, first_name, last_name, personality_archetype FROM coach_career WHERE is_player = 1"
    ).fetchone()

    if league['user_team_id'] != player_coach['current_team_id']:
        errors.append(
            f"league.user_team_id={league['user_team_id']} != "
            f"player coach current_team_id={player_coach['current_team_id']}"
        )
        print("  FAIL")
    else:
        print("  PASS")

    # Verify player coach identity
    if player_coach['first_name'] != 'Bill' or player_coach['last_name'] != 'Walsh':
        errors.append(
            f"Player coach name: {player_coach['first_name']} {player_coach['last_name']}, expected Bill Walsh"
        )
    if player_coach['personality_archetype'] != 'analytics':
        errors.append(
            f"Player coach archetype: {player_coach['personality_archetype']}, expected analytics"
        )

    # -------------------------------------------------------
    # Test 5: Open tenures — every coach with a current_team_id has exactly 1 open tenure
    # -------------------------------------------------------
    print("Test 5: Open tenure integrity...")
    bad_tenures = conn.execute("""
        SELECT c.id, COUNT(ct.id) as open_count
        FROM coach_career c
        LEFT JOIN coach_tenure ct ON ct.coach_id = c.id AND ct.end_year IS NULL
        WHERE c.current_team_id IS NOT NULL
        GROUP BY c.id
        HAVING open_count != 1
    """).fetchall()
    if bad_tenures:
        for bt in bad_tenures:
            errors.append(f"Coach {bt[0]} has {bt[1]} open tenures (expected 1)")
        print(f"  FAIL: {len(bad_tenures)} coaches with wrong tenure count")
    else:
        print("  PASS")

    # -------------------------------------------------------
    # Test 6: Reassignment — move AI coach to different team
    # -------------------------------------------------------
    print("Test 6: Reassignment behavior...")
    # Pick an AI coach and reassign to a different team
    ai_coach = conn.execute(
        "SELECT id, current_team_id FROM coach_career WHERE is_player = 0 LIMIT 1"
    ).fetchone()
    old_team = ai_coach['current_team_id']

    # Find a different team
    other_team = conn.execute(
        "SELECT id FROM team WHERE id != ? LIMIT 1", (old_team,)
    ).fetchone()['id']

    # Remove old team's coach reference first (to avoid 2 coaches on 1 team)
    assign_coach_to_team(conn, ai_coach['id'], other_team, 2024, end_reason_for_previous='fired')

    # Verify old tenure is closed
    old_tenure = conn.execute(
        """SELECT end_year, end_reason FROM coach_tenure
           WHERE coach_id = ? AND team_id = ? AND end_year IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (ai_coach['id'], old_team)
    ).fetchone()
    if old_tenure is None:
        errors.append("Old tenure not found after reassignment")
    elif old_tenure['end_reason'] != 'fired':
        errors.append(f"Old tenure end_reason={old_tenure['end_reason']}, expected 'fired'")

    # Verify new tenure is open
    new_tenure = conn.execute(
        """SELECT end_year, end_reason FROM coach_tenure
           WHERE coach_id = ? AND team_id = ? AND end_year IS NULL""",
        (ai_coach['id'], other_team)
    ).fetchone()
    if new_tenure is None:
        errors.append("New open tenure not created after reassignment")

    # Verify personality sync on new team
    new_team_row = conn.execute(
        "SELECT gm_personality FROM team WHERE id = ?", (other_team,)
    ).fetchone()
    coach_arch = conn.execute(
        "SELECT personality_archetype FROM coach_career WHERE id = ?",
        (ai_coach['id'],)
    ).fetchone()['personality_archetype']
    if new_team_row['gm_personality'] != coach_arch:
        errors.append(
            f"After reassignment: team personality={new_team_row['gm_personality']}, "
            f"coach archetype={coach_arch}"
        )

    if not any("reassignment" in e or "tenure" in e for e in errors):
        print("  PASS")
    else:
        for e in errors:
            if "reassignment" in e or "tenure" in e:
                print(f"  FAIL: {e}")

    # -------------------------------------------------------
    # Test 7: Vacancy — removing player coach does NOT touch league.user_team_id
    # -------------------------------------------------------
    print("Test 7: Vacancy state...")
    player_coach_row = conn.execute(
        "SELECT id, current_team_id FROM coach_career WHERE is_player = 1"
    ).fetchone()
    user_team_before = conn.execute(
        "SELECT user_team_id FROM league WHERE id = 1"
    ).fetchone()['user_team_id']

    # Remove player coach from team (vacancy)
    assign_coach_to_team(
        conn, player_coach_row['id'], None, 2024, end_reason_for_previous='fired'
    )

    user_team_after = conn.execute(
        "SELECT user_team_id FROM league WHERE id = 1"
    ).fetchone()['user_team_id']
    player_coach_team = conn.execute(
        "SELECT current_team_id FROM coach_career WHERE id = ?",
        (player_coach_row['id'],)
    ).fetchone()['current_team_id']

    if player_coach_team is not None:
        errors.append(f"Player coach current_team_id should be NULL, got {player_coach_team}")
    if user_team_after != user_team_before:
        errors.append(
            f"league.user_team_id changed during vacancy: {user_team_before} -> {user_team_after}"
        )

    # Restore player coach for clean state
    assign_coach_to_team(
        conn, player_coach_row['id'], user_team_before, 2024
    )

    if not any("Vacancy" in e or "vacancy" in e or "user_team_id changed" in e for e in errors):
        print("  PASS")
    else:
        for e in errors:
            if "vacancy" in e.lower() or "user_team_id" in e:
                print(f"  FAIL: {e}")

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    conn.close()

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("Phase 4 prompt #1 verification passed.")
        return 0


if __name__ == '__main__':
    generate_fresh_db()
    sys.exit(run_tests())
