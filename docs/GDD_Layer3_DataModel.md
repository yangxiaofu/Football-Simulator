# Football Simulator — Game Design Document
## Layer 3: Data Model

**Version:** 0.1 (Draft)
**Author:** David Dong
**Date:** May 9, 2026
**Status:** Working Draft
**Depends on:** GDD_Layer1_CoreDesign.md, GDD_Layer2_SimulationSpec.md, GDD_Layer2B_TransactionOffseason.md

---

## 1. Tech Stack Decision

### Language: Python 3.11+
- Claude Code's strongest language — ideal for AI-assisted development
- Built-in `sqlite3` module (no ORM needed for a game project)
- Deployable to Steam via PyInstaller (single executable + assets)
- Fast enough for text-based simulation loops; optimize hot paths later

### Database: SQLite
- Single `.db` file = the franchise save file
- Full relational SQL with foreign keys, indexes, and transactions
- Zero server setup — ships with the game executable
- The entire franchise lives in one portable file the player can back up, share, or copy

### Save File Structure
```
/Football Simulator/
├── saves/
│   └── {franchise_name}_{team_name}.db    ← the entire game state
├── assets/
│   └── (team logos, fonts, UI assets)
└── football_sim.exe
```

One `.db` file = one franchise. The player opens a franchise, plays, and the file is continuously updated via SQLite transactions. No separate save step needed — every committed action is permanent.

---

## 2. Entity Overview

The data model is organized into six domains:

| Domain | Entities |
|---|---|
| **League & Structure** | League, Conference, Division, Team, Season, Week |
| **People** | Player, Staff, Scout |
| **Contracts & Cap** | Contract, ContractYear, DraftPick |
| **Transactions** | Transaction, Trade, TradeAsset, FreeAgentOffer, WaiverClaim |
| **Games & Plays** | Game, Play, DriveLog, BoxScore |
| **Statistics & History** | PlayerSeasonStats, PlayerCareerStats, TeamSeasonStats, LegacyScore, HallOfFame |
| **Scouting** | DraftClass, Prospect, ScoutingReport, CombineResult |

---

## 3. Schema Definitions

### 3.1 League & Structure

---

#### `league`
The single top-level record describing the franchise world.

```sql
CREATE TABLE league (
    id                  INTEGER PRIMARY KEY,   -- always 1
    name                TEXT NOT NULL,
    current_season      INTEGER NOT NULL,      -- e.g. 2024
    current_week        INTEGER NOT NULL,      -- 0 = offseason
    current_phase       TEXT NOT NULL,         -- 'offseason' | 'preseason' | 'regular' | 'playoffs'
    salary_cap          INTEGER NOT NULL,      -- in dollars (e.g. 255000000)
    user_team_id        INTEGER NOT NULL,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_team_id) REFERENCES team(id)
);
```

---

#### `conference`
```sql
CREATE TABLE conference (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL   -- 'AFC', 'NFC'
);
```

---

#### `division`
```sql
CREATE TABLE division (
    id              INTEGER PRIMARY KEY,
    conference_id   INTEGER NOT NULL,
    name            TEXT NOT NULL,   -- 'AFC North', 'NFC West', etc.
    FOREIGN KEY (conference_id) REFERENCES conference(id)
);
```

---

#### `team`
```sql
CREATE TABLE team (
    id                  INTEGER PRIMARY KEY,
    division_id         INTEGER NOT NULL,
    city                TEXT NOT NULL,
    nickname            TEXT NOT NULL,
    abbreviation        TEXT NOT NULL,          -- 'CHI', 'DAL'
    gm_personality      TEXT NOT NULL,          -- 'draft_purist' | 'win_now' | 'analytics' | 'loyalty' | 'opportunist'
    prestige            INTEGER NOT NULL,        -- 1-99; affects FA interest tiers
    market_size         INTEGER NOT NULL,        -- 1-99; large = more FA appeal
    stadium_type        TEXT NOT NULL,           -- 'dome' | 'outdoor'
    home_city_climate   TEXT NOT NULL,           -- 'cold' | 'warm' | 'neutral'
    cap_space           INTEGER NOT NULL,        -- recalculated field; cached for performance
    waiver_priority     INTEGER NOT NULL,        -- 1-32; 1 = highest priority
    fan_sentiment       INTEGER NOT NULL DEFAULT 50,  -- 0-100
    FOREIGN KEY (division_id) REFERENCES division(id)
);
```

---

#### `season`
```sql
CREATE TABLE season (
    id              INTEGER PRIMARY KEY,
    year            INTEGER NOT NULL UNIQUE,
    salary_cap      INTEGER NOT NULL,
    champion_team_id INTEGER,
    is_complete     INTEGER NOT NULL DEFAULT 0,  -- boolean
    FOREIGN KEY (champion_team_id) REFERENCES team(id)
);
```

---

#### `week`
```sql
CREATE TABLE week (
    id          INTEGER PRIMARY KEY,
    season_id   INTEGER NOT NULL,
    week_number INTEGER NOT NULL,   -- 1-17 regular; 18-21 playoffs
    week_type   TEXT NOT NULL,      -- 'regular' | 'wildcard' | 'divisional' | 'conference' | 'superbowl'
    is_complete INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (season_id) REFERENCES season(id)
);
```

