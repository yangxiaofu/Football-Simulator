# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Football Simulator — Claude Code Project Context

## What This Project Is

A deep, text-based NFL franchise simulator inspired by Out of the Park Baseball. The player acts as both General Manager and Head Coach of a fictional NFL franchise, building a dynasty across multiple seasons through smart drafting, cap management, and scheme decisions.

Target platform: **Steam (Windows)**
Tech stack: **Python 3.11+ / SQLite** — standard library only, zero external dependencies. `requirements.txt` is intentionally empty (documents future optional deps in comments). Exception: `pywebview>=5.0` added in Phase 6.
Save format: One `.db` file per franchise (SQLite database)

---

## Current Build State

**Phase 6 — GUI (pywebview + PyInstaller), Prompt 7b complete.**

- Phases 0–5 are fully shipped. Do not re-implement or revisit systems from those phases unless fixing a confirmed bug.
- Phase 6 design is locked in `docs/ui/` (9 docs). Framework: HTML/CSS/JS + Alpine.js inside pywebview.
- Milestones shipped: 5.1 (Window + Shell), 5.2 (Team Dashboard), 5.3 (Roster + Player Card), 5.5 (Schedule + Game Preview + Game Recap + first DB mutations), 5.6 (Front Office Hub — render-only, mode-aware), 5.7a (FA Market F-41 + FA Player Card F-42 — read-only), 5.7b (generic modal framework + FA modal stack F-43/F-44/F-45 + 3 contract mutations + watchlist). **The Continue button is now enabled.**
- 5.7b live: generic `modal.js` stack (focus-trap, ESC top-only, backdrop, ARIA — reused by P8/P9); `do_sign_free_agent`, `do_cut_player`, `do_restructure_contract`, `do_add_to_watchlist` (synchronous, process-global single-flight lock, no JobManager — ops are O(1)). Save file now writes contracts/cuts/restructures. Cap recalc is satisfied at the `src.transactions.*` business layer (UI wrappers must NOT re-call it). `player.is_watchlisted` column added (ensure_player_watchlist_column migration).
- Counter-offer flow is NOT implemented — `countered`/`shopped`/`walked` surface as a rejection (later prompt). Cut `post_june_1` param accepted but not honored (standard release only).
- Tests: `python -m pytest src/ui/presenters/tests/ -v` → 79 passed, 1 skipped (optional save absent). New: `test_fa_mutations.py`, `test_modal_views.py`.
- Milestone 5.6.b (do_advance_phase UI mutation + phase advancement button on FO Hub) is deferred. Phase advancement remains CLI-only.
- F-40 (FA Hub) is absorbed into F-01's FA mode — no separate screen. The "Browse FA Market" CTA routes directly to F-41.
- Phase 7: Real Rosters (community data pack, stat-derived ratings from nflfastR/PFR). Design notes in `docs/design/Phase6_RealRosters_DesignNotes.md`.

**One rule: never build UI for a system that isn't working. Run phase exit criteria before advancing.**

---

## Common Commands

All commands are run from the project root. Saves live in `saves/` (gitignored).

```bash
# Create a new franchise
python generate.py saves/<name>.db --season 2024
# Optional: --coach-first-name --coach-last-name --coach-archetype

# Roster / stats inspection
python query_roster.py saves/<name>.db --team CHI
python view_stats.py saves/<name>.db --leaderboard passing --top 10
python view_stats.py saves/<name>.db --stars --week 5
python view_sentiment.py saves/<name>.db --owner
python view_records.py saves/<name>.db

# Simulate
python simulate_game.py saves/<name>.db --home ATL --away CLE --week 1
python run_season.py saves/<name>.db --advance-week
python run_season.py saves/<name>.db --complete-season
python run_season.py saves/<name>.db --standings
python run_season.py saves/<name>.db --depth-chart --team CHI

# Offseason (10-phase loop: review → tags → scouting → FA → draft → camp)
python run_offseason.py saves/<name>.db                  # status header
python run_offseason.py saves/<name>.db --advance-phase
python run_offseason.py saves/<name>.db --draft-board
python run_offseason.py saves/<name>.db --mock-draft

# Multi-season stress harness (headless)
python run_stress_test.py saves/<name>.db --seasons 3

# GUI (Phase 6)
python -m src.ui.window saves/<name>.db           # normal mode
python -m src.ui.window saves/<name>.db --debug   # + Chromium DevTools
```

### Running Verification Tests

No pytest config exists. Verification is per-phase scripts that create their own scratch DB, run a scenario, and exit 0/1.

```bash
python tests/verify/verify_phase5_p4.py                       # most scripts self-bootstrap
python tests/verify/verify_phase5_p9.py saves/scratch.db      # some take explicit DB path
python tests/verify/verify_phase5_shipgate.py                 # full 2-season playthrough + 10-season smoke
python tests/verify/verify_phase5_shipgate.py --skip-smoke    # fast iteration; final gate MUST NOT skip

# GUI presenter tests (pytest required)
python -m pytest src/ui/presenters/tests/ -v
```

