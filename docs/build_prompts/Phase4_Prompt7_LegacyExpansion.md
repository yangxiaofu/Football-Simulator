# Phase 4 Build Prompt #7 — Legacy Score Expansion

**Model**: Sonnet
**Planning mode**: Yes — multi-file data work with a careful additive schema design and several new computed factors.

---

## Context

Phase 4 prompts #1, #2, #2.5, #3, and #4 are complete. The harness passes 12/12 invariants over 3 simulated seasons with realistic AI behavior, sentiment-driven coaching changes, and player firing/reassignment infrastructure. Foundation is solid.

This prompt expands the existing legacy score system (currently 6 mechanical factors in `src/league/legacy.py`) into a meaningful career narrative — adding era difficulty context, starting condition recognition, tenure stability rewards, peer ranking, and end-of-season narrative beats. After this prompt, the player has a north star to play for.

This is the prompt that finally puts the `legacy_score.coach_id` column added in prompt #1 to use, and converts the legacy system from "what the franchise has done while the user was here" into "what this coach has accomplished across their career."

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §4 (entire Legacy Score section — focus on §4.2 new additions, §4.3 storage shape, §4.4 narrative beats, §4.5 dynasty/HOF)
3. `docs/Phase4_DesignDecisions.md` §1.2 (firing model — career legacy MUST be portable across franchises)
4. `src/league/legacy.py` — current 6-factor implementation
5. `src/db/schema.sql` — existing `legacy_score` table (line 718) and `hall_of_fame` table (line 735), both of which gained nullable `coach_id` columns in prompt #1
6. `src/transactions/coach_offers.py` — already reads `legacy_score.total_legacy_score` for quartile classification; this prompt makes that read more meaningful

## Goal

Add five interlocking systems on top of the existing 6-factor legacy:

1. **Era difficulty multiplier** (×0.85 to ×1.15) computed from league-wide W% variance, smoothed over a 3-season window
2. **Starting condition multiplier** (×0.90 to ×1.20) locked at hire moment based on team's prior-season W%
3. **Tenure stability bonus** (additive, +5 per consecutive season past Year 5, caps at +25 at Year 10)
4. **Peer ranking** (display-only metric — rank vs. active coaches and all-time rank vs. retired)
5. **Narrative beat generator** — end-of-season 2–3 line summary, routine voice by default, dramatic voice on inflection points

Plus the existing dynasty flag (3+ championships in 10-year window) and HOF eligibility get wired-up dramatic narrative templates.

**Critical scope discipline**: this prompt does NOT add UI for displaying any of this — that's prompt #9. The data layer and computation must be complete; the polished display layer is separate.

## Tasks

### Task 1 — Schema additions (additive only — no breaking changes)

Add to `src/db/schema.sql`:

```sql
-- Per-coach, per-season legacy snapshot. The new authoritative source
-- for coach legacy data. Keyed by (coach_id, season_year).
CREATE TABLE IF NOT EXISTS coach_legacy_score (
    id                              INTEGER PRIMARY KEY,
    coach_id                        INTEGER NOT NULL,
    season_year                     INTEGER NOT NULL,
    team_id                         INTEGER NOT NULL,

    -- Six base factors (mirror existing legacy.py)
    championships                   INTEGER NOT NULL DEFAULT 0,
    conference_titles               INTEGER NOT NULL DEFAULT 0,
    season_win_pct                  REAL NOT NULL DEFAULT 0,
    stars_developed                 INTEGER NOT NULL DEFAULT 0,
    cap_efficiency_score            INTEGER NOT NULL DEFAULT 50,
    media_legacy_score              INTEGER NOT NULL DEFAULT 50,

    -- New Phase 4 multipliers (applied to this season's contribution)
    era_difficulty_multiplier       REAL NOT NULL DEFAULT 1.0,
    starting_condition_multiplier   REAL NOT NULL DEFAULT 1.0,

    -- Computed: this season's contribution to career legacy
    season_legacy_score             INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(coach_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_coach_legacy_coach ON coach_legacy_score(coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_legacy_season ON coach_legacy_score(season_year);

-- End-of-season narrative beats (one per coach per season)
CREATE TABLE IF NOT EXISTS coach_narrative_beat (
    id              INTEGER PRIMARY KEY,
    coach_id        INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    beat_type       TEXT NOT NULL,        -- 'routine' | 'dramatic' | 'dynasty_milestone' | 'hof_eligible'
    text            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(coach_id, season_year, beat_type)
);

CREATE INDEX IF NOT EXISTS idx_coach_narrative_coach ON coach_narrative_beat(coach_id);

-- Cached peer ranking snapshots (rebuilt each season)
CREATE TABLE IF NOT EXISTS peer_ranking_snapshot (
    id                  INTEGER PRIMARY KEY,
    coach_id            INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    career_legacy_total INTEGER NOT NULL,
    active_rank         INTEGER NOT NULL,         -- rank among active coaches that season
    all_time_rank       INTEGER NOT NULL,         -- rank among all coaches (active + retired)
    n_active            INTEGER NOT NULL,         -- denominator for active rank
    n_all_time          INTEGER NOT NULL,         -- denominator for all-time rank
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(coach_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_peer_ranking_season ON peer_ranking_snapshot(season_year, active_rank);
```

