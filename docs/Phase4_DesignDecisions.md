# Phase 4 Design Decisions — Dynasty

**Status**: Design-locked, ready for Claude Code build prompts
**Date**: 2026-05-09
**Authors**: David (decisions), Claude (synthesis)
**Relationship to GDDs**: Supersedes Phase 4 placeholder content in `docs/GDD_Layer4_FeatureRoadmap.md`. Layer 1–3 GDDs remain authoritative for game vision, simulation, and data model.

---

## 1. Locked Design Anchors

These nine decisions shape every system in Phase 4. Do not change any one of them without revisiting downstream impact across the other eight.

### 1.1 Tonal register — Mixed by context
Dry beat-reporter prose by default; dramatic narration reserved for inflection points (Super Bowl wins, firings, dynasty milestones, HOF inductions). The system decides voice based on event class.

**Implication**: Two narration template libraries — one routine, one dramatic. Routine outnumbers dramatic ~5:1 to keep dramatic earned.

### 1.2 Firing model — Fired → reassign
When the hot seat hits termination, the player's tenure at the current franchise ends. Career continues at a new team. Career legacy stats are portable across franchises.

**Implication**: Save model must support league-as-world rather than franchise-as-world. (See §2.)

### 1.3 Press conference cadence — Weekly during season
~17 routine presser events plus 3–5 event-triggered presser events per regular season. Tier 1 (routine) is autopilot-friendly with 5-second resolution; Tier 2 (event) is the moment the player remembers.

### 1.4 Stability MVP target — 3 hard, 10 soft
Three consecutive seasons must pass all invariant checks for Phase 4 ship. The harness must additionally run a 10-season headless smoke test with crashes / FK violations / infinite loops as the only fail conditions. League realism at year 10 is not a gate.

### 1.5 Cap storage model — Dollars stored, percentage derived
Phase 3 schema already stores dollars — keep it. Add a helper `as_cap_pct(dollars, season_year)` used by AI valuation and FA market normalization. Deal headlines use dollars; AI fairness math uses percentage of current cap. No schema refactor.

### 1.6 Satisfaction persistence — Partial decay across season boundary
Specific grievances (holdout, contract dispute, broken promise) persist at full strength until resolved. General mood states (post-loss frustration, fatigue irritation) decay 50% at season rollover. Rule of thumb: player remembers what was *done to them*; player gets over what *happened on the field*.

### 1.7 Coach identity — Real entity
A `coach_career` row with name (player-customized at game start, default provided), age, personality archetype, career stats, and hire/fire history. The player IS this entity. Required by the firing model.

### 1.8 Firing leash — No unemployment in MVP
Within 2 weeks of firing, the player is offered a new job. Job quality is a function of career legacy at the time of firing:

- Career legacy top quartile → mid/upper-tier job offered
- Career legacy mid range → mid/lower-tier job offered
- Career legacy bottom quartile → bottom-tier job offered (rebuild slog)

A "mutual parting" resignation option is available at owner sentiment 30–50 and earns one tier better.

### 1.9 Phase 4 ship gate — 3 seasons clean
All invariants in §3 pass over 3 simulated seasons. 10-season smoke run completes without crashes. League realism at year 10 may degrade — that is acceptable for MVP.

---

## 2. Save Model Refactor (the architectural elephant)

**Decision**: The .db file represents the LEAGUE world, not a single franchise. Coach identity is portable across franchises and is the persistent layer the player owns; team behavior is driven by whichever coach is currently assigned.

**Why this is unavoidable**: Fired → reassign requires the player's identity to outlive any one franchise. A career spanning 4 teams over 18 seasons cannot live in 4 separate .db files unless we build a synchronization layer — which is more complex than just having one file represent the world.

### 2.1 Audit findings from Phase 0–3 code

- `league.user_team_id` already exists as a NOT NULL pointer to "your team," referenced in 30+ call sites across `legacy.py`, `season.py`, `offseason.py`, `free_agency.py`, `draft.py`. Existing code already knows who you are — it just assumes you never move.
- `team.gm_personality` is the AI behavior driver. It lives on the team, not on any coach entity. There is no head coach entity in the schema today (the `staff` table covers OC/DC/position coaches/scouts only).
- These two facts shape the refactor: we add coach identity without touching the existing personality reads.