---

### 3.2 People

---

#### `player`
The central entity of the game. Contains identity, physical traits, true ratings, and meta-state.

```sql
CREATE TABLE player (
    id                  INTEGER PRIMARY KEY,
    team_id             INTEGER,               -- NULL = free agent
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    position            TEXT NOT NULL,         -- 'QB'|'RB'|'WR'|'TE'|'OL'|'DL'|'LB'|'CB'|'S'|'K'|'P'
    age                 INTEGER NOT NULL,
    years_experience    INTEGER NOT NULL DEFAULT 0,
    college             TEXT,
    draft_year          INTEGER,
    draft_round         INTEGER,
    draft_pick          INTEGER,

    -- True ratings (hidden from player; used by simulation engine)
    true_overall        INTEGER NOT NULL,      -- 1-99
    true_speed          INTEGER NOT NULL,
    true_strength       INTEGER NOT NULL,
    true_football_iq    INTEGER NOT NULL,
    true_durability     INTEGER NOT NULL,
    true_clutch         INTEGER NOT NULL,
    true_catch          INTEGER,               -- NULL for non-skill positions
    true_route_running  INTEGER,
    true_blocking       INTEGER,
    true_pass_rush      INTEGER,
    true_coverage_man   INTEGER,
    true_coverage_zone  INTEGER,
    true_tackling       INTEGER,
    true_accuracy_short INTEGER,               -- QB only
    true_accuracy_mid   INTEGER,
    true_accuracy_deep  INTEGER,
    true_pocket_presence INTEGER,
    true_arm_strength   INTEGER,
    true_elusiveness    INTEGER,
    true_vision         INTEGER,               -- RB only
    true_kick_accuracy  INTEGER,               -- K/P only
    true_kick_power     INTEGER,
    true_yac            INTEGER,

    -- Development ceiling (hidden)
    true_ceiling        INTEGER NOT NULL,      -- 1-99; max achievable overall
    development_trait   TEXT NOT NULL,         -- 'superstar' | 'star' | 'normal' | 'slow'

    -- State
    weekly_stamina      INTEGER NOT NULL DEFAULT 100,   -- 0-100; resets weekly
    season_wear         INTEGER NOT NULL DEFAULT 0,     -- accumulates from Week 10
    satisfaction        INTEGER NOT NULL DEFAULT 75,    -- 0-100; hidden from player
    is_active           INTEGER NOT NULL DEFAULT 1,     -- 0 = retired/cut/practice squad
    roster_status       TEXT NOT NULL DEFAULT 'active', -- 'active'|'ir'|'pup'|'practice_squad'|'free_agent'|'retired'
    injury_status       TEXT,                           -- NULL | 'questionable' | 'doubtful' | 'out'
    injury_weeks_remaining INTEGER DEFAULT 0,

    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX idx_player_team ON player(team_id);
CREATE INDEX idx_player_position ON player(position);
CREATE INDEX idx_player_roster_status ON player(roster_status);
```

---

#### `player_attribute_history`
Tracks how a player's true ratings change over time (development, aging, injury effects).

```sql
CREATE TABLE player_attribute_history (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    attribute_name  TEXT NOT NULL,    -- e.g. 'true_speed', 'true_overall'
    value_before    INTEGER NOT NULL,
    value_after     INTEGER NOT NULL,
    change_reason   TEXT NOT NULL,    -- 'development' | 'aging' | 'injury' | 'recovery'
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX idx_attr_history_player ON player_attribute_history(player_id, season_year);
```

---

#### `scouted_rating`
Stores what each scout (or your collective department) believes a player's ratings are. Separate from true ratings. Applies to both prospects and veterans.

```sql
CREATE TABLE scouted_rating (
    id                  INTEGER PRIMARY KEY,
    player_id           INTEGER,               -- NULL if prospect (not yet drafted)
    prospect_id         INTEGER,               -- NULL if active player
    scout_id            INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    attribute_name      TEXT NOT NULL,
    estimated_value     INTEGER NOT NULL,       -- scout's best guess (1-99)
    confidence_range    INTEGER NOT NULL,       -- ± this many points
    scout_grade         TEXT NOT NULL,          -- 'A+' through 'F' (derived from estimated_value)
    report_week         INTEGER NOT NULL,       -- which week of scouting this report was filed
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (prospect_id) REFERENCES prospect(id),
    FOREIGN KEY (scout_id) REFERENCES staff(id)
);

CREATE INDEX idx_scouted_player ON scouted_rating(player_id, season_year);
CREATE INDEX idx_scouted_prospect ON scouted_rating(prospect_id, season_year);
```

---

#### `staff`
Covers all non-player personnel: coaches, scouts, and front office.