Ship gate scripts write a report to `docs/reports/PhaseN_ShipGate_Report.md`.

### Database Inspection

```bash
sqlite3 saves/<name>.db
# .tables / .schema <table> / .mode column / .headers on
```

Schema is applied via `src/db/schema.sql` plus `ensure_*` migration helpers in `src/db/connection.py`. Older saves are forward-migrated on connect. **When adding a new table or column post-Phase-0, add both an `ensure_*` helper AND the canonical definition in `schema.sql`.**

---

## GDD Reference Guide

Read the relevant GDD section before implementing any system. These are authoritative.

| System | Primary Reference |
|---|---|
| Game vision, core loop, dynasty design | `docs/gdd/GDD_Layer1_CoreDesign.md` |
| Scouting system | `docs/gdd/GDD_Layer1_CoreDesign.md` §13 |
| Play resolution engine, ratings, fatigue | `docs/gdd/GDD_Layer2_SimulationSpec.md` |
| Injury system, weather, special teams | `docs/gdd/GDD_Layer2_SimulationSpec.md` §5–7 |
| Free agency, contracts, trades, draft | `docs/gdd/GDD_Layer2B_TransactionOffseason.md` |
| Player satisfaction, holdouts, retirements | `docs/gdd/GDD_Layer2B_TransactionOffseason.md` §7 |
| Full SQLite schema (all tables) | `docs/gdd/GDD_Layer3_DataModel.md` |
| Build order, phase exit criteria | `docs/gdd/GDD_Layer4_FeatureRoadmap.md` |
| Coach identity, media, dynasty | `docs/design/Phase4_DesignDecisions.md` |
| GUI design (Phase 6, locked) | `docs/ui/` (9 docs) |

---

## Runtime Flow (How Systems Connect)

This section documents multi-file orchestration that can't be inferred from individual files.

**Single game** (`simulate_game.py` or called from season loop)
`game_sim.py` orchestrates: coin toss → `play_caller` selects play → `play_pass`/`play_run`/`play_special` resolves via `matchup.matchup_probability(SAR_a, SAR_d)` → `ratings.py` provides SAR (never raw `true_overall` outside engine) → `fatigue` + `injury` + `weather` modifiers → `stats.py` accumulates → end of game writes `box_score`, `play`, `key_play`. Game reads starters from `depth_chart`.

**Week advance** (`run_season.py --advance-week` → `src/league/season.py`)
Run all games → `weekly_stats.py` recomputes aggregates (idempotent) → `stars_selection.py` populates `weekly_award` → `tier2_triggers.py` checks triggers → `satisfaction.py` weekly eval → `depth_chart` injury fallback / healing → `owner_sentiment` rolls up → CLI prompts Tier 1 press conference (autopilot in headless).

**Season end** (after Super Bowl)
`playoffs.py` finishes bracket → `archive.py` aggregates stats + *deletes `play` rows* (key_play kept permanently) → `development.py` ages/develops → `awards.py` → `legacy.py` → `narrative_beats.py` → `season_recap.py` (gated by `season.recap_shown`).

**Offseason** (`run_offseason.py` → `src/league/offseason.py`)
10-phase sequence stored in `offseason_state`: `review → franchise_tags → scouting → free_agency → hall_of_fame → draft → rookie_signing → roster_cuts → camp → reset`. HOF inductions are a side-effect when leaving `free_agency` (no schema change).

**GUI mutations** (Phase 6, `src/ui/jobs.py`)
`Api.do_advance_week`/`do_sim_game` submit to `JobManager` singleton, which runs mutations on a daemon thread with its own sqlite connection (never `Api._conn`). Process-global lock enforces one mutation at a time. JS `pollTask` polls `get_task_status` until done; `Api._invalidate_conn()` drops the stale cached read connection. Calling `season.advance_week` directly is headless-safe — interactive press-conference prompts live only in `run_season.py` CLI.

**Coach identity** (critical invariant)
`coach_career` = durable identity; `coach_tenure` = team-by-team history. **All coach reassignments must go through `transactions/coaching.assign_coach_to_team()`** — never UPDATE `team.head_coach_id` directly. This is the single mutation point maintaining Invariants #11–12. `coaching_carousel.py` is the AI fire/hire logic that calls this helper.

---

## Key Design Decisions (Do Not Change Without Updating the GDD)

### Ratings
- Players have **true ratings (1–99)** stored in the DB, used only by the simulation engine
- UI always displays **letter grades** — never raw numbers
- Conversion: A+=97-99, A=93-96, A-=90-92, B+=87-89, B=83-86, B-=80-82, C+=77-79, C=73-76, C-=70-72, D+=67-69, D=60-66, F=<60
- **Scouted ratings** are stored separately in `scouted_rating` — never expose `player.true_overall` to the UI layer

