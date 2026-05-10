# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Football Simulator — Claude Code Project Context

## What This Project Is

A deep, text-based NFL franchise simulator inspired by Out of the Park Baseball. The player acts as both General Manager and Head Coach of a fictional NFL franchise, building a dynasty across multiple seasons through smart drafting, cap management, and scheme decisions.

Target platform: **Steam (Windows)**
Tech stack: **Python 3.11+ / SQLite**
Save format: One `.db` file per franchise (SQLite database)

---

## Project Structure

```
/Football Simulator/
├── CLAUDE.md              ← you are here
├── generate.py            ← CLI: generate a new franchise database
├── query_roster.py        ← CLI: display team roster
├── simulate_game.py       ← CLI: simulate a single game or batch
├── run_season.py          ← CLI: season management (Phase 2)
├── run_offseason.py       ← CLI: offseason management (Phase 3)
├── run_stress_test.py     ← CLI: multi-season stress test (Phase 4)
├── view_records.py        ← CLI: league records and history viewer (Phase 4)
├── docs/                  ← Game Design Documents (read before implementing any system)
│   ├── GDD_Layer1_CoreDesign.md
│   ├── GDD_Layer2_SimulationSpec.md
│   ├── GDD_Layer2B_TransactionOffseason.md
│   ├── GDD_Layer3_DataModel.md
│   ├── GDD_Layer4_FeatureRoadmap.md
│   ├── Phase4_StressTest_BaselineFindings.md
│   └── Phase4_ShipGate_Report.md
├── src/                   ← all Python source code
│   ├── db/                ← schema, migrations, connection helpers
│   │   ├── schema.sql           ← full SQLite schema
│   │   ├── connection.py        ← connection helpers, CRUD utilities
│   │   ├── cap.py               ← cap space recalculation
│   │   ├── transactions.py      ← transaction log writer
│   │   └── queries.py           ← centralized SQL queries (Phase 2)
│   ├── engine/            ← simulation engine (Phase 1, complete)
│   │   ├── constants_engine.py  ← narration templates, yard distributions
│   │   ├── matchup.py           ← logistic probability, 1v1 resolution
│   │   ├── fatigue.py           ← stamina drain, fatigue penalties
│   │   ├── injury.py            ← injury checks, severity, career impact
│   │   ├── weather.py           ← weather generation and modifiers
│   │   ├── narration.py         ← play-by-play text templates
│   │   ├── ratings.py           ← SAR calculation (scheme fit, clutch, etc.)
│   │   ├── game_state.py        ← GameState dataclass, clock/drive mgmt
│   │   ├── play_caller.py       ← play selection, 4th down decisions
│   │   ├── stats.py             ← stat accumulator, DB writes
│   │   ├── play_pass.py         ← 5-step pass resolution
│   │   ├── play_run.py          ← 3-step run resolution
│   │   ├── play_special.py      ← FG, punt, kickoff, XP, 2pt
│   │   └── game_sim.py          ← main game loop orchestrator
│   ├── generation/        ← data generation (Phase 0)
│   ├── league/            ← season, standings, playoffs, development (Phase 2)
│   │   ├── standings.py         ← NFL tiebreaker logic, division/conference rankings
│   │   ├── season.py            ← season loop orchestrator, week advancement
│   │   ├── playoffs.py          ← playoff bracket generation, seeding, simulation
│   │   ├── archive.py           ← season-end archival, stats aggregation
│   │   ├── development.py       ← player development and aging logic
│   │   ├── awards.py            ← MVP, Pro Bowl, All-Pro calculations
│   │   ├── legacy.py            ← legacy score and dynasty tracking
│   │   ├── offseason.py         ← offseason loop orchestrator, phase sequencing
│   │   ├── invariants.py        ← 12-invariant battery
│   │   ├── health_report.py     ← League Health Report generator
│   │   ├── stress_harness.py    ← headless multi-season orchestrator
│   │   ├── team_phase.py        ← team phase classifier (rebuild/bridge/contend/win_now/decline)
│   │   ├── historical_records.py ← league records, leaderboards, champion history (Phase 4)
│   │   ├── owner_sentiment.py   ← owner sentiment tracking, hot seat tiers (Phase 4)
│   │   ├── era_context.py       ← era difficulty multiplier computation (Phase 4 Prompt #7)
│   │   ├── peer_ranking.py      ← coach career peer rankings (Phase 4 Prompt #7)
│   │   ├── narrative_beats.py   ← end-of-season narrative generation (Phase 4 Prompt #9)
│   │   ├── weekly_stats.py      ← weekly + season running stat aggregation (Phase 5)
│   │   └── stars_selection.py   ← Stars of the Week selection algorithm (Phase 5)
│   ├── transactions/      ← trades, free agency, contracts, draft, coaching
│   │   ├── contracts.py         ← contract signing, restructuring, release, market value
│   │   ├── satisfaction.py      ← weekly evaluation, warning signals, interventions, contagion
│   │   ├── free_agency.py       ← FA market, interest tiers, pitch meetings, offers, AI signings
│   │   ├── franchise_tag.py     ← exclusive/transition tags, salary calculation, consecutive tags
│   │   ├── trades.py            ← trade value, evaluation, GM personality, AI offers, execution
│   │   ├── draft.py             ← draft loop, pick selection, AI picks, rookie contracts
│   │   ├── coaching.py          ← coach assignment, tenure tracking, personality sync (Phase 4)
│   │   ├── coaching_carousel.py ← AI coach fire/hire based on performance (Phase 4)
│   │   ├── coach_offers.py      ← job offers for vacant coaches (Phase 4)
│   │   ├── press_conference.py  ← Tier 1 weekly press conferences, autopilot (Phase 4 Prompt #5)
│   │   ├── tier2_press_conference.py ← Tier 2 dramatic press events (Phase 4 Prompt #6)
│   │   └── tier2_triggers.py        ← Tier 2 trigger detection (Phase 4 Prompt #6)
│   ├── scouting/          ← draft class generation, scouting reports, draft board
│   │   ├── prospects.py         ← draft class generation, prospect attributes, combine
│   │   ├── scouts.py            ← scout assignment, accuracy tiers, flag detection, UI-safe views
│   │   ├── reports.py           ← phase reports, combine events, competitor intel, mock draft
│   │   └── board.py             ← draft board building, entries, overrides, post-draft review
│   ├── ui/                ← terminal interface
│   │   ├── standings_display.py ← division/conference standings
│   │   ├── stats_display.py     ← stat leaderboards
│   │   ├── roster_display.py    ← roster with contracts
│   │   ├── season_summary.py    ← end-of-season summary display (Phase 4 Prompt #9)
│   │   ├── career_view.py       ← coach career view (Phase 4 Prompt #9)
│   │   ├── dramatic_moments.py  ← dynasty/HOF moment rendering (Phase 4 Prompt #9)
│   │   └── colors.py            ← ANSI color helpers
│   └── utils/             ← shared helpers, constants, probability functions
│       ├── constants.py         ← all tuning constants, thresholds, position lists
│       ├── ai_behavior_matrix.py ← 5x5 personality×phase behavior grid (Phase 4)
│       ├── press_templates.py   ← 30 press conference templates across 8 contexts (Phase 4 Prompt #5)
│       ├── tier2_templates.py   ← 24 dramatic press templates (Phase 4 Prompt #6)
│       └── star_templates.py    ← 40 Stars of the Week narrative templates (Phase 5 Prompt #4)
├── tests/
│   └── verify/            ← Phase 4 verification scripts
│       ├── verify_phase4_p1.py      ← coach identity schema
│       ├── verify_phase4_p2_5.py    ← stress harness baseline
│       ├── verify_phase4_p3.py      ← AI GM behavior
│       ├── verify_phase4_p4.py      ← owner sentiment
│       ├── verify_phase4_p5.py      ← Tier 1 press conferences
│       ├── verify_phase4_p6.py      ← Tier 2 press conferences
│       ├── verify_phase4_p7.py      ← coach legacy expansion
│       ├── verify_phase4_p8.py      ← historical records
│       ├── verify_phase4_p9.py      ← end-of-season UI
│       ├── verify_phase4_shipgate.py ← ship gate (8 exit criteria)
│       ├── verify_phase5_p1.py      ← stats schema & weekly aggregation
│       ├── verify_phase5_p2.py      ← view stats CLI
│       ├── verify_phase5_p3.py      ← depth chart system
│       └── verify_phase5_p4.py      ← Stars of the Week
├── saves/                 ← franchise .db files (gitignored)
└── assets/                ← future UI assets (logos, fonts)
```