```sql
CREATE TABLE staff (
    id                  INTEGER PRIMARY KEY,
    team_id             INTEGER,               -- NULL = available for hire
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    role                TEXT NOT NULL,         -- 'OC'|'DC'|'QB_coach'|'OL_coach'|'WR_coach'
                                               -- |'RB_coach'|'DB_coach'|'ST_coord'
                                               -- |'head_scout'|'regional_scout'|'fa_scout'
    -- Shared ratings (all staff)
    teaching_ability    INTEGER NOT NULL,      -- 1-99
    motivation          INTEGER NOT NULL,      -- 1-99
    loyalty             INTEGER NOT NULL,      -- 1-99; low = more likely to leave

    -- Coach-specific ratings
    scheme_expertise    TEXT,                  -- JSON: {'4_3': 85, 'zone': 72, ...}
    play_calling_iq     INTEGER,               -- OC/DC only
    disguise_rating     INTEGER,               -- DC only

    -- Scout-specific ratings
    talent_evaluation   INTEGER,
    regional_coverage   INTEGER,               -- max prospects trackable
    medical_eye         INTEGER,
    character_read      INTEGER,
    region              TEXT,                  -- regional scouts: 'midwest'|'southeast'|etc.

    years_experience    INTEGER NOT NULL DEFAULT 0,
    reputation          INTEGER NOT NULL DEFAULT 50,  -- affects hire cost

    FOREIGN KEY (team_id) REFERENCES team(id)
);
```

---

### 3.3 Contracts & Cap

---

#### `contract`
One record per player contract. A player has at most one active contract.

```sql
CREATE TABLE contract (
    id                  INTEGER PRIMARY KEY,
    player_id           INTEGER NOT NULL,
    team_id             INTEGER NOT NULL,
    status              TEXT NOT NULL,          -- 'active' | 'expired' | 'voided' | 'restructured'
    total_years         INTEGER NOT NULL,
    total_value         INTEGER NOT NULL,       -- total guaranteed + non-guaranteed
    signing_bonus       INTEGER NOT NULL DEFAULT 0,
    guaranteed_money    INTEGER NOT NULL DEFAULT 0,
    aav                 INTEGER NOT NULL,        -- total_value / total_years
    signed_season       INTEGER NOT NULL,
    void_year           INTEGER,                -- NULL if no void years
    is_franchise_tag    INTEGER NOT NULL DEFAULT 0,
    is_rookie_contract  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX idx_contract_player ON contract(player_id, status);
```

---

#### `contract_year`
One record per year of a contract. Handles the year-by-year structure including restructures and escalators.

```sql
CREATE TABLE contract_year (
    id                  INTEGER PRIMARY KEY,
    contract_id         INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    base_salary         INTEGER NOT NULL,
    prorated_bonus      INTEGER NOT NULL,       -- signing_bonus / total_years
    roster_bonus        INTEGER NOT NULL DEFAULT 0,
    cap_hit             INTEGER NOT NULL,        -- base_salary + prorated_bonus + roster_bonus
    dead_cap_value      INTEGER NOT NULL,        -- if cut this year, this hits the books
    is_void_year        INTEGER NOT NULL DEFAULT 0,
    escalator_trigger   TEXT,                   -- NULL or description of escalator condition
    escalator_amount    INTEGER DEFAULT 0,
    escalator_triggered INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (contract_id) REFERENCES contract(id)
);

CREATE INDEX idx_contract_year_season ON contract_year(season_year);
```

---

#### `draft_pick`
Tracks every draft pick owned by every team, including future picks acquired in trades.

```sql
CREATE TABLE draft_pick (
    id                  INTEGER PRIMARY KEY,
    owned_by_team_id    INTEGER NOT NULL,       -- current owner
    original_team_id    INTEGER NOT NULL,       -- team the pick came from
    season_year         INTEGER NOT NULL,
    round               INTEGER NOT NULL,       -- 1-7
    pick_number         INTEGER,                -- NULL until the season starts and order is set
    is_conditional      INTEGER NOT NULL DEFAULT 0,
    condition_description TEXT,                 -- human-readable condition if conditional
    condition_met       INTEGER,                -- NULL | 0 | 1
    traded              INTEGER NOT NULL DEFAULT 0,
    used                INTEGER NOT NULL DEFAULT 0,
    player_selected_id  INTEGER,                -- filled in after draft
    FOREIGN KEY (owned_by_team_id) REFERENCES team(id),
    FOREIGN KEY (original_team_id) REFERENCES team(id),
    FOREIGN KEY (player_selected_id) REFERENCES player(id)
);

CREATE INDEX idx_draft_pick_owner ON draft_pick(owned_by_team_id, season_year);
```

---

### 3.4 Transactions

---

#### `transaction_log`
Every roster and contract action is written here as an immutable audit trail.

```sql
CREATE TABLE transaction_log (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL,
    week_number     INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,            -- 'signed' | 'released' | 'traded' | 'drafted'
                                               -- | 'ir_placed' | 'ir_returned' | 'waiver_claimed'
                                               -- | 'practice_squad_signed' | 'practice_squad_released'
                                               -- | 'franchise_tagged' | 'retired' | 'restructured'
    team_id         INTEGER NOT NULL,
    player_id       INTEGER,
    description     TEXT NOT NULL,             -- human-readable log line
    cap_impact      INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX idx_txn_team_season ON transaction_log(team_id, season_year);
```

---

#### `satisfaction_event`
Tracks every satisfaction score change for audit and history. One record per delta applied.