The existing `legacy_score` table is **left in place** for backward compatibility. Code that currently reads `legacy_score.total_legacy_score` (e.g., `coach_offers.py` quartile classification) keeps working. The new authoritative source is `coach_legacy_score`, but the old table continues to be written by the updated `legacy.py` so nothing else breaks.

Add `ensure_coach_legacy_tables(conn)` migration helper in `src/db/connection.py` following the prompt #1/#2.5/#4 pattern. Wire into the bootstrap.

### Task 2 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Legacy expansion" section:

```python
# === Era difficulty multiplier ===
ERA_DIFFICULTY_BASELINE_VARIANCE = 0.16        # NFL typical W% stdev across 32 teams
ERA_DIFFICULTY_VARIANCE_RANGE = 0.05           # ±0.05 produces ±0.15 multiplier
ERA_DIFFICULTY_MIN = 0.85                      # one team dominates → easier to win
ERA_DIFFICULTY_MAX = 1.15                      # true parity → harder to win
ERA_DIFFICULTY_SMOOTHING_WINDOW = 3            # average over last N seasons

# === Starting condition multiplier (locked at hire) ===
# (prior_w_pct upper bound, multiplier)
STARTING_CONDITION_BUCKETS = (
    (0.300, 1.20),    # took over a 5-12 disaster — winning here counts a lot
    (0.450, 1.10),
    (0.550, 1.00),    # baseline — average team
    (0.700, 0.95),
    (1.001, 0.90),    # inherited a 13-4 contender — winning was expected
)

# === Tenure stability bonus ===
TENURE_STABILITY_THRESHOLD_YEARS = 5            # bonus starts after Year 5
TENURE_STABILITY_PER_YEAR = 5                   # +5 per consecutive year past threshold
TENURE_STABILITY_CAP = 25                       # max +25 at Year 10

# === Dynasty / HOF narrative triggers ===
DYNASTY_CHAMPIONSHIPS_REQUIRED = 3              # existing: 3+ in 10-year window
DYNASTY_WINDOW_YEARS = 10                       # existing
HOF_LEGACY_THRESHOLD = 200                      # career_legacy_total >= 200 → HOF eligible
                                                # (placeholder; refine after harness data)

# === Narrative beat triggers ===
NARRATIVE_DRAMATIC_TRIGGERS = (
    'championship_won',
    'dynasty_flag_activated',
    'hof_eligible_first_time',
    'narrow_firing_escape',         # sentiment dropped below 20 then recovered above 40
    'star_player_developed',        # at least one player rose from C+ to A
    'first_playoff_appearance',
    'first_division_title',
)

# Routine templates fall back when no dramatic trigger fires
NARRATIVE_TEMPLATE_COUNT_PER_TRIGGER = 4        # variety per dramatic trigger type
```

### Task 3 — Era difficulty multiplier