### 2.2 Schema additions (all purely additive — no column drops or type changes)

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `coach_career` | One row per coach (player + AI) | `id`, `first_name`, `last_name`, `age`, `personality_archetype`, `career_start_year`, `current_team_id` (nullable), `is_player` (bool), `is_active` (bool) |
| `coach_tenure` | One row per stop in a coach's career | `id`, `coach_id`, `team_id`, `start_year`, `end_year` (nullable while active), `end_reason` (`fired` / `resigned` / `mutual` / `championship_walkout` / `current`) |
| `legacy_score` (modified) | Add nullable `coach_id` column for tenure-aware aggregation in Phase 4 prompt #7 | `coach_id` (nullable FK) |
| `hall_of_fame` (modified) | Add nullable `coach_id` FK alongside existing `player_id` and `staff_id` | `coach_id` (nullable FK) |

### 2.3 What stays unchanged

- `team.gm_personality` — remains the active behavior field. All 30+ existing call sites read it unchanged.
- `league.user_team_id` — remains a NOT NULL pointer. Existing code reads it unchanged.

### 2.4 The personality-follows-coach mechanism

`team.gm_personality` is now treated as the *currently-applied philosophy*, not the team's permanent identity. It gets overwritten whenever a coach is assigned to that team. Mechanism is concentrated in one helper:

```python
def assign_coach_to_team(conn, coach_id, team_id, end_reason_for_previous=None):
    """The single mutation point for coach assignment.
    Closes prior tenure, opens new tenure, syncs derived fields."""
    # 1. If coach has an active tenure, close it with end_year and end_reason
    # 2. Create new coach_tenure row (start_year=current_season, end_reason='current')
    # 3. Update coach_career.current_team_id = team_id
    # 4. Copy coach.personality_archetype → team.gm_personality
    # 5. If coach.is_player, update league.user_team_id = team_id
    # All in a single transaction.
```

This is the **only** code path that mutates `coach_career.current_team_id`, `league.user_team_id`, or `team.gm_personality` going forward. Anywhere else writes to these fields is a bug. Invariants #11 and #12 in §3.2 detect drift if it occurs.

**Initial behavior is identical to Phase 3**: at franchise generation, each coach is created with `personality_archetype` = the team's current `gm_personality`. The first call to `assign_coach_to_team` sets identical values back into the same field. No behavior change on Day 1; behavior diverges only as coaches get fired and replaced over time.

### 2.5 Design implication — instant philosophy snap

When a coach is hired, the team's behavior shifts immediately to the new coach's archetype. A "draft_purist" coach inheriting a "win_now"-built roster will feel constrained for 2–3 seasons before they can execute their philosophy. This is realistic and intended; a slow blend across multiple seasons is a post-launch refinement.

This is the mechanism by which AI coach changes drive real league dynamics over 5–10 seasons rather than each team being locked into its starting personality.

### 2.6 generate.py additions

- Create 32 AI coaches at franchise generation: random first/last names, random ages (35–65), `personality_archetype` matched to assigned team's `gm_personality`, open `coach_tenure` row
- Prompt the player at game start for: coach name (default "Coach Smith"), starting team (existing flow), personality archetype (default "Balanced")
- Player coach has `is_player=1`; assignment flows through `assign_coach_to_team` exactly like AI coaches

### 2.7 Scope and migration

**What this is NOT**: a multiplayer model. The save still represents one player's experience. "League as world" is just a storage shape.

**Migration impact**: Existing Phase 0–3 saves do not migrate to Phase 4. Acceptable — those were development artifacts.

**Build cost**: 1 prompt. Schema migration + `assign_coach_to_team` helper + `generate.py` updates. Zero changes to existing 30+ `gm_personality` call sites or `user_team_id` reads.

---

## 3. Multi-Season Stability

### 3.1 Stress harness design

Entry point: `python run_stress_test.py saves/test.db --seasons N --invariants`

The harness:

1. Generates a fresh franchise (or uses an existing save)
2. Runs N consecutive seasons headlessly — no UI prints, no narration writes, no slow paths
3. After each season-end archive, runs the invariant battery
4. After the final season, prints a one-page League Health Report

A `--smoke` flag runs the harness with crash-only checks and skips the invariant battery, for the 10-season smoke run.

### 3.2 Invariant battery (run after every season)