```sql
CREATE TABLE satisfaction_event (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    week            INTEGER NOT NULL,
    delta           INTEGER NOT NULL,       -- change amount (+/-)
    reason          TEXT NOT NULL,           -- e.g. 'winning', 'underpaid', 'franchise_tag'
    new_score       INTEGER NOT NULL,        -- score AFTER the change (0-100)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX idx_satisfaction_event_player ON satisfaction_event(player_id, season_year);
```

---

#### `player_event`
Tracks actionable player events: holdouts, trade demands, interventions, and locker room contagion.

```sql
CREATE TABLE player_event (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    event_type      TEXT NOT NULL,           -- 'holdout' | 'trade_demand' | 'retirement_risk'
                                             -- | 'private_meeting' | 'extension_offer'
                                             -- | 'role_adjustment' | 'contagion'
    season_year     INTEGER NOT NULL,
    week            INTEGER NOT NULL,
    resolved        INTEGER NOT NULL DEFAULT 0,  -- 0 = active, 1 = resolved
    metadata_json   TEXT,                    -- JSON: intervention context, outcome, etc.
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX idx_player_event_player ON player_event(player_id, season_year);
CREATE INDEX idx_player_event_team ON player_event(team_id, season_year);
```

---

#### `trade`
```sql
CREATE TABLE trade (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL,
    week_number     INTEGER NOT NULL,
    team_a_id       INTEGER NOT NULL,
    team_b_id       INTEGER NOT NULL,
    status          TEXT NOT NULL,   -- 'completed' | 'rejected' | 'countered' | 'pending'
    initiated_by    TEXT NOT NULL,   -- 'user' | 'ai'
    FOREIGN KEY (team_a_id) REFERENCES team(id),
    FOREIGN KEY (team_b_id) REFERENCES team(id)
);
```

---

#### `trade_asset`
Each row is one asset moving in one direction within a trade.

```sql
CREATE TABLE trade_asset (
    id              INTEGER PRIMARY KEY,
    trade_id        INTEGER NOT NULL,
    from_team_id    INTEGER NOT NULL,
    to_team_id      INTEGER NOT NULL,
    asset_type      TEXT NOT NULL,   -- 'player' | 'pick'
    player_id       INTEGER,         -- NULL if pick
    draft_pick_id   INTEGER,         -- NULL if player
    FOREIGN KEY (trade_id) REFERENCES trade(id),
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (draft_pick_id) REFERENCES draft_pick(id)
);
```

---

#### `waiver_claim`
```sql
CREATE TABLE waiver_claim (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL,
    week_number     INTEGER NOT NULL,
    player_id       INTEGER NOT NULL,
    claiming_team_id INTEGER NOT NULL,
    claim_priority  INTEGER NOT NULL,   -- team's waiver priority at time of claim
    status          TEXT NOT NULL,      -- 'awarded' | 'denied'
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (claiming_team_id) REFERENCES team(id)
);
```

---

#### `free_agent_offer`
Tracks your active negotiations with free agents.

```sql
CREATE TABLE free_agent_offer (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    offering_team_id INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    round_number    INTEGER NOT NULL DEFAULT 1,    -- negotiation round
    years_offered   INTEGER NOT NULL,
    total_value     INTEGER NOT NULL,
    signing_bonus   INTEGER NOT NULL DEFAULT 0,
    guaranteed_money INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,    -- 'pending' | 'accepted' | 'countered' | 'rejected' | 'shopped'
    player_tier     INTEGER NOT NULL, -- 1, 2, or 3 (interest tier)
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (offering_team_id) REFERENCES team(id)
);
```

#### `fa_interest`
Tracks each free agent's destination preference for every team. Generated at the start of each offseason by `generate_fa_market()`. Preferences are scored 0.0–1.0 based on winning culture (30%), scheme fit (25%), role clarity (20%), market size (15%), and coach relationship (10%). Tier is assigned by rank: top 3 = Tier 1, 4-10 = Tier 2, 11-32 = Tier 3.

```sql
CREATE TABLE fa_interest (
    id                      INTEGER PRIMARY KEY,
    player_id               INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    season_year             INTEGER NOT NULL,
    preference_score        REAL NOT NULL,       -- 0.0 to 1.0 composite preference
    tier                    INTEGER NOT NULL,    -- 1, 2, or 3
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id)   REFERENCES team(id),
    UNIQUE(player_id, team_id, season_year)
);
CREATE INDEX idx_fa_interest_player ON fa_interest(player_id, season_year);
CREATE INDEX idx_fa_interest_team ON fa_interest(team_id, season_year);
```

---

#### `franchise_tag`
Tracks franchise and transition tag applications.

```sql
CREATE TABLE franchise_tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES player(id),
    team_id INTEGER NOT NULL REFERENCES team(id),
    season_year INTEGER NOT NULL,
    tag_type TEXT NOT NULL CHECK(tag_type IN ('exclusive', 'transition')),
    salary INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'signed_extension', 'rescinded')),
    consecutive_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(team_id, season_year, status)
);

CREATE INDEX idx_franchise_tag_player ON franchise_tag(player_id, season_year);
CREATE INDEX idx_franchise_tag_team ON franchise_tag(team_id, season_year, status);
```

