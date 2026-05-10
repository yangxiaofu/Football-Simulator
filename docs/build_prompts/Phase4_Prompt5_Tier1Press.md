# Phase 4 Build Prompt #5 — Tier 1 Weekly Press Conference + Autopilot Default

**Model**: Sonnet
**Planning mode**: Yes — multi-file work with content templates and CLI integration; lay out the structure before writing.

---

## Context

Phase 4's data layer is fully complete. Prompts #1, #2, #2.5, #3, #4, #7, and #8 are done. The harness passes 12/12 invariants over 3 simulated seasons with realistic AI behavior, sentiment-driven coaching changes, legacy expansion, narrative beats, and a populated league record book.

This prompt is a meaningful inflection point: it introduces the first **recurring interactive decision** the player makes during the season. Up to now, the player has been passive — clicking through offseason, watching games. Tier 1 pressers happen every regular season week (17 per season). Each is a single question with three response choices and small but real effects on owner sentiment, fan sentiment, and locker room (player satisfaction).

The autopilot toggle is the load-bearing UX mechanic: players who don't want to engage with 17 weekly decisions can set a default response (e.g., "always accountable") and let the season run. Effects still apply per §5.3 — autopilot is not a free pass — but the player isn't interrupted weekly.

This also wires up the `SENTIMENT_DELTA_PRESSER_PLACEHOLDER = 0` from prompt #4 to actually fire real deltas.

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §5.3 (two-tier press conferences) and §5.4 (fan sentiment), §5.5 (MVP scope boundary), and §1.1 (Mixed-by-context tone — Tier 1 is the dry/routine voice)
3. `src/league/owner_sentiment.py` from prompt #4 — particularly the `update_sentiment` helper and the `'presser'` driver category that's already wired but unused
4. `src/db/schema.sql` — particularly `team.fan_sentiment` (already exists from Phase 0, line 51) and `coach_career` (will gain a new column)
5. `run_season.py` — entry point for `--advance-week`; press events fire after the week's game completes

## Goal

Add the Tier 1 weekly press conference system:

1. **Press event generation** after each regular season week (player coach only; AI teams do NOT get pressers in MVP)
2. **Question templates** organized by context (post-win / post-loss / post-blowout / etc.), with three response choices per template (deflect / accountable / confrontational)
3. **Effect application** on owner sentiment (existing), fan sentiment (already-existing column, never written to), and locker room (player satisfaction system from Phase 3)
4. **Autopilot toggle** stored on the player's `coach_career` row — default response that the system uses without prompting
5. **Interactive CLI flow** in `run_season.py --advance-week` that prompts when autopilot is off
6. **Headless harness compatibility** — auto-resolve to a sane default when running stress tests

