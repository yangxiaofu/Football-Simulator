# Phase 4 Build Prompt #10 — Final Integration Validation + Ship Gate

**Model**: Opus
**Planning mode**: Yes — largest investigation surface area in Phase 4 even though it adds the least code. Plan the validation order before running anything.

---

## Context

All Phase 4 build prompts are complete (#1, #2, #2.5, #3, #4, #5, #6, #7, #8, #9). The harness consistently passes 12/12 invariants over 3-season runs. AI behavior, owner sentiment, hot seat, player reassignment, legacy expansion, historical records, two-tier press conferences, and end-of-season UI are all in place.

This is the Phase 4 ship gate. It does NOT add new features. Its job is to:

1. Run comprehensive validation against the 8 exit criteria from `docs/Phase4_DesignDecisions.md` §9
2. Tune any constants that need adjustment based on observed behavior (NOT refactor logic)
3. Run a 10-season smoke test — the first time this actually runs end-to-end
4. Investigate any systematic issues surfaced
5. Document remaining post-launch deferrals
6. Produce a formal Phase 4 Ship Gate Report

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §9 (Phase 4 Exit Criteria — the 8-item checklist this prompt validates)
3. `docs/Phase4_DesignDecisions.md` §10 (Post-launch roadmap preview)
4. `docs/Phase4_StressTest_BaselineFindings.md` — accumulated findings from prompts #2 through #9
5. All Phase 4 implementation files referenced in `CLAUDE.md` project structure

## Goal

Validate Phase 4 is shippable. Specifically:

1. **Run the validation suite** explicitly against each exit criterion
2. **Tune constants** where harness data shows misalignment with design intent (HOF threshold is the known one; others may surface)
3. **Fix bugs** that block exit criteria — but ONLY fixes; not new features
4. **Document deferred items** that don't block ship but should be tracked for post-launch
5. **Produce a Ship Gate Report** that explicitly checks off each criterion with status (PASS / TUNED / DEFERRED / FAIL)

**Critical scope discipline**: this prompt does NOT add features, refactor for elegance, or implement post-launch items. If a finding requires a structural change (new schema, new module, new system), that's a deferred item for post-launch, not a #10 fix. Tuning = constant adjustments; bug fixes = surgical corrections; everything else = documented and deferred.

## Known issues going in (file these mentally before the run)

1. **HOF threshold = 200 is too low.** Career legacy after 3 seasons was 1,737 (per #7 baseline). Everyone qualifies after 1-2 seasons. Needs recalibration to ~5,000-10,000 based on actual 10-season data.
2. **Tier 2 fire rate at lower end of design target.** Currently ~2/season; design target is 3-5/season. May need trigger threshold relaxation OR may be acceptable at 2/season with a doc update.
3. **Owner sentiment is forgiving.** Only ~1 firing per 3-season harness run. Design intent was 3-5 per 3-season run. May need delta or threshold tuning.
4. **Player coach trends toward bottom of peer rank.** Could be systematic (player team has some disadvantage) or random variance from particular harness runs.
5. **Inv 5 — no contracts in Phase 0.** Known gap, deferred from #2.5. Decide whether to fix here or formally defer to post-launch.
6. **10-season smoke run is untested.** This is the first time it actually runs. Likely surfaces issues.

## Tasks

### Task 1 — Baseline run capture

```bash
rm -f saves/phase4_shipgate_baseline.db
python generate.py saves/phase4_shipgate_baseline.db --season 2024
python run_stress_test.py saves/phase4_shipgate_baseline.db --invariants --seasons 3
python run_stress_test.py saves/phase4_shipgate_baseline.db --smoke --seasons 10
```

Capture full output of both runs. The 10-season smoke is the new test — it WILL likely surface issues. Common failure modes to expect:

- FK violation as some long-tail data wasn't expected to grow
- Infinite loop in offseason phase progression
- Coach turnover producing unrecoverable state (e.g., team with no coach for >1 season)
- Player vacancy auto-accept failing in some edge case
- Memory growth becoming an issue (probably not, but watch)

**If the 10-season smoke crashes**, treat it as a real bug. Find the smallest fix that gets it to completion. Document the fix.

**If the 3-season run drops below 12/12 invariants**, treat it as a regression in some subsequent prompt's integration. Find the root cause and fix.

### Task 2 — Per-criterion validation

Create `verify_phase4_shipgate.py` that explicitly validates each exit criterion with PASS/FAIL output:

```python
"""Phase 4 Ship Gate verification.

Runs against a save file that has had at least 3 (preferably 10) simulated
seasons. Validates each of the 8 exit criteria from
docs/Phase4_DesignDecisions.md §9.

Each criterion prints PASS / FAIL / DEFERRED with detail.
"""
import sqlite3
import sys
import subprocess

DB = "saves/phase4_shipgate_baseline.db"


def criterion_1_invariants_3_seasons():
    """All 12 invariants pass over 3 simulated seasons."""
    # Re-run the harness fresh and check
    result = subprocess.run(
        ["python", "run_stress_test.py", DB, "--invariants", "--seasons", "3"],
        capture_output=True, text=True
    )
    # Look for "12/12 invariants" in output OR check exit code
    passed = result.returncode == 0 and "FAIL" not in result.stdout
    return ('PASS' if passed else 'FAIL', f"exit code {result.returncode}")


def criterion_2_smoke_10_seasons():
    """10-season smoke run completes without crashes or FK violations."""
    result = subprocess.run(
        ["python", "run_stress_test.py", DB, "--smoke", "--seasons", "10"],
        capture_output=True, text=True
    )
    passed = result.returncode == 0
    return ('PASS' if passed else 'FAIL', f"exit code {result.returncode}; stderr: {result.stderr[:200]}")


def criterion_3_league_health():
    """Roster turnover >=20%, retirement >=8%/season, >=4 distinct champions in 3 years,
    no perma-zombie teams."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Distinct champions across last 3 seasons
    distinct_champs = conn.execute("""
        SELECT COUNT(DISTINCT champion_team_id) FROM season
        WHERE is_complete=1 AND champion_team_id IS NOT NULL
        ORDER BY year DESC LIMIT 3
    """).fetchone()[0]

    # Roster turnover and zombie checks require more involved queries — implement
    # as helpers and document the heuristic used.
    # ...

    # Perma-zombie heuristic: a team that has had W% < 0.300 for >= 5 consecutive seasons
    zombies = conn.execute("""
        SELECT team_id, COUNT(*) AS losing_seasons FROM team_season_record
        WHERE wins * 1.0 / (wins + losses + ties) < 0.300
        GROUP BY team_id
        HAVING COUNT(*) >= 5
    """).fetchall()

    issues = []
    if distinct_champs < 4:
        # Note: this is "across 3 years" per design doc. With 3 seasons that's <=3 champions.
        # The real check is "across 10 seasons in smoke run" — distinct_champs >= 4
        # Adjust this to query the smoke save's 10 seasons if available.
        issues.append(f"only {distinct_champs} distinct champions")
    if len(zombies) > 0:
        issues.append(f"{len(zombies)} perma-zombie teams")

    status = 'PASS' if not issues else 'FAIL'
    return (status, '; '.join(issues) or 'all sub-criteria met')


def criterion_4_player_reassignment():
    """Player can be fired and reassigned with career legacy intact."""
    # Check coach_tenure for the player coach: is there at least one closed
    # tenure with end_reason in ('fired', 'resigned', 'mutual')?
    # If yes, that's reassignment having happened in the harness.
    conn = sqlite3.connect(DB)
    closed = conn.execute("""
        SELECT COUNT(*) FROM coach_tenure ct
        JOIN coach_career cc ON cc.id = ct.coach_id
        WHERE cc.is_player=1 AND ct.end_year IS NOT NULL
              AND ct.end_reason IN ('fired', 'resigned', 'mutual')
    """).fetchone()[0]
    # Career legacy intact means coach_legacy_score has rows from BEFORE
    # AND AFTER any reassignment for the player coach.
    if closed == 0:
        return ('DEFERRED', 'player was not fired in this harness run; manually verifiable')
    # Check legacy continuity
    ...
    return ('PASS', f"{closed} closed player tenure(s); legacy continuity verified")


def criterion_5_end_of_season_display():
    """End-of-season display shows: legacy, peer rank, narrative beat,
    hot seat tier, owner expectation."""
    # Render a season summary for the most recent completed season
    sys.path.insert(0, ".")
    from src.ui.season_summary import render_season_summary
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    coach_id = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()[0]
    season_year = conn.execute("SELECT MAX(year) FROM season WHERE is_complete=1").fetchone()[0]
    output = render_season_summary(conn, season_year, coach_id, use_color=False)

    required_phrases = ['LEGACY', 'PEER RANK', 'OWNER', 'NARRATIVE' or 'STORY']
    missing = [p for p in required_phrases if p not in output.upper()]
    status = 'PASS' if not missing else 'FAIL'
    return (status, f"missing sections: {missing}" if missing else "all required sections present")


def criterion_6_tier2_fire_rate():
    """At least 1 Tier 2 event per simulated season on average."""
    conn = sqlite3.connect(DB)
    n_completed = conn.execute("SELECT COUNT(*) FROM season WHERE is_complete=1").fetchone()[0]
    n_tier2 = conn.execute("SELECT COUNT(*) FROM tier2_press_event").fetchone()[0]
    rate = n_tier2 / n_completed if n_completed else 0
    if rate >= 1.0:
        return ('PASS', f"{n_tier2} events / {n_completed} seasons = {rate:.2f}/season")
    elif rate >= 0.5:
        return ('TUNED' if rate < 1.0 else 'PASS',
                f"{n_tier2} events / {n_completed} seasons = {rate:.2f}/season — below target, see tuning")
    else:
        return ('FAIL', f"{rate:.2f}/season — significantly below 1.0 target")


def criterion_7_dynasty_fires():
    """Dynasty flag fires correctly when 3 championships in 10 years achieved.
    
    Test against the 10-season smoke save: at least one coach should have
    accumulated 3 championships, AND the dynasty flag should have been set.
    """
    conn = sqlite3.connect(DB)
    # In the 10-season smoke, did any coach get is_dynasty=1?
    dynasty_count = conn.execute("""
        SELECT COUNT(DISTINCT coach_id) FROM coach_legacy_score
        WHERE coach_id IN (SELECT id FROM coach_career WHERE is_active=1)
    """).fetchone()[0]
    # Also check: did any coach actually accumulate 3+ championships?
    multi_champs = conn.execute("""
        SELECT coach_id, SUM(championships) AS total FROM coach_legacy_score
        GROUP BY coach_id HAVING total >= 3
    """).fetchall()
    
    if not multi_champs:
        return ('DEFERRED', 'no coach accumulated 3+ championships in this run; flag firing untested')
    
    # Verify the flag actually fired for those coaches
    # (legacy_score.is_dynasty or coach_narrative_beat.beat_type='dynasty_milestone')
    ...
    return ('PASS', f"{len(multi_champs)} coach(es) hit 3+ championships; dynasty flag verified")


def criterion_8_hof_fires():
    """HOF eligibility fires for at least one player in 10-season smoke."""
    conn = sqlite3.connect(DB)
    hof_count = conn.execute("""
        SELECT COUNT(*) FROM coach_narrative_beat
        WHERE beat_type='hof_eligible'
    """).fetchone()[0]
    if hof_count > 0:
        return ('PASS', f"{hof_count} HOF beats fired")
    else:
        return ('FAIL', 'no HOF eligibility beats fired across 10 seasons — check threshold tuning')


CRITERIA = [
    ('1. Invariants 3-season',     criterion_1_invariants_3_seasons),
    ('2. Smoke 10-season',         criterion_2_smoke_10_seasons),
    ('3. League health metrics',   criterion_3_league_health),
    ('4. Player reassignment',     criterion_4_player_reassignment),
    ('5. End-of-season display',   criterion_5_end_of_season_display),
    ('6. Tier 2 fire rate',        criterion_6_tier2_fire_rate),
    ('7. Dynasty flag fires',      criterion_7_dynasty_fires),
    ('8. HOF eligibility fires',   criterion_8_hof_fires),
]


def main():
    print("=" * 70)
    print("PHASE 4 SHIP GATE VALIDATION")
    print("=" * 70)
    results = []
    for name, fn in CRITERIA:
        try:
            status, detail = fn()
        except Exception as e:
            status, detail = 'ERROR', f"exception: {e}"
        results.append((name, status, detail))
        marker = {'PASS': '✓', 'TUNED': '~', 'DEFERRED': '·', 'FAIL': '✗', 'ERROR': '!'}[status]
        print(f"  {marker} {name:<35} [{status}]")
        if detail:
            print(f"        {detail}")

    n_pass = sum(1 for _, s, _ in results if s == 'PASS')
    n_total = len(results)
    print()
    print(f"  Result: {n_pass} / {n_total} PASS")
    if n_pass == n_total:
        print("  Phase 4 SHIP GATE: PASSED")
    else:
        print(f"  Phase 4 SHIP GATE: NEEDS WORK")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

```bash
python verify_phase4_shipgate.py
```

### Task 3 — Tuning pass

Based on the validation output, perform the following tuning passes. **All tuning is constant changes only — no logic refactors.**

**3a. HOF threshold (high confidence this needs work)**

Current: `HOF_LEGACY_THRESHOLD = 200` in `src/utils/constants.py`. Almost certainly too low.

Procedure:
1. Query the 10-season smoke save: `SELECT coach_id, SUM(season_legacy_score) AS total FROM coach_legacy_score GROUP BY coach_id ORDER BY total DESC;`
2. The top 1-2 coaches should be HOF-worthy. Set the threshold so it captures the top ~5% of all-time coaches.
3. Likely value range: 5,000–15,000. Pick a value that produces 1-3 HOF inductions across the 10-season run.
4. Re-run criterion_8.

**3b. Tier 2 trigger thresholds (medium confidence)**

If criterion_6 returns < 1.0 events/season:
1. Look at which triggers fired vs. didn't in the smoke save: `SELECT trigger_type, COUNT(*) FROM tier2_press_event GROUP BY trigger_type;`
2. If only 2-3 trigger types ever fired, the others are likely too strict. Common candidates:
   - `TIER2_LOSING_STREAK_GAMES = 3` → try 2 (more frequent)
   - `TIER2_BLOWN_LEAD_POINTS = 14` → try 10 (more frequent), but only if the detector actually has data
   - `TIER2_HOLDOUT_PUBLIC_WEEKS = 4` → try 3
3. Re-run criterion_6 after each tuning step.

**3c. Owner sentiment firing rate (lower confidence — check first)**

If the harness still produces only ~1 firing per 3 seasons:
1. Look at sentiment trajectories: which teams approached the firing tier but didn't cross? `SELECT team_id, MIN(owner_sentiment) FROM ...`
2. Either lower the firing tier thresholds (`HOT_SEAT_TIER_THRESHOLDS`) or amplify negative sentiment deltas.
3. Target: 3-5 firings per 3-season harness run.
4. Don't over-tune — if firings feel right at 1-2/3-seasons in actual play, accept it and update the design doc.

### Task 4 — Bug fixes (only as needed)

If the 10-season smoke run crashes or produces FK violations, fix them. These are real bugs, not tuning. Document each fix.

If criterion_2 passes on first attempt, no work needed in this task — skip to Task 5.

Common bug patterns at the 10-season horizon (be on the lookout):
- Coach age progression eventually creates negative ages or coaches >100 (no retirement logic for coaches yet)
- Career stats overflow some integer column at the long horizon
- Foreign key violations as old data is referenced after archive
- Player satisfaction state corrupting after multiple holdouts
- Free agency market drying up as Phase 0 talent pool depletes

### Task 5 — Investigate systematic findings

If criterion_4 (player reassignment) returned DEFERRED because the player was never fired in the harness, manually trigger one to verify the flow:

```bash
python run_offseason.py saves/phase4_shipgate_baseline.db --force-fire-player
```

(If this CLI flag doesn't exist, write a small `manual_fire_player.py` script that calls the existing logic. This is a one-off verification tool; doesn't need to be polished.)

If the player has been ranked near the bottom of peer rank consistently across multiple harness runs, investigate:
1. Is the player team's `gm_personality` (overwritten by player choice) systematically worse than typical?
2. Does the coaching carousel disadvantage the player somehow?
3. Or is it just variance across small N (3 runs)?

Document the finding either way. If the cause is structural, file as a post-launch issue.

### Task 6 — Document deferred items

Create `docs/Phase4_ShipGate_Report.md`:

```markdown
# Phase 4 Ship Gate Report

**Date**: [today]
**Status**: [PASSED / NEEDS WORK]
**Validated by**: Claude Code (Opus, prompt #10)

## Exit Criteria Results

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Invariants 3-season | PASS | 12/12 over 3 seasons |
| 2 | Smoke 10-season | PASS / TUNED | [outcome + any fixes applied] |
| 3 | League health metrics | PASS / TUNED | [details] |
| 4 | Player reassignment | PASS / DEFERRED | [details] |
| 5 | End-of-season display | PASS | All required sections present |
| 6 | Tier 2 fire rate | PASS / TUNED | [N/season after tuning] |
| 7 | Dynasty flag fires | PASS / DEFERRED | [whether triggered in smoke] |
| 8 | HOF eligibility fires | PASS / TUNED | [threshold adjusted from X to Y] |

## Tuning Applied

- HOF_LEGACY_THRESHOLD: 200 → [N] (calibrated to top ~5% of all-time coaches in 10-season smoke)
- [other tuning constants if any]

## Bug Fixes Applied

- [each fix with one-line description]
- (or "none — 10-season smoke completed cleanly on first attempt")

## Deferred to Post-Launch

These items are KNOWN GAPS that do not block Phase 4 ship but should be tracked:

### Carried over from earlier prompts
- Inv 5 (Phase 0 contracts gap) — every player needs a contract at generation time, currently they don't
- [other items from baseline findings]

### Per design doc §5.5 OUT-of-scope (formally deferred)
- Named beat reporters with personalities
- Multi-turn press dialogues
- Social media / X feed
- Sponsor pressure system
- Player media feuds
- Headline generator beyond template fills
- Owner replacement events
- Family / personal life events

### Per design doc §10 (post-launch roadmap preview)
- Beat reporter personalities + named press corps
- Social media feed mid-week between pressers
- Sponsorship and revenue layer
- Multi-turn press dialogues with branching
- Owner replacement and ownership-era distinctions
- Coach personality drift across career
- Expansion teams (33rd / 34th franchises, divisional realignment)
- Historical replay mode

### Newly surfaced in #10
- [any additional items discovered during validation]

## Sample Output

### League Health Report (10-season smoke)
[paste the report]

### Player Coach Career View
[paste view_career.py output]

### Sample Tier 2 Press Event
[paste a representative one]

## Sign-Off

Phase 4 is [SHIPPABLE / NEEDS ANOTHER PASS] for Steam launch as defined by the
docs/Phase4_DesignDecisions.md exit criteria.

If SHIPPABLE: the dynasty experience meets the design intent of "32 distinct
franchises evolving over time with real coaching pressure, multi-season legacy,
and player-facing narrative." Post-launch items above are tracked but do not
gate launch.

If NEEDS ANOTHER PASS: [list of remaining blockers].
```

### Task 7 — Final updates to CLAUDE.md

Update the Phase 4 checklist:

```
**Phase 4 — Dynasty** ✅

### Phase 4 Checklist
- [x] Save model refactor
- [x] Multi-season stress harness + invariant battery + League Health Report
- [x] Baseline bug fixes (Inv 8, Inv 4, Inv 12 cascade)
- [x] AI GM team-phase classifier + transition rules + coaching carousel
- [x] Owner sentiment + hot seat + reassignment logic
- [x] Tier 1 weekly press conference + autopilot
- [x] Tier 2 event-triggered press conference + dramatic narration
- [x] Legacy score expansion (era multiplier, tenure stability, peer rank, narrative beats)
- [x] Historical records module (record book, leaderboards, champion history, CLI viewer)
- [x] End-of-season legacy display + dynasty/HOF narrative + career view UI
- [x] Phase 4 ship gate validation (3-season hard pass + 10-season smoke + tuning)

**Phase 4 Complete!** ✅
```

Update the "Current Build Phase" section header to reflect Phase 4 completion.

Add `verify_phase4_shipgate.py` and `docs/Phase4_ShipGate_Report.md` to the project structure map.

## Constraints — what NOT to touch

- Do NOT add new features, even if they would make a criterion pass. Tuning constants and surgical bug fixes only.
- Do NOT refactor for elegance, code cleanliness, or "while we're here" improvements.
- Do NOT attempt to fix Inv 5 (no contracts) in this prompt — it requires writing a real Phase 0 contract generator. Defer formally to post-launch.
- Do NOT attempt to add post-launch items from §5.5 or §10. Document them as deferred and move on.
- Do NOT change the design doc to retroactively justify failing exit criteria. If the system can't meet a criterion as designed, document the gap honestly.
- Do NOT skip the 10-season smoke test even if it crashes — fixing it is in scope.
- Do NOT run multiple stress tests in parallel (they may corrupt each other's saves; serialize them).

## Test plan

The validation IS the test. Run `verify_phase4_shipgate.py` before any tuning, after each tuning pass, and one final time after all changes. The final run should produce all PASS or PASS+DEFERRED status with no FAIL.

```bash
# Initial baseline
python verify_phase4_shipgate.py > /tmp/shipgate_baseline.txt

# After each tuning pass
python verify_phase4_shipgate.py > /tmp/shipgate_pass_N.txt

# Final verification
python verify_phase4_shipgate.py
# Should exit 0 with all criteria PASS or DEFERRED
```

If after all reasonable tuning, some criterion still fails, document it honestly in the Ship Gate Report. Better to ship with known gaps documented than to fudge the validation.

## Reference

- `docs/Phase4_DesignDecisions.md` §9 (Phase 4 Exit Criteria — the source of truth for this prompt)
- `docs/Phase4_DesignDecisions.md` §10 (post-launch roadmap)
- `docs/Phase4_DesignDecisions.md` §5.5 (MVP scope boundary — what's deferred)
- `docs/Phase4_StressTest_BaselineFindings.md` — accumulated findings from prompts #2 through #9
- All Phase 4 implementation files referenced in CLAUDE.md
