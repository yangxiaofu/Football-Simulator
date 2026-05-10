# Phase 4 Build Prompt #3 — AI GM Behavior (Phase Classifier + Decision Matrix + Coaching Carousel)

**Model**: Opus
**Planning mode**: Yes — this is the most complex behavior layer in Phase 4. Lay out the design before writing code, especially the integration points with existing Phase 3 modules.

---

## Context

Phase 4 prompts #1, #2, and #2.5 are complete. The harness passes 10/12 invariants on a fresh save (Inv 5 — no contracts in Phase 0 — is the only real failure; Inv 10 retirement is skipped). Foundation is solid.

This prompt is what makes 32 AI teams behave like 32 distinct personalities evolving across multiple seasons. Without it, every AI team behaves identically forever — the league has no dynamism over the 3 simulated seasons in the harness.

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §6 (entire AI GM Behavior section — §6.1 phase classifier, §6.2 personality × phase decision matrix, §6.3 transition triggers, §6.4 coach hiring/firing)
3. `docs/Phase4_StressTest_BaselineFindings.md` — what the harness has measured so far
4. `src/transactions/trades.py` — particularly `_apply_gm_personality()` around line 681 (key integration point)
5. `src/transactions/free_agency.py` — `gm_personality` reads around line 818–830
6. `src/transactions/draft.py` — `gm_personality` reads around line 489–530
7. `src/transactions/coaching.py` — the `assign_coach_to_team` helper from prompt #1, with displacement logic from #2.5

## Goal

Add four interlocking behavior systems:

1. **Team phase classifier**: every team has a current phase (Rebuild / Bridge / Contend / Win-Now / Decline) computed each offseason from cap health, roster age, recent W%, and star count.
2. **Personality × phase decision matrix**: a 5×5 grid that produces behavior modifiers for each combination, applied at decision points in trades, FA, and draft.
3. **Phase transition triggers**: rules that move teams between phases at season transitions, with personality-specific transition speeds.
4. **AI coaching carousel**: AI coaches get fired and replaced based on simplified performance criteria; new hires get archetypes weighted by the team's situation, propagating new behavior through `assign_coach_to_team`.

**Critical scope discipline**: this prompt does NOT introduce owner sentiment, hot seat UI, fan sentiment, or press conferences. Those are prompts #4–#6. The firing rule here is a simplified placeholder ("W% dropped >0.250 from previous season OR 2 consecutive losing seasons") that prompt #4 will eventually replace with proper owner expectations.

## Tasks

### Task 1 — Schema addition

Add one column to the `team` table in `src/db/schema.sql`:

```sql
ALTER TABLE team ADD COLUMN team_phase TEXT NOT NULL DEFAULT 'bridge';
-- 'rebuild' | 'bridge' | 'contend' | 'win_now' | 'decline'
```

Add a migration helper in `src/db/connection.py` (`ensure_team_phase_column(conn)`) following the pattern of other ALTER-style migrations. Wire it into the connection bootstrap.

Default value `'bridge'` is intentional — it's the most neutral phase, applied to fresh franchises before the first phase classification runs.

### Task 2 — Team phase classifier

Create `src/league/team_phase.py`:

```python
"""Phase 4 — Team phase classifier.

Each AI team is in one of 5 phases that determines its strategic behavior.
Phase is recomputed each offseason after season archive.

Per docs/Phase4_DesignDecisions.md §6.1 and §6.3.
"""
import sqlite3
from src.utils.constants import (
    PHASE_REBUILD, PHASE_BRIDGE, PHASE_CONTEND, PHASE_WIN_NOW, PHASE_DECLINE,
    PHASE_STAR_RATING_THRESHOLD,
    PHASE_AGE_YOUNG, PHASE_AGE_PRIME_LOW, PHASE_AGE_PRIME_HIGH, PHASE_AGE_OLD,
    PHASE_CAP_HEALTHY_THRESHOLD, PHASE_CAP_STRESSED_THRESHOLD,
)


def compute_team_phase(conn: sqlite3.Connection, team_id: int, season_year: int) -> str:
    """Classify a team's current phase based on roster age, cap health,
    star count, and recent W%.

    Decision tree (in order — first match wins):
      1. WIN_NOW if: 3+ stars AND star QB present AND avg roster age >= PHASE_AGE_PRIME_HIGH
                    AND last season was winning AND cap commitment top-quartile
      2. DECLINE if: avg roster age > PHASE_AGE_OLD AND cap_space < PHASE_CAP_STRESSED_THRESHOLD
                    AND last season W% < 0.500
      3. REBUILD if: <2 stars OR avg roster age < PHASE_AGE_YOUNG
                    OR cap_space < PHASE_CAP_STRESSED_THRESHOLD with bottom-quartile talent
      4. CONTEND if: 3+ stars AND avg age in [PHASE_AGE_PRIME_LOW, PHASE_AGE_PRIME_HIGH]
                    AND last season W% >= 0.500 AND cap_space >= PHASE_CAP_HEALTHY_THRESHOLD
      5. BRIDGE: default fallback (neither contending nor rebuilding)

    Returns one of PHASE_* constants.
    """
    ...


def update_all_team_phases(conn: sqlite3.Connection, season_year: int) -> dict:
    """Recompute phase for every team. Returns dict of {team_id: new_phase}.
    Writes the result to team.team_phase. Also returns the BEFORE values for
    transition-trigger evaluation in Task 3.
    """
    ...


def transitions_summary(before: dict, after: dict) -> str:
    """For the League Health Report — formats which teams changed phase this season."""
    ...
```

Implement the helpers — read team data, compute phase per the decision tree, write back to `team.team_phase`. Use existing query patterns from `src/db/queries.py`.

### Task 3 — Personality × phase decision matrix

Create `src/utils/ai_behavior_matrix.py` (data-only module — purely a constants table):