**Critical scope discipline**: this prompt does NOT add Tier 2 dramatic event-triggered press conferences (that's #6), beat reporter personalities, multi-turn dialogues, or rich UI. Voice is dry, beat-reporter flat per §1.1. Effects are small per §5.3 — Tier 1 is supposed to be low-stakes; the dramatic moments live in Tier 2.

## Tasks

### Task 1 — Schema additions

Add to `src/db/schema.sql`:

```sql
-- Tier 1 weekly press events
CREATE TABLE IF NOT EXISTS press_event (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    week_number             INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    coach_id                INTEGER NOT NULL,
    context_type            TEXT NOT NULL,           -- 'post_win' | 'post_loss' | etc.
    question_template_id    TEXT NOT NULL,
    selected_response       TEXT,                    -- 'deflect' | 'accountable' | 'confrontational'; NULL = unresolved
    autopilot_used          INTEGER NOT NULL DEFAULT 0,
    delta_owner             INTEGER NOT NULL DEFAULT 0,
    delta_fan               INTEGER NOT NULL DEFAULT 0,
    delta_locker_room       INTEGER NOT NULL DEFAULT 0,
    resolved_at             TEXT,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(season_year, week_number, team_id)
);

CREATE INDEX IF NOT EXISTS idx_press_event_team ON press_event(team_id, season_year);

-- Add autopilot default to coach_career (NULL = no autopilot, prompt every week)
ALTER TABLE coach_career ADD COLUMN press_autopilot_default TEXT;  -- 'deflect' | 'accountable' | 'confrontational' | NULL
```

`team.fan_sentiment` already exists from Phase 0 (column line 51, default 50). This prompt finally writes to it.

Add `ensure_press_tables(conn)` migration helper in `src/db/connection.py` following the established pattern. Wire into the bootstrap.

### Task 2 — Constants

Add to `src/utils/constants.py` in a new "Phase 4 — Tier 1 press conference" section:

```python
# === Press conference (Tier 1) ===
PRESS_AUTOPILOT_VALID_CHOICES = ('deflect', 'accountable', 'confrontational')
PRESS_AUTOPILOT_HARNESS_FALLBACK = 'accountable'   # used by stress harness when no default set

# Effect magnitudes — small per §5.3 (Tier 1 is supposed to be low-stakes)
PRESS_EFFECTS = {
    'deflect': {
        'owner': -1,    # owners don't love deflection
        'fan': -1,      # fans want passion
        'locker_room': +1,  # players appreciate not being thrown under the bus
    },
    'accountable': {
        'owner': +1,    # owners like accountability
        'fan': +1,      # fans like accountability
        'locker_room': 0,
    },
    'confrontational': {
        'owner': -2,    # owners hate public spats
        'fan': +2,      # fans love a fiery coach
        'locker_room': -1,  # players dislike being publicly criticized
    },
}

# Context detection
PRESS_BLOWOUT_MARGIN = 14            # win/loss by 14+ → blowout context
PRESS_LOSING_STREAK_THRESHOLD = 3    # 3+ losses in a row → losing_streak context
PRESS_WINNING_STREAK_THRESHOLD = 3   # 3+ wins in a row → winning_streak context

# Locker room delta application — apply to all rostered players' satisfaction
PRESS_LOCKER_ROOM_PLAYER_LIMIT = 53  # active roster only
```

### Task 3 — Question templates module

Create `src/utils/press_templates.py`:

```python
"""Phase 4 — Tier 1 press conference question templates.

Per docs/Phase4_DesignDecisions.md §1.1 (Mixed-by-context tone — Tier 1 is
dry, beat-reporter flat) and §5.3 (one question, three response choices).

Templates organized by context type. At least 3 templates per context to
provide variety across a 17-week season. Random selection within matching
context.
"""

# Template structure:
#   id: unique string identifier
#   context: context_type matching what generate_weekly_press_event detects
#   question: reporter's question (dry, factual)
#   responses: dict of choice → response text

TEMPLATES = [
    # === post_win (routine win, margin < 14) ===
    {
        'id': 'post_win_1',
        'context': 'post_win',
        'question': "Coach, the team got the W today. What's your read on the performance?",
        'responses': {
            'deflect':         "Just happy to come away with the win. Lots to clean up.",
            'accountable':     "Pleased with the execution but we left plays on the field.",
            'confrontational': "Anyone who thought we wouldn't win this hasn't been watching.",
        },
    },
    {
        'id': 'post_win_2',
        'context': 'post_win',
        'question': "How does this win position the team going forward?",
        'responses': {
            'deflect':         "We're just focused on the next one.",
            'accountable':     "It's one game. Next week we'll be tested again.",
            'confrontational': "It positions us exactly where we should be — at the top.",
        },
    },
    {
        'id': 'post_win_3',
        'context': 'post_win',
        'question': "What was the difference today?",
        'responses': {
            'deflect':         "The guys executed. That's all I'll say.",
            'accountable':     "Better preparation this week translated to better play.",
            'confrontational': "We just outclassed them. Plain and simple.",
        },
    },
    # Add 1-2 more variants → 4-5 total for post_win

    # === post_loss (routine loss, margin < 14) ===
    {
        'id': 'post_loss_1',
        'context': 'post_loss',
        'question': "Coach, where did this one slip away?",
        'responses': {
            'deflect':         "We're going to look at the tape and learn from it.",
            'accountable':     "I didn't have us prepared for what they showed us. That's on me.",
            'confrontational': "The officiating took us out of our rhythm. Period.",
        },
    },
    {
        'id': 'post_loss_2',
        'context': 'post_loss',
        'question': "Was there a turning point in this game?",
        'responses': {
            'deflect':         "A lot of plays. We'll review them all.",
            'accountable':     "We had our chances and didn't capitalize. Comes back to execution.",
            'confrontational': "The turning point was three calls that didn't go our way.",
        },
    },
    {
        'id': 'post_loss_3',
        'context': 'post_loss',
        'question': "How does the locker room respond from here?",
        'responses': {
            'deflect':         "These guys are pros. They'll be ready Monday.",
            'accountable':     "Honestly, I'll need to see. We have to demand more from each other.",
            'confrontational': "Some guys need to look in the mirror. That's all I'll say.",
        },
    },
    # Add 1-2 more variants

    # === post_blowout_win (margin >= 14) ===
    {
        'id': 'post_blowout_win_1',
        'context': 'post_blowout_win',
        'question': "That was a dominant performance. Was it as easy as it looked?",
        'responses': {
            'deflect':         "Nothing in this league is easy. We executed well today.",
            'accountable':     "We had a great week of preparation. The result followed.",
            'confrontational': "When we play our game, this is what happens. Every time.",
        },
    },
    {
        'id': 'post_blowout_win_2',
        'context': 'post_blowout_win',
        'question': "Does a win like this send a message to the rest of the league?",
        'responses': {
            'deflect':         "We're focused on the next opponent. That's it.",
            'accountable':     "We don't need to send messages. We just need to keep playing this way.",
            'confrontational': "It absolutely sends a message. They saw what they saw.",
        },
    },
    # Add 1-2 more

    # === post_blowout_loss (margin >= 14) ===
    {
        'id': 'post_blowout_loss_1',
        'context': 'post_blowout_loss',
        'question': "That was a tough one to watch. What went wrong?",
        'responses': {
            'deflect':         "We'll watch the tape and figure out what to fix.",
            'accountable':     "We got outcoached and outplayed in every phase. I own that.",
            'confrontational': "Players have to make plays. I called what I called. They didn't execute.",
        },
    },
    {
        'id': 'post_blowout_loss_2',
        'context': 'post_blowout_loss',
        'question': "Coach, the fans are frustrated. Your message to them?",
        'responses': {
            'deflect':         "We hear them. We're going to be better.",
            'accountable':     "They have every right to be frustrated. Today wasn't acceptable.",
            'confrontational': "The fans need to understand this is a process. We're building.",
        },
    },
    # Add 1-2 more

    # === post_division_loss (lost to divisional opponent) ===
    {
        'id': 'post_division_loss_1',
        'context': 'post_division_loss',
        'question': "A division loss stings extra. How do you frame this for the room?",
        'responses': {
            'deflect':         "Every game counts the same. We'll move on.",
            'accountable':     "Division games matter. We didn't show up. That's the truth.",
            'confrontational': "They wanted it more. Some of our guys need to ask why.",
        },
    },
    # Add 2 more variants

    # === losing_streak (3+ consecutive losses) ===
    {
        'id': 'losing_streak_1',
        'context': 'losing_streak',
        'question': "Coach, that's three in a row. How do you get the ship righted?",
        'responses': {
            'deflect':         "We're working through it. The schedule has been tough.",
            'accountable':     "I have to do a better job. Period. Starts with me.",
            'confrontational': "Some guys aren't earning their snaps. That's going to change.",
        },
    },
    {
        'id': 'losing_streak_2',
        'context': 'losing_streak',
        'question': "Are you concerned about your job security?",
        'responses': {
            'deflect':         "I don't worry about that. I just coach the team.",
            'accountable':     "I worry about the team. Whatever happens to me follows from that.",
            'confrontational': "That question's beneath you. Next.",
        },
    },
    # Add 1 more

    # === winning_streak (3+ consecutive wins) ===
    {
        'id': 'winning_streak_1',
        'context': 'winning_streak',
        'question': "Three in a row. Are you starting to feel like a contender?",
        'responses': {
            'deflect':         "We're focused on the next one.",
            'accountable':     "We've earned a little something. We have to keep earning.",
            'confrontational': "We've been a contender. Now everyone else sees it.",
        },
    },
    # Add 2 more

    # === routine (fallback when no specific context detected) ===
    {
        'id': 'routine_1',
        'context': 'routine',
        'question': "Coach, what's the team focused on this week?",
        'responses': {
            'deflect':         "Same as every week. The next opponent.",
            'accountable':     "Cleaning up the things we didn't do well last time out.",
            'confrontational': "Winning. That's it. The rest takes care of itself.",
        },
    },
    # Add 2 more
]


def get_templates_by_context(context_type: str) -> list:
    """Return all templates matching a given context. Falls back to 'routine'
    if no templates match the context."""
    matching = [t for t in TEMPLATES if t['context'] == context_type]
    if not matching:
        matching = [t for t in TEMPLATES if t['context'] == 'routine']
    return matching


def get_template_by_id(template_id: str) -> dict:
    """Look up a single template by its id."""
    for t in TEMPLATES:
        if t['id'] == template_id:
            return t
    raise KeyError(f"unknown template id: {template_id}")
```

Aim for ~30 total templates (3-5 per context × 8 contexts). Voice should be dry — beat-reporter flat. No exclamation points. No melodrama. Save dramatic prose for #6.

### Task 4 — Press event generation + resolution

Create `src/transactions/press_conference.py`:

```python
"""Phase 4 — Tier 1 weekly press conference.

Generates one press event per regular season week for the player coach.
Resolves via autopilot if set; otherwise returns the event for interactive
resolution.

Per docs/Phase4_DesignDecisions.md §5.3.
"""
import sqlite3
import random
from datetime import datetime
from src.utils.constants import (
    PRESS_AUTOPILOT_VALID_CHOICES, PRESS_AUTOPILOT_HARNESS_FALLBACK,
    PRESS_EFFECTS, PRESS_BLOWOUT_MARGIN,
    PRESS_LOSING_STREAK_THRESHOLD, PRESS_WINNING_STREAK_THRESHOLD,
)
from src.utils.press_templates import get_templates_by_context, get_template_by_id
from src.league.owner_sentiment import update_sentiment


def detect_context(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> str:
    """Determine the press event context based on the week's game and recent history.

    Detection priority (first match wins):
      1. losing_streak — 3+ consecutive losses
      2. winning_streak — 3+ consecutive wins
      3. post_blowout_win — won by 14+
      4. post_blowout_loss — lost by 14+
      5. post_division_loss — lost to divisional opponent (any margin)
      6. post_win — won this week (default win context)
      7. post_loss — lost this week (default loss context)
      8. routine — bye week or no game data

    Returns one of the context types defined in press_templates.
    """
    ...


def generate_weekly_press_event(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    team_id: int,
    coach_id: int,
    headless: bool = False,
) -> dict:
    """Create one press event for the player coach after the week's game.

    Steps:
      1. Detect context from the week's outcome
      2. Pick a random template from those matching the context
      3. Insert press_event row (selected_response=NULL, unresolved)
      4. Look up coach.press_autopilot_default
      5. If autopilot is set:
           - Resolve immediately with default
           - Apply effects
      6. Else if headless:
           - Resolve with PRESS_AUTOPILOT_HARNESS_FALLBACK
      7. Else:
           - Return the event unresolved for interactive resolution

    Returns: {
        'press_event_id': int,
        'question': str,
        'responses': dict,
        'context': str,
        'resolved': bool,
        'selected_response': str | None,
    }
    """
    ...


def resolve_press_event(
    conn: sqlite3.Connection,
    press_event_id: int,
    response_choice: str,
    is_autopilot: bool = False,
) -> dict:
    """Apply a response choice to an unresolved press event.

    Effects:
      1. Update team.owner_sentiment via update_sentiment(driver='presser',
         delta=PRESS_EFFECTS[choice]['owner'], detail="<short summary>")
      2. Update team.fan_sentiment directly: clamp(0, 100, current + delta)
      3. Apply locker_room delta to player satisfaction (Phase 3 system).
         If applying to all 53 players is heavy, apply to the captain/star
         players only — choose a reasonable subset (top 10 by overall) for MVP.
      4. Update press_event row with selected_response, deltas, resolved_at, autopilot_used

    Validates response_choice is in PRESS_EFFECTS. Raises ValueError otherwise.

    Returns: {
        'delta_owner': int, 'delta_fan': int, 'delta_locker_room': int,
        'new_owner_sentiment': int, 'new_fan_sentiment': int,
    }
    """
    ...


def set_autopilot_default(
    conn: sqlite3.Connection,
    coach_id: int,
    choice: str | None,
) -> None:
    """Set or clear the coach's autopilot default response.
    None = clear autopilot (prompt every week).
    Validates against PRESS_AUTOPILOT_VALID_CHOICES if not None.
    """
    ...


def get_unresolved_press_events(
    conn: sqlite3.Connection,
    coach_id: int,
) -> list:
    """Return any unresolved press events for a coach, ordered by week.
    Used by run_season.py to surface pending pressers to the player.
    """
    ...
```

### Task 5 — Replace the placeholder presser driver in owner_sentiment

In `src/league/owner_sentiment.py` (from prompt #4), the `'presser'` driver category exists but has `SENTIMENT_DELTA_PRESSER_PLACEHOLDER = 0`. This prompt makes the placeholder live: when `resolve_press_event` calls `update_sentiment(driver='presser', delta=N)`, real values flow.

No code change needed in `owner_sentiment.py` — just the calling pattern from `press_conference.py`. But you can REMOVE `SENTIMENT_DELTA_PRESSER_PLACEHOLDER` from `constants.py` since it's now superseded by `PRESS_EFFECTS[choice]['owner']`.

### Task 6 — Hook into run_season.py --advance-week

In `run_season.py`, after the week's game completes and stats are written, but before advancing to the next week:

```python
from src.transactions.press_conference import (
    generate_weekly_press_event, resolve_press_event, set_autopilot_default,
)
from src.utils.press_templates import get_template_by_id

# After game completes:
player_coach = conn.execute(
    "SELECT id, current_team_id FROM coach_career WHERE is_player=1 AND is_active=1"
).fetchone()

# Skip if player is between jobs (vacancy state per §8 item 9)
if player_coach and player_coach['current_team_id']:
    event = generate_weekly_press_event(
        conn, season_year, week_number,
        player_coach['current_team_id'], player_coach['id'],
        headless=False,
    )

    if not event['resolved']:
        # Interactive prompt
        print()
        print("=" * 70)
        print(f"PRESS CONFERENCE — Week {week_number}")
        print("=" * 70)
        print(f"Reporter: \"{event['question']}\"")
        print()
        choices = list(event['responses'].items())
        for i, (choice, text) in enumerate(choices, 1):
            print(f"  {i}. [{choice.upper():<15}] \"{text}\"")
        print()
        print("Enter 1-3 to choose, or prefix with 'a' to set as autopilot default (e.g. 'a2').")

        raw = input("Choice: ").strip().lower()
        set_default = raw.startswith('a')
        if set_default:
            raw = raw[1:].strip()

        try:
            idx = int(raw) - 1
            choice = choices[idx][0]
        except (ValueError, IndexError):
            print("Invalid input — defaulting to 'accountable'.")
            choice = 'accountable'

        result = resolve_press_event(conn, event['press_event_id'], choice, is_autopilot=False)
        if set_default:
            set_autopilot_default(conn, player_coach['id'], choice)
            print(f"Autopilot default set to '{choice}'. Future routine pressers will auto-resolve.")

        print(f"  → Owner: {result['delta_owner']:+d}, Fan: {result['delta_fan']:+d}, "
              f"Locker: {result['delta_locker_room']:+d}")
    else:
        # Auto-resolved via autopilot — print a brief summary
        template = get_template_by_id(
            conn.execute("SELECT question_template_id FROM press_event WHERE id=?",
                         (event['press_event_id'],)).fetchone()[0]
        )
        choice = event['selected_response']
        print(f"  [Autopilot] Press: \"{template['responses'][choice]}\" (chosen: {choice})")
```

Keep the prompt UX simple — single-line input, clear options, no fancy formatting.

### Task 7 — Headless harness compatibility

In `src/league/stress_harness.py`, the harness already advances weeks headlessly. The press event generator's `headless=True` flag handles the auto-resolution. Find the per-week loop in the harness and add:

```python
from src.transactions.press_conference import generate_weekly_press_event

# After the week's game completes (per team or once for the player team):
player_coach = conn.execute(
    "SELECT id, current_team_id FROM coach_career WHERE is_player=1 AND is_active=1"
).fetchone()
if player_coach and player_coach['current_team_id']:
    generate_weekly_press_event(
        conn, season_year, week_number,
        player_coach['current_team_id'], player_coach['id'],
        headless=True,  # auto-resolves to autopilot default OR PRESS_AUTOPILOT_HARNESS_FALLBACK
    )
```

The harness must NOT prompt for input under any condition.

## Constraints — what NOT to touch

- Do NOT add Tier 2 dramatic press conferences. Those are #6, with a separate template library and dramatic voice.
- Do NOT add named beat reporters, multi-turn dialogues, social media reactions, or sponsor pressure. (Post-launch.)
- Do NOT generate press events for AI teams. The carousel from #3 fires AI coaches based on owner sentiment alone — they don't speak to the press in MVP.
- Do NOT modify the AI behavior matrix, owner sentiment math (only call `update_sentiment` with the new presser deltas), legacy scoring, or historical records.
- Do NOT write rich UI — terminal text prompts only. The polished display lives in #9.
- Do NOT apply locker room deltas to all 53 players if it's expensive. Apply to top-10 by overall as a reasonable MVP simplification.
- Do NOT generate press events during playoff weeks. Tier 1 is regular season only (weeks 1-17). Playoff pressers are Tier 2 (#6).

## Test plan

### Step 1 — No regression on existing harness

```bash
rm -f saves/phase4_v5.db
python generate.py saves/phase4_v5.db --season 2024
python run_stress_test.py saves/phase4_v5.db --invariants --seasons 3
```

Expected: 12/12 invariants still pass. Press events generated and auto-resolved each week. The player coach's owner_sentiment trajectory should now include presser-driven movement (small deltas, but real).

### Step 2 — Verify the press conference mechanics

Create `verify_phase4_p5.py`:

```python
"""Verification for Phase 4 Build Prompt #5 — Tier 1 Press Conference."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.transactions.press_conference import (
    generate_weekly_press_event, resolve_press_event, set_autopilot_default,
)
from src.utils.constants import PRESS_EFFECTS

DB = "saves/phase4_v5.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. Schema check
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'press_event' in tables

cols = {r['name'] for r in conn.execute("PRAGMA table_info(coach_career)")}
assert 'press_autopilot_default' in cols

# 2. Press events generated for the player coach across the 3-season run
player_coach_id = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()[0]
n_events = conn.execute(
    "SELECT COUNT(*) FROM press_event WHERE coach_id=?", (player_coach_id,)
).fetchone()[0]
print(f"Press events generated for player coach: {n_events}")
# 3 seasons × 17 regular season weeks = 51 expected
assert n_events >= 40, f"expected ~51 press events across 3 seasons, got {n_events}"

# 3. All events resolved (none unresolved after harness run)
unresolved = conn.execute(
    "SELECT COUNT(*) FROM press_event WHERE selected_response IS NULL"
).fetchone()[0]
assert unresolved == 0, f"{unresolved} press events left unresolved by harness"

# 4. Effect deltas applied
for event in conn.execute(
    "SELECT selected_response, delta_owner, delta_fan, delta_locker_room FROM press_event LIMIT 5"
):
    expected = PRESS_EFFECTS[event['selected_response']]
    assert event['delta_owner'] == expected['owner']
    assert event['delta_fan'] == expected['fan']
    assert event['delta_locker_room'] == expected['locker_room']

# 5. Autopilot setter + clear
set_autopilot_default(conn, player_coach_id, 'deflect')
val = conn.execute("SELECT press_autopilot_default FROM coach_career WHERE id=?",
                   (player_coach_id,)).fetchone()[0]
assert val == 'deflect'

set_autopilot_default(conn, player_coach_id, None)
val = conn.execute("SELECT press_autopilot_default FROM coach_career WHERE id=?",
                   (player_coach_id,)).fetchone()[0]
assert val is None

# 6. Invalid choice raises
try:
    set_autopilot_default(conn, player_coach_id, 'belligerent')
    assert False, "should have raised on invalid choice"
except ValueError:
    pass

# 7. Sentiment events tagged with 'presser' driver populated
n_presser_events = conn.execute(
    "SELECT COUNT(*) FROM sentiment_event WHERE driver='presser'"
).fetchone()[0]
assert n_presser_events > 0, "no sentiment_event rows with driver='presser'"
print(f"Sentiment events from pressers: {n_presser_events}")

# 8. Fan sentiment moved away from default (50) for the player team
player_team_id = conn.execute(
    "SELECT current_team_id FROM coach_career WHERE id=?", (player_coach_id,)
).fetchone()[0]
fan_sent = conn.execute(
    "SELECT fan_sentiment FROM team WHERE id=?", (player_team_id,)
).fetchone()[0]
print(f"Player team fan_sentiment after 3 seasons: {fan_sent}")
# Sanity: should have moved from 50, even if only slightly
# (Don't assert direction — depends on autopilot fallback choice and run outcomes)

print("Phase 4 prompt #5 verification passed.")
```

```bash
python verify_phase4_p5.py
```

### Step 3 — Interactive smoke test

```bash
rm -f saves/phase4_interactive.db
python generate.py saves/phase4_interactive.db --season 2024
python run_season.py saves/phase4_interactive.db --advance-week
```

Expected: after the week's games complete, you see the press conference prompt. Enter `1`, `2`, or `3`. Verify the effect summary printed. Try `a2` to set autopilot — next `--advance-week` should auto-resolve without prompting.

### Step 4 — Sample 5 templates per context

```bash
sqlite3 saves/phase4_v5.db "SELECT context_type, COUNT(*) FROM press_event GROUP BY context_type;"
```

Expected: contexts diverse (not 51 events all in one bucket). If one context dominates wildly, the detector may have a bug.

### Step 5 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #5 Tier 1 press conference (date)

Press events generated per 3-season harness run: {N}
Context distribution: {breakdown}
Autopilot fallback effect on owner sentiment trajectory: {observed delta}
Fan sentiment movement: {min, max, trajectory for player team}

Tuning notes:
- {any context types that fired too often or never}
- {dramatic templates that read flat}
```

### Step 6 — Update CLAUDE.md

```
- [x] Historical records module
- [x] Tier 1 weekly press conference + autopilot default
- [ ] Tier 2 event-triggered press conference
...
```

Add `src/transactions/press_conference.py`, `src/utils/press_templates.py`, `verify_phase4_p5.py` to the project structure map.

## Reference

- `docs/Phase4_DesignDecisions.md` §1.1 (tone — Tier 1 dry, Tier 2 dramatic), §1.3 (cadence — weekly during season), §5.3 (Tier 1 spec), §5.4 (fan sentiment derived stat), §5.5 (MVP scope boundary)
- `src/league/owner_sentiment.py` from prompt #4 — `update_sentiment(driver='presser', ...)` is the integration point
- `docs/Phase4_StressTest_BaselineFindings.md`