| # | Invariant | Test |
|---|-----------|------|
| 1 | Career stats = sum of season stats | `SUM(player_season_stats.X) == player_career_stats.X` for all players, all stat columns |
| 2 | No orphan FK references after archive | `play` rows wiped, but `key_play` and `box_score` references intact |
| 3 | Cap discipline | No team has `cap_space < -MAX_CAP_OVERAGE_TOLERANCE` |
| 4 | Roster integrity | Every team has exactly 53 active + ≤16 practice squad players |
| 5 | Contract continuity | Every active player has exactly one active contract |
| 6 | Awards uniqueness | MVP/OPOY/DPOY each exactly one player; no duplicates |
| 7 | Champion uniqueness | Exactly one Super Bowl winner per season |
| 8 | Coach assignment integrity | Every team has exactly one head coach; every active coach is either assigned to one team OR has `current_team_id IS NULL` AND `is_active=true` (between-jobs state) |
| 9 | Age progression | Every returning player is exactly 1 year older than the previous season |
| 10 | Retirement plausibility | At least 8% of league rosters retire each season (NFL norm: ~10–12%) |
| 11 | Player team pointer sync (with vacancy exception) | When the player coach has `current_team_id IS NOT NULL`, `league.user_team_id` equals `(SELECT current_team_id FROM coach_career WHERE is_player=1 AND is_active=1)`. When the player coach has `current_team_id IS NULL` (between jobs), the invariant does not apply — `league.user_team_id` is permitted to point to any prior team. |
| 12 | Coach-team personality sync | For every team with an active coach, `team.gm_personality` equals `coach_career.personality_archetype` for that coach |

### 3.3 League Health Report (printed after harness completes)

One-page output containing:

- Roster turnover %: distinct starters Year N vs. Year 1, league-wide
- Age distribution histogram by position group
- Cap distribution: how many teams in each cap-health bucket
- Talent distribution: average overall by position, year-over-year delta
- Star count: players rated 90+, year-over-year delta
- Champion list across the run
- Competitive balance: variance in W% across the league
- AI rebuild cycles: count of teams that entered Rebuild phase and exited

### 3.4 Failure modes ranked by likelihood

1. **Stat aggregation divergence** (high). Most likely silent bug. Test #1 catches it.
2. **Cap math drift across inflation** (high). Addressed by §1.5 storage decision; AI valuation uses cap pct.
3. **AI cap discipline collapse** (medium-high). Addressed by §6 phase logic.
4. **Roster turnover under-realism** (medium-high). Addressed by retirement tuning + AI behavior. Test #10 detects it.
5. **Draft class quality drift** (medium). Covered by League Health talent histograms.
6. **Satisfaction state ambiguity** (medium). Addressed by §1.6 partial decay.
7. **FK cascade bugs around archive** (medium). Addressed by test #2.

---

## 4. Legacy Score

### 4.1 Existing 6-factor base (preserved)
Championships, conference titles, career W%, stars developed, cap efficiency, simplified media score. All current weights in `src/league/legacy.py` retained.

### 4.2 New additions

**Era difficulty multiplier (×0.85 to ×1.15)**
Computed from league-wide W% variance over the player's tenure. High variance (one team dominates) → lower multiplier (winning is easier). Low variance (true parity) → higher multiplier (winning is harder). Smoothed over 3-season window to avoid year-to-year swings.

**Starting condition multiplier (×0.90 to ×1.20)**
Based on inheriting team's W% in the season prior to player arrival. Inheriting a 2-15 team and winning a Super Bowl in 5 years applies a permanent ~1.18× to that tenure's championship contribution. Locked at the moment of hire; does not retroactively change.

**Tenure stability factor (additive bonus)**
+5 legacy points per consecutive season at the same franchise past Year 5. Caps at +25 at Year 10. Encourages staying and building rather than chasing rings.

**Peer ranking (display only, not part of score itself)**
Computed at end of each season: rank of player career legacy among all active coach careers, plus an all-time rank vs. retired coaches. This is the wall-poster metric.

### 4.3 Legacy storage shape

Two views:

- **Per-tenure legacy**: what the player did at each franchise. Survives even after the player moves on. Stored as snapshot at tenure end.
- **Career legacy**: rolling sum of all tenure legacies plus tenure-stability bonus. The portable metric.

### 4.4 Narrative beat generator

End of each season, the system generates a 2–3 line summary slot-filled from event templates:

> *"Year [N] — [biggest event of season]. [Second biggest event]. [Tonal coda]."*
>
> Example: *"Year 5 — broke the franchise scoring record at 487 points. Fell to the Phantoms in the Conference Championship. The window is open."*

Templates split routine vs. dramatic per §1.1 tone decision. Dramatic templates trigger when championship won, dynasty milestone hit, firing avoided narrowly, or HOF player developed.

### 4.5 Dynasty / HOF narrative
- Dynasty flag (existing): 3+ championships in 10-year window. On flag activation, generate dramatic narrative.
- HOF eligibility (existing): threshold-based. On qualification, generate dramatic narrative.

These are foundational; only the templates need wiring.

---

## 5. Media & Pressure System

### 5.1 Owner sentiment (0–100)

Drivers and tuning weights:

| Driver | Weight | Cadence |
|--------|--------|---------|
| Win/loss vs. preseason expectation | High | Weekly |
| Cap management (cap room, dead cap level) | Medium | Monthly check |
| Star player satisfaction (any holdout / unhappy star) | Medium | Continuous |
| Press conference tone discipline (cumulative) | Low | Weekly |
| Off-field events | Variable | Event-driven |
| Playoff appearance / win | High | Annual |
| Championship | Massive | Annual |

**Preseason expectation** is set by the owner at season start as one of: `rebuild` / `competitive` / `playoff` / `championship`. Failing the tier costs sentiment; exceeding it earns a bonus. This is the primary mechanism by which legacy and current standing decouple.

### 5.2 Hot seat tiers (derived from owner sentiment)

| Sentiment | Tier | UI label | Behavior |
|-----------|------|----------|----------|
| 70–100 | Untouchable | "Owner has expressed full confidence" | No firing risk |
| 40–69 | Stable | "Owner is monitoring progress" | No firing risk |
| 20–39 | Warm seat | "Owner has expressed concerns" | End-of-season firing roll if expectation missed |
| 10–19 | Hot seat | "Owner is publicly questioning your job" | Per-loss firing roll begins |
| 0–9 | Termination zone | "Owner is meeting with replacements" | High per-loss firing chance + guaranteed offseason firing if no playoffs |

### 5.3 Two-tier press conferences

**Tier 1 — routine weekly** (cadence: every regular season week)
- One question, three response choices (deflect / accountable / confrontational)
- Each choice has small effects on owner / fan / locker room sentiment
- "Set my default response" toggle: player can autopilot routine pressers with their preferred default
- Voice: dry, beat-reporter flat
- Resolves in 5 seconds
- Default is *not zero effect* — autopilot must produce a measurable small drift, otherwise it's a free pass

**Tier 2 — event-triggered** (cadence: ~3–5 per season)
- Triggered by: 3+ game losing streak, blown 14+ point lead, star injury, blockbuster trade, playoff loss, contract holdout going public, dynasty milestone
- 2–3 questions, larger response choices
- Effects 3–5× magnitude of Tier 1
- Voice: dramatic
- Cannot be autopilot-skipped; player must interact
- These are the moments the player remembers

### 5.4 Fan sentiment (derived stat)
- Lower stakes than owner sentiment but visible
- Drifts based on: wins, exciting plays, contract dramas, presser tone choices
- Affects: stadium attendance flavor text, FA recruitment bonus/penalty (talent wants to play in fan-supportive cities)
- Not a firing trigger in MVP

### 5.5 MVP scope boundary

**IN scope for Phase 4**:
- Owner sentiment data layer + UI display
- Hot seat meter UI
- Tier 1 weekly presser with autopilot default
- Tier 2 event-triggered presser
- Fan sentiment derived stat
- Firing trigger logic
- Reassignment job offer logic per §1.8

**OUT — deferred to post-launch**:
- Named beat reporters with personalities
- Multi-turn press dialogues
- Social media / X feed
- Sponsor pressure system
- Player media feuds
- Headline generator beyond template fills
- Owner replacement events
- Family / personal life events

---

## 6. AI GM Behavior

### 6.1 Team phase classifier

Every AI team computes a phase each offseason:

| Phase | Heuristic |
|-------|-----------|
| Rebuild | Bottom-quartile cap health OR roster average age <24 OR <2 stars on roster |
| Bridge | Mid roster age, mid cap, 2–3 stars, mediocre recent W% |
| Contend | Top-half cap health, average age 25–28, 3+ stars, recent winning record |
| Win-Now | Star QB on second contract, oldest cohort still productive, top cap commitment, last year of contention window |
| Decline | Cap stressed, roster aging, recent winning record dropping, no QB pipeline |