Create `src/league/era_context.py`:

```python
"""Phase 4 — Era difficulty multiplier.

Computed from league-wide W% variance. High variance = one team dominates =
easier to win (lower multiplier). Low variance = true parity = harder to win
(higher multiplier).

Smoothed over a 3-season window to avoid year-to-year jitter.

Per docs/Phase4_DesignDecisions.md §4.2 and §8 item 1.
"""
import sqlite3
import statistics
from src.utils.constants import (
    ERA_DIFFICULTY_BASELINE_VARIANCE, ERA_DIFFICULTY_VARIANCE_RANGE,
    ERA_DIFFICULTY_MIN, ERA_DIFFICULTY_MAX, ERA_DIFFICULTY_SMOOTHING_WINDOW,
)


def compute_season_w_pct_variance(conn: sqlite3.Connection, season_year: int) -> float:
    """Return stdev of W% across all 32 teams for the given season.
    Returns ERA_DIFFICULTY_BASELINE_VARIANCE if data is missing (e.g., season
    not yet complete)."""
    ...


def compute_era_difficulty_multiplier(conn: sqlite3.Connection, season_year: int) -> float:
    """Smoothed era difficulty for the given season.

    Logic:
      1. Compute variance for season_year and the 2 prior seasons (where available)
      2. Average the variances
      3. Map: lower-than-baseline variance → higher multiplier (parity = harder)
              higher-than-baseline variance → lower multiplier (dominance = easier)

    Formula (clamped to [ERA_DIFFICULTY_MIN, ERA_DIFFICULTY_MAX]):
      delta = (BASELINE - smoothed_variance) / VARIANCE_RANGE * 0.15
      multiplier = clamp(MIN, MAX, 1.0 + delta)
    """
    ...
```

### Task 4 — Starting condition multiplier

Add to `src/league/legacy.py` (or a new module if it gets too large):

```python
def lookup_starting_condition_multiplier(
    conn: sqlite3.Connection,
    coach_id: int,
    team_id: int,
    hire_season_year: int,
) -> float:
    """Look up the team's W% in the season prior to coach hire and return
    the appropriate multiplier from STARTING_CONDITION_BUCKETS.

    This is locked at hire time — call once when assign_coach_to_team
    creates a new tenure, and store the value (or recompute from
    coach_tenure.start_year on demand).

    For coaches hired in the franchise's first season (no prior data),
    return 1.0 (baseline).
    """
    ...
```

This multiplier is **locked at hire time and does not change** during the tenure. Two implementation options:

- Store it as a column on `coach_tenure` (add `starting_condition_multiplier REAL NOT NULL DEFAULT 1.0`) — most straightforward
- OR look it up dynamically each season from `team_season_record` for `(team_id, hire_season_year - 1)`

Recommended: store on `coach_tenure` (one-line ALTER, locked semantics enforced by storage).

### Task 5 — Tenure stability bonus

Pure computation, no schema changes:

```python
def compute_tenure_stability_bonus(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Compute the additive tenure stability bonus.

    +TENURE_STABILITY_PER_YEAR per consecutive season at the same franchise
    past TENURE_STABILITY_THRESHOLD_YEARS, capped at TENURE_STABILITY_CAP.

    Implementation:
      1. Find the coach's current/most-recent open tenure
      2. Compute years_at_team = season_year - tenure.start_year + 1
      3. If years_at_team <= THRESHOLD: return 0
      4. Else: return min(CAP, PER_YEAR * (years_at_team - THRESHOLD))

    Returns 0 if coach is between jobs or has no tenure.
    """
    ...
```

### Task 6 — Per-coach legacy aggregation

Refactor `src/league/legacy.py` `update_legacy_score()` to:

1. Continue writing to the existing `legacy_score` table (backward compat — `coach_offers.py` reads it)
2. ALSO write to `coach_legacy_score` for the player coach AND every active AI coach
3. Apply era + starting condition multipliers when computing `season_legacy_score` in the new table
4. Recompute the user's career rollup (existing `legacy_score.total_legacy_score`) from `SUM(coach_legacy_score.season_legacy_score) WHERE coach_id = player_coach_id`

