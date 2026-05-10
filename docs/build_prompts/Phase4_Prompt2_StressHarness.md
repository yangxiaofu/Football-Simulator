# Phase 4 Build Prompt #2 — Multi-Season Stress Harness

**Model**: Sonnet
**Planning mode**: Yes — multi-file additive work; lay out the structure before writing code.

---

## Context

Phase 4 prompt #1 (save model refactor) is complete. The Football Simulator now has portable coach identity, AI coaches for all 32 teams, and an `assign_coach_to_team` helper that keeps `team.gm_personality`, `coach_career.current_team_id`, and `league.user_team_id` in sync.

This prompt builds the test platform that every subsequent Phase 4 prompt will validate against. Without this harness, prompts #3, #4, #7, and #10 cannot be honestly verified over multiple seasons.

**Read first**:
1. `CLAUDE.md` — project conventions, layer boundaries
2. `docs/Phase4_DesignDecisions.md` — full Phase 4 design. Pay closest attention to §3 (Multi-Season Stability), §3.2 (12 invariants), §3.3 (League Health Report contents), §1.4 (3-hard / 10-soft stability target)
3. `run_season.py` — how the existing season loop is invoked via CLI (`--advance-week`, `--complete-season`)
4. `run_offseason.py` — how the existing offseason loop is invoked
5. `src/league/season.py` — `advance_week()` function
6. `src/league/offseason.py` — `advance_phase()` and `run_offseason_week()` functions
7. `src/engine/game_sim.py` — `simulate_game(db_path, game_id, verbose=True)` already has a `verbose` flag (set False in the harness)

## Goal

Build a headless multi-season simulation harness that:

1. Runs N consecutive seasons (regular season + playoffs + offseason) without UI prints
2. After each season-end archive, runs the 12-invariant battery and reports PASS/FAIL per invariant
3. After the final season, prints a one-page League Health Report
4. Supports two modes: `--invariants` (full battery, ship gate) and `--smoke` (crash-detection only, longer runs)

**Critical scope discipline**: this prompt does NOT fix any Phase 0–3 bugs the harness surfaces. It only reports them. If invariant #10 (retirement rate) fails because Phase 2 development logic is too conservative, that's a finding to triage in a later prompt — not a fix in this one.

## Tasks

### Task 1 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Stress harness" section:

```python
# Phase 4 — Stress harness
STRESS_TEST_DEFAULT_SEASONS = 3
STRESS_TEST_SMOKE_SEASONS = 10
STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON = 300  # kill if a season takes >5 min

# Invariant tuning
MAX_CAP_OVERAGE_TOLERANCE = 0           # cap_space must be >= 0 at season end
MIN_RETIREMENT_RATE = 0.08              # at least 8% of league rosters retire per season

# League Health Report
HEALTH_STAR_RATING_THRESHOLD = 90       # players overall >= 90 count as "stars"
HEALTH_AGE_BUCKETS = [(20, 24), (25, 28), (29, 32), (33, 99)]
HEALTH_CAP_BUCKETS = [
    ('healthy', 30_000_000, float('inf')),    # >= $30M cap space
    ('tight', 0, 30_000_000),                  # $0–30M
    ('over', float('-inf'), 0),                # negative = over the cap
]
```

### Task 2 — Invariant module

Create `src/league/invariants.py` containing one function per invariant. Each returns a tuple `(passed: bool, detail: str)`:

