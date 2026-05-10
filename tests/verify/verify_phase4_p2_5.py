#!/usr/bin/env python3
"""Verification for Phase 4 Build Prompt #2.5 — Baseline Bug Fixes."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.transactions.coaching import assign_coach_to_team

DB = "saves/phase4_v2.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

print("Phase 4 Prompt #2.5 — Baseline Bug Fixes Verification")
print("=" * 60)

# Test 1: Exactly 32 active coaches after generation
print("\n[Test 1] Checking active coach count...")
n_active = conn.execute("SELECT COUNT(*) FROM coach_career WHERE is_active=1").fetchone()[0]
if n_active != 32:
    print(f"❌ FAIL: expected 32 active coaches, got {n_active}")
    sys.exit(1)
print(f"✓ PASS: {n_active} active coaches")

# Test 2: No team has multiple active coaches
print("\n[Test 2] Checking for duplicate coaches per team...")
dupes = conn.execute("""
    SELECT current_team_id FROM coach_career
    WHERE is_active=1 AND current_team_id IS NOT NULL
    GROUP BY current_team_id HAVING COUNT(*) > 1
""").fetchall()
if len(dupes) > 0:
    print(f"❌ FAIL: teams with duplicate coaches: {[r[0] for r in dupes]}")
    sys.exit(1)
print("✓ PASS: no duplicate coaches on any team")

# Test 3: Displacement test — assign new coach to occupied team
print("\n[Test 3] Testing displacement logic...")
target_team_id = conn.execute("SELECT id FROM team LIMIT 1").fetchone()[0]
existing_coach_id = conn.execute(
    "SELECT id FROM coach_career WHERE current_team_id=? AND is_active=1",
    (target_team_id,)
).fetchone()[0]

# Create a fresh AI coach (not yet assigned)
cur = conn.execute("""
    INSERT INTO coach_career (first_name, last_name, age, personality_archetype,
                              career_start_year, current_team_id, is_player, is_active)
    VALUES ('Test', 'Replacement', 50, 'analytics', 2024, NULL, 0, 1)
""")
new_coach_id = cur.lastrowid

# Assign new coach to target team — should displace existing coach
assign_coach_to_team(conn, new_coach_id, target_team_id, 2024)

# Verify: existing coach is now between jobs
existing_after = conn.execute(
    "SELECT current_team_id, is_active FROM coach_career WHERE id=?",
    (existing_coach_id,)
).fetchone()
if existing_after['current_team_id'] is not None:
    print(f"❌ FAIL: displaced coach still has team: {existing_after['current_team_id']}")
    sys.exit(1)
if existing_after['is_active'] != 1:
    print("❌ FAIL: displaced coach should still be active")
    sys.exit(1)
print("✓ PASS: displaced coach is between jobs and still active")

# Verify: existing coach's tenure was closed with 'replaced'
prev_tenure = conn.execute("""
    SELECT end_year, end_reason FROM coach_tenure
    WHERE coach_id=? AND team_id=? AND end_year IS NOT NULL
    ORDER BY id DESC LIMIT 1
""", (existing_coach_id, target_team_id)).fetchone()
if prev_tenure is None:
    print("❌ FAIL: displaced coach has no closed tenure")
    sys.exit(1)
if prev_tenure['end_reason'] != 'replaced':
    print(f"❌ FAIL: expected end_reason='replaced', got '{prev_tenure['end_reason']}'")
    sys.exit(1)
print("✓ PASS: displaced coach's tenure closed with 'replaced'")

# Verify: new coach is active on target team
new_after = conn.execute(
    "SELECT current_team_id FROM coach_career WHERE id=?", (new_coach_id,)
).fetchone()
if new_after['current_team_id'] != target_team_id:
    print("❌ FAIL: new coach not assigned to target team")
    sys.exit(1)
print("✓ PASS: new coach assigned to target team")

# Verify: target team has exactly one active coach
n_on_team = conn.execute(
    "SELECT COUNT(*) FROM coach_career WHERE current_team_id=? AND is_active=1",
    (target_team_id,)
).fetchone()[0]
if n_on_team != 1:
    print(f"❌ FAIL: target team has {n_on_team} active coaches, expected 1")
    sys.exit(1)
print("✓ PASS: target team has exactly one active coach")

print("\n" + "=" * 60)
print("✅ Phase 4 prompt #2.5 verification (coach fixes) passed.")
conn.close()