### Scheme-Adjusted Rating (SAR)
- Engine never uses raw `true_overall` — always SAR
- `SAR = true_overall + (scheme_fit_bonus × coordinator_fit_multiplier)`

### Matchup Probability
- Logistic function: `P(win) = 1 / (1 + e^(-0.07 × (SAR_attacker - SAR_defender)))`
- `k = 0.07` — adjust only after running 500+ test games

### Play Log Storage
- `play` table: current season only — deleted during season archive
- `key_play`: top 8 plays per game, permanent
- `box_score`: per-player game stats, permanent
- Never query `play` for historical stats — use `player_season_stats` or `player_career_stats`

### Cap Space
- `team.cap_space` is a **cached value**, not computed live
- Call `recalculate_cap_space(team_id, season_year, conn)` after every contract/roster action — never sum `contract_year.cap_hit` at render time

### Save System
- One SQLite `.db` file = one franchise, in `saves/`
- Autosave after every committed action (SQLite transactions — commit = save)

---

## Code Quality Rules

### Before Writing Any Code
1. Check `src/utils/constants.py` first — use existing constants before creating new ones
2. Add new constants to `constants.py` before writing the code that uses them
3. Confirm the module belongs in the correct `src/` subdomain

### No Magic Numbers
Every tuning constant, threshold, limit, and rate must live in `src/utils/constants.py`. Never inline numeric values in simulation or business logic. Key examples: `MATCHUP_K`, `ACTIVE_ROSTER_SIZE`, `LETTER_GRADE_THRESHOLDS`, `BASE_INJURY_RATE`, `SALARY_CAP_YEAR_ONE`.

### Layer Boundaries (Strictly Enforced)

| Layer | Does | Must NOT |
|---|---|---|
| `src/db/` | All SQL queries and schema access | Contain business logic or simulation math |
| `src/engine/` | Play resolution, game loop, SAR | Write UI output or call transaction system |
| `src/league/` | Roster, standings, schedule logic | Execute raw SQL |
| `src/transactions/` | Trades, FA, contracts, draft | Simulate plays or access engine internals |
| `src/ui/` | Display and API surface only | Compute anything; call engine or db directly |
| `src/utils/` | Shared helpers and constants | Import from other `src/` modules |

### Refactor Exceptions (Documented SQL-in-module violations)

These modules have approved inline SQL with documented rationale — do not "fix" them:
- `src/league/invariants.py` — DB integrity auditor; SQL IS its purpose
- `src/league/health_report.py` — analytics/diagnostics
- `src/transactions/coaching.py` — atomic coach assignment (Invariants #11-12)
- `src/league/narrative_beats.py` — slot-filling tightly coupled to data retrieval
- `src/league/historical_records.py` — complex analytics / record book
- `src/transactions/tier2_triggers.py` — INSERT guard must be atomic with trigger decision
- `src/league/weekly_stats.py` — aggregation engine; SQL IS its purpose

### Refactor Checkpoints
Run a refactor pass after a full module is working — not after individual files. Check: inlined numbers → `constants.py`, DB queries in `db/` layer, no `true_overall` outside engine, no dead code.

---

## Coding Conventions

```python
# Database connections — always use context manager
conn = sqlite3.connect(save_path)
conn.execute("PRAGMA foreign_keys = ON")
conn.row_factory = sqlite3.Row

# Mutations — wrap in explicit transactions
with conn:
    conn.execute("UPDATE team SET cap_space = ? WHERE id = ?", (new_cap, team_id))

# Matchup probability
def matchup_probability(sar_attacker: int, sar_defender: int, k: float = 0.07) -> float:
    return 1 / (1 + math.exp(-k * (sar_attacker - sar_defender)))

# Transaction logging — required after every roster/contract action
def log_transaction(conn, season_year, week, txn_type, team_id, player_id, description, cap_impact=0):
    conn.execute("""
        INSERT INTO transaction_log
        (season_year, week_number, transaction_type, team_id, player_id, description, cap_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (season_year, week, txn_type, team_id, player_id, description, cap_impact))
```

---

## What Is Explicitly Out of Scope

Do not implement during the main build:
- Practice squad poaching and full waiver wire priority rules
- Financial system (ticket prices, jersey sales, revenue modeling)
- Multiplayer or online leagues
- 2D/3D match visualization
- Historical replay mode (real NFL seasons)
- Expansion teams or relocation

---

## Phase History

Completed phase checklists are archived in `docs/reports/` (Phase4_ShipGate_Report.md, Phase5_ShipGate_Report.md). Phases 0–5 are fully shipped — their implementation details live in `src/` and the GDDs.

---

## Updating This File

Update `CLAUDE.md` when:
- A phase or milestone ships (update Current Build State)
- A significant design decision changes (update here + the GDD)
- New source files are added to the architecture
- A deferred feature gets promoted to in-scope