---

## GDD Reference Guide

Before implementing any system, read the relevant GDD section. The GDDs are the authoritative source for how every mechanic is designed to work.

| System | Primary Reference |
|---|---|
| Game vision, core loop, dynasty design | `docs/GDD_Layer1_CoreDesign.md` |
| Scouting system (college + free agents) | `docs/GDD_Layer1_CoreDesign.md` §13 |
| Play resolution engine, ratings, fatigue | `docs/GDD_Layer2_SimulationSpec.md` |
| Injury system, weather, special teams | `docs/GDD_Layer2_SimulationSpec.md` §5–7 |
| Free agency, contracts, trades, draft | `docs/GDD_Layer2B_TransactionOffseason.md` |
| Player satisfaction, holdouts, retirements | `docs/GDD_Layer2B_TransactionOffseason.md` §7 |
| Full SQLite schema (all tables) | `docs/GDD_Layer3_DataModel.md` |
| Build order, phase exit criteria | `docs/GDD_Layer4_FeatureRoadmap.md` |
| Coach identity, media, dynasty, exit criteria | `docs/Phase4_DesignDecisions.md` |
| Phase 4 ship gate validation results | `docs/Phase4_ShipGate_Report.md` |

---

## Current Build Phase

**Phase 0 — Foundation** ✅