**Constraints:**
- `UNIQUE(team_id, season_year, status)` — one active tag per team per season
- `CHECK(tag_type IN ('exclusive', 'transition'))`
- `CHECK(status IN ('active', 'signed_extension', 'rescinded'))`

**Indexes:**
- `idx_franchise_tag_player` on `(player_id, season_year)`
- `idx_franchise_tag_team` on `(team_id, season_year, status)`

**Status values:**
- `active` — tag is currently in effect
- `signed_extension` — player signed a long-term deal before tag year began
- `rescinded` — team withdrew the tag

**Consecutive count:**
- `1` for first tag, `2` for second consecutive, etc.
- Drives the salary multiplier (120% increase per consecutive tag)

**Tag types:**
- `exclusive` — player can only negotiate with your team; salary = average of top-5 cap hits at position
- `transition` — player can negotiate with other teams, but you have right of first refusal; salary = average of top-10 cap hits at position

---

### 3.5 Games & Plays

---

#### `game`
One record per scheduled game.

```sql
CREATE TABLE game (
    id                  INTEGER PRIMARY KEY,
    week_id             INTEGER NOT NULL,
    home_team_id        INTEGER NOT NULL,
    away_team_id        INTEGER NOT NULL,
    home_score          INTEGER,               -- NULL until played
    away_score          INTEGER,
    is_complete         INTEGER NOT NULL DEFAULT 0,
    weather_condition   TEXT,                  -- 'clear'|'wind'|'rain'|'snow'|'cold'|'extreme_cold'
    wind_speed          INTEGER DEFAULT 0,     -- mph
    temperature         INTEGER DEFAULT 65,    -- Fahrenheit
    precipitation       INTEGER NOT NULL DEFAULT 0,  -- boolean
    home_field_modifier INTEGER NOT NULL DEFAULT 3,   -- SAR bonus for home team
    FOREIGN KEY (week_id) REFERENCES week(id),
    FOREIGN KEY (home_team_id) REFERENCES team(id),
    FOREIGN KEY (away_team_id) REFERENCES team(id)
);

CREATE INDEX idx_game_week ON game(week_id);
CREATE INDEX idx_game_teams ON game(home_team_id, away_team_id);
```

---

#### `play`
One record per snap. **Current season only** — archived after season end (see §5).

```sql
CREATE TABLE play (
    id                  INTEGER PRIMARY KEY,
    game_id             INTEGER NOT NULL,
    play_number         INTEGER NOT NULL,      -- sequence within the game
    quarter             INTEGER NOT NULL,
    time_remaining      INTEGER NOT NULL,      -- seconds
    possession_team_id  INTEGER NOT NULL,
    field_position      INTEGER NOT NULL,      -- yards from own end zone (1-99)
    down                INTEGER NOT NULL,
    distance            INTEGER NOT NULL,
    home_score          INTEGER NOT NULL,
    away_score          INTEGER NOT NULL,

    -- Play type
    play_type           TEXT NOT NULL,         -- 'pass'|'run'|'fg_attempt'|'punt'|'kickoff'|'extra_point'|'two_point'|'kneel'|'spike'
    is_penalty          INTEGER NOT NULL DEFAULT 0,
    penalty_type        TEXT,
    penalty_team_id     INTEGER,

    -- Outcome
    yards_gained        INTEGER,
    result              TEXT NOT NULL,         -- 'complete'|'incomplete'|'sack'|'td'|'int'
                                               -- |'fumble'|'fg_good'|'fg_miss'|'punt'|'run'|'scramble'
    is_touchdown        INTEGER NOT NULL DEFAULT 0,
    is_turnover         INTEGER NOT NULL DEFAULT 0,
    is_big_play         INTEGER NOT NULL DEFAULT 0,  -- 20+ yard gain

    -- Key players involved
    primary_player_id   INTEGER,               -- ball carrier, QB, or kicker
    target_player_id    INTEGER,               -- receiver on pass plays
    defender_player_id  INTEGER,               -- primary defender

    -- Matchup resolution outputs (used for stat generation)
    pocket_time_grade   TEXT,                  -- 'clean'|'disrupted'|'collapsed'
    separation_yards    REAL,
    clutch_activated    INTEGER NOT NULL DEFAULT 0,

    -- Narration
    narration_text      TEXT NOT NULL,         -- the play-by-play string shown to player

    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (possession_team_id) REFERENCES team(id),
    FOREIGN KEY (primary_player_id) REFERENCES player(id),
    FOREIGN KEY (target_player_id) REFERENCES player(id),
    FOREIGN KEY (defender_player_id) REFERENCES player(id)
);

CREATE INDEX idx_play_game ON play(game_id, play_number);
CREATE INDEX idx_play_bigplay ON play(game_id, is_big_play);
```

---

#### `box_score`
Permanent record of each player's game-level statistics. Persists after play log is archived.

