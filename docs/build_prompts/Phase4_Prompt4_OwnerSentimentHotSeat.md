# Phase 4 Build Prompt #4 — Owner Sentiment + Hot Seat + Player Reassignment

**Model**: Sonnet
**Planning mode**: Yes — multi-file data layer with several integration points; lay out the design before writing code.

---

## Context

Phase 4 prompts #1, #2, #2.5, and #3 are complete. The harness now passes 12/12 invariants on a 3-season run with realistic coaching turnover, three distinct phases, and three different champions. The league behaves like 32 distinct franchises evolving over time.

This prompt introduces the player-facing pressure system. Up to now, the player coach has been invulnerable — there's no firing risk, no consequences for losing, no real stakes. After this prompt, the player can be fired, enter a vacancy state, and be reassigned to a new franchise.

This is also the prompt that REPLACES the simplified firing rule from prompt #3 (`COACH_FIRING_W_PCT_DROP_THRESHOLD` etc.) with proper owner expectations. The carousel becomes sentiment-aware and uniform across player + AI coaches.

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §5 (entire Media & Pressure section — focus on §5.1 sentiment drivers, §5.2 hot seat tiers, but NOT §5.3 press conferences which are #5/#6)
3. `docs/Phase4_DesignDecisions.md` §1.8 (firing leash) and §8 item 9 (vacancy state semantics)
4. `src/transactions/coaching_carousel.py` from prompt #3 — particularly the `COACH_FIRING_*` placeholder constants you'll be replacing
5. `src/transactions/coaching.py` — `assign_coach_to_team` is the single mutation point for all assignment changes (including vacancy and rehire)

## Goal

Add four interlocking systems:

1. **Owner sentiment** (0–100 per team) with seven drivers from §5.1
2. **Preseason expectation tier** set by the owner each season (rebuild / competitive / playoff / championship)
3. **Hot seat tier classification** derived from sentiment, with firing trigger logic per tier
4. **Player coach reassignment**: vacancy state + job offer generation + acceptance flow per §1.8

After this prompt, the existing coaching carousel from #3 becomes sentiment-aware and applies uniformly to AI and player coaches alike. The `is_player` flag only changes what happens AFTER firing (vacancy + offers vs. immediate AI replacement).

**Critical scope discipline**: this prompt does NOT add press conferences (Tier 1 in #5, Tier 2 in #6), fan sentiment, or any rich UI for the hot seat meter. A simple CLI inspection command is fine; the rich display lives in #9.

## Tasks

### Task 1 — Schema additions

Add to `src/db/schema.sql`:

```sql
-- Per-team owner sentiment + preseason expectation
ALTER TABLE team ADD COLUMN owner_sentiment INTEGER NOT NULL DEFAULT 50;        -- 0-100
ALTER TABLE team ADD COLUMN preseason_expectation TEXT NOT NULL DEFAULT 'competitive';
                                                  -- 'rebuild' | 'competitive' | 'playoff' | 'championship'
ALTER TABLE team ADD COLUMN consecutive_warm_seat_seasons INTEGER NOT NULL DEFAULT 0;

-- Discrete sentiment-driving events (audit trail + tunable feedback)
CREATE TABLE IF NOT EXISTS sentiment_event (
    id              INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    week_number     INTEGER,                       -- NULL for offseason events
    driver          TEXT NOT NULL,                 -- 'win_loss' | 'cap' | 'star_satisfaction'
                                                   -- | 'presser' | 'off_field' | 'playoff' | 'championship'
    delta           INTEGER NOT NULL,              -- signed change applied to sentiment
    detail          TEXT,                          -- short narrative line
    created_at      TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_event_team ON sentiment_event(team_id, season_year);

-- Pending job offers for a coach (active during vacancy state)
CREATE TABLE IF NOT EXISTS coach_offer (
    id              INTEGER PRIMARY KEY,
    coach_id        INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    week_extended   INTEGER NOT NULL,              -- which week the offer was made
    week_expires    INTEGER NOT NULL,              -- offer expires after this week
    job_tier        TEXT NOT NULL,                 -- 'upper' | 'mid' | 'lower' | 'bottom'
    status          TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'accepted' | 'declined' | 'expired'
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_coach_offer_coach ON coach_offer(coach_id, status);
```

Add a migration helper `ensure_sentiment_tables(conn)` in `src/db/connection.py` following the prompt #1/#2.5 pattern. Wire it into the connection bootstrap.

### Task 2 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Owner sentiment & hot seat" section:

```python
# === Owner sentiment ===
SENTIMENT_MIN = 0
SENTIMENT_MAX = 100
SENTIMENT_DEFAULT = 50

# Driver weights (typical sentiment delta when the driver fires)
SENTIMENT_DELTA_WIN_VS_EXPECTATION   = +3
SENTIMENT_DELTA_LOSS_VS_EXPECTATION  = -3
SENTIMENT_DELTA_BIG_UPSET_WIN        = +6   # win when expected to lose by 7+
SENTIMENT_DELTA_BAD_UPSET_LOSS       = -6   # lose when expected to win by 7+
SENTIMENT_DELTA_CAP_HEALTHY          = +1   # monthly check, cap_space > $30M
SENTIMENT_DELTA_CAP_OVER             = -3   # monthly check, cap_space < 0
SENTIMENT_DELTA_STAR_HOLDOUT         = -4   # per holdout, applied at start of week
SENTIMENT_DELTA_PLAYOFF_BERTH        = +10
SENTIMENT_DELTA_PLAYOFF_WIN          = +5
SENTIMENT_DELTA_CHAMPIONSHIP         = +25
SENTIMENT_DELTA_PRESSER_PLACEHOLDER  = 0    # filled in by prompts #5/#6

# Preseason expectation: target W% by tier (used for win-vs-expectation evaluation)
EXPECTATION_TIERS = ('rebuild', 'competitive', 'playoff', 'championship')
EXPECTATION_W_PCT_TARGET = {
    'rebuild':      0.300,    # target 5-12; anything above = upside
    'competitive':  0.500,    # target 8-9
    'playoff':      0.625,    # target 10-7
    'championship': 0.750,    # target 13-4
}
# How many wins above/below target trigger the upset deltas
EXPECTATION_UPSET_WIN_MARGIN = 7    # win when projected to lose by 7+ → big upset
EXPECTATION_UPSET_LOSS_MARGIN = 7

# === Hot seat tiers (derived from sentiment) ===
HOT_SEAT_TIER_THRESHOLDS = (
    (70, 'untouchable'),     # 70-100
    (40, 'stable'),          # 40-69
    (20, 'warm_seat'),       # 20-39
    (10, 'hot_seat'),        # 10-19
    (0,  'termination'),     # 0-9
)

# Per-tier firing roll probabilities
FIRING_ROLL_HOT_SEAT_PER_LOSS         = 0.05   # 5% per loss
FIRING_ROLL_TERMINATION_PER_LOSS      = 0.20   # 20% per loss
FIRING_END_OF_SEASON_WARM_SEAT_PROB   = 0.40   # if expectation missed
FIRING_END_OF_SEASON_HOT_SEAT_PROB    = 0.75   # if expectation missed
FIRING_END_OF_SEASON_TERMINATION_PROB = 1.00   # automatic if no playoffs

# Untouchable + Stable: never fire mid-season; rare end-of-season firing
FIRING_END_OF_SEASON_STABLE_PROB      = 0.05   # only if catastrophic miss

# === Player reassignment / job offers (per §1.8) ===
JOB_OFFER_VACANCY_WEEKS = 2                    # offer arrives within 2 weeks
JOB_OFFER_EXPIRES_WEEKS = 4                    # offer is valid for 4 weeks
JOB_OFFERS_PER_LEGACY_QUARTILE = {
    # (n_offers, [allowed_tiers])
    'top':    (3, ['upper', 'upper', 'mid']),       # 3 offers, mostly good
    'mid':    (2, ['mid', 'lower']),                # 2 offers, mid range
    'bottom': (1, ['bottom']),                       # 1 offer, rebuild slog
}
JOB_OFFER_MUTUAL_PARTING_BUMP = 1   # mutual parting earns one tier better

# Tier definitions for job classification
JOB_TIER_THRESHOLDS = {
    # (cap_health_min, recent_w_pct_min) → tier
    'upper':   (20_000_000, 0.500),    # healthy cap + recent winning
    'mid':     (5_000_000, 0.400),
    'lower':   (-10_000_000, 0.300),
    'bottom':  (float('-inf'), float('-inf')),
}

# Career legacy quartile thresholds (uses existing legacy_score.total_legacy_score)
# Will be refined by prompt #7 — these are placeholder ranges
LEGACY_QUARTILE_TOP_THRESHOLD = 75      # career legacy >= 75 → top quartile
LEGACY_QUARTILE_MID_THRESHOLD = 25      # career legacy >= 25 → mid; below = bottom

# Mutual parting available when sentiment is in this range
MUTUAL_PARTING_SENTIMENT_RANGE = (30, 50)
```

### Task 3 — Owner sentiment module

Create `src/transactions/owner_sentiment.py`:

```python
"""Phase 4 — Owner sentiment system.

Tracks per-team owner sentiment (0-100) driven by seven event categories.
Per docs/Phase4_DesignDecisions.md §5.1.

This module is the SINGLE mutation point for team.owner_sentiment.
Anywhere else writes the column is a bug.
"""
import sqlite3
from src.utils.constants import (
    SENTIMENT_MIN, SENTIMENT_MAX,
    SENTIMENT_DELTA_WIN_VS_EXPECTATION, SENTIMENT_DELTA_LOSS_VS_EXPECTATION,
    SENTIMENT_DELTA_BIG_UPSET_WIN, SENTIMENT_DELTA_BAD_UPSET_LOSS,
    SENTIMENT_DELTA_CAP_HEALTHY, SENTIMENT_DELTA_CAP_OVER,
    SENTIMENT_DELTA_STAR_HOLDOUT,
    SENTIMENT_DELTA_PLAYOFF_BERTH, SENTIMENT_DELTA_PLAYOFF_WIN, SENTIMENT_DELTA_CHAMPIONSHIP,
    HOT_SEAT_TIER_THRESHOLDS,
    EXPECTATION_W_PCT_TARGET, EXPECTATION_UPSET_WIN_MARGIN, EXPECTATION_UPSET_LOSS_MARGIN,
)


def update_sentiment(
    conn: sqlite3.Connection,
    team_id: int,
    driver: str,
    delta: int,
    season_year: int,
    week_number: int = None,
    detail: str = None,
) -> int:
    """Apply a sentiment delta to a team. Clamps to [SENTIMENT_MIN, SENTIMENT_MAX].
    Records the event in sentiment_event.

    Returns the new sentiment value.
    """
    ...


def compute_hot_seat_tier(sentiment: int) -> str:
    """Map a sentiment value to a hot seat tier name."""
    for threshold, tier in HOT_SEAT_TIER_THRESHOLDS:
        if sentiment >= threshold:
            return tier
    return 'termination'


def evaluate_game_sentiment(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
    won: bool,
    expected_to_win: bool,
    point_differential: int,
) -> int:
    """Apply sentiment delta after a game completes.

    Logic:
      - Win when expected to win → small positive (default expectation met)
      - Win when expected to lose by 7+ → big upset positive
      - Loss when expected to lose → small negative
      - Loss when expected to win by 7+ → bad upset negative
      - All other cases: baseline win/loss delta

    Returns the new sentiment.
    """
    ...


def evaluate_weekly_sentiment_drivers(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> None:
    """Run continuous sentiment drivers each week:
      - Star satisfaction: count active holdouts, apply STAR_HOLDOUT delta per
      - Cap health (monthly check, every 4 weeks): apply CAP_HEALTHY or CAP_OVER
      - Press conference placeholder (delta = 0; filled in by prompts #5/#6)
    """
    ...


def evaluate_season_end_sentiment(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    made_playoffs: bool,
    playoff_wins: int,
    won_championship: bool,
) -> int:
    """Apply end-of-season sentiment events.
    Returns new sentiment.
    """
    ...
```

Implement each function per the contract. Use the existing query patterns from `src/db/queries.py`.

### Task 4 — Preseason expectation setter

Create `src/transactions/expectations.py` (or add to `owner_sentiment.py`):

```python
def set_preseason_expectation(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
) -> str:
    """Determine the owner's expectation tier for the upcoming season.

    Heuristic (loose — refine with harness data):
      - Compute previous season W% (or 0.500 if no prior data)
      - Compute team_phase from team_phase column (set by prompt #3 carousel)

      Mapping:
        team_phase=rebuild   → expectation 'rebuild' (regardless of prior W%)
        team_phase=bridge    → expectation 'competitive'
        team_phase=contend   → expectation 'playoff' (or 'championship' if last year was playoff)
        team_phase=win_now   → expectation 'championship'
        team_phase=decline   → expectation 'competitive' (owner won't accept rebuild yet)

    Writes to team.preseason_expectation. Returns the chosen tier.
    """
    ...
```

Hook this into the offseason loop's start-of-offseason phase.

### Task 5 — Replace the placeholder firing rule in coaching_carousel

In `src/transactions/coaching_carousel.py` from prompt #3, replace the simplified firing logic with sentiment-aware logic.

```python
# Remove or deprecate:
#   COACH_FIRING_W_PCT_DROP_THRESHOLD
#   COACH_FIRING_CONSECUTIVE_LOSING_SEASONS
# (Or keep them as fallbacks for any team that has no sentiment data — but in
#  practice every team will have sentiment after this prompt.)

def evaluate_firing_decision(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    mid_season: bool = False,
    week_number: int = None,
    just_lost: bool = False,
) -> tuple[bool, str]:
    """Sentiment-aware firing decision for ANY coach (player or AI).

    Returns (should_fire, reason).

    Logic:
      tier = compute_hot_seat_tier(team.owner_sentiment)

      Mid-season:
        if just_lost AND tier == 'hot_seat': roll FIRING_ROLL_HOT_SEAT_PER_LOSS
        if just_lost AND tier == 'termination': roll FIRING_ROLL_TERMINATION_PER_LOSS
        else: do not fire mid-season

      End of season:
        Compute "expectation met" from team's W% vs EXPECTATION_W_PCT_TARGET[expectation]
        if tier == 'untouchable': never
        if tier == 'stable' AND expectation missed by .150+: roll FIRING_END_OF_SEASON_STABLE_PROB
        if tier == 'warm_seat' AND expectation missed: roll FIRING_END_OF_SEASON_WARM_SEAT_PROB
        if tier == 'hot_seat' AND expectation missed: roll FIRING_END_OF_SEASON_HOT_SEAT_PROB
        if tier == 'termination' AND no playoffs: 100% fire

    Reason string is human-readable: "missed playoff expectation" / "termination zone" / etc.
    """
    ...
```

In the carousel's main loop, REMOVE the `is_player=0` filter — fire AI and player coaches uniformly. The next layer (Task 6) handles the player-specific post-firing flow.

### Task 6 — Coach offer system + reassignment

Create `src/transactions/coach_offers.py`:

```python
"""Phase 4 — Job offer generation and player coach reassignment.

When the player coach is fired, they enter vacancy state. Within
JOB_OFFER_VACANCY_WEEKS, one or more offers are generated based on
their career legacy quartile.

Per docs/Phase4_DesignDecisions.md §1.8 and §8 item 9 (vacancy state).
"""
import sqlite3
from src.transactions.coaching import assign_coach_to_team
from src.utils.constants import (
    JOB_OFFER_VACANCY_WEEKS, JOB_OFFER_EXPIRES_WEEKS,
    JOB_OFFERS_PER_LEGACY_QUARTILE, JOB_OFFER_MUTUAL_PARTING_BUMP,
    JOB_TIER_THRESHOLDS,
    LEGACY_QUARTILE_TOP_THRESHOLD, LEGACY_QUARTILE_MID_THRESHOLD,
)


def determine_legacy_quartile(conn: sqlite3.Connection, coach_id: int) -> str:
    """Look up coach's career legacy from legacy_score.
    Returns 'top' / 'mid' / 'bottom'."""
    ...


def classify_team_job_tier(conn: sqlite3.Connection, team_id: int, season_year: int) -> str:
    """Classify a team's vacancy as 'upper'/'mid'/'lower'/'bottom' based on
    cap health + recent W%. Used to filter offers."""
    ...


def generate_job_offers(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
    week_number: int,
    mutual_parting: bool = False,
) -> list:
    """Generate 1-3 job offers for a coach in vacancy state.

    Process:
      1. Look up coach's legacy quartile
      2. Look at JOB_OFFERS_PER_LEGACY_QUARTILE for n_offers + allowed_tiers
      3. If mutual_parting=True, bump each tier by JOB_OFFER_MUTUAL_PARTING_BUMP
      4. Find AI teams with vacant head coach positions (or teams whose
         coach the carousel will fire at this transition) matching the
         allowed tiers
      5. For each match, insert into coach_offer with week_expires =
         week_number + JOB_OFFER_EXPIRES_WEEKS

    Returns list of created offer dicts.

    Edge case: if not enough vacant teams exist at the right tier, the
    carousel should be invoked to create vacancies (fire some AI coaches
    on bottom-tier teams to make room). For MVP, if there's a true
    shortage, fall back to offering whatever's available — never leave
    the player without at least one offer.
    """
    ...


def accept_job_offer(
    conn: sqlite3.Connection,
    coach_id: int,
    offer_id: int,
    season_year: int,
) -> None:
    """Accept a pending offer. Marks the offer as accepted, marks all other
    pending offers for this coach as declined, and calls assign_coach_to_team
    to move the coach to the new team.
    """
    ...


def auto_accept_best_offer(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> int:
    """Headless helper for the harness. Picks the highest-tier pending offer
    (preference order: upper > mid > lower > bottom) and accepts it.
    Returns the team_id the coach was assigned to.
    """
    ...
```

### Task 7 — Hook into season + offseason loops

**7a. `src/league/season.py`** — after each game completes:

```python
# Existing: game completes, stats written...

# NEW Phase 4 sentiment work:
from src.transactions.owner_sentiment import evaluate_game_sentiment
from src.transactions.coaching_carousel import evaluate_firing_decision

home_won = ...  # from game result
expected_winner = ...  # use cap-weighted prior or just team.preseason_expectation tier comparison

evaluate_game_sentiment(conn, home_team_id, season_year, week, home_won,
                        expected_to_win=(expected_winner == home_team_id),
                        point_differential=...)
evaluate_game_sentiment(conn, away_team_id, season_year, week, not home_won,
                        expected_to_win=(expected_winner == away_team_id),
                        point_differential=...)

# Mid-season firing rolls (only for losing teams)
for losing_team_id in [home_team_id if not home_won else away_team_id]:
    should_fire, reason = evaluate_firing_decision(
        conn, losing_team_id, season_year, mid_season=True,
        week_number=week, just_lost=True
    )
    if should_fire:
        # Trigger immediate firing — uses existing carousel infrastructure
        # For player coach: also calls generate_job_offers
        ...
```

Also call `evaluate_weekly_sentiment_drivers` once per team at the start of each week.

**7b. `src/league/offseason.py`**:

At the start of offseason (right after `update_all_team_phases` and BEFORE `run_coaching_carousel`):

```python
from src.transactions.expectations import set_preseason_expectation
from src.transactions.owner_sentiment import evaluate_season_end_sentiment

# 1. End-of-season sentiment events (playoffs, championship)
for team_id in all_team_ids:
    evaluate_season_end_sentiment(conn, team_id, season_year - 1,
                                   made_playoffs=..., playoff_wins=..., won_championship=...)

# 2. Set new preseason expectations
for team_id in all_team_ids:
    set_preseason_expectation(conn, team_id, season_year)

# Existing: update_all_team_phases, run_coaching_carousel (now sentiment-aware)
```

After the carousel runs, if the player coach was fired, the carousel should call `generate_job_offers` and the offseason loop should call `auto_accept_best_offer` to advance past the vacancy (in headless mode). In future interactive UI, the player picks from the offers manually.

### Task 8 — Stress harness compatibility

In `src/league/stress_harness.py` (from prompt #2): the harness must NOT hang when the player coach enters vacancy. Add a default behavior:

```python
# After offseason runs, check if player is in vacancy
player_state = conn.execute(
    "SELECT id, current_team_id FROM coach_career WHERE is_player=1"
).fetchone()
if player_state and player_state['current_team_id'] is None:
    # Auto-accept best offer to keep the harness moving
    from src.transactions.coach_offers import auto_accept_best_offer
    auto_accept_best_offer(conn, player_state['id'], season_year)
```

### Task 9 — Inspection CLI

Add a small inspection command — either a new flag on `run_offseason.py` or a new file `inspect_hot_seat.py`:

```bash
python inspect_hot_seat.py saves/test.db
```

Output (plain text, no rich UI):

```
HOT SEAT REPORT — Season 2026

Your team: BAL (last coached: BAL since 2024)
Owner sentiment: 42 / 100 — Stable
Preseason expectation: PLAYOFF (8-9 W% target: .500)
Current record: 6-7
Recent sentiment events:
  Week 12: -3 loss to PIT (expected to win)
  Week 11: +6 upset win over KC (big upset)
  Week 10: -3 loss to CIN
  ...
```

Keep it minimal — this is a development tool, not the player UI. The rich version lives in #9.

## Constraints — what NOT to touch

- Do NOT add press conferences, dialogue choices, or fan sentiment. (Prompts #5/#6 add Tier 1/2 pressers; fan sentiment can come in #5 or stay deferred.)
- Do NOT modify the legacy score logic or table structure. (Prompt #7.) You only READ `legacy_score.total_legacy_score` for quartile classification.
- Do NOT modify the AI behavior matrix (`src/utils/ai_behavior_matrix.py`).
- Do NOT modify `assign_coach_to_team` from prompt #1/#2.5 — the offer acceptance flow calls it as-is.
- Do NOT add UI beyond the inspection CLI tool. The hot seat meter visual lives in #9.
- Do NOT remove the `team_phase` column or its usage from prompt #3. Phase classification still drives AI behavior; sentiment is a separate concern.

## Test plan

### Step 1 — No regression on existing harness

```bash
rm -f saves/phase4_v4.db
python generate.py saves/phase4_v4.db --season 2024
python run_stress_test.py saves/phase4_v4.db --invariants --seasons 3
```

Expected: still 12/12 invariants pass. Coach turnover count may differ from prompt #3 baseline (sentiment-driven firing is more nuanced than the placeholder rule), but should remain non-zero. No crashes. The harness must handle player vacancy gracefully if the player gets fired during the run.

### Step 2 — Verify sentiment + firing + offer mechanics

Create `verify_phase4_p4.py`:

```python
"""Verification for Phase 4 Build Prompt #4 — Owner Sentiment + Hot Seat."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.transactions.owner_sentiment import (
    update_sentiment, compute_hot_seat_tier, evaluate_game_sentiment,
)
from src.transactions.coach_offers import generate_job_offers, auto_accept_best_offer
from src.transactions.coaching_carousel import evaluate_firing_decision
from src.transactions.coaching import assign_coach_to_team

DB = "saves/phase4_v4.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# 1. Schema check
cols = {r['name'] for r in conn.execute("PRAGMA table_info(team)")}
assert 'owner_sentiment' in cols
assert 'preseason_expectation' in cols
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'sentiment_event' in tables
assert 'coach_offer' in tables

# 2. All teams initialized to default sentiment
default_count = conn.execute("SELECT COUNT(*) FROM team WHERE owner_sentiment=50").fetchone()[0]
assert default_count == 32, f"expected 32 teams at default sentiment, got {default_count}"

# 3. Hot seat tier boundary check
assert compute_hot_seat_tier(75) == 'untouchable'
assert compute_hot_seat_tier(50) == 'stable'
assert compute_hot_seat_tier(25) == 'warm_seat'
assert compute_hot_seat_tier(15) == 'hot_seat'
assert compute_hot_seat_tier(5) == 'termination'

# 4. Sentiment update writes to both team and event log
team_id = 1
new_sentiment = update_sentiment(conn, team_id, 'win_loss', -10, 2024, week_number=5,
                                 detail="test event")
assert new_sentiment == 40
events = conn.execute("SELECT * FROM sentiment_event WHERE team_id=?", (team_id,)).fetchall()
assert len(events) >= 1
assert events[-1]['driver'] == 'win_loss'
assert events[-1]['delta'] == -10

# 5. Sentiment is clamped
update_sentiment(conn, team_id, 'win_loss', -100, 2024, week_number=6)
clamped = conn.execute("SELECT owner_sentiment FROM team WHERE id=?", (team_id,)).fetchone()[0]
assert clamped == 0, f"expected sentiment clamped to 0, got {clamped}"

# 6. Firing decision returns False when sentiment is high
update_sentiment(conn, team_id, 'championship', +100, 2024)  # back to high
should_fire, _ = evaluate_firing_decision(conn, team_id, 2024, mid_season=True, just_lost=True)
assert not should_fire, "should not fire untouchable coach mid-season"

# 7. Firing decision returns True when sentiment hits termination + no playoffs
update_sentiment(conn, team_id, 'win_loss', -100, 2024)  # back to 0
# Force end-of-season scenario with no playoffs
should_fire, reason = evaluate_firing_decision(conn, team_id, 2024, mid_season=False)
# Note: end-of-season firing also depends on actual playoff/expectation data;
# this is a smoke test — exact behavior depends on what data is in the save.
# At minimum, the function should not crash.
print(f"end-of-season firing decision: should_fire={should_fire}, reason={reason}")

# 8. Player vacancy + offer flow
player_coach_id = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()[0]
old_team_id = conn.execute("SELECT current_team_id FROM coach_career WHERE id=?",
                           (player_coach_id,)).fetchone()[0]

# Force vacancy
assign_coach_to_team(conn, player_coach_id, None, 2024, end_reason_for_previous='fired')

# Verify vacancy state
state = conn.execute("SELECT current_team_id FROM coach_career WHERE id=?",
                     (player_coach_id,)).fetchone()
assert state['current_team_id'] is None
# Per §8 item 9: league.user_team_id stays at previous team
league_team = conn.execute("SELECT user_team_id FROM league WHERE id=1").fetchone()[0]
assert league_team == old_team_id, "league.user_team_id should stay at previous team during vacancy"

# Generate offers
offers = generate_job_offers(conn, player_coach_id, 2024, week_number=20)
assert len(offers) >= 1, f"expected at least 1 offer, got {len(offers)}"

# Auto-accept best
new_team_id = auto_accept_best_offer(conn, player_coach_id, 2024)
assert new_team_id is not None

# Verify reassignment took effect
state_after = conn.execute(
    "SELECT current_team_id FROM coach_career WHERE id=?", (player_coach_id,)
).fetchone()['current_team_id']
assert state_after == new_team_id

league_after = conn.execute("SELECT user_team_id FROM league WHERE id=1").fetchone()[0]
assert league_after == new_team_id, "league.user_team_id should update after reassignment"

print("Phase 4 prompt #4 verification passed.")
```

```bash
python verify_phase4_p4.py
```

### Step 3 — Inspection CLI smoke test

```bash
python inspect_hot_seat.py saves/phase4_v4.db
```

Expected: prints a hot seat report for the player's current team with sentiment value, tier, recent events.

### Step 4 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #4 owner sentiment + hot seat (date)

Player firings during 3-season harness run: {N}
Average sentiment trajectory: {summary}
Sentiment tier distribution at season end: {counts per tier}
Job offer generation: {success / failure rate}

Notes:
- Tier balance: {are the firing rolls producing sensible turnover?}
- Player reassignment: {any cases where offer generation failed?}
```

### Step 5 — Update CLAUDE.md

```
- [x] AI GM team-phase classifier + transition rules + coaching carousel
- [x] Owner sentiment + hot seat + reassignment logic
- [ ] Tier 1 weekly press conference + autopilot
...
```

Add `src/transactions/owner_sentiment.py`, `src/transactions/expectations.py` (if separate), `src/transactions/coach_offers.py`, `inspect_hot_seat.py` to the project structure map.

## Reference

- `docs/Phase4_DesignDecisions.md` §5.1 (sentiment drivers), §5.2 (hot seat tiers), §1.8 (firing leash), §8 item 9 (vacancy state)
- `docs/Phase4_DesignDecisions.md` §3.2 invariant #11 — vacancy state has the documented exception (player.current_team_id IS NULL → invariant suspended)
- `docs/Phase4_StressTest_BaselineFindings.md`