```python
"""Phase 4 — Personality × phase behavior matrix.

5 personalities × 5 phases = 25 behavior signatures. Each signature is a dict
of multipliers/strategies that the trade, FA, and draft decision modules apply
on top of base personality behavior.

Per docs/Phase4_DesignDecisions.md §6.2.

Multiplier semantics:
  fa_aggressiveness:        0.0 = no FA spending; 1.0 = baseline; 2.0 = max splash
  trade_picks_for_vets:     0.0 = never; 1.0 = baseline; 2.0 = aggressive picks-out
  trade_vets_for_picks:     0.0 = never; 1.0 = baseline; 2.0 = aggressive sell-off
  contract_restructure:     0.0 = never; 1.0 = baseline; 2.0 = aggressive
  draft_strategy:           'bpa' (best player available)
                            'need' (positional need)
                            'upside' (high ceiling, more risk)
"""

# Personalities (matches existing team.gm_personality vocabulary)
P_DRAFT_PURIST  = 'draft_purist'
P_WIN_NOW       = 'win_now'
P_ANALYTICS     = 'analytics'
P_LOYALTY       = 'loyalty'
P_OPPORTUNIST   = 'opportunist'

# Phases
PH_REBUILD  = 'rebuild'
PH_BRIDGE   = 'bridge'
PH_CONTEND  = 'contend'
PH_WIN_NOW  = 'win_now'
PH_DECLINE  = 'decline'


# 25-cell matrix. Values are tuned to produce visible behavioral divergence
# across 3-5 simulated seasons. Refine after harness data informs.
BEHAVIOR_MATRIX = {
    # (personality, phase): {behavior signature}

    # === DRAFT PURIST ===
    (P_DRAFT_PURIST, PH_REBUILD): {
        'fa_aggressiveness': 0.3, 'trade_picks_for_vets': 0.0, 'trade_vets_for_picks': 2.0,
        'contract_restructure': 0.2, 'draft_strategy': 'bpa',
    },
    (P_DRAFT_PURIST, PH_BRIDGE): {
        'fa_aggressiveness': 0.6, 'trade_picks_for_vets': 0.0, 'trade_vets_for_picks': 1.5,
        'contract_restructure': 0.5, 'draft_strategy': 'bpa',
    },
    (P_DRAFT_PURIST, PH_CONTEND): {
        'fa_aggressiveness': 0.8, 'trade_picks_for_vets': 0.0, 'trade_vets_for_picks': 1.0,
        'contract_restructure': 0.8, 'draft_strategy': 'bpa',
    },
    (P_DRAFT_PURIST, PH_WIN_NOW): {
        'fa_aggressiveness': 1.0, 'trade_picks_for_vets': 0.2, 'trade_vets_for_picks': 0.5,
        'contract_restructure': 1.0, 'draft_strategy': 'bpa',
    },
    (P_DRAFT_PURIST, PH_DECLINE): {
        'fa_aggressiveness': 0.4, 'trade_picks_for_vets': 0.0, 'trade_vets_for_picks': 2.0,
        'contract_restructure': 0.2, 'draft_strategy': 'bpa',
    },

    # === WIN-NOW SPENDER ===
    (P_WIN_NOW, PH_REBUILD): {
        # Notable: still tries to deny rebuild with one big FA splash
        'fa_aggressiveness': 0.8, 'trade_picks_for_vets': 1.5, 'trade_vets_for_picks': 0.5,
        'contract_restructure': 1.5, 'draft_strategy': 'upside',
    },
    (P_WIN_NOW, PH_BRIDGE): {
        'fa_aggressiveness': 1.2, 'trade_picks_for_vets': 0.5, 'trade_vets_for_picks': 0.5,
        'contract_restructure': 1.5, 'draft_strategy': 'need',
    },
    (P_WIN_NOW, PH_CONTEND): {
        'fa_aggressiveness': 1.6, 'trade_picks_for_vets': 2.0, 'trade_vets_for_picks': 0.3,
        'contract_restructure': 1.8, 'draft_strategy': 'need',
    },
    (P_WIN_NOW, PH_WIN_NOW): {
        # Maximum aggression
        'fa_aggressiveness': 2.0, 'trade_picks_for_vets': 2.5, 'trade_vets_for_picks': 0.0,
        'contract_restructure': 2.0, 'draft_strategy': 'need',
    },
    (P_WIN_NOW, PH_DECLINE): {
        # The death spiral — doubles down rather than rebuild
        'fa_aggressiveness': 0.9, 'trade_picks_for_vets': 0.5, 'trade_vets_for_picks': 0.5,
        'contract_restructure': 1.5, 'draft_strategy': 'upside',
    },

    # === ANALYTICS ===
    (P_ANALYTICS, PH_REBUILD):  {'fa_aggressiveness': 0.5, 'trade_picks_for_vets': 0.3, 'trade_vets_for_picks': 1.5, 'contract_restructure': 0.4, 'draft_strategy': 'bpa'},
    (P_ANALYTICS, PH_BRIDGE):   {'fa_aggressiveness': 0.9, 'trade_picks_for_vets': 0.7, 'trade_vets_for_picks': 1.0, 'contract_restructure': 0.8, 'draft_strategy': 'bpa'},
    (P_ANALYTICS, PH_CONTEND):  {'fa_aggressiveness': 1.2, 'trade_picks_for_vets': 1.0, 'trade_vets_for_picks': 0.8, 'contract_restructure': 1.0, 'draft_strategy': 'bpa'},
    (P_ANALYTICS, PH_WIN_NOW):  {'fa_aggressiveness': 1.5, 'trade_picks_for_vets': 1.2, 'trade_vets_for_picks': 0.5, 'contract_restructure': 1.2, 'draft_strategy': 'bpa'},
    (P_ANALYTICS, PH_DECLINE):  {'fa_aggressiveness': 0.7, 'trade_picks_for_vets': 0.5, 'trade_vets_for_picks': 1.8, 'contract_restructure': 0.5, 'draft_strategy': 'bpa'},

    # === LOYALTY ===
    (P_LOYALTY, PH_REBUILD):    {'fa_aggressiveness': 0.6, 'trade_picks_for_vets': 0.5, 'trade_vets_for_picks': 1.0, 'contract_restructure': 0.6, 'draft_strategy': 'need'},
    (P_LOYALTY, PH_BRIDGE):     {'fa_aggressiveness': 1.0, 'trade_picks_for_vets': 0.8, 'trade_vets_for_picks': 0.8, 'contract_restructure': 0.9, 'draft_strategy': 'need'},
    (P_LOYALTY, PH_CONTEND):    {'fa_aggressiveness': 1.1, 'trade_picks_for_vets': 1.0, 'trade_vets_for_picks': 0.6, 'contract_restructure': 1.0, 'draft_strategy': 'need'},
    (P_LOYALTY, PH_WIN_NOW):    {'fa_aggressiveness': 1.3, 'trade_picks_for_vets': 1.0, 'trade_vets_for_picks': 0.4, 'contract_restructure': 1.2, 'draft_strategy': 'need'},
    (P_LOYALTY, PH_DECLINE):    {'fa_aggressiveness': 0.9, 'trade_picks_for_vets': 0.8, 'trade_vets_for_picks': 1.3, 'contract_restructure': 0.8, 'draft_strategy': 'need'},

    # === OPPORTUNIST ===
    (P_OPPORTUNIST, PH_REBUILD):{'fa_aggressiveness': 0.7, 'trade_picks_for_vets': 0.8, 'trade_vets_for_picks': 1.2, 'contract_restructure': 0.7, 'draft_strategy': 'upside'},
    (P_OPPORTUNIST, PH_BRIDGE): {'fa_aggressiveness': 1.0, 'trade_picks_for_vets': 1.0, 'trade_vets_for_picks': 1.0, 'contract_restructure': 1.0, 'draft_strategy': 'bpa'},
    (P_OPPORTUNIST, PH_CONTEND):{'fa_aggressiveness': 1.2, 'trade_picks_for_vets': 1.2, 'trade_vets_for_picks': 0.8, 'contract_restructure': 1.1, 'draft_strategy': 'bpa'},
    (P_OPPORTUNIST, PH_WIN_NOW):{'fa_aggressiveness': 1.4, 'trade_picks_for_vets': 1.5, 'trade_vets_for_picks': 0.6, 'contract_restructure': 1.3, 'draft_strategy': 'bpa'},
    (P_OPPORTUNIST, PH_DECLINE):{'fa_aggressiveness': 0.8, 'trade_picks_for_vets': 0.8, 'trade_vets_for_picks': 1.5, 'contract_restructure': 0.7, 'draft_strategy': 'upside'},
}


def get_behavior_signature(personality: str, phase: str) -> dict:
    """Return the behavior dict for a (personality, phase) combination.
    Falls back to BEHAVIOR_MATRIX[personality, BRIDGE] if phase is unknown.
    """
    return BEHAVIOR_MATRIX.get((personality, phase), BEHAVIOR_MATRIX[(personality, PH_BRIDGE)])
```

