#!/usr/bin/env python3
"""
Phase 4 Prompt #3 Verification Script — AI GM Behavior.

Tests:
1. Behavior matrix has exactly 25 cells, get_behavior_signature() returns valid profiles
2. All 32 teams have valid team_phase values after classification
3. At least 2 distinct phases exist (phase diversity)
4. Coaching carousel creates/fires correctly (coach count stays 32 per team)
5. Personality sync still holds after carousel (Invariant #12)
6. Phase-aware draft/FA/trade imports work without circular dependency

Exit criteria: prints "Phase 4 prompt #3 verification passed." and exits 0.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

SAVE_PATH = "saves/phase4_p3_test.db"


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
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"FAIL: generate.py failed:\n{result.stdout}\n{result.stderr}")
        sys.exit(1)
    print("Generated fresh database.")


def run_tests():
    from src.db.connection import get_connection
    from src.utils.ai_behavior_matrix import BEHAVIOR_MATRIX, get_behavior_signature
    from src.utils.constants import (
        TEAM_PHASES, GM_PERSONALITIES_TUPLE, TEAM_PHASE_DEFAULT,
    )
    from src.league.team_phase import compute_team_phase, update_all_team_phases
    from src.transactions.coaching_carousel import run_coaching_carousel

    conn = get_connection(SAVE_PATH)
    errors = []

    # -------------------------------------------------------
    # Test 1: Behavior matrix completeness
    # -------------------------------------------------------
    print("Test 1: Behavior matrix has 25 cells...")
    expected_count = len(GM_PERSONALITIES_TUPLE) * len(TEAM_PHASES)
    actual_count = len(BEHAVIOR_MATRIX)
    if actual_count != expected_count:
        errors.append(f"Behavior matrix has {actual_count} cells, expected {expected_count}")
    else:
        print(f"  PASS ({actual_count} cells)")

    # Verify all keys are valid combinations
    for (pers, phase), profile in BEHAVIOR_MATRIX.items():
        if pers not in GM_PERSONALITIES_TUPLE:
            errors.append(f"Unknown personality in matrix: {pers}")
        if phase not in TEAM_PHASES:
            errors.append(f"Unknown phase in matrix: {phase}")
        for key in ('fa_aggression_mult', 'trade_willingness_mult', 'overpay_mult',
                     'draft_strategy', 'max_fa_offers_mult', 'trade_vets_for_picks'):
            if key not in profile:
                errors.append(f"Missing key '{key}' in ({pers}, {phase})")

    # Test get_behavior_signature fallback
    fallback = get_behavior_signature('unknown_personality', 'unknown_phase')
    if fallback is None:
        errors.append("get_behavior_signature returned None for unknown inputs")
    elif fallback.get('draft_strategy') != 'bpa':
        errors.append(f"Fallback draft_strategy is {fallback.get('draft_strategy')}, expected 'bpa'")

    # -------------------------------------------------------
    # Test 2: Team phase column exists and classification works
    # -------------------------------------------------------
    print("Test 2: Team phase classification...")
    # Verify column exists
    team_cols = {row[1] for row in conn.execute("PRAGMA table_info(team)").fetchall()}
    if 'team_phase' not in team_cols:
        errors.append("team table missing 'team_phase' column")

    # Run classification
    phase_results = update_all_team_phases(conn, 2024)
    if len(phase_results) != 32:
        errors.append(f"Phase classification returned {len(phase_results)} teams, expected 32")

    # Verify all phases are valid
    invalid_phases = [
        (tid, phase) for tid, phase in phase_results.items()
        if phase not in TEAM_PHASES
    ]
    if invalid_phases:
        errors.append(f"Invalid phases: {invalid_phases}")

    if not any("phase" in e.lower() for e in errors):
        print(f"  PASS (32 teams classified)")

    # -------------------------------------------------------
    # Test 3: Phase diversity — at least 2 distinct phases
    # -------------------------------------------------------
    print("Test 3: Phase diversity...")
    distinct_phases = set(phase_results.values())
    if len(distinct_phases) < 2:
        errors.append(f"Only {len(distinct_phases)} distinct phase(s): {distinct_phases}")
        print(f"  FAIL: only {distinct_phases}")
    else:
        print(f"  PASS ({len(distinct_phases)} distinct phases: {sorted(distinct_phases)})")

    # -------------------------------------------------------
    # Test 4: Coaching carousel mechanics
    # -------------------------------------------------------
    print("Test 4: Coaching carousel...")

    # Count coaches before
    coach_count_before = conn.execute(
        "SELECT COUNT(*) FROM coach_career WHERE is_active = 1"
    ).fetchone()[0]

    # Count teams with coaches before
    teams_with_coaches_before = conn.execute(
        "SELECT COUNT(DISTINCT current_team_id) FROM coach_career WHERE current_team_id IS NOT NULL AND is_active = 1"
    ).fetchone()[0]

    # Run carousel (may not fire anyone in fresh DB with no season history)
    carousel_results = run_coaching_carousel(conn, 2024)
    print(f"  Carousel fired/hired: {len(carousel_results)} coaches")

    # Verify every team still has exactly one active coach
    teams_with_coaches_after = conn.execute("""
        SELECT t.id, COUNT(c.id) as coach_count
        FROM team t
        LEFT JOIN coach_career c ON c.current_team_id = t.id AND c.is_active = 1
        GROUP BY t.id
        HAVING coach_count != 1
    """).fetchall()
    if teams_with_coaches_after:
        for row in teams_with_coaches_after:
            errors.append(f"Team {row[0]} has {row[1]} active coaches (expected 1)")
        print(f"  FAIL: {len(teams_with_coaches_after)} teams with wrong coach count")
    else:
        print("  PASS (all teams have exactly 1 coach)")

    # -------------------------------------------------------
    # Test 5: Personality sync after carousel (Invariant #12)
    # -------------------------------------------------------
    print("Test 5: Personality sync after carousel (Invariant #12)...")
    mismatches = conn.execute("""
        SELECT t.id, t.gm_personality, c.personality_archetype
        FROM team t
        JOIN coach_career c ON c.current_team_id = t.id AND c.is_active = 1
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
    # Test 6: No circular imports — behavior matrix integrations
    # -------------------------------------------------------
    print("Test 6: Behavior matrix integration imports...")
    try:
        from src.transactions.trades import _apply_gm_personality
        from src.transactions.free_agency import run_ai_fa_signings
        from src.transactions.draft import run_ai_pick
        print("  PASS (all imports successful)")
    except ImportError as e:
        errors.append(f"Import failed: {e}")
        print(f"  FAIL: {e}")

    # -------------------------------------------------------
    # Test 7: DB reads — verify stored team_phase values
    # -------------------------------------------------------
    print("Test 7: Stored team_phase values in DB...")
    stored_phases = conn.execute(
        "SELECT id, team_phase FROM team ORDER BY id"
    ).fetchall()
    bad_stored = [
        (row['id'], row['team_phase']) for row in stored_phases
        if row['team_phase'] not in TEAM_PHASES
    ]
    if bad_stored:
        errors.append(f"Invalid stored phases: {bad_stored}")
        print(f"  FAIL: {bad_stored}")
    else:
        print(f"  PASS (32 teams with valid stored phases)")

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
        print("Phase 4 prompt #3 verification passed.")
        return 0


if __name__ == '__main__':
    generate_fresh_db()
    sys.exit(run_tests())
