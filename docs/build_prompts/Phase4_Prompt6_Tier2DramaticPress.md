# Phase 4 Build Prompt #6 — Tier 2 Event-Triggered Dramatic Press Conferences

**Model**: Opus
**Planning mode**: Yes — this is the most narrative-heavy prompt in Phase 4. Lay out the trigger detection design and the template voice direction before writing any content.

---

## Context

Phase 4 prompts #1, #2, #2.5, #3, #4, #7, #8, and #5 are complete. The harness passes 12/12 invariants over 3 simulated seasons with realistic AI behavior, sentiment-driven coaching changes, legacy expansion, narrative beats, historical records, and weekly Tier 1 press conferences.

This is the most narrative-sensitive prompt in Phase 4. Tier 1 established the dry, routine voice — beat-reporter flat, ±1 to ±2 effects, autopilot-friendly. Tier 2 is the **counterpoint**: dramatic, event-triggered, ±3 to ±5 effects per question (×2-3 questions = ±15 per event), cannot be autopilot-skipped. These are the moments the player remembers.

The template voice is the entire deliverable here. Sonnet tends to produce flat dramatic prose ("This is a tough loss. We need to bounce back."). Opus can produce content with edge and specificity ("Five years of work walked off the field with that interception."). The contrast between Tier 1 and Tier 2 is what makes the dynasty experience feel layered. If Tier 2 templates read flat, the entire prompt fails its purpose even if the mechanics work perfectly.

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §1.1 (Mixed-by-context tone — Tier 2 is the dramatic register), §1.3 (cadence), §5.3 (two-tier press conferences — Tier 2 spec), §5.5 (MVP scope boundary)
3. `src/transactions/press_conference.py` from prompt #5 — Tier 1 reference implementation, including the `update_sentiment(driver='presser', ...)` integration point
4. `src/utils/press_templates.py` from prompt #5 — Tier 1 voice reference. Tier 2 must read MEASURABLY DIFFERENT from this. Read 5+ Tier 1 templates before writing a single Tier 2 template.
5. `src/league/owner_sentiment.py` from prompt #4 — sentiment is updated via the same `update_sentiment` helper
6. `src/league/legacy.py` from prompt #7 — dynasty flag activation is one of the trigger conditions; this prompt detects when the flag was newly set this season

## Goal

Add the Tier 2 event-triggered dramatic press conference system:

1. **Trigger detection** that scans for inflection-point conditions after each week and after key events (game completes, trade executes, injury logged, dynasty flag activated)
2. **Multi-question event flow** (2-3 questions per event vs. Tier 1's single question), with cumulative effects across the question sequence
3. **Dramatic template library** — ~3 templates per trigger × 8 triggers = ~24 dramatic templates with the specific voice direction below
4. **Cannot-skip mechanism** — Tier 2 events bypass the autopilot setting from #5 and require player interaction
5. **Tier 2 supersedes Tier 1** in the same week — if a Tier 2 trigger fires, no routine Tier 1 event is generated that week
6. **Headless harness compatibility** — auto-resolves to a fixed default ('accountable') in stress runs

**Critical scope discipline**: this prompt does NOT add named beat reporters, multi-turn dialogues beyond the 2-3 question structure, social media reactions, or sponsor pressure. Voice is dramatic but the mechanic is still: question → 3 choices → effects. The complexity is in the trigger detection and content quality, not the mechanic.

## Voice direction (read carefully before writing templates)

**This is the load-bearing section of the prompt.** Get the voice wrong and the entire system feels like Tier 1 in louder clothes.

### What Tier 2 voice IS:
- **Specific, not generic.** "Five years of work walked off the field with that interception" — not "This is a tough loss." Specificity is what makes drama earned.
- **Edged.** Reporters ask uncomfortable questions. Coaches give answers that have weight. No diplomatic mush.
- **Active verbs, concrete nouns.** "Bled out in the third quarter." "Carried the franchise." "Burned the timeout we needed."
- **Variable length.** A 3-word response can hit harder than a 25-word one. Mix it up.
- **Stakes acknowledged.** Tier 2 fires on inflection points — the responses should know this. "This is the season" / "I knew tonight could be the end" / "We don't get many of these."
- **Voice differentiation per choice.** Deflect = stoic, controlled, holding back. Accountable = exposed, vulnerable, taking weight. Confrontational = fire, edge, willing to draw blood. Each of these should sound like three DIFFERENT coaches reacting to the same moment.

### What Tier 2 voice IS NOT:
- Cliché ("at the end of the day," "it is what it is," "we'll get back to work")
- Hedged ("might," "perhaps," "could be a problem")
- Generic ("tough loss," "great win," "team effort")
- Therapy-speak ("we'll process this," "important to acknowledge feelings")
- Coachspeak that any coach in any sport could say verbatim

### Writing prompts to test against:
For each template you write, ask: "Could this exact response appear in a Tier 1 template?" If yes, rewrite it. Tier 2 should be unmistakably different — a player skimming the choices should feel the moment.

## Tasks

### Task 1 — Schema additions

Add to `src/db/schema.sql`:

```sql
-- Tier 2 dramatic press events (multi-question)
CREATE TABLE IF NOT EXISTS tier2_press_event (
    id                       INTEGER PRIMARY KEY,
    season_year              INTEGER NOT NULL,
    week_number              INTEGER NOT NULL,
    team_id                  INTEGER NOT NULL,
    coach_id                 INTEGER NOT NULL,
    trigger_type             TEXT NOT NULL,        -- 'losing_streak_3' | 'championship_won' | etc.
    template_id              TEXT NOT NULL,
    n_questions              INTEGER NOT NULL,     -- 2 or 3
    total_delta_owner        INTEGER NOT NULL DEFAULT 0,
    total_delta_fan          INTEGER NOT NULL DEFAULT 0,
    total_delta_locker_room  INTEGER NOT NULL DEFAULT 0,
    is_resolved              INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT NOT NULL,
    resolved_at              TEXT,
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id)
);

CREATE INDEX IF NOT EXISTS idx_tier2_press_event_team ON tier2_press_event(team_id, season_year);

-- One row per question response within a Tier 2 event
CREATE TABLE IF NOT EXISTS tier2_press_response (
    id                   INTEGER PRIMARY KEY,
    event_id             INTEGER NOT NULL,
    question_index       INTEGER NOT NULL,       -- 1, 2, or 3
    selected_response    TEXT NOT NULL,          -- 'deflect' | 'accountable' | 'confrontational'
    delta_owner          INTEGER NOT NULL,
    delta_fan            INTEGER NOT NULL,
    delta_locker_room    INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES tier2_press_event(id),
    UNIQUE(event_id, question_index)
);
```

Add `ensure_tier2_press_tables(conn)` migration helper in `src/db/connection.py` following the established pattern. Wire into the bootstrap.

### Task 2 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Tier 2 dramatic press" section:

```python
# === Tier 2 dramatic press conference ===
TIER2_MAX_PER_WEEK = 1                       # at most one Tier 2 event per week
TIER2_HEADLESS_FALLBACK = 'accountable'      # used by stress harness
TIER2_VALID_CHOICES = ('deflect', 'accountable', 'confrontational')

# Effects per question (3-5x Tier 1 magnitude per §5.3)
TIER2_EFFECTS = {
    'deflect':         {'owner': -3, 'fan': -3, 'locker_room': +2},
    'accountable':     {'owner': +4, 'fan': +4, 'locker_room': +1},
    'confrontational': {'owner': -5, 'fan': +5, 'locker_room': -3},
}

# Trigger detection thresholds
TIER2_LOSING_STREAK_GAMES = 3                # 3+ consecutive losses
TIER2_BLOWN_LEAD_POINTS = 14                 # team led by 14+ at any point but lost
TIER2_STAR_RATING_THRESHOLD = 90             # players rated 90+ qualify as "stars"
TIER2_BLOCKBUSTER_PICK_ROUND = 1             # 1st-round picks count as blockbuster
TIER2_HOLDOUT_PUBLIC_WEEKS = 4               # holdout becomes public after 4 weeks

# Trigger priority order (highest to lowest — first fire wins)
TIER2_TRIGGER_PRIORITY = (
    'championship_won',
    'dynasty_milestone',
    'playoff_loss',
    'blockbuster_trade',
    'star_injury',
    'blown_14_point_lead',
    'holdout_public',
    'losing_streak_3',
)

# Cap on Tier 2 events per season (sanity bound; hard limit)
TIER2_MAX_PER_SEASON = 8
```

### Task 3 — Trigger detection

Create `src/transactions/tier2_triggers.py`:

```python
"""Phase 4 — Tier 2 trigger detection.

Each detector returns (fired: bool, context: dict) where context contains
slot-fill data for the template (e.g., star_player_name, win_total).
Per docs/Phase4_DesignDecisions.md §5.3.
"""
import sqlite3
from src.utils.constants import (
    TIER2_LOSING_STREAK_GAMES, TIER2_BLOWN_LEAD_POINTS,
    TIER2_STAR_RATING_THRESHOLD, TIER2_BLOCKBUSTER_PICK_ROUND,
    TIER2_HOLDOUT_PUBLIC_WEEKS, TIER2_TRIGGER_PRIORITY,
)


def detect_losing_streak_3(conn, team_id, season_year, week_number) -> tuple:
    """Fire when team loses 3+ in a row, but only on the 3rd loss
    (not on losses 4, 5, etc. — once per streak)."""
    ...


def detect_blown_14_point_lead(conn, team_id, season_year, week_number) -> tuple:
    """Fire when team led by 14+ at any point in last week's game but lost.
    Requires reading game's score progression — if that data isn't available
    in the current schema (e.g., only final score is stored), implement a
    proxy: large lead = won at halftime by 14+ but lost final.
    If even halftime score isn't tracked, this trigger can return (False, {})
    and we'll wire it later. Document the limitation."""
    ...


def detect_star_injury(conn, team_id, season_year, week_number) -> tuple:
    """Fire when a player rated 90+ moved to IR (or 'injured' status)
    this week. Read from player_event or transaction_log.
    Context: {'star_name': str, 'star_position': str, 'severity': str}"""
    ...


def detect_blockbuster_trade(conn, team_id, season_year, week_number) -> tuple:
    """Fire when this team executed a trade this week involving:
      - A player rated 90+, OR
      - A 1st-round pick
    Read from trade + trade_asset tables.
    Context: {'trade_summary': str, 'asset_description': str}"""
    ...


def detect_playoff_loss(conn, team_id, season_year, week_number) -> tuple:
    """Fire when team lost a playoff game this week. Detect via week.week_type
    and game result.
    Context: {'round': str, 'opponent_abbr': str, 'final_score': str}"""
    ...


def detect_holdout_public(conn, team_id, season_year, week_number) -> tuple:
    """Fire when a star player (rated 90+) on this team has been holding out
    for HOLDOUT_PUBLIC_WEEKS or more, AND no Tier 2 holdout event has fired
    for this player this season (one-time per holdout per season).
    Read from satisfaction_event or player_event.
    Context: {'star_name': str, 'weeks_held_out': int}"""
    ...


def detect_dynasty_milestone(conn, team_id, season_year, week_number) -> tuple:
    """Fire when the dynasty flag was newly set this season (per legacy_score
    or coach_legacy_score — check whether is_dynasty became 1 this season).
    Context: {'n_championships': int, 'window_start_year': int}"""
    ...


def detect_championship_won(conn, team_id, season_year, week_number) -> tuple:
    """Fire when team won the Super Bowl this week.
    Context: {'opponent_abbr': str, 'final_score': str, 'mvp_name': str}"""
    ...


# Registry — order matches TIER2_TRIGGER_PRIORITY (highest first)
ALL_TIER2_DETECTORS = (
    ('championship_won',       detect_championship_won),
    ('dynasty_milestone',      detect_dynasty_milestone),
    ('playoff_loss',           detect_playoff_loss),
    ('blockbuster_trade',      detect_blockbuster_trade),
    ('star_injury',            detect_star_injury),
    ('blown_14_point_lead',    detect_blown_14_point_lead),
    ('holdout_public',         detect_holdout_public),
    ('losing_streak_3',        detect_losing_streak_3),
)


def detect_tier2_trigger(conn, team_id, season_year, week_number) -> tuple:
    """Run detectors in priority order. Returns the first that fires
    or (None, {}) if none fire.

    Returns: (trigger_type: str | None, context: dict)
    """
    for trigger_type, detector in ALL_TIER2_DETECTORS:
        fired, context = detector(conn, team_id, season_year, week_number)
        if fired:
            return (trigger_type, context)
    return (None, {})
```

If any detector requires data the existing schema doesn't track (e.g., halftime scores for blown_14_point_lead), document the limitation in the function docstring and have it return `(False, {})` for now. Don't invent columns.

### Task 4 — Dramatic template library

Create `src/utils/tier2_templates.py`:

```python
"""Phase 4 — Tier 2 dramatic press conference templates.

Per docs/Phase4_DesignDecisions.md §1.1 (dramatic register, contrast with
Tier 1's beat-reporter flatness).

VOICE DIRECTION: see Phase4_Prompt6_Tier2DramaticPress.md "Voice direction"
section. Specificity over generic. Edge over hedged. Active verbs.

Each template has 2-3 questions. Each question has 3 response choices.
Slot-fills use {curly_braces} for context-injected fields.

Templates organized by trigger_type. Aim for 3 templates per trigger (variety
across a multi-season run).
"""

# === EXAMPLES (3 templates fully written; extend pattern to all 8 triggers) ===

TEMPLATES = [
    # === championship_won ===
    {
        'id': 'championship_won_1',
        'trigger': 'championship_won',
        'questions': [
            {
                'question': "Coach. You just won the Super Bowl. What's the first thing through your head?",
                'responses': {
                    'deflect':         "Relief.",
                    'accountable':     "Every face that helped us get here. Every one.",
                    'confrontational': "That nobody picked us. Nobody. And here we are.",
                },
            },
            {
                'question': "What does this mean for the franchise long-term?",
                'responses': {
                    'deflect':         "We'll worry about that tomorrow. Tonight is tonight.",
                    'accountable':     "It means the next group of players knows it can be done here.",
                    'confrontational': "It means the rest of the league has to come to us now.",
                },
            },
            {
                'question': "Are you already thinking about repeating?",
                'responses': {
                    'deflect':         "Tonight. Just tonight.",
                    'accountable':     "I'd be lying if I said no. The work starts again Monday.",
                    'confrontational': "We're not just thinking about it. We're going to do it.",
                },
            },
        ],
    },

    # === dynasty_milestone ===
    {
        'id': 'dynasty_milestone_1',
        'trigger': 'dynasty_milestone',
        'questions': [
            {
                'question': "Three championships in {window} years. People are using the word dynasty. Do you?",
                'responses': {
                    'deflect':         "I leave that to others.",
                    'accountable':     "I won't say it. The players who built it can.",
                    'confrontational': "I've earned the word. So have they.",
                },
            },
            {
                'question': "What separates this team from the ones that came close but didn't repeat?",
                'responses': {
                    'deflect':         "Health. Luck. The margin is thin.",
                    'accountable':     "Honestly? People who didn't believe themselves quietly enough to keep working.",
                    'confrontational': "Pretenders convince themselves. Champions just keep showing up.",
                },
            },
        ],
    },

    # === playoff_loss ===
    {
        'id': 'playoff_loss_1',
        'trigger': 'playoff_loss',
        'questions': [
            {
                'question': "{round} loss to {opponent_abbr}. Coach, when does it sink in?",
                'responses': {
                    'deflect':         "It already has.",
                    'accountable':     "Right now. Walking off that field. It's there.",
                    'confrontational': "When the league realizes it should've been us.",
                },
            },
            {
                'question': "What changes in the offseason?",
                'responses': {
                    'deflect':         "Everything gets evaluated. Same as always.",
                    'accountable':     "More than I want to say tonight. We weren't good enough.",
                    'confrontational': "A lot of things you'll read about. Some of it you won't like.",
                },
            },
            {
                'question': "Your message to the locker room tonight?",
                'responses': {
                    'deflect':         "I already gave it. Stays in there.",
                    'accountable':     "That I owe them better. Starting now.",
                    'confrontational': "That if you can't handle this feeling, you don't belong on the next team.",
                },
            },
        ],
    },

    # === star_injury ===
    {
        'id': 'star_injury_1',
        'trigger': 'star_injury',
        'questions': [
            {
                'question': "{star_name} is down. Initial read on the severity?",
                'responses': {
                    'deflect':         "I'll let the doctors talk about it tomorrow.",
                    'accountable':     "It looked bad. I won't pretend otherwise.",
                    'confrontational': "Next man up. That's the only read I have.",
                },
            },
            {
                'question': "How does the team adjust without him?",
                'responses': {
                    'deflect':         "Same way we always do. Together.",
                    'accountable':     "Honestly? It's going to be hard. He's irreplaceable.",
                    'confrontational': "We've got guys who can play. They'll get their shot.",
                },
            },
        ],
    },

    # === blockbuster_trade ===
    # === blown_14_point_lead ===
    # === holdout_public ===
    # === losing_streak_3 ===
    # ... extend pattern. Aim for 3 templates per trigger.
]


def get_templates_by_trigger(trigger_type: str) -> list:
    """Return all templates matching a trigger. Empty list if none match
    (caller must handle — possibly by skipping the event)."""
    return [t for t in TEMPLATES if t['trigger'] == trigger_type]


def get_template_by_id(template_id: str) -> dict:
    for t in TEMPLATES:
        if t['id'] == template_id:
            return t
    raise KeyError(f"unknown template id: {template_id}")
```

**For each remaining trigger** (`blockbuster_trade`, `blown_14_point_lead`, `holdout_public`, `losing_streak_3`), write 3 templates following the same pattern: 2-3 questions per template, 3 voice-differentiated responses per question, slot-fill placeholders for context data.

**Total target**: 24 templates (8 triggers × 3 templates each). About half are written above as examples; you write the rest. **Voice quality is the deliverable**.

### Task 5 — Tier 2 event generation + resolution

Create `src/transactions/tier2_press_conference.py`:

```python
"""Phase 4 — Tier 2 dramatic press conferences.

Multi-question events triggered by inflection points. Cannot be autopilot-skipped
(per §5.3 — these are the moments the player remembers).

Per docs/Phase4_DesignDecisions.md §5.3 Tier 2 spec.
"""
import sqlite3
import random
from datetime import datetime
from src.utils.constants import (
    TIER2_VALID_CHOICES, TIER2_HEADLESS_FALLBACK, TIER2_EFFECTS,
    TIER2_MAX_PER_WEEK, TIER2_MAX_PER_SEASON,
)
from src.utils.tier2_templates import get_templates_by_trigger, get_template_by_id
from src.transactions.tier2_triggers import detect_tier2_trigger
from src.league.owner_sentiment import update_sentiment


def maybe_generate_tier2_event(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    team_id: int,
    coach_id: int,
    headless: bool = False,
) -> dict | None:
    """Check if a Tier 2 trigger fires this week for this team.
    If yes, generate the event. If no, return None.

    Steps:
      1. Check season cap — if TIER2_MAX_PER_SEASON already hit, skip
      2. Run detect_tier2_trigger
      3. If no trigger: return None
      4. Pick a random template matching the trigger
      5. Insert tier2_press_event row (is_resolved=0)
      6. Slot-fill template questions with context data
      7. If headless: auto-resolve to TIER2_HEADLESS_FALLBACK for all questions
      8. Return event dict for interactive resolution

    Returns: {
        'event_id': int,
        'trigger_type': str,
        'questions': [{'index': 1, 'question': '...', 'responses': {...}}, ...],
        'is_resolved': bool,
    } or None
    """
    ...


def resolve_tier2_question(
    conn: sqlite3.Connection,
    event_id: int,
    question_index: int,
    response_choice: str,
    is_headless: bool = False,
) -> dict:
    """Apply effects for one question in a Tier 2 event sequence.

    Effects per question:
      - update_sentiment(driver='presser', delta=TIER2_EFFECTS[choice]['owner'],
        detail=f"Tier 2 ({trigger_type}) Q{n}")
      - team.fan_sentiment += TIER2_EFFECTS[choice]['fan']
      - locker_room delta on top-10 players (same MVP simplification as Tier 1)

    Inserts a tier2_press_response row. Updates total_delta_* on the event row.
    If question_index == n_questions (last question), marks event is_resolved=1
    and resolved_at = now.

    Returns delta dict for display.
    """
    ...


def resolve_tier2_event_headless(
    conn: sqlite3.Connection,
    event_id: int,
) -> None:
    """Resolve all remaining questions for an event using TIER2_HEADLESS_FALLBACK."""
    ...
```

### Task 6 — Suppress Tier 1 when Tier 2 fires same week

In `src/transactions/press_conference.py` from prompt #5, modify `generate_weekly_press_event` (or its caller in `run_season.py` / harness) to check whether a Tier 2 event has been generated for this team this week. If yes, skip Tier 1 generation.

Simplest implementation: in `run_season.py` and `stress_harness.py`, run Tier 2 detection FIRST. If a Tier 2 event fires, generate it and skip the Tier 1 call. Otherwise, generate the Tier 1 routine event.

```python
# In the per-week flow (run_season.py and stress_harness.py):
tier2_event = maybe_generate_tier2_event(conn, season_year, week_number, team_id, coach_id, headless=...)
if tier2_event is not None:
    # Tier 2 fired — present it (interactive) or it's already resolved (headless)
    if not tier2_event['is_resolved']:
        # Interactive multi-question flow
        for q in tier2_event['questions']:
            present_question_and_resolve(...)
else:
    # No Tier 2 fired — fall through to routine Tier 1
    generate_weekly_press_event(...)
```

### Task 7 — CLI integration in run_season.py

Extend the press conference flow in `run_season.py --advance-week` to handle Tier 2 events when they fire. Multi-question display:

```
================================================================
TIER 2 PRESS CONFERENCE — Week 19 (Conference Championship)
================================================================
[Trigger: playoff_loss vs KC, 24-21]

Question 1 of 3
Reporter: "Conference championship loss to KC. Coach, when does it sink in?"
  1. [DEFLECT]         "It already has."
  2. [ACCOUNTABLE]     "Right now. Walking off that field. It's there."
  3. [CONFRONTATIONAL] "When the league realizes it should've been us."
Choice: 2
  → Owner +4, Fan +4, Locker +1

Question 2 of 3
Reporter: "What changes in the offseason?"
  ...
```

No autopilot prompts in Tier 2 ('a' prefix syntax is ignored). Each question must be interactively resolved. After the final question resolves, print a summary:

```
TIER 2 EVENT COMPLETE
Total effects: Owner +12, Fan +9, Locker +2
```

### Task 8 — Stress harness compatibility

In `src/league/stress_harness.py`, replace the existing per-week press call with the Tier 2-first pattern:

```python
from src.transactions.tier2_press_conference import maybe_generate_tier2_event
from src.transactions.press_conference import generate_weekly_press_event

# Per week, for the player team:
tier2 = maybe_generate_tier2_event(conn, season_year, week_number, team_id, coach_id, headless=True)
if tier2 is None:
    generate_weekly_press_event(conn, season_year, week_number, team_id, coach_id, headless=True)
```

Both Tier 2 and Tier 1 must auto-resolve in headless mode. The harness must NOT prompt for input under any condition.

## Constraints — what NOT to touch

- Do NOT modify the Tier 1 templates from prompt #5 — voice differentiation between tiers is the entire design intent. If Tier 1 templates need editing too (e.g., a few are too dramatic), file as a follow-up; do not edit in this prompt.
- Do NOT add named beat reporters, multi-turn dialogue branching, social media reactions, or sponsor pressure. (Post-launch.)
- Do NOT add Tier 2 events for AI teams. Player coach only, same as Tier 1.
- Do NOT modify the AI behavior matrix, owner sentiment math, or legacy scoring.
- Do NOT add a UI beyond terminal text. Polished display in #9.
- Do NOT exceed TIER2_MAX_PER_SEASON (8). If the design produces more than 8 events per season in playtesting, raise the cap or tighten the triggers — not in this prompt, but flag for tuning.

## Test plan

### Step 1 — No regression on existing harness

```bash
rm -f saves/phase4_v6.db
python generate.py saves/phase4_v6.db --season 2024
python run_stress_test.py saves/phase4_v6.db --invariants --seasons 3
```

Expected: 12/12 invariants still pass. Tier 2 events fire some weeks (replacing Tier 1 those weeks); both resolve in headless mode.

### Step 2 — Verify Tier 2 mechanics

Create `verify_phase4_p6.py`:

```python
"""Verification for Phase 4 Build Prompt #6 — Tier 2 Dramatic Press."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.transactions.tier2_press_conference import maybe_generate_tier2_event
from src.utils.constants import TIER2_EFFECTS, TIER2_MAX_PER_SEASON

DB = "saves/phase4_v6.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. Schema check
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'tier2_press_event' in tables
assert 'tier2_press_response' in tables

# 2. Some Tier 2 events fired across the 3-season run
n_events = conn.execute("SELECT COUNT(*) FROM tier2_press_event").fetchone()[0]
print(f"Tier 2 events generated across 3 seasons: {n_events}")
assert n_events >= 3, f"expected at least 3 Tier 2 events across 3 seasons, got {n_events}"

# 3. Per-season cap respected
per_season = conn.execute("""
    SELECT season_year, COUNT(*) c FROM tier2_press_event
    WHERE coach_id = (SELECT id FROM coach_career WHERE is_player=1)
    GROUP BY season_year
""").fetchall()
for row in per_season:
    assert row['c'] <= TIER2_MAX_PER_SEASON, \
        f"season {row['season_year']} had {row['c']} Tier 2 events (cap is {TIER2_MAX_PER_SEASON})"

# 4. All events resolved (none unresolved after harness)
unresolved = conn.execute("SELECT COUNT(*) FROM tier2_press_event WHERE is_resolved=0").fetchone()[0]
assert unresolved == 0, f"{unresolved} Tier 2 events left unresolved"

# 5. Each event has its expected number of question responses
events = conn.execute("SELECT id, n_questions FROM tier2_press_event").fetchall()
for e in events:
    n_responses = conn.execute(
        "SELECT COUNT(*) FROM tier2_press_response WHERE event_id=?", (e['id'],)
    ).fetchone()[0]
    assert n_responses == e['n_questions'], \
        f"event {e['id']} expected {e['n_questions']} responses, got {n_responses}"

# 6. Effect deltas match constants
for r in conn.execute("SELECT selected_response, delta_owner, delta_fan, delta_locker_room FROM tier2_press_response LIMIT 5"):
    expected = TIER2_EFFECTS[r['selected_response']]
    assert r['delta_owner'] == expected['owner']
    assert r['delta_fan'] == expected['fan']
    assert r['delta_locker_room'] == expected['locker_room']

# 7. Trigger diversity — at least 2 different trigger types fired across the run
n_distinct = conn.execute("SELECT COUNT(DISTINCT trigger_type) FROM tier2_press_event").fetchone()[0]
print(f"Distinct Tier 2 triggers fired: {n_distinct}")
assert n_distinct >= 2, f"only {n_distinct} distinct trigger fired; expected at least 2"

# 8. Tier 1 suppressed when Tier 2 fires same week
overlaps = conn.execute("""
    SELECT t2.season_year, t2.week_number FROM tier2_press_event t2
    JOIN press_event t1 ON t1.season_year=t2.season_year
                       AND t1.week_number=t2.week_number
                       AND t1.team_id=t2.team_id
""").fetchall()
assert len(overlaps) == 0, f"Tier 1 + Tier 2 overlap in {len(overlaps)} weeks (suppression failed)"

print("Phase 4 prompt #6 verification passed.")
```

```bash
python verify_phase4_p6.py
```

### Step 3 — Voice quality spot-check

```bash
sqlite3 saves/phase4_v6.db "SELECT trigger_type, template_id FROM tier2_press_event ORDER BY season_year, week_number;"
```

Then read 3-4 of the actual templates from `src/utils/tier2_templates.py`. **The quality bar is "could a player tell from reading the response choice that this is a Tier 2 moment, not Tier 1?"** If responses sound like they could appear in Tier 1, the voice work isn't done. Rewrite as needed before declaring the prompt complete.

### Step 4 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #6 Tier 2 dramatic press (date)

Tier 2 events fired per 3-season run: {N}
Trigger distribution: {breakdown by trigger_type}
Sentiment delta from Tier 2 events: {avg per event, total per season}

Voice quality notes:
- Strongest templates: {ids}
- Weakest templates needing rewrite: {ids — flag for future content pass}

Tuning notes:
- {any triggers firing too often or never}
- {priority order edits if needed}
```

### Step 5 — Update CLAUDE.md

```
- [x] Tier 1 weekly press conference + autopilot
- [x] Tier 2 event-triggered press conference + dramatic narration
- [ ] End-of-season legacy display + dynasty/HOF narrative
...
```

Add `src/transactions/tier2_press_conference.py`, `src/transactions/tier2_triggers.py`, `src/utils/tier2_templates.py`, `verify_phase4_p6.py` to the project structure map.

## Reference

- `docs/Phase4_DesignDecisions.md` §1.1 (Mixed-by-context tone — Tier 2 is the dramatic register)
- `docs/Phase4_DesignDecisions.md` §1.3 (cadence — Tier 2 ~3-5 per season)
- `docs/Phase4_DesignDecisions.md` §5.3 (Tier 2 spec — multi-question, 3-5x effects, no autopilot)
- `docs/Phase4_DesignDecisions.md` §5.5 (MVP scope — what's IN vs. deferred to post-launch)
- `src/utils/press_templates.py` from prompt #5 — Tier 1 voice reference (read for contrast before writing Tier 2 templates)