```python
"""Phase 4 — Multi-season stability invariants.

Each function takes a connection and the season_year just completed.
Returns (passed, detail). detail is empty on pass, contains the failure
explanation on fail.

Per docs/Phase4_DesignDecisions.md §3.2.
"""
import sqlite3
from typing import Tuple

InvariantResult = Tuple[bool, str]


def invariant_01_career_stats_match_seasons(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Career stats = sum of season stats for all players, all stat columns."""
    # Compare SUM(player_season_stats.X) to player_career_stats.X for all numeric columns
    # If any diverge, return (False, f"divergence in {col} for player {pid}: career={c} vs sum={s}")
    ...


def invariant_02_no_orphan_fk_references(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """After season archive, key_play and box_score references must remain intact."""
    # SELECT key_play rows where game_id NOT IN (SELECT id FROM game)
    # SELECT box_score rows where game_id NOT IN (SELECT id FROM game)
    ...


def invariant_03_cap_discipline(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """No team has cap_space < -MAX_CAP_OVERAGE_TOLERANCE."""
    ...


def invariant_04_roster_integrity(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Every team has exactly 53 active + <=16 practice squad players."""
    # Use the existing player.roster_status field
    ...


def invariant_05_contract_continuity(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Every active player has exactly one active contract."""
    ...


def invariant_06_awards_uniqueness(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """MVP/OPOY/DPOY are each exactly one player; no duplicates."""
    # Check the awards table (or wherever MVP is stored — see Phase 2 awards.py)
    ...


def invariant_07_champion_uniqueness(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Exactly one Super Bowl winner per completed season."""
    # SELECT season WHERE is_complete=1 AND champion_team_id IS NULL — must be empty
    ...


def invariant_08_coach_assignment_integrity(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Every team has exactly one head coach assigned via coach_career.current_team_id;
    every active coach is either assigned to one team OR has current_team_id IS NULL
    AND is_active=1 (between-jobs vacancy state)."""
    ...


def invariant_09_age_progression(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """Every returning player is exactly 1 year older than the previous season.
    Cross-reference player_attribute_history for previous season's age."""
    ...


def invariant_10_retirement_plausibility(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """At least MIN_RETIREMENT_RATE of league rosters retire each season.
    Counted as: players whose roster_status changed to 'retired' during the season."""
    # If <8%, return (False, f"only {n} retirements ({pct:.1%}); expected >= 8%")
    ...


def invariant_11_player_team_pointer_sync(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """When the player coach has current_team_id IS NOT NULL, league.user_team_id
    equals coach_career.current_team_id WHERE is_player=1.
    When player.current_team_id IS NULL (vacancy), the invariant does not apply.

    Per docs/Phase4_DesignDecisions.md §3.2 invariant #11 with vacancy exception."""
    ...


def invariant_12_coach_team_personality_sync(conn: sqlite3.Connection, season_year: int) -> InvariantResult:
    """For every team with an active assigned coach, team.gm_personality equals
    coach.personality_archetype."""
    ...


# Registry — order matters for report output
ALL_INVARIANTS = [
    ('01 Career stats = sum of seasons', invariant_01_career_stats_match_seasons),
    ('02 No orphan FK references', invariant_02_no_orphan_fk_references),
    ('03 Cap discipline', invariant_03_cap_discipline),
    ('04 Roster integrity', invariant_04_roster_integrity),
    ('05 Contract continuity', invariant_05_contract_continuity),
    ('06 Awards uniqueness', invariant_06_awards_uniqueness),
    ('07 Champion uniqueness', invariant_07_champion_uniqueness),
    ('08 Coach assignment integrity', invariant_08_coach_assignment_integrity),
    ('09 Age progression', invariant_09_age_progression),
    ('10 Retirement plausibility', invariant_10_retirement_plausibility),
    ('11 Player team pointer sync', invariant_11_player_team_pointer_sync),
    ('12 Coach-team personality sync', invariant_12_coach_team_personality_sync),
]


def run_all_invariants(conn: sqlite3.Connection, season_year: int) -> list:
    """Run every invariant. Returns list of (name, passed, detail) tuples."""
    results = []
    for name, fn in ALL_INVARIANTS:
        try:
            passed, detail = fn(conn, season_year)
        except Exception as e:
            passed, detail = False, f"invariant raised exception: {e}"
        results.append((name, passed, detail))
    return results
```

For each invariant, write the actual SQL/logic. If a piece of data the invariant needs doesn't exist yet (e.g., an awards table), check whether it exists in the current schema first. If it doesn't, the invariant should return `(True, "skipped — awards table not yet implemented")` rather than crashing. Note skipped invariants in the report.

### Task 3 — League Health Report

Create `src/league/health_report.py`:

```python
"""Phase 4 — League Health Report generator.

Produces a one-page summary of league state after a stress test run.
Per docs/Phase4_DesignDecisions.md §3.3.
"""
import sqlite3
from src.utils.constants import (
    HEALTH_STAR_RATING_THRESHOLD,
    HEALTH_AGE_BUCKETS,
    HEALTH_CAP_BUCKETS,
)


def generate_health_report(conn: sqlite3.Connection, year_one: int, year_final: int) -> str:
    """Produce the report as a printable string.

    Sections (each as a labeled block):
      - Run summary (years covered, seasons completed)
      - Roster turnover %: distinct starters in year_final vs year_one, league-wide
      - Age distribution histogram by position group
      - Cap distribution: count of teams in each cap bucket
      - Talent distribution: average overall by position, year-over-year delta
      - Star count (rating >= HEALTH_STAR_RATING_THRESHOLD), year-over-year delta
      - Champion list across the run
      - Competitive balance: variance in W% across the league at year_final
      - AI rebuild cycles: count of teams whose gm_personality changed
        (proxy for coach turnover) — uses transaction_log if available; falls back
        to "N/A — coach turnover tracking not yet implemented"
    """
    ...
```