Goal: Database schema created, 32 teams generated with rosters, queryable from command line.

### Phase 0 Checklist
- [x] SQLite schema created (`src/db/schema.sql`)
- [x] Database connection module (`src/db/connection.py`)
- [x] Cap space recalculation utility (`src/db/cap.py`)
- [x] Transaction log writer (`src/db/transactions.py`)
- [x] 32 fictional teams generated with divisions and conferences
- [x] Player generator (position-specific attribute distributions)
- [x] 53-man rosters for all 32 teams (1,696 players)
- [x] Staff generated for all 32 teams (352 staff total)
- [x] Schedule generated (17-game regular season, 272 games)
- [x] Exit criteria passing: `python query_roster.py saves/test_franchise.db --team CHI`

**Phase 0 Complete!** ✅

---

**Phase 1 — Simulation Engine**

Goal: Play resolution engine that simulates full games with narrated play-by-play and realistic stat output.

### Phase 1 Checklist
- [x] Engine constants updated (`src/utils/constants.py` — injury/severity GDD-correct, 80+ new constants)
- [x] Engine-only constants (`src/engine/constants_engine.py` — narration templates, yard distributions)
- [x] Matchup system (`src/engine/matchup.py` — logistic probability, 1v1 and group resolution)
- [x] Fatigue system (`src/engine/fatigue.py` — stamina drain, fatigue penalties, season wear)
- [x] Injury system (`src/engine/injury.py` — per-play checks, 6-tier severity, career-altering)
- [x] Weather system (`src/engine/weather.py` — generation by climate/week, rating modifiers)
- [x] Narration engine (`src/engine/narration.py` — template library for all play types)
- [x] SAR calculation (`src/engine/ratings.py` — scheme fit, coach bonus, home field, clutch)
- [x] Game state (`src/engine/game_state.py` — clock, drives, possession, scoring)
- [x] Play calling (`src/engine/play_caller.py` — situational play selection, 4th down decisions)
- [x] Stats accumulator (`src/engine/stats.py` — in-memory tracking, box_score/play/key_play writes)
- [x] Pass resolution (`src/engine/play_pass.py` — 5-step tree: pre-snap, rush, route, throw, YAC)
- [x] Run resolution (`src/engine/play_run.py` — 3-step tree: gap, second level, open field)
- [x] Special teams (`src/engine/play_special.py` — FG, punt, kickoff, XP, 2pt)
- [x] Game loop (`src/engine/game_sim.py` — coin toss, kickoff, drives, quarters, halftime, OT)
- [x] CLI entry point (`simulate_game.py` — single game and batch modes)
- [x] Tuning pass (32-game batch: stats within NFL target ranges)
- [x] Exit criteria passing: `python simulate_game.py saves/test_franchise.db --home ATL --away CLE --week 1`
- [x] Refactor pass complete (return stats, no magic numbers, layer boundaries verified)

**Phase 1 Complete!** ✅

---

**Phase 2 — Full Season Simulation** ✅

Goal: Simulate complete 17-game regular seasons + playoffs, crown champion, archive stats, develop players.

