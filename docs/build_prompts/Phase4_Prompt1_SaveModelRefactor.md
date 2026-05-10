# Phase 4 Build Prompt #1 — Save Model Refactor

**Model**: Opus
**Planning mode**: Yes — schema-touching, multi-file, defines the foundation for all of Phase 4. Lay out the plan before writing code.

---

## Context

You are implementing Phase 4 of the Football Simulator project (NFL franchise simulator in Python 3.11 / SQLite). Phases 0–3 are complete. Phase 4 introduces the dynasty layer: portable coach identity, multi-team careers, owner pressure, hot seat, legacy expansion, AI GM behavior maturation, and historical records.

This prompt is the foundational refactor that everything else in Phase 4 depends on. Get it right.

**Read first, in this order**:
1. `CLAUDE.md` — project conventions, layer boundaries, code quality rules
2. `docs/Phase4_DesignDecisions.md` — full Phase 4 design. Pay closest attention to §2 (Save Model Refactor) and §3.2 invariants #11 and #12. §1.7, §1.8, and §8 item 9 also constrain this work.
3. `src/db/schema.sql` — current schema. Note especially the `team` table (line 38, including `gm_personality` column) and the `league` table (line 14, including `user_team_id`).
4. `src/db/connection.py` — observe the existing `ensure_*_tables()` migration helper pattern from Phase 3 (`ensure_fa_tables`, `ensure_franchise_tag_table`, `ensure_offseason_state_table`, `ensure_scouting_tables`).
5. `src/generation/teams.py` — current franchise generation, particularly `initialize_league()` (line 112) and the team creation loop above it. The `gm_personality` field is set per team during generation here.

## Goal

Add coach identity as a first-class entity to the data model. The coach is portable across franchises (required by the Fired → reassign decision in §1.2 of the design doc). `assign_coach_to_team` is the single mutation point that keeps `coach_career.current_team_id`, `team.gm_personality`, and `league.user_team_id` in sync.

**Critical constraint**: initial league behavior after generation must be byte-identical to Phase 3. None of the 30+ existing `team['gm_personality']` reads should observe any change. The refactor is purely additive at the schema level and at the call-site level.

## Tasks

### Task 1 — Schema additions

Add to `src/db/schema.sql`:

```sql
-- ====================
-- 8. COACH IDENTITY (Phase 4)
-- ====================

-- One row per coach (player + AI). Coach identity persists across teams.
CREATE TABLE coach_career (
    id                    INTEGER PRIMARY KEY,
    first_name            TEXT NOT NULL,
    last_name             TEXT NOT NULL,
    age                   INTEGER NOT NULL,
    personality_archetype TEXT NOT NULL,    -- same vocabulary as team.gm_personality:
                                            -- 'draft_purist' | 'win_now' | 'analytics' | 'loyalty' | 'opportunist'
    career_start_year     INTEGER NOT NULL,
    current_team_id       INTEGER,           -- NULL when between jobs
    is_player             INTEGER NOT NULL DEFAULT 0,
    is_active             INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (current_team_id) REFERENCES team(id)
);

CREATE INDEX idx_coach_career_active ON coach_career(is_active, is_player);
CREATE INDEX idx_coach_career_team ON coach_career(current_team_id);

-- One row per stop in a coach's career. Open tenure has end_year IS NULL.
CREATE TABLE coach_tenure (
    id              INTEGER PRIMARY KEY,
    coach_id        INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    start_year      INTEGER NOT NULL,
    end_year        INTEGER,                 -- NULL while active
    end_reason      TEXT,                    -- 'fired' | 'resigned' | 'mutual' | 'championship_walkout' | 'current'
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX idx_coach_tenure_coach ON coach_tenure(coach_id, end_year);
```

ALTER existing tables (additive only):

```sql
ALTER TABLE legacy_score ADD COLUMN coach_id INTEGER REFERENCES coach_career(id);
ALTER TABLE hall_of_fame ADD COLUMN coach_id INTEGER REFERENCES coach_career(id);
```

The new `legacy_score.coach_id` and `hall_of_fame.coach_id` columns are added now but NOT yet wired into any aggregation logic. That's Phase 4 prompt #7.

### Task 2 — Migration helper

In `src/db/connection.py`, add `ensure_coach_tables(conn)` following the existing `ensure_*_tables()` pattern. It must:

- Be idempotent (safe to call on a database that already has the tables)
- Create `coach_career`, `coach_tenure`, and their indexes if missing
- Run the two ALTER TABLE statements wrapped in try/except (column may already exist on re-run)

Wire `ensure_coach_tables(conn)` into the same code path as the other `ensure_*` functions. Do not skip this — Phase 3 saves opened with Phase 4 code must auto-migrate the schema.