Format the output as plain text with clear section headers, suitable for terminal display. Width ~80 chars. Use simple ASCII (no fancy box-drawing).

### Task 4 — Stress harness orchestrator

Create `src/league/stress_harness.py`:

```python
"""Phase 4 — Headless multi-season simulation harness.

Runs N seasons end-to-end without UI prints, optionally running the
invariant battery after each season and the League Health Report at the end.

Per docs/Phase4_DesignDecisions.md §3.1.
"""
import sqlite3
import time
from contextlib import redirect_stdout
import io


def run_stress_test(
    db_path: str,
    n_seasons: int,
    mode: str,                      # 'invariants' or 'smoke'
    starting_season_year: int,
    print_progress: bool = True,
) -> dict:
    """Main entry point.

    Returns a dict with:
      - 'completed_seasons': int
      - 'crashed': bool
      - 'crash_detail': str | None
      - 'invariant_results_by_year': dict[int, list]  (only if mode='invariants')
      - 'health_report': str  (only if mode='invariants')
      - 'duration_seconds': float

    Loop per season:
      1. Advance through regular season (call advance_week until season complete)
         Wrap calls in redirect_stdout(io.StringIO()) to suppress narration.
         Make sure simulate_game is called with verbose=False.
      2. Advance through playoffs (advance_week continues into playoffs)
      3. Run season archive (whatever Phase 2 does at season end)
      4. Advance through full offseason (call advance_phase repeatedly until
         next regular season)
      5. If mode='invariants', run invariants against the just-completed season
         and store the results
      6. Check timeout — if a single season exceeds STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON,
         mark crashed and bail
    """
    ...


def _advance_one_season_silent(conn: sqlite3.Connection) -> None:
    """Run a single season + offseason headlessly. Suppresses stdout."""
    ...
```

Key design points:

- **Use existing functions, don't re-implement.** Import `advance_week` from `src/league/season.py`, `advance_phase` from `src/league/offseason.py`. The harness orchestrates these in a loop; it does not contain game logic.
- **Suppress narration via stdout redirection.** The simplest reliable way is `with redirect_stdout(io.StringIO()):` around the whole season advancement. The `simulate_game(verbose=False)` flag exists already — make sure that's threaded through wherever the harness triggers game simulation.
- **The player coach is treated as an AI for the duration of the test.** No interactive prompts. If the existing offseason or season loop has any interactive prompt for the player team, find and bypass it (or note the bypass mechanism — it may already exist in the form of a `--no-prompt` flag or default behavior).

### Task 5 — CLI entry point

Create `run_stress_test.py` in the project root, following the pattern of `run_season.py` and `run_offseason.py`:

```python
"""Phase 4 — Multi-season stress test CLI.

Usage:
    python run_stress_test.py saves/test.db --invariants --seasons 3
    python run_stress_test.py saves/test.db --smoke --seasons 10
    python run_stress_test.py saves/test.db --invariants    # defaults to 3 seasons
    python run_stress_test.py saves/test.db --smoke         # defaults to 10 seasons
"""
import argparse
import sqlite3
import sys
from src.utils.constants import STRESS_TEST_DEFAULT_SEASONS, STRESS_TEST_SMOKE_SEASONS
from src.db.connection import get_connection
from src.league.stress_harness import run_stress_test
from src.league.invariants import ALL_INVARIANTS


def main():
    parser = argparse.ArgumentParser(description="Phase 4 multi-season stress harness")
    parser.add_argument('db_path', help='Path to franchise .db file')
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--invariants', action='store_true',
                            help='Run full invariant battery after each season (ship gate)')
    mode_group.add_argument('--smoke', action='store_true',
                            help='Crash-detection only; longer runs, no invariant checks')
    parser.add_argument('--seasons', type=int, default=None,
                        help=f'Number of seasons to run. Default: {STRESS_TEST_DEFAULT_SEASONS} for --invariants, '
                             f'{STRESS_TEST_SMOKE_SEASONS} for --smoke')

    args = parser.parse_args()

    mode = 'invariants' if args.invariants else 'smoke'
    n_seasons = args.seasons or (STRESS_TEST_DEFAULT_SEASONS if mode == 'invariants' else STRESS_TEST_SMOKE_SEASONS)

    # Get current season from league table
    conn = get_connection(args.db_path)
    starting_year = conn.execute("SELECT current_season FROM league WHERE id=1").fetchone()[0]
    conn.close()

    print(f"Stress test: {n_seasons} seasons starting from {starting_year}, mode={mode}")
    print("=" * 70)

    result = run_stress_test(
        db_path=args.db_path,
        n_seasons=n_seasons,
        mode=mode,
        starting_season_year=starting_year,
    )

    # Print results
    print(f"\nCompleted seasons: {result['completed_seasons']}/{n_seasons}")
    print(f"Duration: {result['duration_seconds']:.1f}s")

    if result['crashed']:
        print(f"\n❌ CRASHED: {result['crash_detail']}")
        sys.exit(2)

    if mode == 'invariants':
        print("\n" + "=" * 70)
        print("INVARIANT BATTERY")
        print("=" * 70)
        any_failed = False
        for year, results in result['invariant_results_by_year'].items():
            print(f"\nSeason {year}:")
            for name, passed, detail in results:
                marker = '✓' if passed else '✗'
                print(f"  {marker} {name}")
                if not passed:
                    print(f"      {detail}")
                    any_failed = True

        print("\n" + "=" * 70)
        print("LEAGUE HEALTH REPORT")
        print("=" * 70)
        print(result['health_report'])

        sys.exit(1 if any_failed else 0)

    # Smoke mode
    print(f"\n✓ Smoke test passed: {result['completed_seasons']} seasons completed without crash")
    sys.exit(0)


if __name__ == '__main__':
    main()
```