```python
def update_coach_legacy_score(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Compute and store one coach's legacy contribution for the given season.
    Returns the season_legacy_score written.

    Steps:
      1. Identify the coach's team this season (from coach_tenure with
         start_year <= season_year AND (end_year IS NULL OR end_year >= season_year))
      2. Compute base 6 factors (championships this season, conf title, win pct,
         stars developed, cap efficiency, media — same logic as existing legacy.py)
      3. Look up era_difficulty_multiplier (from era_context.py)
      4. Look up starting_condition_multiplier (from coach_tenure or computed)
      5. season_legacy_score = (sum of weighted base factors) * era_mult * starting_mult
      6. Write/update coach_legacy_score row for (coach_id, season_year)
      7. Return season_legacy_score

    Coaches between jobs (current_team_id IS NULL) get a row with all
    zeros for that season. They didn't contribute to any team's outcome.
    """
    ...


def update_all_coach_legacy_scores(
    conn: sqlite3.Connection,
    season_year: int,
) -> dict:
    """Run update_coach_legacy_score for every active coach.
    Returns dict {coach_id: season_legacy_score}."""
    ...


def compute_career_legacy_total(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Sum of all season_legacy_score rows for a coach, plus the current
    tenure_stability_bonus.

    Used by peer ranking and HOF eligibility checks.
    """
    ...
```

### Task 7 — Peer ranking snapshot

Create `src/league/peer_ranking.py`:

```python
"""Phase 4 — Peer ranking among coaches.

Computes each coach's career legacy rank vs. (a) active peers and
(b) all-time including retired coaches. Snapshot stored once per season
in peer_ranking_snapshot.

Per docs/Phase4_DesignDecisions.md §4.2 (peer ranking is display-only,
not part of the score itself).
"""
import sqlite3


def update_peer_rankings(conn: sqlite3.Connection, season_year: int) -> dict:
    """For each coach, compute career_legacy_total and rank them.

    Two ranks per coach:
      - active_rank: position among coaches with is_active=1
      - all_time_rank: position among ALL coaches who have ever existed

    Writes a row per coach to peer_ranking_snapshot. Returns dict
    {coach_id: (active_rank, all_time_rank)}.
    """
    ...


def get_player_peer_rank(conn: sqlite3.Connection, season_year: int) -> dict:
    """Convenience: return the latest snapshot for the player coach.
    Returns {'active_rank': int, 'n_active': int, 'all_time_rank': int,
             'n_all_time': int, 'career_legacy_total': int}.
    """
    ...
```

### Task 8 — Narrative beat generator

Create `src/league/narrative_beats.py`:

```python
"""Phase 4 — End-of-season narrative beat generator.

Produces a 2-3 line summary slot-filled from event templates. One beat per
coach per season. Routine voice by default; dramatic voice when an inflection
point fires.

Per docs/Phase4_DesignDecisions.md §4.4 and the Mixed-by-context tone decision
in §1.1.
"""
import sqlite3
import random
from src.utils.constants import (
    NARRATIVE_DRAMATIC_TRIGGERS,
    NARRATIVE_TEMPLATE_COUNT_PER_TRIGGER,
)


# Routine templates — slot-filled with {year}, {biggest_event}, {team_abbr}, {record}
ROUTINE_TEMPLATES = [
    "Year {year} — {team_abbr} finished {record}. {biggest_event}. The work continues.",
    "Year {year} — {record} for {team_abbr}. {biggest_event}.",
    "Year {year} — {biggest_event}. {team_abbr} closed at {record}.",
    "Year {year} — {team_abbr} went {record}. {biggest_event}. Onward.",
    # Add ~8-12 variants for variety
    ...
]

# Dramatic templates per trigger
DRAMATIC_TEMPLATES = {
    'championship_won': [
        "Year {year} — {team_abbr} are champions. {n_titles} title in {coach_name}'s career. {coda}",
        "Year {year} — Lombardi Trophy hoisted in {team_abbr}. The {coach_last_name} era is real.",
        # 4 variants per trigger
        ...
    ],
    'dynasty_flag_activated': [
        "Year {year} — Dynasty. Three championships in {window} years. {team_abbr} owns the league.",
        ...
    ],
    'hof_eligible_first_time': [
        "Year {year} — {coach_name} crossed the threshold. Hall of Fame inductee, when the time comes.",
        ...
    ],
    'narrow_firing_escape': [
        "Year {year} — The hot seat got cold. {biggest_event}. {team_abbr} closed {record}.",
        ...
    ],
    'star_player_developed': [
        "Year {year} — {star_name} broke through. Years of patience, paid off in {team_abbr}.",
        ...
    ],
    'first_playoff_appearance': [
        "Year {year} — First playoff trip. {team_abbr} {record}. The page turns.",
        ...
    ],
    'first_division_title': [
        "Year {year} — Division crown. {team_abbr} {record}. The first of many?",
        ...
    ],
}


def detect_dramatic_triggers(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> list:
    """Inspect the season's outcome for any dramatic triggers.
    Returns a list of trigger names (may be empty)."""
    ...


def identify_biggest_event(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> str:
    """Pick the most narratively significant event of the season for slot-fill.
    Examples: "broke the franchise scoring record at 487 points",
              "fell in the divisional round to PIT",
              "drafted franchise QB Marvin Harrison Jr",
              "extended the playoff drought to 5 seasons"
    """
    ...


def generate_narrative_beat(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> dict:
    """Generate one narrative beat for a coach's season.

    Process:
      1. Detect dramatic triggers
      2. If any dramatic trigger fires, pick a template from DRAMATIC_TEMPLATES
         for the highest-priority trigger
         (priority order: dynasty > championship > hof_eligible >
          star_player > first_division > first_playoff > narrow_firing)
      3. Else use a routine template
      4. Slot-fill with season facts
      5. Write to coach_narrative_beat
      6. Return {'beat_type': ..., 'text': ...}
    """
    ...


def generate_all_narrative_beats(conn: sqlite3.Connection, season_year: int) -> dict:
    """Run for every active coach. Returns dict {coach_id: beat_dict}."""
    ...
```

For routine templates: aim for ~10–12 variants for variety. For dramatic templates: ~4 variants per trigger × 7 triggers = ~28 dramatic templates. The total content footprint is moderate.

### Task 9 — Dynasty / HOF wiring

Existing dynasty flag (`legacy_score.is_dynasty`) and HOF eligibility (`legacy_score.hof_eligible`) work. This task connects them to the narrative system.

In `src/league/legacy.py`, after the season's legacy is updated:

```python
def evaluate_dynasty_and_hof(conn: sqlite3.Connection, coach_id: int, season_year: int) -> list:
    """Check whether the coach has crossed dynasty or HOF thresholds this
    season for the FIRST time. Returns list of trigger names that newly
    activated.

    Dynasty trigger: COUNT(championships) over [season_year - DYNASTY_WINDOW + 1, season_year]
                     >= DYNASTY_CHAMPIONSHIPS_REQUIRED, AND the dynasty flag was
                     NOT previously set
    HOF trigger:     career_legacy_total >= HOF_LEGACY_THRESHOLD AND hof_eligible
                     was NOT previously set
    """
    ...
```

When either trigger fires, the narrative beat generator (Task 8) automatically picks the dramatic template via `detect_dramatic_triggers`.

### Task 10 — Hook into season transition

In `src/league/offseason.py`, add to the season transition flow (after season archive, before phase classifier):

```python
# Existing: archive...

# NEW Phase 4 work:
from src.league.era_context import compute_era_difficulty_multiplier  # (auto-cached if needed)
from src.league.legacy import update_all_coach_legacy_scores, evaluate_dynasty_and_hof
from src.league.peer_ranking import update_peer_rankings
from src.league.narrative_beats import generate_all_narrative_beats

# 1. Update per-coach legacy with era/starting multipliers applied
update_all_coach_legacy_scores(conn, season_year)

# 2. Check dynasty/HOF triggers (and update flags)
for coach_id in active_coach_ids:
    evaluate_dynasty_and_hof(conn, coach_id, season_year)

# 3. Compute peer rankings for the season
update_peer_rankings(conn, season_year)

# 4. Generate narrative beats
generate_all_narrative_beats(conn, season_year)

# Existing: update_all_team_phases, run_coaching_carousel, etc.
```