The values above are starting estimates. They're tuned to produce noticeable divergence across 3-5 seasons in stress tests. Refine after harness data shows what's actually happening.

### Task 4 — Phase transition triggers

Add to `src/league/team_phase.py`:

```python
def evaluate_transitions(conn: sqlite3.Connection, season_year: int, before_phases: dict) -> dict:
    """After phase classifier runs, determine which transitions to apply
    based on personality-modulated triggers.

    Returns dict {team_id: (old_phase, new_phase, reason)} for teams that transitioned.

    Triggers (per design doc §6.3):
      Contend → Decline: 2 consecutive losing seasons + roster avg age >28 + cap stressed
      Decline → Rebuild: First losing season after Decline tag + dead cap forecast >20% of cap
      Rebuild → Bridge: Cap recovered + 2+ young stars developed
      Bridge → Contend: 2 consecutive .500+ seasons + 3+ stars
      Contend → Win-Now: Star QB enters contract Year 4-5 of second deal + roster top-quartile

    Personality modifiers on transition speed:
      Draft Purist:    transitions to Rebuild +1 round faster, transitions to Win-Now +1 round slower
      Win-Now Spender: transitions to Win-Now +1 round faster, transitions to Rebuild +1 round slower
                       (this is the death-spiral driver — stays in Decline an extra year)
      Analytics:       no modifier (baseline)
      Loyalty:         transitions to Rebuild +1 round slower (loyal to vets)
      Opportunist:     no modifier; takes whatever transition the math suggests
    """
    ...
```

Note: phase classifier (Task 2) does the *initial* classification from current state. Transition triggers are an additional layer that can OVERRIDE the classifier when a multi-season signal warrants it (e.g., Win-Now Spender stays in Decline despite the classifier suggesting Rebuild).

Implementation: classifier runs first, then `evaluate_transitions` reviews and may overwrite specific phases. The personality modifier delays Win-Now Spender's exit from Decline by one cycle.