### Phase 2 Checklist
- [x] Database query module (`src/db/queries.py` — centralized SQL for standings, stats, records)
- [x] Standings calculator (`src/league/standings.py` — NFL tiebreakers, division/conference rankings)
- [x] Season loop (`src/league/season.py` — week advancement, game simulation, injury healing)
- [x] Playoff system (`src/league/playoffs.py` — bracket generation, seeding, wildcard through Super Bowl)
- [x] Season archival (`src/league/archive.py` — stats aggregation, play log cleanup, draft order)
- [x] Player development (`src/league/development.py` — age-based growth/decline, attribute history)
- [x] Awards system (`src/league/awards.py` — MVP, OPOY, DPOY, Pro Bowl, All-Pro)
- [x] Legacy score (`src/league/legacy.py` — dynasty tracking, franchise performance)
- [x] CLI entry point (`run_season.py` — advance-week, standings, complete-season)
- [x] Terminal UI (`src/ui/standings_display.py`, `stats_display.py`, `roster_display.py`)
- [x] Phase 2 constants added to `src/utils/constants.py` (development, aging, awards)
- [x] Multi-season test passing (2 full seasons simulated with development/aging)
- [x] Exit criteria passing: `python run_season.py saves/test.db --complete-season`

**Phase 2 Complete!** ✅

---

**Phase 3 — Offseason Loop** ✅

Goal: Free agency, contracts, trades, scouting, and draft systems that create a full offseason cycle.

### Phase 3 Checklist
- [x] Contract constants added to `src/utils/constants.py` (market multipliers, restructure limits, salary escalation)
- [x] Contract query functions added to `src/db/queries.py` (13 new functions for contract CRUD)
- [x] Contract system (`src/transactions/contracts.py` — offer, restructure, release, dead cap, market value)
- [x] Satisfaction constants added to `src/utils/constants.py` (warning tiers, contagion, interventions, motivation)
- [x] Satisfaction schema (`satisfaction_event`, `player_event` tables + migration function in `connection.py`)
- [x] Satisfaction query functions added to `src/db/queries.py` (11 new functions)
- [x] Player satisfaction system (`src/transactions/satisfaction.py` — weekly eval, warning signals, interventions, contagion)
- [x] Free agency constants added to `src/utils/constants.py` (preference weights, tiers, market timing, AI behavior, signals)
- [x] Free agency schema (`fa_interest` table + migration function `ensure_fa_tables()` in `connection.py`)
- [x] Free agency query functions added to `src/db/queries.py` (15 new functions)
- [x] Free agency system (`src/transactions/free_agency.py` — market generation, interest tiers, pitch meetings, offers, AI signings)
- [x] Franchise tag constants added to `src/utils/constants.py` (tag limits, top-N values, multiplier, satisfaction penalties)
- [x] Franchise tag schema (`franchise_tag` table + migration function `ensure_franchise_tag_table()` in `connection.py`)
- [x] Franchise tag query functions added to `src/db/queries.py` (13 new functions)
- [x] Franchise tag system (`src/transactions/franchise_tag.py` — exclusive/transition tags, salary calculation, consecutive tags, removal)
- [x] Trade constants added to `src/utils/constants.py` (pick values, age modifiers, GM behavior, deadline)
- [x] Trade query functions added to `src/db/queries.py` (13 new functions for trade/pick CRUD)
- [x] Trade system (`src/transactions/trades.py` — trade value, evaluation, GM personality, AI offers, execution)
- [x] Scouting constants added to `src/utils/constants.py` (position counts, accuracy tiers, flag rates, combine ranges, college mapping)
- [x] Scouting schema migration (`scouting_flag` table + `ensure_scouting_tables()` in `connection.py`)
- [x] Scouting query functions added to `src/db/queries.py` (16 new functions for draft class, prospect, assignment, scouted rating, flag CRUD)
- [x] Draft class generation (`src/scouting/prospects.py` — prospect generation, position distribution, combine, flags)
- [x] Scout assignment and evaluation (`src/scouting/scouts.py` — capacity, accuracy tiers, flag detection, UI-safe views)
- [x] Scouting phase/report constants added to `src/utils/constants.py` (phase bonuses, combine events, mock draft, intel, board weights)
- [x] Scouting report schema (`combine_event`, `competitor_intel`, `draft_board` tables + ALTER TABLE migrations in `connection.py`)
- [x] Scouting report query functions added to `src/db/queries.py` (18 new functions for phase reports, combine, intel, mock, board CRUD)
- [x] Scouting phase cycle (`src/scouting/reports.py` — phase reports, combine events, competitor intelligence, mock draft)
- [x] Draft board system (`src/scouting/board.py` — board building, entries, overrides, post-draft review)
- [x] Draft system (`src/transactions/draft.py` — draft loop, pick selection, rookie contracts)
- [x] Offseason constants added to `src/utils/constants.py` (phase sequence, narratives, roster limit)
- [x] Offseason schema (`offseason_state` table + migration function `ensure_offseason_state_table()` in `connection.py`)
- [x] Offseason query functions added to `src/db/queries.py` (8 new functions for offseason state CRUD)
- [x] Offseason loop orchestrator (`src/league/offseason.py` — 10-phase sequencing: review → tags → scouting → FA → draft → camp)
- [x] CLI entry point for offseason management (`run_offseason.py` — 15 commands, interactive draft)
- [x] Exit criteria passing: full offseason cycle completes with FA signings, draft, and roster cuts

