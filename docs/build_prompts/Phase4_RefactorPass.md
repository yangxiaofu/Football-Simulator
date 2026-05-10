# Phase 4 Refactor Pass — CLAUDE.md Compliance Audit

**Model**: Sonnet
**Planning mode**: Yes — multi-file audit work with a fix-versus-defer judgment call per finding.

---

## Context

All Phase 4 build prompts (#1, #2, #2.5, #3, #4, #5, #6, #7, #8, #9, #10) are complete. Phase 4 — Dynasty has shipped per the design doc's exit criteria.

`CLAUDE.md` includes a "Refactor Checkpoints" rule: after a full module is complete, run a structural pass to enforce the four code quality rules. Phase 4 added ~22 new modules across `src/league/`, `src/transactions/`, `src/utils/`, and `src/ui/`. A refactor checkpoint is overdue.

This prompt does NOT add features. It audits the Phase 4 code for the four `CLAUDE.md` violations, fixes them surgically, and validates that behavior is unchanged via the existing verify scripts and harness. The deliverable is cleaner code that passes the same tests.

**Read first**:
1. `CLAUDE.md` — particularly "Code Quality Rules" and "Layer Boundaries"
2. The list of new Phase 4 modules below in Task 1
3. `src/db/queries.py` — the canonical home for SQL queries (extension target)
4. `src/utils/constants.py` — the canonical home for tuning constants (extension target)

## Goal

Bring Phase 4 modules into compliance with `CLAUDE.md` rules:

1. **No inline SQL in business logic.** Raw `conn.execute(...)` calls outside `src/db/` move into `src/db/queries.py` as named helper functions.
2. **No magic numbers in code.** Numeric literals inlined in business logic move into `src/utils/constants.py` as named constants.
3. **Layer boundaries respected.** `src/ui/` doesn't access the database directly; it calls helpers in `src/league/` or `src/transactions/`. `src/utils/` doesn't import from other `src/` modules.
4. **No dead code / commented-out blocks.** Remove abandoned helpers, unused imports, commented experiments.

**Critical scope discipline**:
- Behavior MUST NOT change. The harness must produce 12/12 invariants and all `verify_phase4_p*.py` scripts must still pass after the refactor.
- Only Phase 4 modules are in scope. Do NOT refactor pre-Phase-4 code (the Phase 0-3 codebase has its own conventions; leave them alone).
- This is NOT a "while we're here" pass. Do NOT add type hints, restructure long functions, simplify expressions, or rename for clarity unless the rename fixes a CLAUDE.md violation.
- Some violations may be acceptable to leave with a documented justification (e.g., `src/league/invariants.py` is inherently SQL-heavy because it audits the database — moving every query into `queries.py` would just rename the location of the same SQL). Use judgment; document deferrals.

## Tasks

### Task 1 — Audit phase

Phase 4 added these modules. Audit each one against the four rules. Produce a findings list before fixing anything.

**`src/league/`**:
- `owner_sentiment.py`
- `team_phase.py`
- `era_context.py`
- `peer_ranking.py`
- `narrative_beats.py`
- `historical_records.py`
- `stress_harness.py`
- `invariants.py`
- `health_report.py`
- `legacy.py` (extended significantly in #7)
- `offseason.py` (extended with hooks)
- `season.py` (extended with hooks)

**`src/transactions/`**:
- `coaching.py`
- `coaching_carousel.py`
- `coach_offers.py`
- `press_conference.py`
- `tier2_press_conference.py`
- `tier2_triggers.py`

**`src/utils/`**:
- `ai_behavior_matrix.py`
- `press_templates.py`
- `tier2_templates.py`
- `constants.py` (extended)

**`src/ui/`**:
- `season_summary.py`
- `career_view.py`
- `dramatic_moments.py`
- `colors.py`

**Top-level CLI files** (not strictly modules but worth auditing):
- `run_stress_test.py`
- `view_records.py`
- `view_career.py`
- `verify_phase4_p*.py` files (these are tests; light audit only)

For each module, run these specific greps and inspections:

```bash
# Inline SQL outside db/ layer
grep -rn "conn.execute" src/league/ src/transactions/ src/utils/ src/ui/

# Magic numbers (any 2+ digit number not in constants.py and not obviously a column index/loop bound)
grep -rnE "[^a-zA-Z_][0-9]{2,}" src/league/ src/transactions/ src/ui/ \
  | grep -v "constants" | grep -v "test"

# Layer boundary violations
grep -rn "from src.engine" src/ui/ src/transactions/ src/utils/
grep -rn "from src.db" src/ui/                # UI should NOT import db directly
grep -rn "from src" src/utils/                # utils should be dependency-free
```

Compile findings into a working file at `docs/Phase4_RefactorFindings.md` (will be deleted after the refactor; this is just a working doc):

```markdown
# Phase 4 Refactor Findings

## Inline SQL violations (move to src/db/queries.py)
- src/league/owner_sentiment.py:42 — `conn.execute("SELECT owner_sentiment FROM team WHERE id=?")`
  → New helper: `get_team_sentiment(conn, team_id)`
- ... etc

## Magic numbers (move to constants.py)
- src/league/team_phase.py:67 — `if avg_age < 28:` — should be PHASE_AGE_PRIME_HIGH
- ... etc

## Layer boundary violations
- src/ui/season_summary.py:88 — directly calls `conn.execute("SELECT...")` — must move to a presenter helper
- ... etc

## Dead code
- src/league/era_context.py:120-130 — commented-out experimental smoothing function
- ... etc

## Acceptable to leave (documented justification)
- src/league/invariants.py — inherently SQL-heavy (its job is auditing the DB).
  Moving every query to queries.py would not improve clarity. Deferred.
- ... etc
```

### Task 2 — Layer boundary clarification for UI

The trickiest finding will likely be: **the UI modules from #9 read data directly via `conn.execute`**. Per `CLAUDE.md`:

> ui: Display only — Compute anything; call engine or db directly

Per the layer rules, UI should call `src/league/` or `src/transactions/` helpers that return ready-to-display data, not query the DB directly.

**Practical approach**: for each UI section renderer that has inline SQL, do ONE of the following:

1. **Move the SQL to `src/db/queries.py`** as a named helper (e.g., `get_season_summary_data(conn, season_year, coach_id)` returns a dict). The UI then calls this helper.

2. **Move the data assembly to a "presenter" function** in the relevant business-logic module (e.g., `src/league/season_summary_data.py` with `assemble_season_summary(conn, season_year, coach_id) -> dict`). This is the more rigorous separation.

For MVP simplicity and given the scope discipline, **Option 1 is acceptable** — moving raw SQL into named query helpers in `src/db/queries.py`. This satisfies the "no raw SQL in UI" rule even if it doesn't fully implement the presenter pattern. Document this choice in the refactor findings.

### Task 3 — Magic number harvest

Be judicious here. Not every numeric literal is a magic number.

**Move to constants.py**:
- Threshold values used in business logic (`if score >= 90:` → `if score >= STAR_RATING_THRESHOLD:`)
- Default values (`return 50` → `return SENTIMENT_DEFAULT`)
- Tuning multipliers and weights
- Magic strings used in branch conditions (`if status == 'active':` → use a constant if the string appears in 3+ places)

**Acceptable to leave inline**:
- Loop indices (`for i in range(3):` if 3 is structural, not tuning)
- String formatting (`f"{value:.2f}"`)
- Index accesses (`row[0]`)
- Single-use values inside a single function whose meaning is locally obvious

When in doubt, **prefer moving to constants** — adding a named constant rarely hurts readability; leaving a magic number inline almost always does.

### Task 4 — Dead code removal

For each Phase 4 module, look for:

- Commented-out function definitions or large blocks (use git for history; remove the comment)
- Unused imports
- Abandoned helper functions (defined but never called — verify with `grep`)
- TODO comments referring to scope that was completed or formally deferred elsewhere
- Print statements left from debugging

Remove cleanly. If something looks important but unused, ASK before removing — don't silently delete code that might be referenced from outside Phase 4.

### Task 5 — Apply fixes systematically

Work through the findings list. For each fix:

1. Make the change
2. Run the relevant verify script: `python verify_phase4_p[N].py`
3. If it fails, the change broke behavior — revert and investigate

When all findings are addressed (or formally deferred with documented justification), proceed to Task 6.

### Task 6 — Regression validation

This is the load-bearing step. The refactor is acceptable ONLY if behavior is unchanged.

```bash
# 1. All Phase 4 verify scripts still pass
for v in verify_phase4_p1.py verify_phase4_p2_5.py verify_phase4_p3.py \
         verify_phase4_p4.py verify_phase4_p5.py verify_phase4_p6.py \
         verify_phase4_p7.py verify_phase4_p8.py verify_phase4_p9.py \
         verify_phase4_shipgate.py; do
    echo "=== $v ==="
    python "$v" || { echo "FAIL: $v"; break; }
done
```

```bash
# 2. Full harness 3-season + 10-season
rm -f saves/refactor_test.db
python generate.py saves/refactor_test.db --season 2024
python run_stress_test.py saves/refactor_test.db --invariants --seasons 3
python run_stress_test.py saves/refactor_test.db --smoke --seasons 10
```

Expected: 12/12 invariants pass on the 3-season run; 10-season smoke completes without crashes.

```bash
# 3. Sample UI render — visual sanity
python view_career.py saves/refactor_test.db --season 2026 --no-color | head -50
python view_records.py saves/refactor_test.db --records | head -30
```

Expected: same content as before refactor (modulo random variation in the harness's particular run). If the season summary now has missing sections or the records output looks wrong, a query was broken in the move to `queries.py`.

### Task 7 — Update CLAUDE.md project structure

Phase 4 added many files. Verify the project structure section in `CLAUDE.md` lists all of them. Add anything missing. Adjust if any modules moved during the refactor.

Also append a one-line entry to the Phase 4 checklist:

```
**Phase 4 — Dynasty** ✅
[existing items checked off]
- [x] Phase 4 refactor pass (CLAUDE.md compliance, layer boundaries, magic number harvest)
```

### Task 8 — Clean up working artifacts

Delete `docs/Phase4_RefactorFindings.md` after the refactor is complete. It was a working doc; the findings are now resolved (or documented as accepted deferrals in the Ship Gate Report or CLAUDE.md if they're permanent).

## Constraints — what NOT to touch

- Do NOT change behavior anywhere. The refactor must be byte-identical or behaviorally identical to pre-refactor for deterministic operations.
- Do NOT refactor pre-Phase-4 code. Phase 0-3 modules have their own conventions; leave them alone.
- Do NOT add type hints, docstrings, or comments unless replacing something dead-code-removed.
- Do NOT restructure long functions. "Function is too long" is not a CLAUDE.md violation.
- Do NOT rename functions or variables unless the rename fixes a violation (e.g., a magic-number constant getting a name).
- Do NOT add tests beyond what's already in the verify scripts.
- Do NOT introduce new modules beyond moving existing code into `src/db/queries.py` or `src/utils/constants.py`.
- Do NOT formally fix Inv 5 (Phase 0 contracts gap) — it's deferred per the Ship Gate Report.
- Do NOT touch the AI behavior matrix values (`ai_behavior_matrix.py`), narrative beat templates, or press conference templates. The data IS the deliverable; restructuring it is out of scope.

## Test plan

The validation IS the test plan. The two regression checks in Task 6 must both pass:

1. All verify_phase4_p*.py scripts: 0 failures
2. Stress harness: 12/12 invariants on 3-season; smoke completes on 10-season

If either fails, the refactor broke something. Revert the most recent change and investigate.

A successful refactor leaves:
- Cleaner code that complies with CLAUDE.md
- Same behavior (verifiable via tests)
- A working findings doc deleted (Task 8)
- Updated CLAUDE.md project structure
- Phase 4 checklist marked complete

## Reference

- `CLAUDE.md` "Code Quality Rules" section
- `CLAUDE.md` "Layer Boundaries" table
- `docs/Phase4_DesignDecisions.md` — design intent (read if any refactor decision feels structural)
- `docs/Phase4_ShipGate_Report.md` — known deferred items (do not "fix" these as part of refactor)
- `src/db/queries.py` — extension target for relocated SQL
- `src/utils/constants.py` — extension target for relocated magic numbers