Order matters: legacy update before dynasty/HOF (which reads it), then peer ranking (reads career totals), then narrative beats (which read all of the above).

## Constraints — what NOT to touch

- Do NOT modify the existing `legacy_score` table schema. Add columns there only if absolutely required (and you've explained why in the plan). The new authoritative source is `coach_legacy_score`; the old table continues to be written by `update_legacy_score` for backward compat.
- Do NOT add UI for displaying legacy, peer rank, or narrative beats. (Prompt #9.)
- Do NOT modify the AI behavior matrix (prompt #3) or owner sentiment (prompt #4).
- Do NOT modify `assign_coach_to_team`. Calling sites (e.g., the offer acceptance flow) should set `coach_tenure.starting_condition_multiplier` AFTER the assignment if they need to lock the value.
- Do NOT add press conference content (prompts #5/#6) or fan sentiment.
- Do NOT modify the stress harness or invariant battery, EXCEPT to verify existing invariants still pass with the new tables in place.

## Test plan

### Step 1 — No regression on existing harness

```bash
rm -f saves/phase4_v7.db
python generate.py saves/phase4_v7.db --season 2024
python run_stress_test.py saves/phase4_v7.db --invariants --seasons 3
```

Expected: 12/12 invariants still pass. New tables populated for all coaches each season.

### Step 2 — Verify per-coach legacy + multipliers + peer ranking

Create `verify_phase4_p7.py`:

```python
"""Verification for Phase 4 Build Prompt #7 — Legacy Score Expansion."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.league.era_context import compute_era_difficulty_multiplier, compute_season_w_pct_variance
from src.league.legacy import compute_career_legacy_total, compute_tenure_stability_bonus
from src.league.peer_ranking import get_player_peer_rank
from src.league.narrative_beats import generate_narrative_beat

DB = "saves/phase4_v7.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. Schema check
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'coach_legacy_score' in tables
assert 'coach_narrative_beat' in tables
assert 'peer_ranking_snapshot' in tables

# 2. Coach legacy populated for every active coach for every completed season
n_seasons_completed = conn.execute(
    "SELECT COUNT(*) FROM season WHERE is_complete=1"
).fetchone()[0]
n_active_coaches = conn.execute(
    "SELECT COUNT(*) FROM coach_career WHERE is_active=1"
).fetchone()[0]
n_legacy_rows = conn.execute("SELECT COUNT(*) FROM coach_legacy_score").fetchone()[0]
expected_min = n_seasons_completed * (n_active_coaches - 5)  # allow for some between-jobs slack
assert n_legacy_rows >= expected_min, \
    f"expected at least {expected_min} legacy rows, got {n_legacy_rows}"

# 3. Era difficulty multiplier in valid range
seasons = [r[0] for r in conn.execute("SELECT year FROM season WHERE is_complete=1")]
for season_year in seasons:
    era_mult = compute_era_difficulty_multiplier(conn, season_year)
    assert 0.85 <= era_mult <= 1.15, \
        f"era multiplier out of range for {season_year}: {era_mult}"

# 4. Starting condition multipliers stored on tenure rows
tenures_with_mult = conn.execute(
    "SELECT COUNT(*) FROM coach_tenure WHERE starting_condition_multiplier IS NOT NULL"
).fetchone()[0]
assert tenures_with_mult > 0, "no tenures have starting_condition_multiplier set"

# 5. Tenure stability bonus = 0 for fresh tenures
player_id = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()[0]
latest_season = max(seasons) if seasons else 2024
bonus = compute_tenure_stability_bonus(conn, player_id, latest_season)
assert bonus == 0, f"player has bonus {bonus} after only 3 seasons; expected 0"

# 6. Peer ranking returns sensible structure
rank = get_player_peer_rank(conn, latest_season)
assert 'active_rank' in rank
assert 'n_active' in rank
assert 1 <= rank['active_rank'] <= rank['n_active']
print(f"Player peer rank: {rank['active_rank']} of {rank['n_active']} active")

# 7. Narrative beats generated for player every season
beats = conn.execute(
    "SELECT season_year, beat_type, text FROM coach_narrative_beat WHERE coach_id=? ORDER BY season_year",
    (player_id,)
).fetchall()
assert len(beats) >= n_seasons_completed - 1, \
    f"expected ~{n_seasons_completed} beats for player, got {len(beats)}"
for beat in beats:
    print(f"  Year {beat['season_year']} ({beat['beat_type']}): {beat['text']}")

# 8. Career total is sum of season scores
career_total = compute_career_legacy_total(conn, player_id, latest_season)
season_sum = conn.execute(
    "SELECT COALESCE(SUM(season_legacy_score), 0) FROM coach_legacy_score WHERE coach_id=?",
    (player_id,)
).fetchone()[0]
expected = season_sum + bonus  # career_total = season_sum + tenure_stability_bonus
assert career_total == expected, \
    f"career total {career_total} != season_sum {season_sum} + bonus {bonus}"

print("Phase 4 prompt #7 verification passed.")
```

```bash
python verify_phase4_p7.py
```

### Step 3 — Spot-check narrative quality

```bash
sqlite3 saves/phase4_v7.db "SELECT coach_career.first_name || ' ' || coach_career.last_name AS coach, season_year, beat_type, text FROM coach_narrative_beat JOIN coach_career ON coach_career.id = coach_narrative_beat.coach_id ORDER BY season_year LIMIT 10;"
```

Read the output. Does the prose sound like a beat reporter (routine) or HBO Hard Knocks (dramatic) per the §1.1 mixed-by-context decision? If the dramatic templates feel flat, note for tuning — they're the highest-leverage content in the prompt.

### Step 4 — Verify legacy quartile classifier still works

`coach_offers.py` from prompt #4 reads `legacy_score.total_legacy_score` for quartile classification. Verify it still returns sensible values:

```bash
sqlite3 saves/phase4_v7.db "SELECT season_year, total_legacy_score FROM legacy_score ORDER BY season_year;"
```

Should show monotonically rising values (career legacy accumulates). If the values are zero or unchanged from before, the backward-compat write path in `update_legacy_score` is broken.

### Step 5 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #7 legacy expansion (date)

Era difficulty multipliers observed: {min, median, max}
Starting condition multipliers distribution: {bucket counts}
Player peer rank trajectory: Year 1 → Year 3
Sample narrative beats:
  Year 1: [text]
  Year 2: [text]
  Year 3: [text]
Dynasty / HOF triggers fired during 3-season run: {count, types}

Tuning notes:
- {anything that feels off — e.g., "era multiplier always near 1.0 because variance smoothing is too aggressive"}
- {dramatic templates needing rewrite}
```

### Step 6 — Update CLAUDE.md

```
- [x] Owner sentiment + hot seat + reassignment logic
- [x] Legacy score expansion (era multiplier, tenure stability, peer rank, narrative beats)
- [ ] Tier 1 weekly press conference + autopilot
...
```

Add `src/league/era_context.py`, `src/league/peer_ranking.py`, `src/league/narrative_beats.py` to the project structure map. Note that `src/league/legacy.py` was extended (not replaced).

## Reference

- `docs/Phase4_DesignDecisions.md` §4 (entire Legacy Score section)
- `docs/Phase4_DesignDecisions.md` §1.1 (Mixed-by-context tone — routine vs. dramatic narration)
- `docs/Phase4_DesignDecisions.md` §1.2 (Fired → reassign — career legacy must be portable)
- `docs/Phase4_DesignDecisions.md` §8 item 1 (era multiplier should NOT swing wildly year-to-year — smoothing window of 3+ seasons)
- `docs/Phase4_StressTest_BaselineFindings.md`