### Task 5 — Wire phase awareness into existing decision points

This is the integration work. You're modifying three Phase 3 modules to consult the behavior matrix. Keep changes minimal and localized.

**5a. `src/transactions/trades.py`**

Find `_apply_gm_personality()` around line 681. Add a phase-aware multiplier layer:

```python
def _apply_gm_personality(verdict, gm_personality, offered_assets, requested_assets, ...):
    # Existing personality-only logic stays...

    # NEW: phase-aware modifier
    team_phase = receiving_team.get('team_phase', 'bridge')
    sig = get_behavior_signature(gm_personality, team_phase)

    # If this trade requires sending picks for vets, multiply willingness by sig['trade_picks_for_vets']
    # If this trade requires sending vets for picks, multiply willingness by sig['trade_vets_for_picks']
    # Apply the modifier to the verdict's accept/decline probability
    ...
```

The exact multiplier application depends on how `_apply_gm_personality` currently shapes the verdict. Keep the change small — just one or two multiplier applications in the existing logic.

**5b. `src/transactions/free_agency.py`**

Find the AI signing logic around line 818–830. Add phase-aware FA aggressiveness:

```python
# Existing code reads team['gm_personality']
# NEW: also read team['team_phase'], look up behavior signature
sig = get_behavior_signature(personality, team_phase)
# Multiply the team's FA budget / offer amount by sig['fa_aggressiveness']
```

**5c. `src/transactions/draft.py`**

Find the GM personality logic around line 489–530. Add phase-aware draft strategy:

```python
sig = get_behavior_signature(gm_personality, team_phase)
strategy = sig['draft_strategy']
# Existing logic branches by personality; add a layer that branches by sig['draft_strategy']
# 'bpa' = sort by talent; 'need' = filter by team's position needs; 'upside' = sort by ceiling
```

For each integration point, leave the existing personality-only logic in place as the fallback (in case `team_phase` is missing or unknown). The phase logic is a multiplier/modifier layer on top, not a replacement.

### Task 6 — AI coaching carousel

Create `src/transactions/coaching_carousel.py`:

```python
"""Phase 4 — AI coaching carousel.

Fires AI coaches who underperform expectations and hires replacements.
Runs at the season transition (after archive, before next season's offseason
phases begin).

Per docs/Phase4_DesignDecisions.md §6.4. Uses simplified firing criteria
since full owner sentiment is in prompt #4.
"""
import sqlite3
import random
from src.transactions.coaching import assign_coach_to_team
from src.utils.constants import (
    COACH_FIRING_W_PCT_DROP_THRESHOLD,
    COACH_FIRING_CONSECUTIVE_LOSING_SEASONS,
    COACH_HIRING_ARCHETYPE_WEIGHTS,
)
from src.utils.ai_behavior_matrix import P_DRAFT_PURIST, P_WIN_NOW, P_ANALYTICS, P_LOYALTY, P_OPPORTUNIST


def run_coaching_carousel(conn: sqlite3.Connection, season_year: int) -> dict:
    """For each AI team, decide whether to fire the head coach. If fired,
    immediately hire a replacement with archetype weighted by the team's
    situation.

    Simplified firing criteria (placeholder for owner sentiment in #4):
      - Fire if last season W% dropped by >COACH_FIRING_W_PCT_DROP_THRESHOLD
        (default 0.250) compared to previous season
      - Fire if team has had >=COACH_FIRING_CONSECUTIVE_LOSING_SEASONS losing seasons
        (default 2) in a row
      - Never fire a coach who just won the Super Bowl

    Returns dict {team_id: (fired_coach_name, hired_coach_name, reason)} for
    teams that turned over.
    """
    ...


def _select_replacement_archetype(conn: sqlite3.Connection, team_id: int, season_year: int) -> str:
    """Weighted random selection of archetype for a new AI coach hire.

    Weighting logic (loose heuristics — refine with harness data):
      - If team is currently in REBUILD or DECLINE, weight toward draft_purist + analytics
      - If team is in CONTEND or WIN_NOW, weight toward win_now + opportunist
      - BRIDGE teams use uniform random
      - Loyalty is always represented as a smaller weight

    Returns one of the P_* archetypes from ai_behavior_matrix.
    """
    ...
```