### Task 3 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Coach generation" section:

```python
# Phase 4 — Coach generation
COACH_MIN_AGE = 35
COACH_MAX_AGE = 65
DEFAULT_PLAYER_COACH_FIRST_NAME = "Head"
DEFAULT_PLAYER_COACH_LAST_NAME = "Coach"
DEFAULT_PLAYER_COACH_ARCHETYPE = "analytics"

COACH_TENURE_END_REASONS = ('fired', 'resigned', 'mutual', 'championship_walkout', 'current')
GM_PERSONALITIES_TUPLE = ('draft_purist', 'win_now', 'analytics', 'loyalty', 'opportunist')
```

(The existing `GM_PERSONALITIES` list referenced by `src/generation/teams.py` line 74 stays; the new tuple is for validation in the coach helper.)

### Task 4 — Single mutation helper

Create a new file `src/transactions/coaching.py`:

```python
"""Coach assignment and tenure management (Phase 4).

This module owns the single mutation point for coach assignment.
Per docs/Phase4_DesignDecisions.md §2.4, this is the ONLY code path that
should write to:
  - coach_career.current_team_id
  - coach_career.is_active
  - team.gm_personality
  - league.user_team_id

If invariants #11 or #12 in §3.2 ever fail, search for direct writes outside
this module — they are bugs.
"""
import sqlite3


def assign_coach_to_team(
    conn: sqlite3.Connection,
    coach_id: int,
    team_id: int | None,
    season_year: int,
    end_reason_for_previous: str = 'current',
) -> None:
    """The single mutation point for coach assignment.

    Performs all of the following in one transaction:
      1. If coach has an open tenure (end_year IS NULL), close it with
         end_year=season_year and end_reason=end_reason_for_previous
      2. Update coach_career.current_team_id = team_id (may be NULL if vacancy)
      3. If team_id is not None:
           a. Create new coach_tenure row (start_year=season_year, end_reason='current')
           b. Copy coach.personality_archetype → team.gm_personality
      4. If coach.is_player AND team_id is not None: update league.user_team_id = team_id
         If coach.is_player AND team_id is NULL: leave league.user_team_id unchanged
         (per §8 item 9 — vacancy state keeps the previous-team pointer stable
         so the 30+ existing reads of league.user_team_id continue to work without
         NULL guards)

    Args:
        conn: SQLite connection
        coach_id: coach_career.id
        team_id: target team.id, or None for vacancy state
        season_year: current league season year (used for tenure boundaries)
        end_reason_for_previous: must be one of COACH_TENURE_END_REASONS;
            ignored if coach has no open tenure
    """
    # Implementation:
    # - Use `with conn:` for the transaction
    # - Validate end_reason_for_previous against COACH_TENURE_END_REASONS
    # - Read coach row first to get is_player, personality_archetype
    # - Close prior tenure if exists
    # - Update coach_career.current_team_id
    # - If team_id is not None, open new tenure and copy personality to team
    # - If coach is player and team_id is not None, update league.user_team_id
    ...
```

Implement the function body following the contract above. Use parameterized queries throughout. Follow the patterns in `src/transactions/contracts.py` for transaction style.

### Task 5 — Generator updates

In `src/generation/teams.py`:

After all 32 teams are inserted (and after `initialize_league` is called), add a function `generate_ai_coaches(conn, season_year)` that creates one coach per team. For each team:

- Random `first_name` and `last_name` (use existing name generation utilities if present in `src/generation/`; otherwise add simple lists at the top of the file with ~50 first names and ~50 last names)
- Random `age` between `COACH_MIN_AGE` and `COACH_MAX_AGE`
- `personality_archetype` = the team's existing `gm_personality` (CRITICAL — this is what keeps Day-1 behavior identical to Phase 3)
- `career_start_year` = `season_year`
- `is_player = 0`
- `is_active = 1`
- After inserting the coach row, call `assign_coach_to_team(conn, coach_id, team_id, season_year)`
- The end_reason_for_previous default ('current') is fine since AI coaches have no prior tenure on first generation

In `generate.py` (the CLI entry point):

After `initialize_league` completes, prompt the player for:
1. Coach first name (default `DEFAULT_PLAYER_COACH_FIRST_NAME`)
2. Coach last name (default `DEFAULT_PLAYER_COACH_LAST_NAME`)
3. Personality archetype — show numbered options from `GM_PERSONALITIES_TUPLE` (default index for `DEFAULT_PLAYER_COACH_ARCHETYPE`)
4. The starting team flow is unchanged (existing logic picks team_ids[0] as user_team_id)

