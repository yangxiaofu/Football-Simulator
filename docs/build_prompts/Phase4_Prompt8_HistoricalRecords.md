# Phase 4 Build Prompt #8 — Historical Records Module

**Model**: Sonnet
**Planning mode**: Optional but recommended — small scope but multiple record categories; a short plan keeps the categorization complete.

---

## Context

Phase 4 prompts #1, #2, #2.5, #3, #4, and #7 are complete. The dynasty data layer is fully in place: coach identity, AI behavior, owner sentiment, hot seat, player reassignment, legacy scoring with multipliers, peer ranking, and narrative beats.

This prompt is the lowest-risk piece remaining. Pure read-only aggregation: a league record book, all-time stat leaderboards, and a richer champion history. After this, the data layer is complete and the remaining prompts (#5, #6, #9, #10) are content/UI/integration.

The narrative beat generator was already built in #7. This prompt does NOT touch that — it builds a separate, complementary historical records system that lives at the league level (most passing yards in league history) rather than the per-coach level (your tenure highlights).

**Read first**:
1. `CLAUDE.md`
2. `docs/Phase4_DesignDecisions.md` §7 prompt #8 line item
3. `src/db/schema.sql` — particularly the `box_score` (line 511), `player_season_stats` (line 589), `player_career_stats` (line 657), `team_season_record` (line 701), and `season` (line 55) tables
4. `src/league/narrative_beats.py` from prompt #7 — separate system; this prompt does not modify it

## Goal

Add three read-only systems on top of existing stats data:

1. **League record book**: one row per (category, scope) tracking the current single-game / single-season / career record holder for each major stat category. Updated at season end.
2. **All-time leaders**: leaderboard queries that return the top N for any stat category at any scope.
3. **Champion history**: enriched champion list with year, winner, runner-up, score, MVP, and head coach at the time.

Plus a small CLI inspection tool (`view_records.py`) so the records can be inspected from the terminal. The polished UI lives in #9.

**Critical scope discipline**: this prompt does NOT modify any existing stats writers, the narrative beat generator (#7), the AI behavior matrix (#3), or owner sentiment (#4). It reads from existing data and writes to new tables.

## Tasks

### Task 1 — Schema additions

Add to `src/db/schema.sql`:

```sql
-- League-wide records (one row per category × scope)
CREATE TABLE IF NOT EXISTS league_record (
    id                  INTEGER PRIMARY KEY,
    category            TEXT NOT NULL,         -- e.g. 'passing_yards', 'rushing_tds'
    scope               TEXT NOT NULL,         -- 'single_game' | 'single_season' | 'career'
    record_value        INTEGER NOT NULL,
    holder_player_id    INTEGER,               -- NULL for team or coach records
    holder_team_id      INTEGER,               -- NULL for player or coach records
    holder_coach_id     INTEGER,               -- NULL for player or team records
    season_year         INTEGER,               -- year the record was set
    week_number         INTEGER,               -- only for single_game scope
    set_at              TEXT,                  -- ISO timestamp when written to DB
    FOREIGN KEY (holder_player_id) REFERENCES player(id),
    FOREIGN KEY (holder_team_id) REFERENCES team(id),
    FOREIGN KEY (holder_coach_id) REFERENCES coach_career(id),
    UNIQUE(category, scope)
);

CREATE INDEX IF NOT EXISTS idx_league_record_category ON league_record(category, scope);

-- Champion history details (extends existing season table)
ALTER TABLE season ADD COLUMN runner_up_team_id INTEGER REFERENCES team(id);
ALTER TABLE season ADD COLUMN championship_home_score INTEGER;
ALTER TABLE season ADD COLUMN championship_away_score INTEGER;
ALTER TABLE season ADD COLUMN championship_mvp_player_id INTEGER REFERENCES player(id);
ALTER TABLE season ADD COLUMN championship_coach_id INTEGER REFERENCES coach_career(id);
```

Add `ensure_records_tables(conn)` migration helper in `src/db/connection.py` following the established pattern. Wire into the bootstrap.

### Task 2 — Constants: record category definitions

Add to `src/utils/constants.py` in a new "Phase 4 — Historical records" section:

```python
# === League record categories ===
# Each entry: (display_name, source_table, source_column)
LEAGUE_RECORD_CATEGORIES = {
    # Player records — passing
    'passing_yards':    ('Passing yards',    'pass_yards'),
    'passing_tds':      ('Passing TDs',      'pass_tds'),
    'completions':      ('Completions',      'completions'),
    'pass_attempts':    ('Pass attempts',    'pass_attempts'),

    # Player records — rushing
    'rushing_yards':    ('Rushing yards',    'rush_yards'),
    'rushing_tds':      ('Rushing TDs',      'rush_tds'),
    'rush_attempts':    ('Rush attempts',    'rush_attempts'),

    # Player records — receiving
    'receiving_yards':  ('Receiving yards',  'rec_yards'),
    'receptions':       ('Receptions',       'receptions'),
    'receiving_tds':    ('Receiving TDs',    'rec_tds'),

    # Player records — defense
    'sacks':            ('Sacks',            'sacks'),
    'interceptions':    ('Interceptions',    'interceptions'),
    'tackles':          ('Tackles',          'tackles'),

    # Player records — special teams
    'field_goals':      ('Field goals made', 'fg_made'),
    'fg_long':          ('Longest FG',       'fg_long'),
}

# Verify column names match what's actually in box_score and player_*_stats.
# Adjust to actual schema if any names differ.

LEAGUE_RECORD_SCOPES = ('single_game', 'single_season', 'career')

# === Team records ===
TEAM_RECORD_CATEGORIES = {
    'season_wins':        ('Most wins, season',     'team_season_record', 'wins'),
    'season_points_for':  ('Most points scored',    'team_season_record', 'points_for'),
    'season_w_pct':       ('Best W%, season',       'team_season_record', 'wins'),  # computed
}

# === Champion history display config ===
CHAMPION_HISTORY_DEFAULT_LIMIT = 25            # show last 25 champions by default

# === All-time leaders default ===
ALL_TIME_LEADERS_DEFAULT_TOP_N = 10
```

Verify the column names in `LEAGUE_RECORD_CATEGORIES` against the actual `box_score`, `player_season_stats`, and `player_career_stats` schemas. If any column name differs (e.g., `pass_yds` instead of `pass_yards`), adjust the mapping. Don't invent columns that don't exist.

### Task 3 — Record updater

Create `src/league/historical_records.py`:

```python
"""Phase 4 — Historical records module.

Tracks league-wide records (single-game, single-season, career) and provides
read API for leaderboards and champion history.

Per docs/Phase4_DesignDecisions.md §7 prompt #8.
"""
import sqlite3
from datetime import datetime
from src.utils.constants import (
    LEAGUE_RECORD_CATEGORIES, LEAGUE_RECORD_SCOPES,
    TEAM_RECORD_CATEGORIES,
    CHAMPION_HISTORY_DEFAULT_LIMIT, ALL_TIME_LEADERS_DEFAULT_TOP_N,
)


def update_league_records(conn: sqlite3.Connection, season_year: int) -> dict:
    """Scan stats tables at season end and update league_record rows where
    new records have been set.

    Process per category × scope:
      single_game:    SELECT MAX(value), player_id, game_id FROM box_score WHERE game's season = season_year
      single_season:  SELECT MAX(value), player_id FROM player_season_stats WHERE season_year = season_year
      career:         SELECT MAX(value), player_id FROM player_career_stats

    For each, compare against the existing league_record row. If new value
    exceeds existing record (or no record exists), update the row with
    new holder, value, season_year, week_number (single_game only), set_at.

    Returns dict {category: {scope: True/False}} of which records were broken
    this season — useful for downstream narrative.
    """
    ...


def update_champion_history(
    conn: sqlite3.Connection,
    season_year: int,
    champion_team_id: int,
    runner_up_team_id: int,
    home_score: int,
    away_score: int,
    mvp_player_id: int,
    coach_id: int,
) -> None:
    """Write the championship details for a completed season to the season
    table. Called by the playoffs system when the Super Bowl completes.

    For backfill of historical seasons that don't have these details (e.g.,
    save was generated before this prompt landed), values stay NULL — the
    UI handles missing data gracefully.
    """
    ...
```

### Task 4 — Read API

Add to `src/league/historical_records.py`:

```python
def get_record_book(
    conn: sqlite3.Connection,
    scope: str = None,
    category: str = None,
) -> list:
    """Return league records as a list of dicts.

    Filters:
      scope=None: all scopes
      scope='single_game': only game records
      ...
      category=None: all categories
      category='passing_yards': only passing yards records (one per scope)

    Each dict: {
        'category': 'passing_yards',
        'category_display': 'Passing yards',
        'scope': 'single_season',
        'record_value': 4823,
        'holder_player_id': 123,
        'holder_player_name': 'Patrick Williams',  # joined
        'holder_team_id': 5,
        'holder_team_abbr': 'CHI',                 # joined
        'season_year': 2026,
        'week_number': None,
    }
    """
    ...


def get_all_time_leaders(
    conn: sqlite3.Connection,
    category: str,
    scope: str = 'career',
    top_n: int = ALL_TIME_LEADERS_DEFAULT_TOP_N,
) -> list:
    """Return top N for a stat category at the given scope.

    For scope='career': read from player_career_stats
    For scope='single_season': read from player_season_stats (rows can repeat
        the same player across years, but each row is a distinct (player, year))
    For scope='single_game': read from box_score (each row is a distinct game)

    Returns list of dicts with player_id, player_name, team_abbr at time of stat,
    value, season_year (and week_number for single_game).

    Sorted descending by value.
    """
    ...


def get_champion_history(
    conn: sqlite3.Connection,
    n: int = CHAMPION_HISTORY_DEFAULT_LIMIT,
) -> list:
    """Return the last N completed seasons' champion details.

    Each row: {
        'season_year': 2025,
        'champion_team_id': 14,
        'champion_team_abbr': 'KC',
        'runner_up_team_id': 9,
        'runner_up_team_abbr': 'PHI',
        'final_score': '24-21',
        'mvp_player_id': 234,
        'mvp_player_name': 'Patrick Williams',
        'coach_id': 7,
        'coach_name': 'Bill Walsh',
    }

    Sorted descending by season_year (most recent first). For seasons missing
    runner_up / MVP / coach data (pre-prompt-#8 saves), those fields are None.
    """
    ...


def get_team_record_book(conn: sqlite3.Connection, team_id: int) -> dict:
    """Return team-specific franchise records (most wins in a season, most
    points scored, championships, longest playoff drought, etc.).

    Useful for #7's narrative beats that reference 'broke the franchise
    scoring record' — but #7 doesn't currently call this. Build the API
    so it's available for future use.
    """
    ...
```

### Task 5 — Hook into season transition

In `src/league/offseason.py`, add to the season transition flow (after `update_all_coach_legacy_scores` from #7, before the AI behavior phase classifier):

```python
from src.league.historical_records import update_league_records

# NEW Phase 4 work:
broken_records = update_league_records(conn, season_year)
# (Optional log) — useful for narrative integration in #6 Tier 2 pressers
```

In `src/league/playoffs.py` (or wherever the Super Bowl completes), add:

```python
from src.league.historical_records import update_champion_history

# After the Super Bowl game completes:
update_champion_history(
    conn, season_year,
    champion_team_id=...,
    runner_up_team_id=...,
    home_score=..., away_score=...,
    mvp_player_id=...,         # selected by existing awards.py logic
    coach_id=...,              # head coach of champion team (lookup via coach_career)
)
```

If MVP selection logic doesn't currently exist (or differs), use the player with the highest impact stat in the championship game (passing yards / rushing yards / receiving yards / sacks — pick whichever is highest). For MVP this is fine; refine post-launch.

### Task 6 — CLI inspection tool

Create `view_records.py` in the project root:

```python
"""Phase 4 — League records and history viewer.

Usage:
    python view_records.py saves/test.db                          # show all records
    python view_records.py saves/test.db --records                # record book only
    python view_records.py saves/test.db --leaders passing_yards  # all-time leaders for category
    python view_records.py saves/test.db --champions              # champion history
    python view_records.py saves/test.db --champions --limit 10   # last 10 champions
"""
import argparse
import sqlite3
from src.db.connection import get_connection
from src.league.historical_records import (
    get_record_book, get_all_time_leaders, get_champion_history,
)


def print_record_book(conn):
    """Print the league record book in three sections (game / season / career)."""
    print("=" * 70)
    print("LEAGUE RECORD BOOK")
    print("=" * 70)
    for scope in ('single_game', 'single_season', 'career'):
        records = get_record_book(conn, scope=scope)
        if not records:
            continue
        print(f"\n{scope.replace('_', ' ').upper()}")
        print("-" * 70)
        for r in records:
            holder = r.get('holder_player_name') or r.get('holder_team_abbr') or '—'
            year = r.get('season_year') or '—'
            print(f"  {r['category_display']:<22} {r['record_value']:>6}  {holder:<25} ({year})")


def print_leaders(conn, category, scope='career', top_n=10):
    print("=" * 70)
    print(f"ALL-TIME LEADERS — {category} ({scope})")
    print("=" * 70)
    leaders = get_all_time_leaders(conn, category, scope, top_n)
    for i, l in enumerate(leaders, 1):
        print(f"  {i:>2}. {l['player_name']:<25} {l['value']:>6} ({l['team_abbr']}, {l['season_year']})")


def print_champions(conn, limit):
    print("=" * 70)
    print("CHAMPION HISTORY")
    print("=" * 70)
    champs = get_champion_history(conn, n=limit)
    for c in champs:
        score = c.get('final_score') or '—'
        runner_up = c.get('runner_up_team_abbr') or '—'
        mvp = c.get('mvp_player_name') or '—'
        coach = c.get('coach_name') or '—'
        print(f"  {c['season_year']}  {c['champion_team_abbr']:<4} def. {runner_up:<4} {score}")
        print(f"        MVP: {mvp:<25}  Coach: {coach}")


def main():
    parser = argparse.ArgumentParser(description="Phase 4 historical records viewer")
    parser.add_argument('db_path')
    parser.add_argument('--records', action='store_true')
    parser.add_argument('--leaders', metavar='CATEGORY')
    parser.add_argument('--champions', action='store_true')
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--scope', default='career', choices=['single_game', 'single_season', 'career'])
    parser.add_argument('--top-n', type=int, default=10)

    args = parser.parse_args()
    conn = get_connection(args.db_path)

    # Default: show everything
    show_all = not (args.records or args.leaders or args.champions)
    if args.records or show_all:
        print_record_book(conn)
        print()
    if args.leaders:
        print_leaders(conn, args.leaders, args.scope, args.top_n)
        print()
    if args.champions or show_all:
        print_champions(conn, args.limit)


if __name__ == '__main__':
    main()
```

## Constraints — what NOT to touch

- Do NOT modify the existing stats writers (`src/engine/stats.py` or anything that writes to `box_score` / `player_season_stats` / `player_career_stats`).
- Do NOT modify the narrative beat generator from prompt #7 (`src/league/narrative_beats.py`). Records and narrative beats are complementary but separate.
- Do NOT modify the legacy scoring system from prompt #7 (`src/league/legacy.py`). This prompt reads stats data directly.
- Do NOT add UI beyond the CLI inspection tool. The polished display lives in #9.
- Do NOT modify the AI behavior matrix or owner sentiment systems.
- Do NOT add team-record narrative integration (e.g., "broke the franchise scoring record"). The team-record API exists for future use but is not wired into anything in this prompt.
- Do NOT backfill historical champion data for Super Bowls completed before this prompt landed — those rows will have NULL runner_up / MVP / coach values, and the read API handles that gracefully.

## Test plan

### Step 1 — No regression on existing harness

```bash
rm -f saves/phase4_v8.db
python generate.py saves/phase4_v8.db --season 2024
python run_stress_test.py saves/phase4_v8.db --invariants --seasons 3
```

Expected: still 12/12 invariants pass. New tables populated; new columns on `season` populated for the 3 simulated seasons.

### Step 2 — Inspect the records

```bash
python view_records.py saves/phase4_v8.db
```

Expected output: a record book with single-game, single-season, and career records populated for major stat categories; a champion history showing 3 entries (one per season) with team, runner-up, score, MVP, coach.

```bash
python view_records.py saves/phase4_v8.db --leaders passing_yards --scope career --top-n 5
```

Expected: top 5 career passing yards leaders.

### Step 3 — Verification script

Create `verify_phase4_p8.py`:

```python
"""Verification for Phase 4 Build Prompt #8 — Historical Records."""
import sqlite3
import sys

sys.path.insert(0, ".")
from src.league.historical_records import (
    get_record_book, get_all_time_leaders, get_champion_history,
)

DB = "saves/phase4_v8.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. Schema check
tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'league_record' in tables

cols = {r['name'] for r in conn.execute("PRAGMA table_info(season)")}
for c in ('runner_up_team_id', 'championship_home_score', 'championship_away_score',
          'championship_mvp_player_id', 'championship_coach_id'):
    assert c in cols, f"season.{c} column missing"

# 2. Records populated for the categories defined in constants
n_records = conn.execute("SELECT COUNT(*) FROM league_record").fetchone()[0]
print(f"Records tracked: {n_records}")
assert n_records >= 10, f"expected at least 10 records tracked, got {n_records}"

# 3. Each tracked record has a holder
unholdered = conn.execute("""
    SELECT category, scope FROM league_record
    WHERE holder_player_id IS NULL AND holder_team_id IS NULL AND holder_coach_id IS NULL
""").fetchall()
assert len(unholdered) == 0, f"records with no holder: {[dict(r) for r in unholdered]}"

# 4. Read API smoke tests
records = get_record_book(conn)
assert len(records) > 0, "get_record_book returned empty"

# Pick a category that should have leaders
leaders = get_all_time_leaders(conn, 'passing_yards', scope='career', top_n=5)
assert len(leaders) > 0, "no career passing yards leaders"
# Sorted descending
values = [l['value'] for l in leaders]
assert values == sorted(values, reverse=True), "leaders not sorted descending"

# 5. Champion history populated for completed seasons
champs = get_champion_history(conn, n=10)
n_completed = conn.execute("SELECT COUNT(*) FROM season WHERE is_complete=1").fetchone()[0]
assert len(champs) >= min(n_completed, 1), \
    f"expected at least {min(n_completed, 1)} champions, got {len(champs)}"

# 6. Each champion has a champion_team_abbr (the basic field)
for c in champs:
    assert c.get('champion_team_abbr'), f"champion missing team abbr: {c}"

print("Phase 4 prompt #8 verification passed.")
```

```bash
python verify_phase4_p8.py
```

### Step 4 — Document findings

Append to `docs/Phase4_StressTest_BaselineFindings.md`:

```markdown
## Update — Prompt #8 historical records (date)

Records populated: {N categories × 3 scopes}
Champion history coverage: {N seasons with full details vs. partial}

Sample records:
  Most passing yards (single-season): {value} by {player} ({team}, {year})
  Most career receptions: {value} by {player}

Tuning notes:
- {any record values that look unrealistic — e.g., "single-game passing yards of 142 suggests game sim is too low"}
```

If any record values look unrealistic, that's actually informative — it suggests the underlying game simulation may be undertuned for offensive output. Note for follow-up but don't fix in this prompt.

### Step 5 — Update CLAUDE.md

```
- [x] Legacy score expansion
- [x] Historical records module (record book, leaderboards, champion history, CLI viewer)
- [ ] Tier 1 weekly press conference + autopilot
...
```

Add `src/league/historical_records.py` and `view_records.py` to the project structure map.

## Reference

- `docs/Phase4_DesignDecisions.md` §7 prompt #8 line item
- `docs/Phase4_StressTest_BaselineFindings.md`
- `src/league/narrative_beats.py` from prompt #7 — separate system; NOT modified by this prompt
