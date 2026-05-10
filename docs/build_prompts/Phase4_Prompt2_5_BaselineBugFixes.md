# Phase 4 Build Prompt #2.5 — Baseline Bug Fixes

**Model**: Sonnet
**Planning mode**: Yes — small surface area, but two distinct bugs in different files; lay out the plan first.

---

## Context

Phase 4 prompt #2 (multi-season stress harness) is complete and surfaced 4 invariant failures. Two are blocking the next prompt (#3 — AI GM behavior) and need to be fixed before we proceed. Two others are deferred.

This is a surgical fix prompt. Total scope is small. The point is to get the harness to pass 10+ of 12 invariants so prompt #3 has a clean platform.

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_StressTest_BaselineFindings.md` — the baseline findings doc from prompt #2
3. `docs/Phase4_DesignDecisions.md` §2.4 (the `assign_coach_to_team` contract) and §3.2 invariants #4, #8, #12

## Goal

Fix two bugs surfaced by the stress harness:

1. **Invariant #8 (BAL has 2 coaches)** — a Phase 4 prompt #1 regression. The user's team gets both an AI coach (from `generate_ai_coaches`) and a player coach (from `generate.py`). Both have open tenures. The team has 2 active coaches.
2. **Invariant #4 (AI teams grow ~7 players/season)** — a pre-existing Phase 3 bug. Roster cuts are gated to the user's team only. AI teams never trim their rosters in the offseason, so they grow unboundedly.

Invariant #12 (coach-team personality sync) cascades from #8 and should pass automatically once #8 is fixed. Verify after the fix.

Invariants #5 (no contracts generated in Phase 0) is **deferred** — do NOT attempt to fix it in this prompt. It's a deeper Phase 0 gap that needs its own investigation.

## Tasks

### Task 1 — Fix BAL duplicate coach

The bug is in two places, both of which need addressing:

**1a. Generation-time fix** (efficient path):

In `src/generation/teams.py`, modify `generate_ai_coaches(conn, season_year)` to accept a `skip_team_id` parameter and skip generating an AI coach for that team. The user's team will get its player coach from `generate.py` instead.

```python
def generate_ai_coaches(conn, season_year, skip_team_id=None):
    """Create one AI coach per team, skipping skip_team_id if provided.
    The skipped team will have its head coach assigned via the player coach
    flow in generate.py."""
    ...
```

In `generate.py`, update the call to pass the user's team ID:

```python
generate_ai_coaches(conn, season_year, skip_team_id=user_team_id)
```

After this fix, fresh franchise generation produces exactly 32 active coaches (31 AI + 1 player), all assigned to distinct teams.

**1b. Runtime fix — coach displacement in `assign_coach_to_team`** (durable fix):

The current `assign_coach_to_team` only closes the *coach's* prior tenure (if they had one). It does NOT close the *team's* prior coach's tenure. This will bite us in Phase 4 prompt #3 when AI coaches start getting fired and replaced. Fix it now.

Add a "Step 0" to `src/transactions/coaching.py`:

```python
def assign_coach_to_team(conn, coach_id, team_id, season_year, end_reason_for_previous='current'):
    """The single mutation point for coach assignment.

    Step 0 (NEW): If team_id is not None and another active coach is currently
    assigned to that team, displace them — close their open tenure with
    end_reason='replaced', set their current_team_id=NULL, leave is_active=1.

    Steps 1-4: unchanged from prompt #1.
    """
    # Step 0: Displace existing coach on destination team
    if team_id is not None:
        existing = conn.execute(
            "SELECT id FROM coach_career WHERE current_team_id=? AND is_active=1 AND id != ?",
            (team_id, coach_id)
        ).fetchone()
        if existing:
            displaced_coach_id = existing[0]
            # Close their open tenure
            conn.execute("""
                UPDATE coach_tenure
                SET end_year=?, end_reason='replaced'
                WHERE coach_id=? AND end_year IS NULL
            """, (season_year, displaced_coach_id))
            # Mark them as between jobs (still active, no team)
            conn.execute(
                "UPDATE coach_career SET current_team_id=NULL WHERE id=?",
                (displaced_coach_id,)
            )

    # Steps 1-4: existing logic unchanged
    ...
```

Add `'replaced'` to `COACH_TENURE_END_REASONS` in `src/utils/constants.py`:

```python
COACH_TENURE_END_REASONS = ('fired', 'resigned', 'mutual', 'championship_walkout', 'current', 'replaced')
```

### Task 2 — Fix AI roster cuts

Find the roster-cut gate in the offseason loop. Likely locations:
- `src/league/offseason.py` — search for any phase function that filters by `user_team_id` or `team_id == user_team_id`
- Look specifically for the `final_cuts` / `roster_cuts` / `training_camp` phase (whatever it's named)
- The bug pattern is something like:

```python
if team_id == user_team_id:
    apply_roster_cuts(conn, team_id, ...)
```

Or:

```python
for team_id in [user_team_id]:  # should iterate all 32 teams
    apply_roster_cuts(...)