**Phase 3 Complete!** ✅

---

**Phase 4 — Dynasty & Coach Identity** ✅

Goal: Coach identity as a first-class entity, portable careers, media/pressure system, 3-season stability.

### Phase 4 Checklist
- [x] Coach identity schema (`coach_career`, `coach_tenure` tables + `coach_id` on `legacy_score`, `hall_of_fame`)
- [x] Migration helper (`ensure_coach_tables()` in `connection.py`)
- [x] Coach constants added to `src/utils/constants.py` (age range, defaults, tenure reasons)
- [x] Single mutation helper (`src/transactions/coaching.py` — `assign_coach_to_team`)
- [x] AI coach generation (`generate_ai_coaches()` in `src/generation/teams.py`)
- [x] Player coach creation in `generate.py` (CLI flags: `--coach-first-name`, `--coach-last-name`, `--coach-archetype`)
- [x] Verification passing: `python verify_phase4_p1.py` exits 0
- [x] Multi-season stress harness + invariant battery + League Health Report
- [x] Baseline bug fixes (Inv 4, Inv 8, Inv 12 cascade) — `verify_phase4_p2_5.py` passing
- [x] AI GM behavior matrix (`src/utils/ai_behavior_matrix.py` — 25-cell personality×phase grid)
- [x] Team phase classifier (`src/league/team_phase.py` — rebuild/bridge/contend/win_now/decline)
- [x] Coaching carousel (`src/transactions/coaching_carousel.py` — AI coach fire/hire)
- [x] Phase-aware trade/FA/draft logic (behavior matrix multipliers in trades, free_agency, draft)
- [x] Verification passing: `python verify_phase4_p3.py` exits 0
- [x] 3-season stress test passing: 12/12 invariants, 10 coaching changes, 3 distinct phases
- [x] Historical records module (record book, leaderboards, champion history, CLI viewer)
- [x] Tier 1 weekly press conference system (Phase 4 Prompt #5)
- [x] Press conference constants added to `src/utils/constants.py` (autopilot choices, effects, context detection)
- [x] Press templates library (`src/utils/press_templates.py` — 30 templates across 8 contexts)
- [x] Press event schema (`press_event` table + `presser_delta` column on `owner_sentiment`)
- [x] Migration helper (`ensure_press_tables()` in `connection.py`)
- [x] Press conference module (`src/transactions/press_conference.py` — context detection, generation, resolution, autopilot)
- [x] CLI integration (`run_season.py` — interactive prompt after each regular season game)
- [x] Stress harness integration (`src/league/stress_harness.py` — headless auto-resolve)
- [x] Verification passing: `python verify_phase4_p5.py` exits 0
- [x] Tier 2 event-triggered press conference + dramatic templates (Phase 4 Prompt #6)
- [x] Legacy score integration with coach identity
- [x] Ship gate validation: 8/8 exit criteria passing (`tests/verify/verify_phase4_shipgate.py`)
- [x] Phase 4 refactor pass complete (CLAUDE.md compliance: SQL extraction, magic number harvest)

**Phase 4 Complete!** ✅

---

**Phase 5 — In-Season Stats & Media** (In Progress)

Goal: Weekly stat aggregation, leaderboards, Stars of the Week, and enhanced media system.

### Phase 5 Checklist
- [x] **Prompt #1**: Stats Schema & Weekly Aggregation
  - 5 new tables (`player_week_stats`, `player_season_running`, `team_week_stats`, `team_season_running`, `weekly_award`)
  - 33 CRUD query functions in `src/db/queries.py`
  - `src/league/weekly_stats.py` (idempotent recompute-from-SUM aggregation)
  - Integration with `season.py` (aggregate after each week)
  - Verification: `python tests/verify/verify_phase5_p1.py`
- [x] **Prompt #2**: View Stats CLI
  - `view_stats.py` CLI + queries (`--leaderboard {passing|rushing|receiving|defense|sacks|interceptions}` with `--top N` and `--week N | --through-week N`; `--player`, `--team`, `--week`, `--stars`)
  - Display via `src/ui/stats_view.py` (pure presentation, no SQL)
  - NFL-style leaderboard qualifiers (14 att/game passing, 6.25 car/game rushing)
  - `--stars` shows empty-state message until Prompt #4
  - Verification: `python tests/verify/verify_phase5_p2.py` (9 checks including scope-creep guard, Phase 4 regression, layer boundary scan)
- [x] **Prompt #3**: Depth Chart System
  - `depth_chart` table (27 granular positions, UNIQUE constraint, 3 indexes)
  - `src/transactions/depth_chart.py` (CRUD, injury fallback, healing restoration, position validation)
  - Engine integration: `game_sim.py` uses depth chart for lineup building
  - Season integration: `season.py` calls `process_injury_fallback` / `process_healing_restoration` after each week
  - CLI: `run_season.py --depth-chart`, `--set-starter`, `--swap-depth`, `--reset-depth`
  - Verification: `python tests/verify/verify_phase5_p3.py`
- [x] **Prompt #4**: Stars of the Week Selection Algorithm
  - `src/league/stars_selection.py` — selection algorithm (zero inline SQL), 4 award categories, ST threshold gate, idempotent upsert
  - `src/utils/star_templates.py` — ~40 narrative templates across OFFENSE / DEFENSE / SPECIAL_TEAMS / USER_TEAM_MVP (lambda match pattern)
  - `weekly_award` table populated after each regular-season and playoff week
  - Auto-print in weekly summary (season.py + playoffs.py); `view_stats.py --stars [--week N]` renders real data
  - Verification: `python tests/verify/verify_phase5_p4.py` (13 checks including 4 mandatory guards)
- [ ] **Prompt #5**: TBD

**Phase 5 In Progress...**

---

## Key Design Decisions (Do Not Change Without Updating the GDD)

These decisions are load-bearing — changing them has cascade effects across multiple systems.

### Ratings
- Players have **true ratings (1–99)** stored in the database, used only by the simulation engine
- The UI always displays **letter grades (A+ to F)** — never raw numbers
- Conversion: A+=97-99, A=93-96, A-=90-92, B+=87-89, B=83-86, B-=80-82, C+=77-79, C=73-76, C-=70-72, D+=67-69, D=60-66, F=<60
- **Scouted ratings** are stored separately in `scouted_rating` table — never expose `player.true_overall` to the UI layer

### Scheme-Adjusted Rating (SAR)
- The simulation engine never uses raw `true_overall` — always uses SAR
- `SAR = true_overall + (scheme_fit_bonus × coordinator_fit_multiplier)`
- Scheme fit is the primary reason player trades require more thought than sorting by Overall

### Matchup Probability
- Uses logistic function: `P(win) = 1 / (1 + e^(-0.07 × (SAR_attacker - SAR_defender)))`
- Tuning constant `k = 0.07` — adjust only after running 500+ test games

### Play Log Storage
- `play` table: **current season only** — deleted during season archive
- `key_play` table: top 8 plays per game, **permanent**
- `box_score` table: per-player game stats, **permanent**
- Never query `play` for historical stats — use `player_season_stats` or `player_career_stats`

### Cap Space
- `team.cap_space` is a **cached value**, not computed live
- Call `recalculate_cap_space(team_id, season_year, conn)` after every contract/roster action
- Never sum `contract_year.cap_hit` at render time

### Save System
- One SQLite `.db` file = one franchise
- Stored in `saves/` directory
- Autosave after every committed action (use SQLite transactions — commit = save)

---

## Working with the Database

### Creating a New Franchise
```bash
# Generate a complete franchise with teams, players, staff, and schedule
python generate.py saves/my_franchise.db --season 2024

# This creates:
# - 32 teams with divisions and conferences
# - 1,696 players (53-man rosters)
# - 352 staff members (11 per team)
# - 272 games across 17 weeks
```

### Querying a Roster
```bash
# View a team's roster
python query_roster.py saves/my_franchise.db --team CHI
python query_roster.py saves/my_franchise.db --team "Green Bay"
```

### Creating a New Database (Advanced)
```bash
# Create a new franchise database from schema only (no data)
sqlite3 saves/my_franchise.db < src/db/schema.sql
```

### Inspecting the Database
```bash
# Open SQLite CLI
sqlite3 saves/my_franchise.db

# Useful SQLite commands in the CLI:
.tables                    # List all tables
.schema table_name         # Show table structure
.mode column              # Format output as columns
.headers on               # Show column headers
SELECT * FROM team LIMIT 5;  # Query example
```

### Schema Validation
The schema is defined in `src/db/schema.sql` and must match `docs/GDD_Layer3_DataModel.md` exactly. When modifying the schema:
1. Update `src/db/schema.sql`
2. Update the corresponding GDD section
3. Test with a fresh database creation
4. Update any affected data generation code

---

## Coding Conventions

### File Organization
- One module per system domain (engine, transactions, scouting, etc.)
- Database queries live in the `db/` layer — no raw SQL in business logic files
- All constants (tuning values, rating thresholds, position lists) live in `src/utils/constants.py`

### Database Access Pattern
```python
# Always use context manager for connections
import sqlite3

def get_connection(save_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(save_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # allows dict-style column access
    return conn

# Wrap mutations in explicit transactions
with conn:  # auto-commits on success, rolls back on exception
    conn.execute("UPDATE team SET cap_space = ? WHERE id = ?", (new_cap, team_id))
```

### Probability & Simulation
```python
import math

def matchup_probability(sar_attacker: int, sar_defender: int, k: float = 0.07) -> float:
    """Returns probability (0–1) that attacker wins the matchup."""
    return 1 / (1 + math.exp(-k * (sar_attacker - sar_defender)))
```

### Rating Conversion
```python
def to_letter_grade(rating: int) -> str:
    """Convert internal 1-99 rating to display letter grade."""
    if rating >= 97: return "A+"
    if rating >= 93: return "A"
    if rating >= 90: return "A-"
    if rating >= 87: return "B+"
    if rating >= 83: return "B"
    if rating >= 80: return "B-"
    if rating >= 77: return "C+"
    if rating >= 73: return "C"
    if rating >= 70: return "C-"
    if rating >= 67: return "D+"
    if rating >= 60: return "D"
    return "F"
```

### Transaction Logging
```python
# Every roster/contract action must call this
def log_transaction(conn, season_year, week, txn_type, team_id, player_id, description, cap_impact=0):
    conn.execute("""
        INSERT INTO transaction_log
        (season_year, week_number, transaction_type, team_id, player_id, description, cap_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (season_year, week, txn_type, team_id, player_id, description, cap_impact))
```

---

## Code Quality Rules

These rules apply to every file written in this project. Do not skip them under time pressure.

### Before Writing Any Code
1. Check `src/utils/constants.py` first — if the value you need already exists there, use it
2. If you need a new constant, add it to `constants.py` before writing the code that uses it
3. Confirm the module you're writing belongs in the correct `src/` subdomain (no cross-domain SQL, no business logic in `db/`)

### No Magic Numbers
Never inline numeric values in code. Every tuning constant, threshold, limit, and rate must live in `src/utils/constants.py`.

Values that **must** be in `constants.py` (never hardcoded):

```python
# Simulation tuning
MATCHUP_K = 0.07                    # logistic curve steepness
VARIANCE_CAP = 15                   # max random modifier per play
BIG_PLAY_RATE = 0.08                # probability of 20+ yard gain
TURNOVER_BASE_RATE = 0.012          # base per-play fumble/INT probability
HOME_FIELD_MODIFIER = 3             # SAR bonus for home team

# Roster limits
ACTIVE_ROSTER_SIZE = 53
PRACTICE_SQUAD_SIZE = 16
MAX_CONTRACT_YEARS = 6
FRANCHISE_TAG_LIMIT = 1             # per team per year

# Ratings
RATING_MIN = 1
RATING_MAX = 99
LETTER_GRADE_THRESHOLDS = {         # true rating → letter grade
    97: "A+", 93: "A", 90: "A-",
    87: "B+", 83: "B", 80: "B-",
    77: "C+", 73: "C", 70: "C-",
    67: "D+", 60: "D"
}   # anything below 60 → "F"

# Injury
BASE_INJURY_RATE = 0.004            # per play baseline
FATIGUE_INJURY_MULTIPLIER = 1.3     # applied when stamina < 40%

# Fatigue
STAMINA_MILD_THRESHOLD = 60         # below this: -3 to ratings
STAMINA_MODERATE_THRESHOLD = 40     # below this: -8 to ratings
STAMINA_SEVERE_THRESHOLD = 20       # below this: -15 + double injury rate
SEASON_WEAR_START_WEEK = 10         # cumulative wear begins here

# Cap
SALARY_CAP_YEAR_ONE = 255_000_000   # inflates ~5% per season
CAP_INFLATION_RATE = 0.05

# Season structure
REGULAR_SEASON_WEEKS = 17
PLAYOFF_TEAMS_PER_CONFERENCE = 7
KEY_PLAYS_PER_GAME = 8              # stored permanently after archive
```

If you find yourself typing a number directly into simulation or business logic code, stop and add it to `constants.py` first.

### Refactor Checkpoints
When a full module is complete (all files in a `src/` subdirectory are written and working), run a refactor pass before moving to the next module:
- Scan for any inlined numbers — move to `constants.py`
- Confirm all DB queries are in the `db/` layer, not in business logic
- Confirm no `player.true_overall` or other true rating fields are exposed outside the engine layer
- Remove any dead code or commented-out blocks

Do not refactor after every individual file — only after a full module is working and tested.

### Layer Boundaries (Strictly Enforced)
| Layer | What it does | What it must NOT do |
|---|---|---|
| `src/db/` | All SQL queries and schema access | Contain business logic or simulation math |
| `src/engine/` | Play resolution, game loop, SAR calculation | Write UI output or call transaction system directly |
| `src/league/` | Roster, standings, schedule logic | Execute raw SQL |
| `src/transactions/` | Trades, FA, contracts, draft | Simulate plays or access engine internals |
| `src/ui/` | Display only | Compute anything; call engine or db directly |
| `src/utils/` | Shared helpers and constants | Import from other `src/` modules (utils is dependency-free) |

### Phase 4 Refactor Exceptions

The following modules have documented exceptions to the "no inline SQL" rule:

**src/league/invariants.py** (28 queries)
- **Rationale**: DB integrity auditor — its purpose is to execute validation queries
- **CLAUDE.md acknowledgment**: "invariants.py is inherently SQL-heavy (DB auditing)"

**src/league/health_report.py** (12 queries)
- **Rationale**: Analytics/diagnostics tool with ad-hoc aggregate queries
- **Pattern**: Similar to invariants.py (reporting, not business logic)

**src/transactions/coaching.py** (10 queries)
- **Rationale**: Single mutation point for coach assignment, maintains Invariants #11-12
- **Pattern**: Tightly-coupled transaction that must execute atomically
- **Alternative**: Extracting queries would scatter invariant maintenance

**src/league/narrative_beats.py** (15 queries)
- **Rationale**: Narrative generation tightly couples slot-filling logic with data retrieval
- **Pattern**: Extracting queries would not improve clarity

**src/league/historical_records.py** (11 queries)
- **Rationale**: Complex analytics with dynamic record book queries
- **Pattern**: Similar to health_report.py (analytics/reporting)

These exceptions are documented and accepted as architecturally sound.

---

## Phase Build Sequence

```
Phase 0  (Weeks 1–3)   Foundation — schema, generation, data layer
Phase 1  (Weeks 4–10)  Simulation Engine — play resolution, narration, injuries
Phase 2  (Weeks 11–14) Full Season — season loop, playoffs, archive, development
Phase 3  (Weeks 15–20) Offseason Loop — FA, contracts, trades, scouting, draft
Phase 4  (Weeks 21–26) Dynasty — 3-season stability, legacy score, media/pressure
```

**The one rule: never build UI for a system that isn't working.**
Run the phase exit criteria before advancing to the next phase.

---

## What Is Explicitly Out of Scope (Do Not Build)

These are deferred to post-launch. Do not implement during the main build:

- Practice squad poaching and full waiver wire priority rules (simplified waiver in MVP)
- Financial system (ticket prices, jersey sales, revenue modeling)
- Multiplayer or online leagues
- 2D/3D match visualization
- Historical replay mode (real NFL seasons)
- Expansion teams or relocation

---

## Updating This File

Update `CLAUDE.md` when:
- A phase is completed (check off items, update "Current Build Phase")
- A significant design decision changes (update the relevant section + the GDD)
- New source files are added (update the project structure map)
- A deferred feature gets promoted to in-scope

The GDD documents in `docs/` are the source of truth for *what* to build. This file is the source of truth for *where things are* and *what's been decided*.