Then create the player coach:
- `is_player = 1`, `is_active = 1`
- `age = 45` (a reasonable default; can be made configurable post-MVP)
- `career_start_year = season_year`
- Call `assign_coach_to_team(conn, player_coach_id, user_team_id, season_year)`

**Important**: this overwrites the user team's `gm_personality` with the player's chosen archetype. That is intended behavior per §2.5. The user is taking over the team; their philosophy applies from Day 1.

Use sensible CLI prompt UX (input(), defaults shown in brackets, accept Enter for default). If `generate.py` already uses argparse for flags, add corresponding `--coach-first-name`, `--coach-last-name`, `--coach-archetype` flags so the generation can be scripted in tests.

### Task 6 — Backwards compatibility for existing test save

If `saves/test_franchise.db` exists from Phase 0–3 work, opening it with `ensure_coach_tables(conn)` should add the new tables and columns without erroring. It will not have any coach rows — that's fine for now. The next Phase 4 prompt (#2) will add a one-off backfill helper if needed; this prompt does not.

## Constraints — what NOT to touch

- Do NOT modify any of the 30+ existing `team['gm_personality']` call sites in `src/league/legacy.py`, `src/league/season.py`, `src/league/offseason.py`, `src/transactions/free_agency.py`, `src/transactions/draft.py`, `src/transactions/trades.py`, `src/transactions/contracts.py`, `src/transactions/franchise_tag.py`. They continue to read the field directly; the helper writes to it.
- Do NOT modify the `legacy_score` aggregation logic in `src/league/legacy.py`. The new `coach_id` column is added but unused. (Phase 4 prompt #7 wires it up.)
- Do NOT add owner sentiment, hot seat, fan sentiment, or firing logic. (Phase 4 prompt #4.)
- Do NOT add the stress harness, invariant battery, or league health report. (Phase 4 prompt #2.)
- Do NOT add AI coach hiring/firing on AI teams or personality matrices. (Phase 4 prompt #3.)
- Do NOT touch the `staff` table — head coach is a separate entity from position coaches.
- Do NOT add press conference logic. (Phase 4 prompts #5 and #6.)

## Test plan

### Step 1 — Generate a fresh franchise

```bash
python generate.py saves/phase4_test.db --season 2024 \
  --coach-first-name "Bill" --coach-last-name "Walsh" --coach-archetype "analytics"
```

(Use whatever flag syntax you implemented; if you went with interactive prompts only, run interactively and accept defaults.)

### Step 2 — Run verification script

Create `verify_phase4_p1.py` in the project root:

```python
"""Verification for Phase 4 Build Prompt #1 — Save Model Refactor."""
import sqlite3
import subprocess
import sys

DB = "saves/phase4_test.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# 1. Schema check
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'coach_career' in tables, "coach_career table missing"
assert 'coach_tenure' in tables, "coach_tenure table missing"

cols_legacy = {r['name'] for r in conn.execute("PRAGMA table_info(legacy_score)")}
assert 'coach_id' in cols_legacy, "legacy_score.coach_id column missing"
cols_hof = {r['name'] for r in conn.execute("PRAGMA table_info(hall_of_fame)")}
assert 'coach_id' in cols_hof, "hall_of_fame.coach_id column missing"

# 2. Coach population
coaches = conn.execute("SELECT COUNT(*) c FROM coach_career WHERE is_active=1").fetchone()['c']
assert coaches == 33, f"expected 33 active coaches (32 AI + 1 player), got {coaches}"

players = conn.execute("SELECT COUNT(*) c FROM coach_career WHERE is_player=1").fetchone()['c']
assert players == 1, f"expected exactly 1 player coach, got {players}"

# 3. Personality sync invariant (#12)
mismatches = conn.execute("""
    SELECT t.id, t.abbreviation, t.gm_personality, c.personality_archetype
    FROM team t
    JOIN coach_career c ON c.current_team_id = t.id AND c.is_active=1
    WHERE t.gm_personality != c.personality_archetype
""").fetchall()
assert len(mismatches) == 0, f"personality sync failed for {len(mismatches)} teams: {[dict(m) for m in mismatches]}"

# 4. Player team pointer invariant (#11)
player = conn.execute("SELECT current_team_id FROM coach_career WHERE is_player=1").fetchone()
league = conn.execute("SELECT user_team_id FROM league WHERE id=1").fetchone()
assert player['current_team_id'] == league['user_team_id'], \
    f"player team pointer drift: coach.current_team_id={player['current_team_id']}, league.user_team_id={league['user_team_id']}"

# 5. Open tenures
open_tenures = conn.execute("SELECT COUNT(*) c FROM coach_tenure WHERE end_year IS NULL").fetchone()['c']
assert open_tenures == 33, f"expected 33 open tenures, got {open_tenures}"

# 6. Existing query_roster.py regression
result = subprocess.run(
    ["python", "query_roster.py", DB, "--team", "CHI"],
    capture_output=True, text=True
)
assert result.returncode == 0, f"query_roster.py regression — exited {result.returncode}\nstderr: {result.stderr}"

# 7. assign_coach_to_team reassignment behavior
sys.path.insert(0, ".")
from src.transactions.coaching import assign_coach_to_team

player_coach_id = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()['id']
old_team_id = conn.execute("SELECT current_team_id FROM coach_career WHERE id=?", (player_coach_id,)).fetchone()['current_team_id']
new_team_id = conn.execute("SELECT id FROM team WHERE id != ? LIMIT 1", (old_team_id,)).fetchone()['id']
player_archetype = conn.execute("SELECT personality_archetype FROM coach_career WHERE id=?", (player_coach_id,)).fetchone()['personality_archetype']

# Reassign player coach to new team (simulating fired → rehired)
assign_coach_to_team(conn, player_coach_id, new_team_id, season_year=2024, end_reason_for_previous='fired')

# Verify new team's personality matches player's archetype
new_team_personality = conn.execute("SELECT gm_personality FROM team WHERE id=?", (new_team_id,)).fetchone()['gm_personality']
assert new_team_personality == player_archetype, \
    f"new team personality not synced: expected {player_archetype}, got {new_team_personality}"

# Verify league.user_team_id updated
league_team = conn.execute("SELECT user_team_id FROM league WHERE id=1").fetchone()['user_team_id']
assert league_team == new_team_id, f"league.user_team_id not updated: {league_team} != {new_team_id}"

# Verify previous tenure closed correctly
prev_tenure = conn.execute("""
    SELECT end_year, end_reason FROM coach_tenure
    WHERE coach_id=? AND team_id=? AND end_year IS NOT NULL
    ORDER BY id DESC LIMIT 1
""", (player_coach_id, old_team_id)).fetchone()
assert prev_tenure is not None, "previous tenure not found"
assert prev_tenure['end_year'] == 2024 and prev_tenure['end_reason'] == 'fired', \
    f"previous tenure not closed correctly: {dict(prev_tenure)}"

# 8. Vacancy state — assign player to None
assign_coach_to_team(conn, player_coach_id, None, season_year=2024, end_reason_for_previous='fired')

player_team = conn.execute("SELECT current_team_id FROM coach_career WHERE id=?", (player_coach_id,)).fetchone()['current_team_id']
assert player_team is None, f"player should be vacancy (None), got {player_team}"

# Per §8 item 9: league.user_team_id must remain pointing at the previous (most recent) team
league_team_after_vacancy = conn.execute("SELECT user_team_id FROM league WHERE id=1").fetchone()['user_team_id']
assert league_team_after_vacancy == new_team_id, \
    f"league.user_team_id changed during vacancy: expected {new_team_id} (unchanged), got {league_team_after_vacancy}"

print("Phase 4 prompt #1 verification passed.")
```

```bash
python verify_phase4_p1.py
```

Exit criteria: the verification script prints "Phase 4 prompt #1 verification passed." and exits 0. Any assertion failure means the prompt is not complete.

### Step 3 — Update CLAUDE.md

After verification passes, append the Phase 4 prompt #1 completion to the Phase 4 checklist in `CLAUDE.md`:

```
**Phase 4 — Dynasty**

### Phase 4 Checklist
- [x] Save model refactor (`coach_career`, `coach_tenure`, `assign_coach_to_team`, generator updates)
- [ ] Multi-season stress harness + invariant battery
- [ ] AI GM team-phase classifier + transition rules
- [ ] Owner sentiment + hot seat + reassignment logic
- [ ] Tier 1 weekly press conference + autopilot
- [ ] Tier 2 event-triggered press conference
- [ ] Legacy score expansion (era multiplier, tenure stability, peer rank)
- [ ] Historical records module
- [ ] End-of-season legacy display + dynasty/HOF narrative
- [ ] Phase 4 exit-criteria run (3-season hard pass + 10-season smoke)
```

Add `src/transactions/coaching.py` to the project structure map in CLAUDE.md.

## Reference

Full design context: `docs/Phase4_DesignDecisions.md`, especially:
- §1.7 Coach identity decision
- §1.8 Firing leash
- §2 Save Model Refactor (entire section)
- §3.2 Invariants #11 and #12
- §8 items 7, 8, 9 (mutation point discipline, AI replacement timing, vacancy state)