Phase is a tag the AI uses to make all decisions consistently across FA, draft, trades, and contract management.

### 6.2 Personality × phase decision matrix

Each personality archetype × phase combination produces a behavior profile.

**Draft Purist × Rebuild**: aggressive trade-down, hoard picks, walk all UFAs >30, sign cheap bridge FAs only
**Draft Purist × Contend**: small targeted FA splashes only at need positions, draft BPA, refuse to trade picks for vets
**Draft Purist × Decline**: trade aging vets early for picks, accept rebuild before forced

**Win-Now Spender × Rebuild**: still tries to sign one big FA to deny rebuild, restructures contracts to avoid cap pain, drafts upside over polish
**Win-Now Spender × Contend**: trades 1st-round picks for veteran difference-makers, signs top FAs at every need, restructures aggressively
**Win-Now Spender × Decline**: doubles down rather than rebuild, leads to dead cap reckoning in 1–2 years

Other archetypes (Balanced, Value Hunter, Stability First, Aggressive Trader) get similar matrices following the same pattern.

### 6.3 Phase transition triggers

- **Contend → Decline**: Two consecutive losing seasons + roster avg age >28 + cap stressed
- **Decline → Rebuild**: First losing season after Decline tag + dead cap forecast >20% of cap
- **Rebuild → Bridge**: Cap recovered + 2+ young stars developed
- **Bridge → Contend**: Two consecutive .500+ seasons + 3+ stars
- **Contend → Win-Now**: Star QB enters contract Year 4–5 of second deal + roster top-quartile

Personality affects transition speed and willingness:
- Draft Purist transitions to Rebuild fast and to Win-Now slowly
- Win-Now Spender transitions to Win-Now fast and to Rebuild reluctantly (stays in Decline an extra year, producing the death-spiral arc)

### 6.4 AI coach hiring/firing

AI coaches use the same firing logic as the player (owner sentiment + expectation tier). When fired, a new coach with a random personality archetype is hired immediately at the season transition (no vacancy gap for AI teams).

The new coach's archetype is written into `team.gm_personality` via `assign_coach_to_team` (see §2.4), so all Phase 3 trade/FA/draft logic that reads `gm_personality` automatically picks up the new behavior on the next decision tick. This is the mechanism by which league behavior actually evolves over 5–10 simulated seasons rather than each team being locked into its starting personality.

Personality archetype distribution for new AI hires: weighted toward the team's owner expectation tier set in §5.1 (a `championship`-tier owner is more likely to hire a Win-Now Spender; a `rebuild`-tier owner is more likely to hire a Draft Purist). This keeps owner expectations and hiring behavior coherent.

---

## 7. Build Sequence

Each numbered item = one Claude Code build prompt. Sequence respects dependencies.

| # | Prompt | Dependencies | Risk |
|---|--------|--------------|------|
| 1 | Save model refactor: add `coach_career`, `coach_tenure`, `legacy_score.coach_id`, `hall_of_fame.coach_id`. Add `assign_coach_to_team` helper as single mutation point. Update `generate.py` to create 32 AI coaches + 1 player coach. Zero changes to existing `gm_personality` or `user_team_id` reads. | None | Medium — additive schema, one helper, zero call-site refactor |
| 2 | Headless multi-season stress harness + invariant battery + League Health Report | #1 | Medium — must be honest about failures |
| 3 | AI GM team-phase classifier + personality-phase decision matrix + transition triggers + AI coach firing/hiring | #1, #2 | Medium-high — most complex behavior layer |
| 4 | Owner sentiment data layer + hot seat tier logic + reassignment job offer logic | #1 | Low — pure data |
| 5 | Tier 1 weekly press conference + autopilot default toggle | #4 | Low — UI shell |
| 6 | Tier 2 event-triggered press conference + dramatic narration templates | #4, #5 | Medium — content-heavy |
| 7 | Legacy score expansion: era multiplier, starting-condition multiplier, tenure stability, per-tenure + career storage, peer ranking | #1, #2, #3 | Medium — depends on AI realism for era variance to mean something |
| 8 | Historical records module: league record book, all-time leaders, champion history, narrative beat generator | #1, #7 | Low — read-only aggregation |
| 9 | End-of-season legacy display + dynasty/HOF narrative + season-summary narrative beats | #7, #8 | Low — UI layer |
| 10 | Final 3-season exit-criteria run + 10-season smoke test. Tune any failures. | All above | High — integration |

