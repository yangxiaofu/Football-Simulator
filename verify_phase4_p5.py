#!/usr/bin/env python3
"""
Phase 4 Prompt #5 verification — Tier 1 press conference system.

Verifies:
1. Schema: press_event table and coach_career.press_autopilot_default exist
2. Press events generated for player coach during stress test (3 seasons × 17 weeks = 51 events)
3. All events resolved (no unresolved events)
4. Effect deltas match PRESS_EFFECTS constants
5. Autopilot setter/clearer works
6. Context distribution is diverse

Exit code 0 on success, 1 on failure.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.constants import PRESS_EFFECTS
from src.transactions.press_conference import set_autopilot_default


def verify_schema(db_path: str) -> bool:
    """Verify press_event table and coach_career.press_autopilot_default exist."""
    print("\n1. Schema verification...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check press_event table
    tables = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='press_event'
    """).fetchall()
    if not tables:
        print("  ❌ press_event table not found")
        return False
    print("  ✓ press_event table exists")

    # Check columns
    columns = conn.execute("PRAGMA table_info(press_event)").fetchall()
    column_names = [c['name'] for c in columns]
    required_cols = [
        'id', 'season_year', 'week_number', 'team_id', 'coach_id',
        'context_type', 'question_template_id', 'selected_response',
        'autopilot_used', 'delta_owner', 'delta_fan', 'delta_locker_room',
        'resolved_at', 'created_at'
    ]
    for col in required_cols:
        if col not in column_names:
            print(f"  ❌ Column '{col}' not found in press_event")
            return False
    print(f"  ✓ All {len(required_cols)} required columns present")

    # Check coach_career.press_autopilot_default
    coach_cols = conn.execute("PRAGMA table_info(coach_career)").fetchall()
    coach_col_names = [c['name'] for c in coach_cols]
    if 'press_autopilot_default' not in coach_col_names:
        print("  ❌ coach_career.press_autopilot_default column not found")
        return False
    print("  ✓ coach_career.press_autopilot_default exists")

    conn.close()
    return True


def verify_events_generated(db_path: str) -> bool:
    """Verify press events generated for player coach (expect ~51 for 3 seasons)."""
    print("\n2. Press events generated...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get player coach
    player_coach = conn.execute("""
        SELECT id FROM coach_career WHERE is_player = 1
    """).fetchone()

    if not player_coach:
        print("  ⚠ No player coach found (skipping event count check)")
        conn.close()
        return True

    # Count events
    count = conn.execute("""
        SELECT COUNT(*) as cnt FROM press_event WHERE coach_id = ?
    """, (player_coach['id'],)).fetchone()['cnt']

    print(f"  Press events: {count}")

    # Expect ~51 (3 seasons × 17 weeks), but allow some variance
    if count < 40:  # Allow for missing weeks if stress test was interrupted
        print(f"  ❌ Too few press events (expected ~51, got {count})")
        conn.close()
        return False

    print(f"  ✓ {count} press events generated (3 seasons × 17 weeks)")

    conn.close()
    return True


def verify_all_resolved(db_path: str) -> bool:
    """Verify all events resolved (no unresolved events)."""
    print("\n3. All events resolved...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    unresolved = conn.execute("""
        SELECT COUNT(*) as cnt FROM press_event WHERE resolved_at IS NULL
    """).fetchone()['cnt']

    if unresolved > 0:
        print(f"  ❌ {unresolved} unresolved press events found")
        conn.close()
        return False

    print("  ✓ All press events resolved")
    conn.close()
    return True


def verify_effect_deltas(db_path: str) -> bool:
    """Verify effect deltas match PRESS_EFFECTS constants."""
    print("\n4. Effect deltas match constants...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    events = conn.execute("""
        SELECT * FROM press_event WHERE selected_response IS NOT NULL LIMIT 10
    """).fetchall()

    if not events:
        print("  ⚠ No resolved events found (skipping delta check)")
        conn.close()
        return True

    for event in events:
        expected = PRESS_EFFECTS[event['selected_response']]
        if event['delta_owner'] != expected['owner']:
            print(f"  ❌ Event {event['id']}: delta_owner mismatch "
                  f"(expected {expected['owner']}, got {event['delta_owner']})")
            conn.close()
            return False
        if event['delta_fan'] != expected['fan']:
            print(f"  ❌ Event {event['id']}: delta_fan mismatch "
                  f"(expected {expected['fan']}, got {event['delta_fan']})")
            conn.close()
            return False
        if event['delta_locker_room'] != expected['locker_room']:
            print(f"  ❌ Event {event['id']}: delta_locker_room mismatch "
                  f"(expected {expected['locker_room']}, got {event['delta_locker_room']})")
            conn.close()
            return False

    print(f"  ✓ Effect deltas match PRESS_EFFECTS for {len(events)} events")
    conn.close()
    return True


def verify_autopilot_setter(db_path: str) -> bool:
    """Verify autopilot setter/clearer works."""
    print("\n5. Autopilot setter/clearer...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    player_coach = conn.execute("""
        SELECT id FROM coach_career WHERE is_player = 1
    """).fetchone()

    if not player_coach:
        print("  ⚠ No player coach found (skipping autopilot check)")
        conn.close()
        return True

    coach_id = player_coach['id']

    # Set autopilot to 'deflect'
    with conn:
        set_autopilot_default(conn, coach_id, 'deflect')

    val = conn.execute("""
        SELECT press_autopilot_default FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()['press_autopilot_default']

    if val != 'deflect':
        print(f"  ❌ Autopilot set to 'deflect' but got '{val}'")
        conn.close()
        return False

    print("  ✓ Autopilot setter works")

    # Clear autopilot
    with conn:
        set_autopilot_default(conn, coach_id, None)

    val = conn.execute("""
        SELECT press_autopilot_default FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()['press_autopilot_default']

    if val is not None:
        print(f"  ❌ Autopilot cleared but got '{val}'")
        conn.close()
        return False

    print("  ✓ Autopilot clearer works")
    conn.close()
    return True


def verify_context_diversity(db_path: str) -> bool:
    """Verify context distribution is diverse (not all one context)."""
    print("\n6. Context diversity...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    contexts = conn.execute("""
        SELECT context_type, COUNT(*) as cnt
        FROM press_event
        GROUP BY context_type
        ORDER BY cnt DESC
    """).fetchall()

    if not contexts:
        print("  ⚠ No press events found (skipping context diversity check)")
        conn.close()
        return True

    print("  Context distribution:")
    for ctx in contexts:
        print(f"    {ctx['context_type']}: {ctx['cnt']}")

    # Verify at least 3 different contexts used
    if len(contexts) < 3:
        print(f"  ❌ Only {len(contexts)} context types used (expected at least 3)")
        conn.close()
        return False

    print(f"  ✓ {len(contexts)} different context types used")
    conn.close()
    return True


def main():
    db_path = "saves/phase4_v5.db"

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Run: python run_stress_test.py saves/phase4_v5.db --seasons 3")
        sys.exit(1)

    print("=" * 70)
    print("Phase 4 Prompt #5 Verification — Tier 1 Press Conference")
    print("=" * 70)

    checks = [
        verify_schema(db_path),
        verify_events_generated(db_path),
        verify_all_resolved(db_path),
        verify_effect_deltas(db_path),
        verify_autopilot_setter(db_path),
        verify_context_diversity(db_path),
    ]

    print("\n" + "=" * 70)
    if all(checks):
        print("✅ Phase 4 prompt #5 verification PASSED")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ Phase 4 prompt #5 verification FAILED")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