```

Fix: remove the gate. Roster cuts must run for all 32 teams during the cuts phase. AI teams should be cut down to the 53-man active roster + 16-man practice squad limit identically to the user's team.

If the AI cut logic doesn't exist (only the user team has cut logic), implement a simple AI version: cut to 53 active by removing the lowest-rated players at each position group while respecting position-minimum rules from `src/utils/constants.py`. This should mirror what the user's auto-cut would do if no manual selections were made.

Document the change in a comment so future readers know this was a baseline fix.

## Constraints — what NOT to touch

- Do NOT modify the stress harness, invariant battery, or health report from prompt #2.
- Do NOT attempt to fix Invariant #5 (no contracts generated). That's a deeper Phase 0 gap deferred to a later prompt.
- Do NOT modify any AI behavior logic (trades, FA, draft) — those are pre-existing and out of scope.
- Do NOT add new coach personality logic — that's prompt #3.

## Test plan

### Step 1 — Verify the bug fixes on a fresh generation

```bash
rm -f saves/phase4_v2.db
python generate.py saves/phase4_v2.db --season 2024
```

Then a quick inline check:

```bash
sqlite3 saves/phase4_v2.db "SELECT COUNT(*) FROM coach_career WHERE is_active=1;"
# Expected: 32

sqlite3 saves/phase4_v2.db "SELECT current_team_id, COUNT(*) FROM coach_career WHERE is_active=1 GROUP BY current_team_id HAVING COUNT(*) > 1;"
# Expected: 0 rows (no team has more than one active coach)
```

### Step 2 — Test displacement logic

Create `verify_phase4_p2_5.py` in the project root:

```python
"""Verification for Phase 4 Build Prompt #2.5 — Baseline Bug Fixes."""
import sqlite3
import sys
import random

sys.path.insert(0, ".")
from src.transactions.coaching import assign_coach_to_team

DB = "saves/phase4_v2.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# 1. Coach count after generation
n_active = conn.execute("SELECT COUNT(*) FROM coach_career WHERE is_active=1").fetchone()[0]
assert n_active == 32, f"expected 32 active coaches, got {n_active}"

# 2. No team has multiple active coaches
dupes = conn.execute("""
    SELECT current_team_id FROM coach_career
    WHERE is_active=1 AND current_team_id IS NOT NULL
    GROUP BY current_team_id HAVING COUNT(*) > 1
""").fetchall()
assert len(dupes) == 0, f"teams with duplicate coaches: {[r[0] for r in dupes]}"

# 3. Displacement test — create a new AI coach and assign to existing team
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
assign_coach_to_team(conn, new_coach_id, target_team_id, 2024, end_reason_for_previous='current')

# Verify: existing coach is now between jobs
existing_after = conn.execute(
    "SELECT current_team_id, is_active FROM coach_career WHERE id=?",
    (existing_coach_id,)
).fetchone()
assert existing_after['current_team_id'] is None, \
    f"displaced coach still has team: {existing_after['current_team_id']}"
assert existing_after['is_active'] == 1, "displaced coach should still be active (between jobs)"

# Verify: existing coach's tenure was closed with 'replaced'
prev_tenure = conn.execute("""
    SELECT end_year, end_reason FROM coach_tenure
    WHERE coach_id=? AND team_id=? AND end_year IS NOT NULL
    ORDER BY id DESC LIMIT 1
""", (existing_coach_id, target_team_id)).fetchone()
assert prev_tenure is not None, "displaced coach has no closed tenure"
assert prev_tenure['end_reason'] == 'replaced', \
    f"expected end_reason='replaced', got '{prev_tenure['end_reason']}'"

# Verify: new coach is active on target team
new_after = conn.execute(
    "SELECT current_team_id FROM coach_career WHERE id=?", (new_coach_id,)
).fetchone()
assert new_after['current_team_id'] == target_team_id, "new coach not assigned"

# Verify: target team has exactly one active coach
n_on_team = conn.execute(
    "SELECT COUNT(*) FROM coach_career WHERE current_team_id=? AND is_active=1",
    (target_team_id,)
).fetchone()[0]
assert n_on_team == 1, f"target team has {n_on_team} active coaches, expected 1"

print("Phase 4 prompt #2.5 verification (coach fixes) passed.")
```

```bash
python verify_phase4_p2_5.py
```

### Step 3 — Re-run the stress harness

```bash
rm -f saves/phase4_stress_v2.db
python generate.py saves/phase4_stress_v2.db --season 2024
python run_stress_test.py saves/phase4_stress_v2.db --invariants --seasons 3
```

**Expected after fixes**:
- Invariant #4 (roster integrity) → PASS (rosters stable at 53 active across all 32 teams)
- Invariant #8 (coach assignment) → PASS (one coach per team, no duplicates)
- Invariant #12 (coach-team personality sync) → PASS (cascade resolution from #8)
- Invariant #5 (contract continuity) → still FAIL (deferred)

Final score should be **10 PASS / 1 FAIL / 1 SKIP** (Inv 5 fails, Inv 10 retirement was skipped per the prompt #2 baseline).

### Step 4 — Update baseline findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #2.5 fixes applied (2026-MM-DD)

Fixed:
- Inv 8: BAL duplicate coach (root cause: AI coach generation didn't skip user's team)
- Inv 4: AI roster growth (root cause: Phase 3 roster cuts gated to user team only)
- Inv 12: cascade fix (no longer fails once #8 is fixed)

Remaining failures:
- Inv 5: no contracts generated in Phase 0 — deferred for separate investigation

Post-fix invariant pass rate: 10/12 (1 fail, 1 skip)
```

### Step 5 — Update CLAUDE.md

Append to the Phase 4 checklist:

```
- [x] Save model refactor
- [x] Multi-season stress harness + invariant battery + League Health Report
- [x] Baseline bug fixes (Inv 8, Inv 4, Inv 12 cascade)
- [ ] AI GM team-phase classifier + transition rules
...
```

## Reference

- `docs/Phase4_DesignDecisions.md` §2.4 (assign_coach_to_team contract — now extended with Step 0 displacement)
- `docs/Phase4_DesignDecisions.md` §3.2 invariants #4, #8, #12
- `docs/Phase4_StressTest_BaselineFindings.md` — what the harness found
