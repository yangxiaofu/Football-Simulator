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

**Phase 6 — GUI (pywebview + PyInstaller), Milestone 5.11 fully complete.**

- Phases 0–5 are fully shipped. Do not re-implement or revisit systems from those phases unless fixing a confirmed bug.
- Phase 6 design is locked in `docs/ui/` (9 docs). Framework: HTML/CSS/JS + Alpine.js inside pywebview.
- Milestones shipped: 5.1 (Window + Shell), 5.2 (Team Dashboard), 5.3 (Roster + Player Card), 5.5 (Schedule + Game Preview + Game Recap + first DB mutations), 5.6 (Front Office Hub — render-only, mode-aware), 5.7a (FA Market F-41 + FA Player Card F-42 — read-only), 5.7b (generic modal framework + FA modal stack F-43/F-44/F-45 + 3 contract mutations + watchlist). **The Continue button is now enabled.**
- 5.7b live: generic `modal.js` stack (focus-trap, ESC top-only, backdrop, ARIA — reused by P8/P9); `do_sign_free_agent`, `do_cut_player`, `do_restructure_contract`, `do_add_to_watchlist` (synchronous, process-global single-flight lock, no JobManager — ops are O(1)). Save file now writes contracts/cuts/restructures. Cap recalc is satisfied at the `src.transactions.*` business layer (UI wrappers must NOT re-call it). `player.is_watchlisted` column added (ensure_player_watchlist_column migration).
- **5.8 fully shipped (2026-06-21)**: All trade + scouting GUI. Backend: `do_propose_trade`, `do_respond_to_trade`, `do_counter_trade`, `do_add/remove_from_trade_block`, `do_assign_scout`, `do_set_board_rank` (synchronous single-flight). Trade JS: `trade_hub.js` (F-50), `trade_block.js` (F-51), `incoming_trades.js` (F-54), `trade_builder.js` (F-52, debounced `getTradePreview`), `modal_trade_evaluator.js` (F-53), `modal_counter_offer.js` (F-55). Scouting JS: `scouting_hub.js` (F-30), `draft_class.js` (F-31, client-side filter), `prospect_card.js` (F-32, tabbed Overview/Intel), `scout_assignments.js` (F-33, add/remove inline), `draft_board.js` (F-37, ▲▼ optimistic reorder). `board.update_board_rank(shift_siblings=True)` keeps ranks contiguous.
- **5.9 fully shipped (2026-06-21)**: Draft Room (F-60) — backend, JS, and decision modal. Backend (P9a): `src/ui/presenters/draft.py` (`build_draft_room`, `build_available_board`); api.py: `get_draft_room`, `get_available_board`, `do_initialize_draft`, `do_make_pick`, `do_sim_ai_picks`. JS (P9b): `screens/draft_room.js` (three-column: live feed + your board + league status, sim controls with 400ms stagger animation, pre-draft "Initialize" path, draft-complete banner) + `screens/modal_draft_decision.js` (auto-opens on user-on-clock, `closeOnEsc:false` + `backdropDismissable:false`, 5:00 display-only timer, top-3 quick-pick + searchable "Other Player…" panel + auto-pick, live trade offers UI with Accept/Decline disabled in v1). Route `/front-office/draft` registered. FO Hub "Draft Room" CTA fixed (was placeholder). Tests: 119 pass / 1 skipped.
- **5.10a fully shipped (2026-06-21)**: Recap Moments Polish (Pattern D). `recap_narrative.py` expanded to 10 game categories (blowout/big/tight/close × win/loss + overtime_win/overtime_loss), 4 templates each (40 total) + prose blocks for blowout/OT + `build_season_headline`/`build_season_prose` for 4 season result categories. `game_recap.py` adds `narrative_detail` field (blowout/OT only). `game_recap.js` adds score count-up (600ms RAF), hero fade-in, card stagger. `season_review.py` (new) + `season_review.js` (new) — F-10 Season Review screen with W-L count-up hero, 4-card fact grid, leaders, offseason moves, "Begin {year} Season" CTA. FO Hub Season Review CTA wired (was placeholder).
- **5.10b fully shipped (2026-06-21)**: Playoff Bracket (S-08) + Super Bowl Recap (S-11). `src/ui/presenters/playoff.py` (new): `build_playoff_bracket` (seeds via `standings.get_playoff_seeds`, games from `get_all_games_for_week` per round) + `build_super_bowl_recap` (embeds `game_recap.build()` result). `game_recap.py` adds `playoff_round` field (from existing `week_type` in enriched row — WILD CARD ROUND / DIVISIONAL ROUND / CONFERENCE CHAMPIONSHIP / SUPER BOWL). `game_recap.js` adds playoff round badge in hero zone. `playoff_bracket.js` (new) — 4-column CSS grid per conference + SB card, round-in-progress banner, user-team accent. `super_bowl_recap.js` (new) — Pattern D max polish: hero fade-in + score count-up + `championReveal` 400ms animation at 350ms. `screens.css` extended with bracket + SB classes. FO Hub postseason mode adds Playoff Bracket card (`#/playoff/bracket`). Routes: `#/playoff/bracket`, `#/playoff/super-bowl`. Tests: 126 pass / 1 skipped.
- **5.10c fully shipped (2026-06-21)**: Combine Results (F-34), Post-Draft Review (F-62), Past Season Summary (D-04). `combine_results.py` (new presenter): risers/fallers with narratives, position standouts (fastest 40, most bench), attendee count, headline. `post_draft_review.py` (new presenter): used picks from `draft_state`, scouted grades, board rank vs pick comparison (value/reach), class grade A–D. `past_season.py` (new thin wrapper): calls `build_season_review(conn, season_year)` with explicit year + sets `is_history_view=True`. `season_review.py` refactored: accepts optional `season_year` param (default: `current_season - 1`). `queries.get_combine_standouts()` added. FO Hub scouting mode adds "Combine Results" card when combine events exist; camp mode adds "Draft Review" card when picks used > 0. Routes: `#/front-office/combine-results`, `#/front-office/post-draft-review`, `#/history/season/:year` (parameterized). JS: `combine_results.js`, `post_draft_review.js`, `past_season.js`. Deferred (v1.1): Career Retirement Tribute, Hall of Fame Induction. **Tests: 130 pass / 1 skipped.** Milestone 5.10 fully complete.
- **5.11 fully shipped (2026-06-21)**: Dynasty Section (D-01 to D-07, D-04 done in 5.10c). `src/ui/presenters/dynasty.py` (new): `build_dynasty_hub`, `build_franchise_history`, `build_season_archive`, `build_awards_history`, `build_legacy_tracker`, `build_retired_player` — all read-only, no mutations. api.py: 6 new read endpoints (`get_dynasty_hub`, `get_franchise_history`, `get_season_archive`, `get_awards_history`, `get_legacy_tracker`, `get_retired_player`). JS: `dynasty_hub.js` (D-01, summary bar + 4 cards + sub-nav), `franchise_history.js` (D-02, sortable season table), `season_archive.js` (D-03, league champion list), `awards_history.js` (D-05, tab toggle: Season Awards | Career Leaders), `legacy_tracker.js` (D-06, score progression table + badges), `retired_player.js` (D-07, career stats + season log + awards). `shell.js`: 6 new routes + `dynastyPlayerMatch` parameterized route for `#/dynasty/player/:id`. `screens.css`: `.champion-row`, `.missed-row`, `.dynasty-badge`, `.hof-badge`, `.retired-badge`. **Tests: 136 pass / 1 skipped.**
- **5.12 fully shipped (2026-06-21)**: Title Screen, Load Franchise, Settings, Help, Scheme Settings (T-10), PyInstaller packaging spike. `src/ui/settings.py` (new): `load()`, `save()`, `add_recent_save()`, `_saves_dir()` — stdlib-only, atomic writes, platform-aware path. `src/ui/presenters/scheme.py` (new): `build_scheme_settings`, `apply_scheme_update` — validates against `SCHEME_ATTRIBUTE_MAP_*`, `_label()` handles numeric keys (`4_3` → `4-3`). `ensure_scheme_columns` migration adds `scheme_offense`/`scheme_defense` to `team` table (defaults: `pro_style`/`4_3`). api.py: 6 new methods (`get_save_files`, `do_load_franchise`, `get_settings`, `do_save_settings`, `get_scheme_settings`, `do_update_scheme`); `__init__` accepts `save_path=None`; `_get_conn()` raises `ValueError("No franchise loaded")` when no franchise — all callers' try/except handles gracefully. `window.py`: `save_path` is now `nargs='?'` (optional). `index.html`: `#title-screen` + `#app-shell` wrapper; both start `.hidden`; JS toggles on bootstrap. `shell.js`: `DOMContentLoaded` calls `getAppInfo()` — on `ok=false` shows title screen, otherwise shows game shell; `window.onFranchiseLoaded` callback used by load-franchise screen; Scheme sub-nav item activated. JS screens: `load_franchise.js`, `settings_screen.js`, `help_screen.js`, `scheme_settings.js`. `src/ui/__main__.py` (new): PyInstaller entry point. `football_sim.spec` (new): `--onedir` build targeting `FootballSimulator.exe`. **Tests: 140 pass / 1 skipped.** Phase 6 v1 UI scope complete. Deferred to v1.1: T-03 Depth Chart, T-04 Practice Squad, T-07 Cap Overview, T-08 Coaching Staff, D-08 HOF Induction ceremony, Career Retirement Tribute, New Franchise Setup GUI, full Year-10 performance gate.
- Counter-offer full asset editor is NOT implemented — counter modal sends same-structure assets (future polish). Cut `post_june_1` param accepted but not honored (standard release only).
- Tests: `python -m pytest src/ui/presenters/tests/ -v` → **140 pass / 1 skipped**. New in P12: `test_scheme.py` (4 tests covering scheme label formatting, option shape, roundtrip update, invalid input rejection).
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
