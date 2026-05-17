-- Football Simulator — SQLite Database Schema
-- Version: 0.1
-- Based on: GDD_Layer3_DataModel.md
-- Date: May 9, 2026

-- Enable foreign key constraints (must be set per connection)
PRAGMA foreign_keys = ON;

-- ====================
-- 1. LEAGUE & STRUCTURE
-- ====================

-- The single top-level record describing the franchise world
CREATE TABLE IF NOT EXISTS league (
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

CREATE TABLE IF NOT EXISTS conference (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL   -- 'AFC', 'NFC'
);

CREATE TABLE IF NOT EXISTS division (
    id              INTEGER PRIMARY KEY,
    conference_id   INTEGER NOT NULL,
    name            TEXT NOT NULL,   -- 'AFC North', 'NFC West', etc.
    FOREIGN KEY (conference_id) REFERENCES conference(id)
);

CREATE TABLE IF NOT EXISTS team (
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
    team_phase          TEXT NOT NULL DEFAULT 'bridge', -- 'rebuild' | 'bridge' | 'contend' | 'win_now' | 'decline'
    FOREIGN KEY (division_id) REFERENCES division(id)
);

CREATE TABLE IF NOT EXISTS season (
    id              INTEGER PRIMARY KEY,
    year            INTEGER NOT NULL UNIQUE,
    salary_cap      INTEGER NOT NULL,
    champion_team_id INTEGER,
    is_complete     INTEGER NOT NULL DEFAULT 0,  -- boolean
    runner_up_team_id INTEGER,
    championship_home_score INTEGER,
    championship_away_score INTEGER,
    championship_mvp_player_id INTEGER,
    championship_coach_id INTEGER,
    recap_shown             INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (champion_team_id) REFERENCES team(id),
    FOREIGN KEY (runner_up_team_id) REFERENCES team(id),
    FOREIGN KEY (championship_mvp_player_id) REFERENCES player(id),
    FOREIGN KEY (championship_coach_id) REFERENCES coach_career(id)
);

CREATE TABLE IF NOT EXISTS week (
    id          INTEGER PRIMARY KEY,
    season_id   INTEGER NOT NULL,
    week_number INTEGER NOT NULL,   -- 1-17 regular; 18-21 playoffs
    week_type   TEXT NOT NULL,      -- 'regular' | 'wildcard' | 'divisional' | 'conference' | 'superbowl'
    is_complete INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (season_id) REFERENCES season(id)
);

-- ====================
-- 2. PEOPLE
-- ====================

-- The central entity of the game. Contains identity, physical traits, true ratings, and meta-state.
CREATE TABLE IF NOT EXISTS player (
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
    is_watchlisted      INTEGER NOT NULL DEFAULT 0,      -- GUI FA watchlist flag (Phase 6 P7b)

    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_player_team ON player(team_id);
CREATE INDEX IF NOT EXISTS idx_player_position ON player(position);
CREATE INDEX IF NOT EXISTS idx_player_roster_status ON player(roster_status);

-- Tracks how a player's true ratings change over time (development, aging, injury effects)
CREATE TABLE IF NOT EXISTS player_attribute_history (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    attribute_name  TEXT NOT NULL,    -- e.g. 'true_speed', 'true_overall'
    value_before    INTEGER NOT NULL,
    value_after     INTEGER NOT NULL,
    change_reason   TEXT NOT NULL,    -- 'development' | 'aging' | 'injury' | 'recovery'
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX IF NOT EXISTS idx_attr_history_player ON player_attribute_history(player_id, season_year);

-- Stores what each scout believes a player's ratings are. Separate from true ratings.
-- Applies to both prospects and veterans.
CREATE TABLE IF NOT EXISTS scouted_rating (
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
    phase               TEXT,                  -- 'early'|'midseason'|'combine'|'predraft'
    notes               TEXT,                  -- phase-specific scouting narrative
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (prospect_id) REFERENCES prospect(id),
    FOREIGN KEY (scout_id) REFERENCES staff(id)
);

CREATE INDEX IF NOT EXISTS idx_scouted_player ON scouted_rating(player_id, season_year);
CREATE INDEX IF NOT EXISTS idx_scouted_prospect ON scouted_rating(prospect_id, season_year);

-- Covers all non-player personnel: coaches, scouts, and front office
CREATE TABLE IF NOT EXISTS staff (
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

-- ====================
-- 3. CONTRACTS & CAP
-- ====================

-- One record per player contract. A player has at most one active contract.
CREATE TABLE IF NOT EXISTS contract (
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

CREATE INDEX IF NOT EXISTS idx_contract_player ON contract(player_id, status);

-- One record per year of a contract. Handles year-by-year structure including restructures and escalators.
CREATE TABLE IF NOT EXISTS contract_year (
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

CREATE INDEX IF NOT EXISTS idx_contract_year_season ON contract_year(season_year);

-- Tracks every draft pick owned by every team, including future picks acquired in trades
CREATE TABLE IF NOT EXISTS draft_pick (
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

CREATE INDEX IF NOT EXISTS idx_draft_pick_owner ON draft_pick(owned_by_team_id, season_year);

-- Draft event sequence — tracks the live draft as it unfolds
CREATE TABLE IF NOT EXISTS draft_state (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    season_year         INTEGER NOT NULL,
    pick_number_overall INTEGER NOT NULL,
    round               INTEGER NOT NULL,
    pick_in_round       INTEGER NOT NULL,
    team_id             INTEGER NOT NULL REFERENCES team(id),
    original_team_id    INTEGER NOT NULL REFERENCES team(id),
    prospect_id         INTEGER REFERENCES prospect(id),
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','used','traded')),
    war_room_reaction   TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(season_year, pick_number_overall)
);
CREATE INDEX IF NOT EXISTS idx_draft_state_season ON draft_state(season_year, status);

-- ====================
-- 4. TRANSACTIONS
-- ====================

-- Every roster and contract action is written here as an immutable audit trail
CREATE TABLE IF NOT EXISTS transaction_log (
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

CREATE INDEX IF NOT EXISTS idx_txn_team_season ON transaction_log(team_id, season_year);

-- Tracks every satisfaction score change for audit and history
CREATE TABLE IF NOT EXISTS satisfaction_event (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    week            INTEGER NOT NULL,
    delta           INTEGER NOT NULL,       -- change amount (+/-)
    reason          TEXT NOT NULL,           -- e.g. 'winning', 'underpaid', 'franchise_tag'
    new_score       INTEGER NOT NULL,        -- score AFTER the change (0-100)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    -- Phase 5 P8 additions (applied via ensure_satisfaction_tables migration):
    --   ALTER TABLE satisfaction_event ADD COLUMN reason_code TEXT;
    FOREIGN KEY (player_id) REFERENCES player(id)
);

CREATE INDEX IF NOT EXISTS idx_satisfaction_event_player ON satisfaction_event(player_id, season_year);

-- Tracks actionable player events (holdouts, trade demands, interventions, contagion)
CREATE TABLE IF NOT EXISTS player_event (
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

CREATE INDEX IF NOT EXISTS idx_player_event_player ON player_event(player_id, season_year);
CREATE INDEX IF NOT EXISTS idx_player_event_team ON player_event(team_id, season_year);

-- Phase 5 Prompt #3: Explicit depth chart for user-controlled lineup management
CREATE TABLE IF NOT EXISTS depth_chart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    position_slot TEXT NOT NULL,  -- 'QB', 'RB', 'WR1', 'WR2', 'LT', 'MLB', 'CB1', etc.
    slot_order INTEGER NOT NULL,  -- 1=starter, 2=backup1, 3=backup2
    player_id INTEGER NOT NULL,
    is_user_set INTEGER NOT NULL DEFAULT 0,  -- 0=auto-filled, 1=user explicitly chose
    replaced_player_id INTEGER,  -- Original starter when auto-promoted due to injury
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES player(id) ON DELETE CASCADE,
    FOREIGN KEY (replaced_player_id) REFERENCES player(id) ON DELETE SET NULL,
    UNIQUE(team_id, season_year, position_slot, slot_order)  -- One player per slot
);

CREATE INDEX IF NOT EXISTS idx_depth_chart_team_season ON depth_chart(team_id, season_year);
CREATE INDEX IF NOT EXISTS idx_depth_chart_player ON depth_chart(player_id);
CREATE INDEX IF NOT EXISTS idx_depth_chart_position ON depth_chart(team_id, season_year, position_slot);

CREATE TABLE IF NOT EXISTS trade (
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

-- Each row is one asset moving in one direction within a trade
CREATE TABLE IF NOT EXISTS trade_asset (
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

CREATE TABLE IF NOT EXISTS waiver_claim (
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

-- Tracks active negotiations with free agents
CREATE TABLE IF NOT EXISTS free_agent_offer (
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

-- Tracks each free agent's destination preference for every team
CREATE TABLE IF NOT EXISTS fa_interest (
    id                      INTEGER PRIMARY KEY,
    player_id               INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    season_year             INTEGER NOT NULL,
    preference_score        REAL NOT NULL,
    tier                    INTEGER NOT NULL,       -- 1, 2, or 3
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id)   REFERENCES team(id),
    UNIQUE(player_id, team_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_fa_interest_player ON fa_interest(player_id, season_year);
CREATE INDEX IF NOT EXISTS idx_fa_interest_team ON fa_interest(team_id, season_year);
-- Phase 5 P7 additions (applied via ensure_fa_tables migration):
--   ALTER TABLE fa_interest ADD COLUMN outcome_narrative TEXT;
--   ALTER TABLE fa_interest ADD COLUMN reason_code TEXT;

-- Tracks franchise tag applications
CREATE TABLE IF NOT EXISTS franchise_tag (
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

CREATE INDEX IF NOT EXISTS idx_franchise_tag_player ON franchise_tag(player_id, season_year);
CREATE INDEX IF NOT EXISTS idx_franchise_tag_team ON franchise_tag(team_id, season_year, status);

-- ====================
-- 5. GAMES & PLAYS
-- ====================

-- One record per scheduled game
CREATE TABLE IF NOT EXISTS game (
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

CREATE INDEX IF NOT EXISTS idx_game_week ON game(week_id);
CREATE INDEX IF NOT EXISTS idx_game_teams ON game(home_team_id, away_team_id);

-- One record per snap. CURRENT SEASON ONLY — archived after season end
CREATE TABLE IF NOT EXISTS play (
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

CREATE INDEX IF NOT EXISTS idx_play_game ON play(game_id, play_number);
CREATE INDEX IF NOT EXISTS idx_play_bigplay ON play(game_id, is_big_play);

-- Permanent record of each player's game-level statistics. Persists after play log is archived.
CREATE TABLE IF NOT EXISTS box_score (
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

    -- Return stats
    punt_returns INTEGER DEFAULT 0,
    punt_return_yards INTEGER DEFAULT 0,
    punt_return_tds INTEGER DEFAULT 0,
    kick_returns INTEGER DEFAULT 0,
    kick_return_yards INTEGER DEFAULT 0,
    kick_return_tds INTEGER DEFAULT 0,

    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_box_score_game ON box_score(game_id);
CREATE INDEX IF NOT EXISTS idx_box_score_player ON box_score(player_id);

-- The 5–10 highlight plays preserved permanently per game after the play log is archived
CREATE TABLE IF NOT EXISTS key_play (
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

-- ====================
-- 6. STATISTICS & HISTORY
-- ====================

-- Aggregated stats per player per season. Computed from box_score records at season end.
CREATE TABLE IF NOT EXISTS player_season_stats (
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

    -- Missing stats from box_score that should aggregate to season level
    sacks_taken             INTEGER DEFAULT 0,
    fumbles                 INTEGER DEFAULT 0,
    punts                   INTEGER DEFAULT 0,
    punt_yards              INTEGER DEFAULT 0,
    xp_attempts             INTEGER DEFAULT 0,
    xp_made                 INTEGER DEFAULT 0,
    fg_long                 INTEGER DEFAULT 0,

    -- Return stats
    punt_returns            INTEGER DEFAULT 0,
    punt_return_yards       INTEGER DEFAULT 0,
    punt_return_tds         INTEGER DEFAULT 0,
    kick_returns            INTEGER DEFAULT 0,
    kick_return_yards       INTEGER DEFAULT 0,
    kick_return_tds         INTEGER DEFAULT 0,

    -- Awards (set at season end)
    made_pro_bowl           INTEGER NOT NULL DEFAULT 0,
    made_all_pro            INTEGER NOT NULL DEFAULT 0,
    won_mvp                 INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(player_id, season_year)
);

-- Running career totals. Updated at the end of each season.
CREATE TABLE IF NOT EXISTS player_career_stats (
    id                      INTEGER PRIMARY KEY,
    player_id               INTEGER NOT NULL UNIQUE,
    seasons_played          INTEGER NOT NULL DEFAULT 0,
    teams_played_for        INTEGER NOT NULL DEFAULT 0,  -- count of distinct teams

    -- Career totals
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

    -- Missing career totals that should mirror season stats
    career_pass_attempts    INTEGER DEFAULT 0,
    career_completions      INTEGER DEFAULT 0,
    career_carries          INTEGER DEFAULT 0,
    career_receptions       INTEGER DEFAULT 0,
    career_targets          INTEGER DEFAULT 0,
    career_tackles          INTEGER DEFAULT 0,
    career_pass_deflections INTEGER DEFAULT 0,
    career_forced_fumbles   INTEGER DEFAULT 0,
    career_fumbles          INTEGER DEFAULT 0,
    career_sacks_taken      INTEGER DEFAULT 0,

    -- Career return totals
    career_punt_returns     INTEGER DEFAULT 0,
    career_punt_return_yards INTEGER DEFAULT 0,
    career_punt_return_tds  INTEGER DEFAULT 0,
    career_kick_returns     INTEGER DEFAULT 0,
    career_kick_return_yards INTEGER DEFAULT 0,
    career_kick_return_tds  INTEGER DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id)
);

-- Win/loss record and standings data per team per season
CREATE TABLE IF NOT EXISTS team_season_record (
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

-- Tracks the user's franchise legacy over time
CREATE TABLE IF NOT EXISTS legacy_score (
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
    hof_eligible            INTEGER NOT NULL DEFAULT 0,

    -- Coach identity (Phase 4)
    coach_id                INTEGER,
    FOREIGN KEY (coach_id) REFERENCES coach_career(id)
);

CREATE TABLE IF NOT EXISTS hall_of_fame (
    id                  INTEGER PRIMARY KEY,
    player_id           INTEGER,
    staff_id            INTEGER,
    coach_id            INTEGER,             -- Phase 4: coach identity
    inducted_season     INTEGER NOT NULL,
    induction_speech    TEXT,                -- generated narrative
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (staff_id) REFERENCES staff(id),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id)
);

-- ====================
-- 7. SCOUTING DOMAIN
-- ====================

-- One record per year's draft class — the pool of generated prospects
CREATE TABLE IF NOT EXISTS draft_class (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL UNIQUE,
    class_strength  TEXT NOT NULL,   -- 'weak' | 'average' | 'strong' | 'historic'
    class_notes     TEXT             -- e.g. "QB-rich class", "deep defensive class"
);

-- A college player eligible for the draft. Becomes a player record upon being drafted.
CREATE TABLE IF NOT EXISTS prospect (
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
    true_catch          INTEGER,
    true_route_running  INTEGER,
    true_blocking       INTEGER,
    true_pass_rush      INTEGER,
    true_coverage_man   INTEGER,
    true_coverage_zone  INTEGER,
    true_tackling       INTEGER,
    true_accuracy_short INTEGER,
    true_accuracy_mid   INTEGER,
    true_accuracy_deep  INTEGER,
    true_pocket_presence INTEGER,
    true_arm_strength   INTEGER,
    true_elusiveness    INTEGER,
    true_vision         INTEGER,
    true_kick_accuracy  INTEGER,
    true_kick_power     INTEGER,
    true_yac            INTEGER,

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

CREATE INDEX IF NOT EXISTS idx_prospect_class ON prospect(draft_class_id, position);

-- Tracks which scouts are assigned to which prospects each week
CREATE TABLE IF NOT EXISTS scouting_assignment (
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

-- Generated weekly during the pre-draft period. Represents public consensus, not your private board.
CREATE TABLE IF NOT EXISTS mock_draft (
    id              INTEGER PRIMARY KEY,
    season_year     INTEGER NOT NULL,
    published_week  INTEGER NOT NULL,
    pick_number     INTEGER NOT NULL,
    prospect_id     INTEGER NOT NULL,
    mocking_to_team_id INTEGER NOT NULL,
    narrative           TEXT,                  -- mock draft narrative context
    FOREIGN KEY (prospect_id) REFERENCES prospect(id),
    FOREIGN KEY (mocking_to_team_id) REFERENCES team(id)
);

CREATE TABLE IF NOT EXISTS combine_event (
    id              INTEGER PRIMARY KEY,
    prospect_id     INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    event_type      TEXT NOT NULL,
    narrative       TEXT NOT NULL,
    grade_impact    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (prospect_id) REFERENCES prospect(id)
);
CREATE INDEX IF NOT EXISTS idx_combine_event_prospect ON combine_event(prospect_id, season_year);

CREATE TABLE IF NOT EXISTS competitor_intel (
    id              INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL,
    prospect_id     INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    narrative       TEXT NOT NULL,
    is_accurate     INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (prospect_id) REFERENCES prospect(id)
);
CREATE INDEX IF NOT EXISTS idx_competitor_intel_prospect ON competitor_intel(prospect_id, season_year);

CREATE TABLE IF NOT EXISTS draft_board (
    id              INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL,
    prospect_id     INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    board_rank      REAL NOT NULL,
    board_override  INTEGER,
    phase_trend     TEXT NOT NULL DEFAULT 'stable'
        CHECK(phase_trend IN ('improving','stable','declining')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (prospect_id) REFERENCES prospect(id),
    UNIQUE(team_id, season_year, prospect_id)
);
CREATE INDEX IF NOT EXISTS idx_draft_board_team ON draft_board(team_id, season_year);

-- Tracks per-team offseason progress through phase sequence
CREATE TABLE IF NOT EXISTS offseason_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES team(id),
    season_year INTEGER NOT NULL,
    current_phase TEXT NOT NULL CHECK(current_phase IN (
        'end_of_season_review', 'staff_evaluation', 'franchise_tag_window',
        'scouting_early', 'combine', 'free_agency', 'predraft',
        'draft', 'training_camp', 'season_ready'
    )),
    end_of_season_review_complete INTEGER NOT NULL DEFAULT 0,
    staff_evaluation_complete INTEGER NOT NULL DEFAULT 0,
    franchise_tag_window_complete INTEGER NOT NULL DEFAULT 0,
    scouting_early_complete INTEGER NOT NULL DEFAULT 0,
    combine_complete INTEGER NOT NULL DEFAULT 0,
    free_agency_complete INTEGER NOT NULL DEFAULT 0,
    predraft_complete INTEGER NOT NULL DEFAULT 0,
    draft_complete INTEGER NOT NULL DEFAULT 0,
    training_camp_complete INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(team_id, season_year)
);
CREATE INDEX IF NOT EXISTS idx_offseason_state_team ON offseason_state(team_id, season_year);

-- ====================
-- 8. COACH IDENTITY (Phase 4)
-- ====================

CREATE TABLE IF NOT EXISTS coach_career (
    id                    INTEGER PRIMARY KEY,
    first_name            TEXT NOT NULL,
    last_name             TEXT NOT NULL,
    age                   INTEGER NOT NULL,
    personality_archetype TEXT NOT NULL,
    career_start_year     INTEGER NOT NULL,
    current_team_id       INTEGER,
    is_player             INTEGER NOT NULL DEFAULT 0,
    is_active             INTEGER NOT NULL DEFAULT 1,
    press_autopilot_default TEXT,  -- NULL = prompt every week, else 'deflect'|'accountable'|'confrontational'
    FOREIGN KEY (current_team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_coach_career_active ON coach_career(is_active, is_player);
CREATE INDEX IF NOT EXISTS idx_coach_career_team ON coach_career(current_team_id);

CREATE TABLE IF NOT EXISTS coach_tenure (
    id              INTEGER PRIMARY KEY,
    coach_id        INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    start_year      INTEGER NOT NULL,
    end_year        INTEGER,
    end_reason      TEXT,
    starting_condition_multiplier REAL NOT NULL DEFAULT 1.0,  -- Phase 4 Prompt #7
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_coach_tenure_coach ON coach_tenure(coach_id, end_year);

-- ====================
-- 9. OWNER SENTIMENT & JOB OFFERS (Phase 4 Prompt #4)
-- ====================

-- Owner sentiment tracking (one row per team per season)
CREATE TABLE IF NOT EXISTS owner_sentiment (
    id                      INTEGER PRIMARY KEY,
    team_id                 INTEGER NOT NULL,
    season_year             INTEGER NOT NULL,
    sentiment_score         INTEGER NOT NULL DEFAULT 70,
    preseason_expectation   TEXT,  -- 'rebuild'|'competitive'|'playoff'|'championship'
    hot_seat_tier           TEXT NOT NULL DEFAULT 'stable',

    -- Driver breakdowns (for inspection/tuning)
    wins_vs_expectation     INTEGER NOT NULL DEFAULT 0,
    cap_management_score    INTEGER NOT NULL DEFAULT 0,
    star_holdout_penalty    INTEGER NOT NULL DEFAULT 0,
    playoff_bonus           INTEGER NOT NULL DEFAULT 0,
    championship_bonus      INTEGER NOT NULL DEFAULT 0,
    presser_delta           INTEGER NOT NULL DEFAULT 0,

    -- Phase 5 P8 additions (applied via ensure_owner_sentiment_tables migration):
    --   ALTER TABLE owner_sentiment ADD COLUMN reason_code TEXT;
    --   ALTER TABLE owner_sentiment ADD COLUMN reason_detail TEXT;
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(team_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_owner_sentiment_team ON owner_sentiment(team_id, season_year);

-- Job offers during vacancy (player coach only)
CREATE TABLE IF NOT EXISTS coach_job_offer (
    id                  INTEGER PRIMARY KEY,
    coach_id            INTEGER NOT NULL,
    team_id             INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    week_offered        INTEGER NOT NULL,
    offer_quality_tier  TEXT NOT NULL,  -- 'elite'|'good'|'average'|'struggling'
    is_accepted         INTEGER NOT NULL DEFAULT 0,
    is_declined         INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id)
);

CREATE INDEX IF NOT EXISTS idx_coach_job_offer_coach ON coach_job_offer(coach_id);

-- ====================
-- 10. COACH LEGACY EXPANSION (Phase 4 Prompt #7)
-- ====================

-- Per-coach, per-season legacy snapshot
CREATE TABLE IF NOT EXISTS coach_legacy_score (
    id                              INTEGER PRIMARY KEY,
    coach_id                        INTEGER NOT NULL,
    season_year                     INTEGER NOT NULL,
    team_id                         INTEGER NOT NULL,

    -- Six base factors (mirror existing legacy.py weights)
    championships                   INTEGER NOT NULL DEFAULT 0,
    conference_titles               INTEGER NOT NULL DEFAULT 0,
    season_win_pct                  REAL NOT NULL DEFAULT 0,
    stars_developed                 INTEGER NOT NULL DEFAULT 0,
    cap_efficiency_score            INTEGER NOT NULL DEFAULT 50,
    media_legacy_score              INTEGER NOT NULL DEFAULT 50,

    -- Phase 4 multipliers
    era_difficulty_multiplier       REAL NOT NULL DEFAULT 1.0,
    starting_condition_multiplier   REAL NOT NULL DEFAULT 1.0,

    -- Computed season contribution
    season_legacy_score             INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(coach_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_coach_legacy_coach ON coach_legacy_score(coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_legacy_season ON coach_legacy_score(season_year);

-- End-of-season narrative beats
CREATE TABLE IF NOT EXISTS coach_narrative_beat (
    id              INTEGER PRIMARY KEY,
    coach_id        INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    beat_type       TEXT NOT NULL,  -- 'routine' | 'dramatic' | 'dynasty_milestone' | 'hof_eligible'
    text            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(coach_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_coach_narrative_coach ON coach_narrative_beat(coach_id);

-- ====================
-- 10. TIER 1 PRESS CONFERENCE (Phase 4 Prompt #5)
-- ====================

-- Weekly press conference events (one per team per week during regular season)
CREATE TABLE IF NOT EXISTS press_event (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    week_number             INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    coach_id                INTEGER NOT NULL,
    context_type            TEXT NOT NULL,
    question_template_id    TEXT NOT NULL,
    selected_response       TEXT,                    -- 'deflect' | 'accountable' | 'confrontational'
    autopilot_used          INTEGER NOT NULL DEFAULT 0,
    delta_owner             INTEGER NOT NULL DEFAULT 0,
    delta_fan               INTEGER NOT NULL DEFAULT 0,
    delta_locker_room       INTEGER NOT NULL DEFAULT 0,
    resolved_at             TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    template_id             TEXT,                    -- Phase 5 P9: written at resolve time for LRU anti-repetition
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(season_year, week_number, team_id)
);

CREATE INDEX IF NOT EXISTS idx_press_event_team ON press_event(team_id, season_year);

-- ====================
-- 10b. TIER 2 DRAMATIC PRESS CONFERENCE (Phase 4 Prompt #6)
-- ====================

-- One row per dramatic event (2-3 questions per event)
CREATE TABLE IF NOT EXISTS tier2_press_event (
    id                  INTEGER PRIMARY KEY,
    season_year         INTEGER NOT NULL,
    week_number         INTEGER NOT NULL,
    team_id             INTEGER NOT NULL,
    coach_id            INTEGER NOT NULL,
    trigger_type        TEXT NOT NULL,
    template_id         TEXT NOT NULL,
    num_questions       INTEGER NOT NULL,
    resolved_at         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id)
);

CREATE INDEX IF NOT EXISTS idx_tier2_press_event_team ON tier2_press_event(team_id, season_year);

-- One row per question within a Tier 2 event (2-3 per event)
CREATE TABLE IF NOT EXISTS tier2_press_response (
    id                  INTEGER PRIMARY KEY,
    event_id            INTEGER NOT NULL,
    question_index      INTEGER NOT NULL,
    question_text       TEXT NOT NULL,
    selected_response   TEXT,           -- 'deflect' | 'accountable' | 'confrontational'
    delta_owner         INTEGER NOT NULL DEFAULT 0,
    delta_fan           INTEGER NOT NULL DEFAULT 0,
    delta_locker_room   INTEGER NOT NULL DEFAULT 0,
    resolved_at         TEXT,
    FOREIGN KEY (event_id) REFERENCES tier2_press_event(id)
);

CREATE INDEX IF NOT EXISTS idx_tier2_press_response_event ON tier2_press_response(event_id);

-- Deduplication guard: prevents same trigger from firing repeatedly
CREATE TABLE IF NOT EXISTS tier2_trigger_guard (
    id              INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    trigger_type    TEXT NOT NULL,
    guard_key       TEXT NOT NULL,
    fired_week      INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(team_id, season_year, trigger_type, guard_key)
);

CREATE INDEX IF NOT EXISTS idx_tier2_trigger_guard_team ON tier2_trigger_guard(team_id, season_year);

-- Cached peer ranking snapshots
CREATE TABLE IF NOT EXISTS peer_ranking_snapshot (
    id                  INTEGER PRIMARY KEY,
    coach_id            INTEGER NOT NULL,
    season_year         INTEGER NOT NULL,
    career_legacy_total INTEGER NOT NULL,
    active_rank         INTEGER NOT NULL,
    all_time_rank       INTEGER NOT NULL,
    n_active            INTEGER NOT NULL,
    n_all_time          INTEGER NOT NULL,
    FOREIGN KEY (coach_id) REFERENCES coach_career(id),
    UNIQUE(coach_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_peer_ranking_season ON peer_ranking_snapshot(season_year, active_rank);

-- ====================
-- 11. HISTORICAL RECORDS (Phase 4 Prompt #8)
-- ====================

-- League-wide records (one row per category × scope)
CREATE TABLE IF NOT EXISTS league_record (
    id                  INTEGER PRIMARY KEY,
    category            TEXT NOT NULL,         -- e.g. 'passing_yards', 'rushing_tds'
    scope               TEXT NOT NULL,         -- 'single_game' | 'single_season' | 'career'
    record_value        REAL NOT NULL,         -- REAL for stats like sacks (0.5 increments)
    holder_player_id    INTEGER,               -- NULL for team/coach records
    holder_team_id      INTEGER,               -- NULL for player/coach records
    holder_coach_id     INTEGER,               -- NULL for player/team records
    holder_name         TEXT NOT NULL,         -- denormalized for historical accuracy
    season_year         INTEGER,               -- year the record was set
    week_number         INTEGER,               -- only for single_game scope
    set_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (holder_player_id) REFERENCES player(id),
    FOREIGN KEY (holder_team_id) REFERENCES team(id),
    FOREIGN KEY (holder_coach_id) REFERENCES coach_career(id),
    UNIQUE(category, scope)
);

CREATE INDEX IF NOT EXISTS idx_league_record_category ON league_record(category, scope);

-- ====================
-- 12. NARRATIVE MOMENT TRACKING (Phase 4 Prompt #9)
-- ====================

CREATE TABLE IF NOT EXISTS narrative_moment_shown (
    coach_id        INTEGER NOT NULL,
    moment_type     TEXT NOT NULL,        -- 'dynasty' | 'hof_eligible'
    shown_season    INTEGER NOT NULL,
    PRIMARY KEY (coach_id, moment_type),
    FOREIGN KEY (coach_id) REFERENCES coach_career(id)
);

-- ====================
-- 13. WEEKLY STATS CACHE (Phase 5)
-- ====================

-- Per-player per-week snapshot (ephemeral, deleted at season archive)
CREATE TABLE IF NOT EXISTS player_week_stats (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    week_number             INTEGER NOT NULL,
    player_id               INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    is_playoff              INTEGER NOT NULL DEFAULT 0,

    -- Passing
    pass_attempts           INTEGER NOT NULL DEFAULT 0,
    completions             INTEGER NOT NULL DEFAULT 0,
    pass_yards              INTEGER NOT NULL DEFAULT 0,
    pass_tds                INTEGER NOT NULL DEFAULT 0,
    interceptions_thrown    INTEGER NOT NULL DEFAULT 0,
    sacks_taken             INTEGER NOT NULL DEFAULT 0,

    -- Rushing
    carries                 INTEGER NOT NULL DEFAULT 0,
    rush_yards              INTEGER NOT NULL DEFAULT 0,
    rush_tds                INTEGER NOT NULL DEFAULT 0,
    fumbles                 INTEGER NOT NULL DEFAULT 0,

    -- Receiving
    targets                 INTEGER NOT NULL DEFAULT 0,
    receptions              INTEGER NOT NULL DEFAULT 0,
    rec_yards               INTEGER NOT NULL DEFAULT 0,
    rec_tds                 INTEGER NOT NULL DEFAULT 0,

    -- Defense
    tackles                 INTEGER NOT NULL DEFAULT 0,
    sacks                   REAL NOT NULL DEFAULT 0,
    interceptions           INTEGER NOT NULL DEFAULT 0,
    pass_deflections        INTEGER NOT NULL DEFAULT 0,
    forced_fumbles          INTEGER NOT NULL DEFAULT 0,

    -- Kicking
    fg_attempts             INTEGER NOT NULL DEFAULT 0,
    fg_made                 INTEGER NOT NULL DEFAULT 0,
    fg_long                 INTEGER NOT NULL DEFAULT 0,
    xp_attempts             INTEGER NOT NULL DEFAULT 0,
    xp_made                 INTEGER NOT NULL DEFAULT 0,
    punts                   INTEGER NOT NULL DEFAULT 0,
    punt_yards              INTEGER NOT NULL DEFAULT 0,

    -- Returns
    punt_returns            INTEGER NOT NULL DEFAULT 0,
    punt_return_yards       INTEGER NOT NULL DEFAULT 0,
    punt_return_tds         INTEGER NOT NULL DEFAULT 0,
    kick_returns            INTEGER NOT NULL DEFAULT 0,
    kick_return_yards       INTEGER NOT NULL DEFAULT 0,
    kick_return_tds         INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(season_year, week_number, player_id, is_playoff)
);

CREATE INDEX IF NOT EXISTS idx_player_week_stats_week ON player_week_stats(season_year, week_number, is_playoff);
CREATE INDEX IF NOT EXISTS idx_player_week_stats_player ON player_week_stats(player_id, season_year);

-- Running season totals (live cache, updated incrementally)
CREATE TABLE IF NOT EXISTS player_season_running (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    player_id               INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    is_playoff              INTEGER NOT NULL DEFAULT 0,
    games_played            INTEGER NOT NULL DEFAULT 0,

    -- Passing
    pass_attempts           INTEGER NOT NULL DEFAULT 0,
    completions             INTEGER NOT NULL DEFAULT 0,
    pass_yards              INTEGER NOT NULL DEFAULT 0,
    pass_tds                INTEGER NOT NULL DEFAULT 0,
    interceptions_thrown    INTEGER NOT NULL DEFAULT 0,
    sacks_taken             INTEGER NOT NULL DEFAULT 0,

    -- Rushing
    carries                 INTEGER NOT NULL DEFAULT 0,
    rush_yards              INTEGER NOT NULL DEFAULT 0,
    rush_tds                INTEGER NOT NULL DEFAULT 0,
    fumbles                 INTEGER NOT NULL DEFAULT 0,

    -- Receiving
    targets                 INTEGER NOT NULL DEFAULT 0,
    receptions              INTEGER NOT NULL DEFAULT 0,
    rec_yards               INTEGER NOT NULL DEFAULT 0,
    rec_tds                 INTEGER NOT NULL DEFAULT 0,

    -- Defense
    tackles                 INTEGER NOT NULL DEFAULT 0,
    sacks                   REAL NOT NULL DEFAULT 0,
    interceptions           INTEGER NOT NULL DEFAULT 0,
    pass_deflections        INTEGER NOT NULL DEFAULT 0,
    forced_fumbles          INTEGER NOT NULL DEFAULT 0,

    -- Kicking
    fg_attempts             INTEGER NOT NULL DEFAULT 0,
    fg_made                 INTEGER NOT NULL DEFAULT 0,
    fg_long                 INTEGER NOT NULL DEFAULT 0,
    xp_attempts             INTEGER NOT NULL DEFAULT 0,
    xp_made                 INTEGER NOT NULL DEFAULT 0,
    punts                   INTEGER NOT NULL DEFAULT 0,
    punt_yards              INTEGER NOT NULL DEFAULT 0,

    -- Returns
    punt_returns            INTEGER NOT NULL DEFAULT 0,
    punt_return_yards       INTEGER NOT NULL DEFAULT 0,
    punt_return_tds         INTEGER NOT NULL DEFAULT 0,
    kick_returns            INTEGER NOT NULL DEFAULT 0,
    kick_return_yards       INTEGER NOT NULL DEFAULT 0,
    kick_return_tds         INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(season_year, player_id, is_playoff)
);

CREATE INDEX IF NOT EXISTS idx_player_season_running_player ON player_season_running(player_id, season_year);
CREATE INDEX IF NOT EXISTS idx_player_season_running_pass_yards ON player_season_running(season_year, is_playoff, pass_yards DESC);
CREATE INDEX IF NOT EXISTS idx_player_season_running_rush_yards ON player_season_running(season_year, is_playoff, rush_yards DESC);
CREATE INDEX IF NOT EXISTS idx_player_season_running_rec_yards ON player_season_running(season_year, is_playoff, rec_yards DESC);
CREATE INDEX IF NOT EXISTS idx_player_season_running_tackles ON player_season_running(season_year, is_playoff, tackles DESC);
CREATE INDEX IF NOT EXISTS idx_player_season_running_sacks ON player_season_running(season_year, is_playoff, sacks DESC);

-- Per-team per-week snapshot (ephemeral)
CREATE TABLE IF NOT EXISTS team_week_stats (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    week_number             INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    is_playoff              INTEGER NOT NULL DEFAULT 0,

    -- Offensive stats
    points_scored           INTEGER NOT NULL DEFAULT 0,
    total_yards             INTEGER NOT NULL DEFAULT 0,
    pass_yards              INTEGER NOT NULL DEFAULT 0,
    rush_yards              INTEGER NOT NULL DEFAULT 0,
    turnovers               INTEGER NOT NULL DEFAULT 0,
    third_down_conversions  INTEGER NOT NULL DEFAULT 0,
    third_down_attempts     INTEGER NOT NULL DEFAULT 0,

    -- Defensive stats
    points_allowed          INTEGER NOT NULL DEFAULT 0,
    yards_allowed           INTEGER NOT NULL DEFAULT 0,
    sacks_recorded          REAL NOT NULL DEFAULT 0,
    takeaways               INTEGER NOT NULL DEFAULT 0,

    -- Game result
    won                     INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(season_year, week_number, team_id, is_playoff)
);

CREATE INDEX IF NOT EXISTS idx_team_week_stats_week ON team_week_stats(season_year, week_number, is_playoff);
CREATE INDEX IF NOT EXISTS idx_team_week_stats_team ON team_week_stats(team_id, season_year);

-- Running team totals (live cache)
CREATE TABLE IF NOT EXISTS team_season_running (
    id                      INTEGER PRIMARY KEY,
    season_year             INTEGER NOT NULL,
    team_id                 INTEGER NOT NULL,
    is_playoff              INTEGER NOT NULL DEFAULT 0,
    games_played            INTEGER NOT NULL DEFAULT 0,

    -- Offensive stats
    points_scored           INTEGER NOT NULL DEFAULT 0,
    total_yards             INTEGER NOT NULL DEFAULT 0,
    pass_yards              INTEGER NOT NULL DEFAULT 0,
    rush_yards              INTEGER NOT NULL DEFAULT 0,
    turnovers               INTEGER NOT NULL DEFAULT 0,
    third_down_conversions  INTEGER NOT NULL DEFAULT 0,
    third_down_attempts     INTEGER NOT NULL DEFAULT 0,

    -- Defensive stats
    points_allowed          INTEGER NOT NULL DEFAULT 0,
    yards_allowed           INTEGER NOT NULL DEFAULT 0,
    sacks_recorded          REAL NOT NULL DEFAULT 0,
    takeaways               INTEGER NOT NULL DEFAULT 0,

    -- Record
    wins                    INTEGER NOT NULL DEFAULT 0,
    losses                  INTEGER NOT NULL DEFAULT 0,
    ties                    INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(season_year, team_id, is_playoff)
);

CREATE INDEX IF NOT EXISTS idx_team_season_running_team ON team_season_running(team_id, season_year);
CREATE INDEX IF NOT EXISTS idx_team_season_running_points_scored ON team_season_running(season_year, is_playoff, points_scored DESC);
CREATE INDEX IF NOT EXISTS idx_team_season_running_points_allowed ON team_season_running(season_year, is_playoff, points_allowed ASC);

-- Stars of the Week awards
CREATE TABLE IF NOT EXISTS weekly_award (
    id                  INTEGER PRIMARY KEY,
    season_year         INTEGER NOT NULL,
    week_number         INTEGER NOT NULL,
    is_playoff          INTEGER NOT NULL DEFAULT 0,
    award_type          TEXT NOT NULL,  -- 'OFFENSE' | 'DEFENSE' | 'SPECIAL_TEAMS' | 'USER_TEAM_MVP'
    player_id           INTEGER NOT NULL,
    team_id             INTEGER NOT NULL,
    score               REAL NOT NULL,
    narrative_blurb     TEXT NOT NULL,
    FOREIGN KEY (player_id) REFERENCES player(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    UNIQUE(season_year, week_number, is_playoff, award_type)
);

CREATE INDEX IF NOT EXISTS idx_weekly_award_week ON weekly_award(season_year, week_number, is_playoff);
CREATE INDEX IF NOT EXISTS idx_weekly_award_player ON weekly_award(player_id, season_year);