```sql
CREATE TABLE box_score (
    id              INTEGER PRIMARY KEY,
    game_id         INTEGER NOT NULL,
    player_id       INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,

    -- Passing
    pass_attempts   INTEGER NOT NULL DEFAULT 0,
    completions     INTEGER NOT NULL DEFAULT 0,
    pass_yards      INTEGER NOT NULL DEFAULT 0,
    pass_tds        INTEGER NOT NULL DEFAULT 0,
    interceptions_thrown INTEGER NOT NULL DEFAULT 0,
    sacks_taken     INTEGER NOT NULL DEFAULT 0,

    -- Rushing
    carries         INTEGER NOT NULL DEFAULT 0,
    rush_yards      INTEGER NOT NULL DEFAULT 0,
    rush_tds        INTEGER NOT NULL DEFAULT 0,
    fumbles         INTEGER NOT NULL DEFAULT 0,

    -- Receiving
    targets         INTEGER NOT NULL DEFAULT 0,
    receptions      INTEGER NOT NULL DEFAULT 0,
    rec_yards       INTEGER NOT NULL DEFAULT 0,
    rec_tds         INTEGER NOT NULL DEFAULT 0,

    -- Defense
    tackles         INTEGER NOT NULL DEFAULT 0,
    sacks           REAL NOT NULL DEFAULT 0,     -- can be 0.5
    interceptions   INTEGER NOT NULL DEFAULT 0,
    pass_deflections INTEGER NOT NULL DEFAULT 0,
    forced_fumbles  INTEGER NOT NULL DEFAULT 0,

    -- Kicking
    fg_attempts     INTEGER NOT NULL DEFAULT 0,
    fg_made         INTEGER NOT NULL DEFAULT 0,
    fg_long         INTEGER NOT NULL DEFAULT 0,
    xp_attempts     INTEGER NOT NULL DEFAULT 0,
    xp_made         INTEGER NOT NULL DEFAULT 0,
    punts           INTEGER NOT NULL DEFAULT 0,
    punt_yards      INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX idx_box_score_game ON box_score(game_id);
CREATE INDEX idx_box_score_player ON box_score(player_id);
```

---

#### `key_play`
The 5–10 highlight plays preserved permanently per game after the play log is archived.

```sql
CREATE TABLE key_play (
    id              INTEGER PRIMARY KEY,
    game_id         INTEGER NOT NULL,
    play_number     INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    time_remaining  INTEGER NOT NULL,
    result          TEXT NOT NULL,
    yards_gained    INTEGER,
    narration_text  TEXT NOT NULL,
    primary_player_id INTEGER,
    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (primary_player_id) REFERENCES player(id)
);
```

---

### 3.6 Statistics & History

---

#### `player_season_stats`
Aggregated stats per player per season. Computed from box_score records at season end.

```sql
CREATE TABLE player_season_stats (
    id                      INTEGER PRIMARY KEY,
    player_id               INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    season_year             INTEGER NOT NULL,
    games_played            INTEGER NOT NULL DEFAULT 0,
    games_started           INTEGER NOT NULL DEFAULT 0,

    -- Passing
    pass_attempts           INTEGER NOT NULL DEFAULT 0,
    completions             INTEGER NOT NULL DEFAULT 0,
    pass_yards              INTEGER NOT NULL DEFAULT 0,
    pass_tds                INTEGER NOT NULL DEFAULT 0,
    interceptions_thrown    INTEGER NOT NULL DEFAULT 0,
    passer_rating           REAL,              -- computed field

    -- Rushing
    carries                 INTEGER NOT NULL DEFAULT 0,
    rush_yards              INTEGER NOT NULL DEFAULT 0,
    rush_tds                INTEGER NOT NULL DEFAULT 0,
    yards_per_carry         REAL,

    -- Receiving
    targets                 INTEGER NOT NULL DEFAULT 0,
    receptions              INTEGER NOT NULL DEFAULT 0,
    rec_yards               INTEGER NOT NULL DEFAULT 0,
    rec_tds                 INTEGER NOT NULL DEFAULT 0,
    catch_percentage        REAL,

    -- Defense
    tackles                 INTEGER NOT NULL DEFAULT 0,
    sacks                   REAL NOT NULL DEFAULT 0,
    interceptions           INTEGER NOT NULL DEFAULT 0,
    pass_deflections        INTEGER NOT NULL DEFAULT 0,

    -- Kicking
    fg_made                 INTEGER NOT NULL DEFAULT 0,
    fg_attempts             INTEGER NOT NULL DEFAULT 0,
    fg_percentage           REAL,

    -- Awards (set at season end)
    made_pro_bowl           INTEGER NOT NULL DEFAULT 0,
    made_all_pro            INTEGER NOT NULL DEFAULT 0,
    won_mvp                 INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(player_id, season_year)
);
```

---

#### `player_career_stats`
Running career totals. Updated at the end of each season.

```sql
CREATE TABLE player_career_stats (
    id                      INTEGER PRIMARY KEY,
    player_id               INTEGER NOT NULL UNIQUE,
    seasons_played          INTEGER NOT NULL DEFAULT 0,
    teams_played_for        INTEGER NOT NULL DEFAULT 0,  -- count of distinct teams

    -- Career totals (same stat columns as season stats, omitted for brevity)
    -- All same columns as player_season_stats but career aggregated
    career_pass_yards       INTEGER NOT NULL DEFAULT 0,
    career_pass_tds         INTEGER NOT NULL DEFAULT 0,
    career_rush_yards       INTEGER NOT NULL DEFAULT 0,
    career_rush_tds         INTEGER NOT NULL DEFAULT 0,
    career_rec_yards        INTEGER NOT NULL DEFAULT 0,
    career_rec_tds          INTEGER NOT NULL DEFAULT 0,
    career_sacks            REAL NOT NULL DEFAULT 0,
    career_interceptions    INTEGER NOT NULL DEFAULT 0,
    career_fg_made          INTEGER NOT NULL DEFAULT 0,
    career_pro_bowls        INTEGER NOT NULL DEFAULT 0,
    career_all_pro          INTEGER NOT NULL DEFAULT 0,
    peak_overall            INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id)
);
```