The carousel is called from the offseason loop (Task 7).

### Task 7 — Hook into offseason loop

In `src/league/offseason.py`, add to the season transition flow:

```python
# After season archive, before next offseason phases begin:
from src.league.team_phase import update_all_team_phases, evaluate_transitions
from src.transactions.coaching_carousel import run_coaching_carousel

def transition_to_next_season(conn, season_year):
    # Existing archive logic...

    # NEW Phase 4 work:
    before_phases = {row['id']: row['team_phase'] for row in conn.execute("SELECT id, team_phase FROM team")}
    update_all_team_phases(conn, season_year)
    transitions = evaluate_transitions(conn, season_year, before_phases)
    carousel_changes = run_coaching_carousel(conn, season_year)

    # Optional: log to transaction_log for traceability
    ...
```

Find the right hook — it should run AFTER the season is archived (so we have full season W% data) and BEFORE the next offseason's free agency phase (so AI behavior in FA reflects the new phase).

### Task 8 — Constants

Add to `src/utils/constants.py`:

```python
# Phase 4 — AI behavior phases
PHASE_REBUILD = 'rebuild'
PHASE_BRIDGE = 'bridge'
PHASE_CONTEND = 'contend'
PHASE_WIN_NOW = 'win_now'
PHASE_DECLINE = 'decline'
ALL_PHASES = (PHASE_REBUILD, PHASE_BRIDGE, PHASE_CONTEND, PHASE_WIN_NOW, PHASE_DECLINE)

# Phase classification thresholds
PHASE_STAR_RATING_THRESHOLD = 90
PHASE_AGE_YOUNG = 24
PHASE_AGE_PRIME_LOW = 25
PHASE_AGE_PRIME_HIGH = 28
PHASE_AGE_OLD = 30
PHASE_CAP_HEALTHY_THRESHOLD = 30_000_000
PHASE_CAP_STRESSED_THRESHOLD = 5_000_000
PHASE_DEAD_CAP_REBUILD_TRIGGER_PCT = 0.20  # >20% of cap = forced rebuild

# AI coaching carousel
COACH_FIRING_W_PCT_DROP_THRESHOLD = 0.250
COACH_FIRING_CONSECUTIVE_LOSING_SEASONS = 2
COACH_HIRING_ARCHETYPE_WEIGHTS = {
    # Used by _select_replacement_archetype as base weights
    'rebuild_or_decline': {'draft_purist': 3, 'analytics': 3, 'opportunist': 2, 'loyalty': 1, 'win_now': 1},
    'contend_or_win_now': {'win_now': 3, 'opportunist': 3, 'analytics': 2, 'loyalty': 1, 'draft_purist': 1},
    'bridge':             {'draft_purist': 2, 'win_now': 2, 'analytics': 2, 'loyalty': 2, 'opportunist': 2},
}
```

## Constraints — what NOT to touch