## Constraints — what NOT to touch

- Do NOT modify any Phase 0–3 game logic. The harness is read-only against existing systems and only ORCHESTRATES them.
- Do NOT fix any bugs the harness surfaces. Failing invariants and Phase 0–3 misbehavior are findings, not fixes. Log them; move on.
- Do NOT add UI for the report beyond plain text. (Phase 4 prompt #9 handles end-of-season display.)
- Do NOT add any new game mechanics or AI behaviors. (Phase 4 prompt #3.)
- Do NOT modify `assign_coach_to_team` or any coach identity code from prompt #1.
- Do NOT add the player-vacancy mechanic or owner sentiment. (Phase 4 prompt #4.)
- If an invariant references data that doesn't exist in the schema yet (e.g., MVP/OPOY awards table), have the invariant return `(True, "skipped — <reason>")` rather than failing. Note skipped invariants in the output so they're tracked.

## Test plan

### Step 1 — Generate a fresh save

```bash
rm -f saves/phase4_stress.db
python generate.py saves/phase4_stress.db --season 2024
```

### Step 2 — Run the 3-season invariant battery

```bash
python run_stress_test.py saves/phase4_stress.db --invariants --seasons 3
```

Expected output: each of the 12 invariants runs against each of 3 seasons (36 invariant evaluations total). Output prints PASS/FAIL per invariant per season, then the League Health Report.

**This prompt is complete when**:
- The harness runs to completion (does not crash)
- All 12 invariants execute (PASS, FAIL, or "skipped" — all three are acceptable)
- The League Health Report prints all sections
- Exit code: 0 if all invariants passed, 1 if any failed (NOT a prompt failure — a finding)

### Step 3 — Run the 10-season smoke test

```bash
rm -f saves/phase4_smoke.db
python generate.py saves/phase4_smoke.db --season 2024
python run_stress_test.py saves/phase4_smoke.db --smoke --seasons 10
```

Expected: completes 10 seasons. Crashing here is the only true failure mode for smoke.

### Step 4 — Document findings

Create `docs/Phase4_StressTest_BaselineFindings.md` capturing:
- Which invariants pass / fail / skip on a fresh save with the current Phase 0–3 code
- Any patterns in the failures (e.g., "retirement rate is consistently 4%, well below the 8% target — suggests aging tuning is too conservative")
- Crashes encountered in smoke mode (if any)

This document seeds the work for prompts #3, #7, #10 — it tells us what's actually broken vs. what we assumed was broken.

### Step 5 — Update CLAUDE.md

Append to the Phase 4 checklist:

```
- [x] Save model refactor
- [x] Multi-season stress harness + invariant battery + League Health Report
- [ ] AI GM team-phase classifier + transition rules
...
```

Add `run_stress_test.py`, `src/league/stress_harness.py`, `src/league/invariants.py`, `src/league/health_report.py` to the project structure map.

## Reference

Full design context: `docs/Phase4_DesignDecisions.md`, especially:
- §1.4 Stability MVP target (3 hard, 10 soft)
- §3 Multi-Season Stability (entire section)
- §3.2 Invariant battery (12 invariants — exact specs)
- §3.3 League Health Report contents
- §9 Phase 4 Exit Criteria — items 1–3 reference this harness