**Parallelizable**: #4 can start as soon as #1 lands, even before #2 is complete (data-only, no harness dependency). #8 can be built any time after #1 — only reads from existing tables.

**Deferred to post-launch** (do not build in Phase 4):
- Named beat reporter personalities
- Social media feed
- Sponsor / financial pressure
- Multi-turn press dialogues
- Player media feuds
- Owner replacement events
- Family / personal life events
- Coach personality drift over career
- Expansion / relocation

---

## 8. Things to Catch During Build (not blocking)

1. The era difficulty multiplier should NOT swing wildly year-to-year (smoothing window of 3+ seasons).
2. Tier 1 press conferences with autopilot on must produce a measurable but small effect — not zero, or autopilot becomes a free pass.
3. The "mutual parting" resignation option needs UI affordance the player notices. Otherwise no one will use it.
4. AI Win-Now Spender's death spiral (Decline → forced Rebuild with no picks) must produce *recoverable* teams over 3–5 years, not permanent zombies. Tune the dead cap timeline.
5. Fan sentiment effect on FA recruitment should be modest. Otherwise it overrides personality archetype logic.
6. Career legacy must be visible before *and* after a firing. Player should see what they're playing for at all times.
7. The `assign_coach_to_team` helper must be the ONLY code path that writes to `coach_career.current_team_id`, `league.user_team_id`, or `team.gm_personality`. If invariants #11 or #12 ever fail in the harness, grep for direct writes outside this helper.
8. AI coach replacement must happen synchronously at the moment of firing (no vacancy state for AI teams). Otherwise `team.gm_personality` diverges from `coach.personality_archetype` during the gap and invariant #12 fails.
9. Player vacancy state during between-jobs window — locked. During the gap between firing and rehire, the data shape is:
   - `coach_career.current_team_id` for the player → NULL (truthful field)
   - `coach_career.is_active` for the player → 1 (still in the league, just unassigned)
   - `league.user_team_id` → previous team (kept stable so the 30+ existing reads keep working without NULL guards)
   - No open `coach_tenure` row for the player (a new one is created when `assign_coach_to_team` is called on the new offer)
   - UI labels the dashboard as "Last Coached: [team]" during the window
   - Invariant #11 has a documented exception (see §3.2) that suspends the sync check while the player is between jobs

   **Vacancy duration**:
   - End-of-season firings: ~2 weeks of offseason per §1.8, then new offer
   - Mid-season firings: rest of current season (player watches under interim AI coach) + 2 offseason weeks, then new offer

   Both cases use the same data shape; only duration differs.

---

## 9. Phase 4 Exit Criteria

Phase 4 is complete when all of the following pass:

1. `python run_stress_test.py saves/test.db --seasons 3 --invariants` passes all 10 invariants
2. `python run_stress_test.py saves/test.db --seasons 10 --smoke` completes without crashes or FK violations
3. League Health Report after 3 seasons shows: roster turnover ≥20%, retirement count ≥8% per season, ≥4 distinct Super Bowl participants across 3 years, no perma-zombie teams
4. Player can be fired and reassigned to a new team with career legacy intact
5. End-of-season display shows: legacy score, peer rank, narrative beat, hot seat tier, owner expectation for next year
6. At least one Tier 2 press event triggered per simulated season on average
7. Dynasty flag fires correctly when 3 championships in 10 years achieved
8. HOF eligibility narrative fires for at least one player in the 10-season smoke test

---

## 10. Post-Phase-4 Roadmap (preview, not commitments)

Once Phase 4 ships and the dynasty loop is stable, the natural next layer is content depth on top of stable bones:

- Beat reporter personalities + named press corps
- Social media feed mid-week between pressers
- Sponsorship and revenue layer
- Multi-turn press dialogues with branching
- Owner replacement and ownership-era distinctions
- Coach personality drift across career (a young hothead becomes a veteran statesman)
- Expansion teams (33rd / 34th franchises, divisional realignment)
- Historical replay mode

None of these are required for Steam launch. Phase 4 as scoped above is the launch-ready dynasty experience.