- Do NOT introduce owner sentiment, hot seat, fan sentiment, or any UI for press conferences. (Prompts #4, #5, #6.)
- Do NOT modify the player coach's firing logic. The player is never fired by this prompt — the carousel only runs against AI teams. The player coach is exempt (filter by `is_player=0` in the carousel).
- Do NOT modify the legacy score system (prompt #7) or historical records (prompt #8).
- Do NOT modify `assign_coach_to_team` from prompt #1/#2.5 — the new AI hires call it as-is.
- Do NOT modify the stress harness or invariants.
- Do NOT add a new phase or personality archetype — work within the existing 5×5 grid.
- Do NOT attempt to fix Inv 5 (no contracts) — still deferred.

## Test plan

### Step 1 — Verify additive-only changes don't break the existing harness

```bash
rm -f saves/phase4_v3.db
python generate.py saves/phase4_v3.db --season 2024
python run_stress_test.py saves/phase4_v3.db --invariants --seasons 3
```

Expected: still 10/12 invariants PASS (Inv 5 FAIL, Inv 10 SKIP). No regression. Phase classifier writes phases; coaching carousel runs but does not break anything.

### Step 2 — Verify behavioral signal

Create `verify_phase4_p3.py` in the project root:

```python
"""Verification for Phase 4 Build Prompt #3 — AI GM Behavior."""
import sqlite3
import sys

DB = "saves/phase4_v3.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. team.team_phase column exists and is populated for all teams
phases = conn.execute("SELECT id, team_phase FROM team").fetchall()
assert len(phases) == 32, f"expected 32 teams, got {len(phases)}"
for row in phases:
    assert row['team_phase'] in ('rebuild', 'bridge', 'contend', 'win_now', 'decline'), \
        f"team {row['id']} has invalid phase: {row['team_phase']}"

# 2. After 3-season stress test, expect at least SOME phase diversity
phase_counts = {}
for row in phases:
    phase_counts[row['team_phase']] = phase_counts.get(row['team_phase'], 0) + 1
print(f"Phase distribution: {phase_counts}")
assert len(phase_counts) >= 2, f"expected at least 2 distinct phases, got: {phase_counts}"

# 3. Coaching carousel produced at least 1 coach turnover across 3 seasons
# Look for closed tenures with end_reason='fired' or 'replaced' (not 'current')
turnovers = conn.execute("""
    SELECT COUNT(*) FROM coach_tenure
    WHERE end_year IS NOT NULL AND end_reason IN ('fired', 'replaced')
""").fetchone()[0]
print(f"Coach turnovers across 3 seasons: {turnovers}")
assert turnovers >= 1, f"expected at least 1 coach turnover, got {turnovers}"

# 4. At least 1 team has a different gm_personality than at generation
# (proxy for "AI hired a new coach with a different archetype")
# This requires comparing to a fresh-generation snapshot — skip if not feasible,
# but document in baseline findings.

# 5. Behavior matrix import smoke test
sys.path.insert(0, ".")
from src.utils.ai_behavior_matrix import BEHAVIOR_MATRIX, get_behavior_signature
assert len(BEHAVIOR_MATRIX) == 25, f"expected 25 cells in matrix, got {len(BEHAVIOR_MATRIX)}"
sig = get_behavior_signature('win_now', 'win_now')
assert 'fa_aggressiveness' in sig, "behavior signature missing fa_aggressiveness"
assert sig['fa_aggressiveness'] >= 1.5, "Win-Now × Win-Now should be max aggression"

print("Phase 4 prompt #3 verification passed.")
```

```bash
python verify_phase4_p3.py
```

### Step 3 — Inspect League Health Report for behavioral divergence

Look at the report from Step 1 and verify:
- `Roster turnover %` is non-trivial (likely 15–30% by season 3)
- Champion list shows >1 distinct team across 3 seasons (parity check)
- W% variance is non-zero (some teams clearly better than others)
- AI rebuild cycles count is >0 (at least one team transitioned phase)

If all four signals appear, behavior is working. If everything looks identical to the baseline (no turnover, same phase distribution, no transitions), the integration is too weak — likely the multipliers in the matrix aren't being applied to actual decision logic.

### Step 4 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #3 AI behavior (date)

Phase distribution after 3 seasons: {results from verify script}
Coach turnovers: {count}
Champion uniqueness: {N distinct champions in 3 seasons}
W% variance trajectory: {year 1 vs year 3}

Behavioral signal: PASS / WEAK / NONE
Notes: {any tuning observations — e.g., "Win-Now Spender death spiral too fast"}
```

### Step 5 — Update CLAUDE.md

Append to the Phase 4 checklist:

```
- [x] Save model refactor
- [x] Multi-season stress harness + invariant battery + League Health Report
- [x] Baseline bug fixes (Inv 8, Inv 4, Inv 12 cascade)
- [x] AI GM team-phase classifier + transition rules + coaching carousel
- [ ] Owner sentiment + hot seat + reassignment logic
...
```

Add `src/league/team_phase.py`, `src/utils/ai_behavior_matrix.py`, `src/transactions/coaching_carousel.py` to the project structure map.

## Reference

- `docs/Phase4_DesignDecisions.md` §6 (entire AI GM Behavior section)
- `docs/Phase4_StressTest_BaselineFindings.md` — baseline behavior to compare against
- `docs/Phase4_DesignDecisions.md` §8 item 4 — Win-Now Spender death-spiral must produce *recoverable* teams over 3-5 years, not permanent zombies. Tune the dead-cap timeline and the Decline → Rebuild trigger speed accordingly.