---

#### `team_season_record`
Win/loss record and standings data per team per season.

```sql
CREATE TABLE team_season_record (
    id                  INTEGER PRIMARY KEY,
    team_id             INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    wins                INTEGER NOT NULL DEFAULT 0,
    losses              INTEGER NOT NULL DEFAULT 0,
    ties                INTEGER NOT NULL DEFAULT 0,
    points_for          INTEGER NOT NULL DEFAULT 0,
    points_against      INTEGER NOT NULL DEFAULT 0,
    made_playoffs       INTEGER NOT NULL DEFAULT 0,
    playoff_result      TEXT,                -- NULL | 'wildcard' | 'divisional' | 'conference' | 'superbowl_loss' | 'champion'
    draft_position      INTEGER,             -- final pick position (set post-season)
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(team_id, season_year)
);
```

---

#### `legacy_score`
Tracks the user's franchise legacy over time.

```sql
CREATE TABLE legacy_score (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL UNIQUE,
    championships           INTEGER NOT NULL DEFAULT 0,   -- career total
    conference_titles       INTEGER NOT NULL DEFAULT 0,
    career_win_pct          REAL NOT NULL DEFAULT 0,
    stars_developed         INTEGER NOT NULL DEFAULT 0,   -- players developed from C or below to A
    cap_efficiency_score    INTEGER NOT NULL DEFAULT 50,  -- 0-100
    seasons_coached         INTEGER NOT NULL DEFAULT 0,
    media_legacy_score      INTEGER NOT NULL DEFAULT 50,

    -- Composite
    total_legacy_score      INTEGER NOT NULL DEFAULT 0,
    is_dynasty              INTEGER NOT NULL DEFAULT 0,   -- 3+ SBs in 10-season window
    hof_eligible            INTEGER NOT NULL DEFAULT 0
);
```

---

#### `hall_of_fame`
```sql
CREATE TABLE hall_of_fame (
    id                  INTEGER PRIMARY KEY,
    player_id           INTEGER,
    staff_id            INTEGER,
    inducted_season     INTEGER NOT NULL,
    induction_speech    TEXT,                -- generated narrative
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (staff_id) REFERENCES staff(id)
);
```

---

### 3.7 Scouting Domain

---

#### `draft_class`
One record per year's draft class — the pool of generated prospects.

```sql
CREATE TABLE draft_class (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL UNIQUE,
    class_strength  TEXT NOT NULL,   -- 'weak' | 'average' | 'strong' | 'historic'
    class_notes     TEXT             -- e.g. "QB-rich class", "deep defensive class"
);
```

---

#### `prospect`
A college player eligible for the draft. Becomes a `player` record upon being drafted.

```sql
CREATE TABLE prospect (
    id                  INTEGER PRIMARY KEY,
    draft_class_id      INTEGER NOT NULL,
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    position            TEXT NOT NULL,
    age                 INTEGER NOT NULL,
    college             TEXT NOT NULL,
    college_conference  TEXT NOT NULL,      -- 'SEC'|'Big Ten'|'ACC'|'Pac-12'|'Big 12'|'G5'

    -- True ratings (hidden)
    true_overall        INTEGER NOT NULL,
    true_ceiling        INTEGER NOT NULL,
    development_trait   TEXT NOT NULL,

    -- All position-relevant true attribute columns (same as player table)
    true_speed          INTEGER NOT NULL,
    true_strength       INTEGER NOT NULL,
    true_football_iq    INTEGER NOT NULL,
    true_durability     INTEGER NOT NULL,
    true_clutch         INTEGER NOT NULL,
    -- (position-specific attributes follow same pattern as player table)

    -- Flags (generated at creation, revealed progressively)
    has_injury_history  INTEGER NOT NULL DEFAULT 0,
    injury_history_desc TEXT,
    has_character_flag  INTEGER NOT NULL DEFAULT 0,
    character_flag_desc TEXT,

    -- Combine results (set during combine phase)
    combine_forty       REAL,          -- 40-yard dash time
    combine_bench       INTEGER,       -- bench press reps
    combine_vertical    REAL,          -- vertical jump inches
    combine_wonderlic   INTEGER,       -- interview/intelligence score (1-50)
    combine_attended    INTEGER NOT NULL DEFAULT 0,

    -- Draft result
    was_drafted         INTEGER NOT NULL DEFAULT 0,
    drafted_by_team_id  INTEGER,
    draft_round         INTEGER,
    draft_pick          INTEGER,
    player_id           INTEGER,       -- set after drafting; links to the created player record

    FOREIGN KEY (draft_class_id) REFERENCES draft_class(id),
    FOREIGN KEY (drafted_by_team_id) REFERENCES team(id),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX idx_prospect_class ON prospect(draft_class_id, position);
```

---

#### `scouting_assignment`
Tracks which scouts are assigned to which prospects each week.

```sql
CREATE TABLE scouting_assignment (
    id              INTEGER PRIMARY KEY,
    scout_id        INTEGER NOT NULL,
    prospect_id     INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    week_assigned   INTEGER NOT NULL,
    week_completed  INTEGER,           -- NULL if still in progress
    hours_invested  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (scout_id) REFERENCES staff(id),
    FOREIGN KEY (prospect_id) REFERENCES prospect(id)
);
```

---

#### `mock_draft`
Generated weekly during the pre-draft period. Represents public consensus, not your private board.

```sql
CREATE TABLE mock_draft (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL,
    published_week  INTEGER NOT NULL,
    pick_number     INTEGER NOT NULL,
    prospect_id     INTEGER NOT NULL,
    mocking_to_team_id INTEGER NOT NULL,
    FOREIGN KEY (prospect_id) REFERENCES prospect(id),
    FOREIGN KEY (mocking_to_team_id) REFERENCES team(id)
);
```

---

## 4. Key Relationships Summary

```
league (1) ──── (1) team [user_team]
team (1) ──── (many) player
team (1) ──── (many) staff
team (1) ──── (many) draft_pick [owned_by]
player (1) ──── (1) contract [active]
contract (1) ──── (many) contract_year
player (1) ──── (many) player_season_stats
player (1) ──── (1) player_career_stats
player (1) ──── (many) scouted_rating
game (1) ──── (many) play [current season only]
game (1) ──── (many) box_score [permanent]
game (1) ──── (many) key_play [permanent]
prospect (1) ──── (many) scouted_rating
prospect (1) ──── (1) player [after draft]
draft_class (1) ──── (many) prospect
trade (1) ──── (many) trade_asset
```

---

## 5. Season Archival Process

At the end of each season, the game runs a **season archive job** before advancing to the next year. This keeps the database size manageable without losing historical context.

### Archive Steps (run in order):

```
1. Compute player_season_stats from box_score records for the completed season
2. Update player_career_stats with the new season totals
3. Select top 8 plays per game (by impact) → insert into key_play
4. DELETE all play records for the completed season
5. Compute team_season_record final standings
6. Run player development pass (update true ratings based on age, usage, coaching)
7. Run aging pass (apply age-based attribute decay to players 29+)
8. Update legacy_score for the user's franchise
9. Generate new draft_class for the upcoming season
10. Reset weekly_stamina to 100 for all players
11. Reset season_wear to 0 for all players
12. Advance league.current_season + 1
```

This process runs once and takes under a second. The `play` table drops from ~80,000 rows (500 games × 160 plays) to zero. The `key_play` table retains ~4,000 rows (500 games × 8 highlights). All statistical history is preserved in `box_score`, `player_season_stats`, and `player_career_stats`.

---

## 6. Performance Considerations

### Indexes
Critical indexes are defined inline above. The most important for simulation performance:
- `idx_play_game` — play retrieval during live game simulation
- `idx_player_team` — roster loading
- `idx_contract_year_season` — cap calculation (runs constantly)

### Cap Calculation
The `team.cap_space` column is a **cached value** — it's not computed live. It's recalculated and written to the database whenever any contract, trade, or roster action occurs. This avoids summing `contract_year` rows on every UI render.

```python
def recalculate_cap_space(team_id, season_year, conn):
    result = conn.execute("""
        SELECT league.salary_cap - COALESCE(SUM(cy.cap_hit), 0)
        FROM league, contract c
        JOIN contract_year cy ON cy.contract_id = c.id
        WHERE c.team_id = ? AND cy.season_year = ? AND c.status = 'active'
    """, (team_id, season_year)).fetchone()
    conn.execute("UPDATE team SET cap_space = ? WHERE id = ?",
                 (result[0], team_id))
```

### Simulation Loop
The play-resolution engine runs entirely in-memory during a game. No database writes occur mid-game — plays are batched and inserted in a single transaction after the game completes. This keeps the simulation loop fast and the database writes clean.

---

## 7. Data Model Design Rules

1. **True ratings are never sent to the UI layer.** The application layer always fetches scouted ratings or translated letter grades — never raw true values. This enforces the information fog at the code level, not just in design.

2. **Every roster and contract action writes to `transaction_log`.** This gives you a full audit trail for the franchise history and makes the transaction ticker (the UI log of recent moves) trivially easy to build.

3. **The `play` table is ephemeral; `box_score` is permanent.** Never build a feature that queries `play` for historical stats — that table may not exist for past seasons. All historical queries go through `player_season_stats` or `player_career_stats`.

4. **Cap space is always cached, never computed live.** Recalculate on every transaction, never on every render.

5. **Prospects and players are separate tables.** A prospect becomes a player upon being drafted — at that point a `player` record is created and `prospect.player_id` is set. This separation keeps the draft class clean and avoids polluting the active player roster with undrafted prospects.

---

*Next: Layer 4 — Feature Roadmap (prioritized list from MVP to v1.0 to future releases)*
