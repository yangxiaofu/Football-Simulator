"""
Centralized database query functions for Phase 2 (season, standings, stats).

All SQL lives here per layer boundary rules. Business logic modules
call these functions instead of writing raw SQL.
"""

import sqlite3
from typing import Optional


# ======================
# LEAGUE STATE
# ======================

def get_league_state(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Get current league state (season, week, phase)."""
    return conn.execute("SELECT * FROM league WHERE id = 1").fetchone()


def update_league_state(
    conn: sqlite3.Connection,
    season: int,
    week: int,
    phase: str,
) -> None:
    """Update league calendar (season, week, phase)."""
    conn.execute(
        "UPDATE league SET current_season = ?, current_week = ?, current_phase = ? WHERE id = 1",
        (season, week, phase),
    )


def get_season(conn: sqlite3.Connection, year: int) -> Optional[sqlite3.Row]:
    """Get a season record by year."""
    return conn.execute("SELECT * FROM season WHERE year = ?", (year,)).fetchone()


def mark_season_complete(conn: sqlite3.Connection, season_year: int) -> None:
    """Set season.is_complete = 1."""
    conn.execute(
        "UPDATE season SET is_complete = 1 WHERE year = ?",
        (season_year,),
    )


def set_season_champion(
    conn: sqlite3.Connection, season_year: int, team_id: int,
) -> None:
    """Set the champion for a season."""
    conn.execute(
        "UPDATE season SET champion_team_id = ? WHERE year = ?",
        (team_id, season_year),
    )


# ======================
# WEEK / GAME
# ======================

def get_week(
    conn: sqlite3.Connection, season_year: int, week_number: int,
) -> Optional[sqlite3.Row]:
    """Get a week record by season and number."""
    return conn.execute("""
        SELECT w.* FROM week w
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ? AND w.week_number = ?
    """, (season_year, week_number)).fetchone()


def get_week_by_id(conn: sqlite3.Connection, week_id: int) -> Optional[sqlite3.Row]:
    """Get a week record by ID."""
    return conn.execute("SELECT * FROM week WHERE id = ?", (week_id,)).fetchone()


def mark_week_complete(conn: sqlite3.Connection, week_id: int) -> None:
    """Flag a week as complete."""
    conn.execute("UPDATE week SET is_complete = 1 WHERE id = ?", (week_id,))


def get_unplayed_games_for_week(
    conn: sqlite3.Connection, season_year: int, week_number: int,
) -> list[sqlite3.Row]:
    """Get all incomplete games for a given week."""
    return conn.execute("""
        SELECT g.* FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ? AND w.week_number = ? AND g.is_complete = 0
        ORDER BY g.id
    """, (season_year, week_number)).fetchall()


def get_all_games_for_week(
    conn: sqlite3.Connection, season_year: int, week_number: int,
) -> list[sqlite3.Row]:
    """Get all games (played and unplayed) for a given week."""
    return conn.execute("""
        SELECT g.* FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ? AND w.week_number = ?
        ORDER BY g.id
    """, (season_year, week_number)).fetchall()


def mark_game_complete(
    conn: sqlite3.Connection,
    game_id: int,
    home_score: int,
    away_score: int,
) -> None:
    """Flag a game as complete with scores."""
    conn.execute("""
        UPDATE game SET home_score = ?, away_score = ?, is_complete = 1
        WHERE id = ?
    """, (home_score, away_score, game_id))


def insert_game(
    conn: sqlite3.Connection,
    week_id: int,
    home_team_id: int,
    away_team_id: int,
) -> int:
    """Insert a new game record and return its ID."""
    cursor = conn.execute("""
        INSERT INTO game (week_id, home_team_id, away_team_id, is_complete)
        VALUES (?, ?, ?, 0)
    """, (week_id, home_team_id, away_team_id))
    return cursor.lastrowid


def insert_week(
    conn: sqlite3.Connection,
    season_id: int,
    week_number: int,
    week_type: str,
) -> int:
    """Insert a new week record and return its ID."""
    cursor = conn.execute("""
        INSERT INTO week (season_id, week_number, week_type, is_complete)
        VALUES (?, ?, ?, 0)
    """, (season_id, week_number, week_type))
    return cursor.lastrowid


# ======================
# TEAM / DIVISION / CONFERENCE
# ======================

def get_all_teams(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all 32 teams."""
    return conn.execute("SELECT * FROM team ORDER BY id").fetchall()


def get_team(conn: sqlite3.Connection, team_id: int) -> Optional[sqlite3.Row]:
    """Get a team by ID."""
    return conn.execute("SELECT * FROM team WHERE id = ?", (team_id,)).fetchone()


def get_team_by_abbreviation(conn: sqlite3.Connection, abbreviation: str) -> Optional[sqlite3.Row]:
    """Get a team by its 3-letter abbreviation (case-insensitive)."""
    return conn.execute(
        "SELECT * FROM team WHERE UPPER(abbreviation) = UPPER(?)",
        (abbreviation,)
    ).fetchone()


def get_team_division(conn: sqlite3.Connection, team_id: int) -> Optional[sqlite3.Row]:
    """Get the division for a team."""
    return conn.execute("""
        SELECT d.* FROM division d
        JOIN team t ON t.division_id = d.id
        WHERE t.id = ?
    """, (team_id,)).fetchone()


def get_division_teams(conn: sqlite3.Connection, division_id: int) -> list[sqlite3.Row]:
    """Get all teams in a division."""
    return conn.execute(
        "SELECT * FROM team WHERE division_id = ? ORDER BY id", (division_id,),
    ).fetchall()


def get_all_divisions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all divisions with conference info."""
    return conn.execute("""
        SELECT d.*, c.name as conference_name
        FROM division d
        JOIN conference c ON d.conference_id = c.id
        ORDER BY c.name, d.name
    """).fetchall()


def get_conference_divisions(
    conn: sqlite3.Connection, conference_id: int,
) -> list[sqlite3.Row]:
    """Get all divisions in a conference."""
    return conn.execute(
        "SELECT * FROM division WHERE conference_id = ? ORDER BY name",
        (conference_id,),
    ).fetchall()


def get_conferences(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all conferences."""
    return conn.execute("SELECT * FROM conference ORDER BY id").fetchall()


# ======================
# STANDINGS / RECORDS
# ======================

def get_team_season_record(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get a team's season record."""
    return conn.execute("""
        SELECT * FROM team_season_record
        WHERE team_id = ? AND season_year = ?
    """, (team_id, season_year)).fetchone()


def upsert_team_season_record(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    wins: int,
    losses: int,
    ties: int,
    points_for: int,
    points_against: int,
) -> None:
    """Insert or update a team's season record."""
    existing = get_team_season_record(conn, team_id, season_year)
    if existing:
        conn.execute("""
            UPDATE team_season_record
            SET wins = ?, losses = ?, ties = ?,
                points_for = ?, points_against = ?
            WHERE team_id = ? AND season_year = ?
        """, (wins, losses, ties, points_for, points_against,
              team_id, season_year))
    else:
        conn.execute("""
            INSERT INTO team_season_record
            (team_id, season_year, wins, losses, ties, points_for, points_against)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (team_id, season_year, wins, losses, ties, points_for, points_against))


def set_team_playoff_result(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    result: str,
    made_playoffs: int = 1,
) -> None:
    """Update a team's playoff result."""
    conn.execute("""
        UPDATE team_season_record
        SET playoff_result = ?, made_playoffs = ?
        WHERE team_id = ? AND season_year = ?
    """, (result, made_playoffs, team_id, season_year))


def set_team_draft_position(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    draft_position: int,
) -> None:
    """Set a team's draft position."""
    conn.execute("""
        UPDATE team_season_record
        SET draft_position = ?
        WHERE team_id = ? AND season_year = ?
    """, (draft_position, team_id, season_year))


def get_completed_games_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all completed games for a team in a season."""
    return conn.execute("""
        SELECT g.* FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 1
        ORDER BY w.week_number
    """, (season_year, team_id, team_id)).fetchall()


def get_head_to_head_record(
    conn: sqlite3.Connection,
    team_a_id: int,
    team_b_id: int,
    season_year: int,
) -> dict:
    """Get head-to-head record between two teams for a season.

    Returns dict with 'wins', 'losses', 'ties' from team_a's perspective.
    """
    games = conn.execute("""
        SELECT g.* FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ?
          AND g.is_complete = 1
          AND ((g.home_team_id = ? AND g.away_team_id = ?)
            OR (g.home_team_id = ? AND g.away_team_id = ?))
    """, (season_year, team_a_id, team_b_id, team_b_id, team_a_id)).fetchall()

    wins = losses = ties = 0
    for g in games:
        if g['home_team_id'] == team_a_id:
            a_score, b_score = g['home_score'], g['away_score']
        else:
            a_score, b_score = g['away_score'], g['home_score']

        if a_score > b_score:
            wins += 1
        elif a_score < b_score:
            losses += 1
        else:
            ties += 1

    return {'wins': wins, 'losses': losses, 'ties': ties}


def get_division_record(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> dict:
    """Get a team's record within its division.

    Returns dict with 'wins', 'losses', 'ties'.
    """
    div = get_team_division(conn, team_id)
    if not div:
        return {'wins': 0, 'losses': 0, 'ties': 0}

    div_teams = get_division_teams(conn, div['id'])
    div_team_ids = [t['id'] for t in div_teams if t['id'] != team_id]

    wins = losses = ties = 0
    for opp_id in div_team_ids:
        h2h = get_head_to_head_record(conn, team_id, opp_id, season_year)
        wins += h2h['wins']
        losses += h2h['losses']
        ties += h2h['ties']

    return {'wins': wins, 'losses': losses, 'ties': ties}


def get_conference_record(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> dict:
    """Get a team's record within its conference.

    Returns dict with 'wins', 'losses', 'ties'.
    """
    div = get_team_division(conn, team_id)
    if not div:
        return {'wins': 0, 'losses': 0, 'ties': 0}

    conf_divisions = get_conference_divisions(conn, div['conference_id'])
    conf_team_ids = []
    for d in conf_divisions:
        teams = get_division_teams(conn, d['id'])
        for t in teams:
            if t['id'] != team_id:
                conf_team_ids.append(t['id'])

    wins = losses = ties = 0
    games = get_completed_games_for_team(conn, team_id, season_year)
    for g in games:
        opp_id = g['away_team_id'] if g['home_team_id'] == team_id else g['home_team_id']
        if opp_id not in conf_team_ids:
            continue
        if g['home_team_id'] == team_id:
            my_score, opp_score = g['home_score'], g['away_score']
        else:
            my_score, opp_score = g['away_score'], g['home_score']

        if my_score > opp_score:
            wins += 1
        elif my_score < opp_score:
            losses += 1
        else:
            ties += 1

    return {'wins': wins, 'losses': losses, 'ties': ties}


# ======================
# STATS QUERIES
# ======================

def get_player_box_scores(
    conn: sqlite3.Connection, player_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all box scores for a player in a season."""
    return conn.execute("""
        SELECT bs.* FROM box_score bs
        JOIN game g ON bs.game_id = g.id
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE bs.player_id = ? AND s.year = ?
        ORDER BY w.week_number
    """, (player_id, season_year)).fetchall()


def get_all_box_scores_for_season(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Get all box scores for an entire season."""
    return conn.execute("""
        SELECT bs.*, p.position, p.team_id as current_team_id
        FROM box_score bs
        JOIN game g ON bs.game_id = g.id
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        JOIN player p ON bs.player_id = p.id
        WHERE s.year = ?
    """, (season_year,)).fetchall()


def get_season_stats_leaders(
    conn: sqlite3.Connection, season_year: int, stat: str, limit: int = 10,
) -> list[sqlite3.Row]:
    """Get top players for a stat in a season from player_season_stats."""
    valid_stats = {
        'pass_yards', 'pass_tds', 'rush_yards', 'rush_tds',
        'rec_yards', 'rec_tds', 'receptions', 'tackles',
        'sacks', 'interceptions', 'fg_made', 'passer_rating',
    }
    if stat not in valid_stats:
        return []
    return conn.execute(f"""
        SELECT pss.*, p.first_name, p.last_name, p.position,
               t.abbreviation as team_abbr
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.id
        JOIN team t ON pss.team_id = t.id
        WHERE pss.season_year = ?
        ORDER BY pss.{stat} DESC
        LIMIT ?
    """, (season_year, limit)).fetchall()


def insert_player_season_stats(
    conn: sqlite3.Connection, stats: dict,
) -> None:
    """Insert a player_season_stats record."""
    conn.execute("""
        INSERT OR REPLACE INTO player_season_stats (
            player_id, team_id, season_year, games_played, games_started,
            pass_attempts, completions, pass_yards, pass_tds,
            interceptions_thrown, passer_rating,
            carries, rush_yards, rush_tds, yards_per_carry,
            targets, receptions, rec_yards, rec_tds, catch_percentage,
            tackles, sacks, interceptions, pass_deflections,
            fg_made, fg_attempts, fg_percentage,
            sacks_taken, fumbles, punts, punt_yards,
            xp_attempts, xp_made, fg_long,
            punt_returns, punt_return_yards, punt_return_tds,
            kick_returns, kick_return_yards, kick_return_tds
        ) VALUES (
            :player_id, :team_id, :season_year, :games_played, :games_started,
            :pass_attempts, :completions, :pass_yards, :pass_tds,
            :interceptions_thrown, :passer_rating,
            :carries, :rush_yards, :rush_tds, :yards_per_carry,
            :targets, :receptions, :rec_yards, :rec_tds, :catch_percentage,
            :tackles, :sacks, :interceptions, :pass_deflections,
            :fg_made, :fg_attempts, :fg_percentage,
            :sacks_taken, :fumbles, :punts, :punt_yards,
            :xp_attempts, :xp_made, :fg_long,
            :punt_returns, :punt_return_yards, :punt_return_tds,
            :kick_returns, :kick_return_yards, :kick_return_tds
        )
    """, stats)


def upsert_player_career_stats(
    conn: sqlite3.Connection, player_id: int, season_stats: dict,
) -> None:
    """Add season totals to career stats (insert if new, update if existing)."""
    existing = conn.execute(
        "SELECT * FROM player_career_stats WHERE player_id = ?",
        (player_id,),
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE player_career_stats SET
                seasons_played = seasons_played + 1,
                career_pass_yards = career_pass_yards + ?,
                career_pass_tds = career_pass_tds + ?,
                career_rush_yards = career_rush_yards + ?,
                career_rush_tds = career_rush_tds + ?,
                career_rec_yards = career_rec_yards + ?,
                career_rec_tds = career_rec_tds + ?,
                career_sacks = career_sacks + ?,
                career_interceptions = career_interceptions + ?,
                career_fg_made = career_fg_made + ?,
                career_pro_bowls = career_pro_bowls + ?,
                career_all_pro = career_all_pro + ?,
                career_pass_attempts = career_pass_attempts + ?,
                career_completions = career_completions + ?,
                career_carries = career_carries + ?,
                career_receptions = career_receptions + ?,
                career_targets = career_targets + ?,
                career_tackles = career_tackles + ?,
                career_pass_deflections = career_pass_deflections + ?,
                career_fumbles = career_fumbles + ?,
                career_sacks_taken = career_sacks_taken + ?,
                career_punt_returns = career_punt_returns + ?,
                career_punt_return_yards = career_punt_return_yards + ?,
                career_punt_return_tds = career_punt_return_tds + ?,
                career_kick_returns = career_kick_returns + ?,
                career_kick_return_yards = career_kick_return_yards + ?,
                career_kick_return_tds = career_kick_return_tds + ?,
                peak_overall = MAX(peak_overall, ?)
            WHERE player_id = ?
        """, (
            season_stats.get('pass_yards', 0),
            season_stats.get('pass_tds', 0),
            season_stats.get('rush_yards', 0),
            season_stats.get('rush_tds', 0),
            season_stats.get('rec_yards', 0),
            season_stats.get('rec_tds', 0),
            season_stats.get('sacks', 0),
            season_stats.get('interceptions', 0),
            season_stats.get('fg_made', 0),
            season_stats.get('made_pro_bowl', 0),
            season_stats.get('made_all_pro', 0),
            season_stats.get('pass_attempts', 0),
            season_stats.get('completions', 0),
            season_stats.get('carries', 0),
            season_stats.get('receptions', 0),
            season_stats.get('targets', 0),
            season_stats.get('tackles', 0),
            season_stats.get('pass_deflections', 0),
            season_stats.get('fumbles', 0),
            season_stats.get('sacks_taken', 0),
            season_stats.get('punt_returns', 0),
            season_stats.get('punt_return_yards', 0),
            season_stats.get('punt_return_tds', 0),
            season_stats.get('kick_returns', 0),
            season_stats.get('kick_return_yards', 0),
            season_stats.get('kick_return_tds', 0),
            season_stats.get('current_overall', 0),
            player_id,
        ))
    else:
        conn.execute("""
            INSERT INTO player_career_stats (
                player_id, seasons_played,
                career_pass_yards, career_pass_tds,
                career_rush_yards, career_rush_tds,
                career_rec_yards, career_rec_tds,
                career_sacks, career_interceptions, career_fg_made,
                career_pro_bowls, career_all_pro, peak_overall,
                career_pass_attempts, career_completions,
                career_carries, career_receptions, career_targets,
                career_tackles, career_pass_deflections,
                career_fumbles, career_sacks_taken,
                career_punt_returns, career_punt_return_yards, career_punt_return_tds,
                career_kick_returns, career_kick_return_yards, career_kick_return_tds
            ) VALUES (
                ?, 1,
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
        """, (
            player_id,
            season_stats.get('pass_yards', 0),
            season_stats.get('pass_tds', 0),
            season_stats.get('rush_yards', 0),
            season_stats.get('rush_tds', 0),
            season_stats.get('rec_yards', 0),
            season_stats.get('rec_tds', 0),
            season_stats.get('sacks', 0),
            season_stats.get('interceptions', 0),
            season_stats.get('fg_made', 0),
            season_stats.get('made_pro_bowl', 0),
            season_stats.get('made_all_pro', 0),
            season_stats.get('current_overall', 0),
            season_stats.get('pass_attempts', 0),
            season_stats.get('completions', 0),
            season_stats.get('carries', 0),
            season_stats.get('receptions', 0),
            season_stats.get('targets', 0),
            season_stats.get('tackles', 0),
            season_stats.get('pass_deflections', 0),
            season_stats.get('fumbles', 0),
            season_stats.get('sacks_taken', 0),
            season_stats.get('punt_returns', 0),
            season_stats.get('punt_return_yards', 0),
            season_stats.get('punt_return_tds', 0),
            season_stats.get('kick_returns', 0),
            season_stats.get('kick_return_yards', 0),
            season_stats.get('kick_return_tds', 0),
        ))


def delete_play_logs_for_season(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Delete all play records for a season. Returns count deleted."""
    cursor = conn.execute("""
        DELETE FROM play WHERE game_id IN (
            SELECT g.id FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE s.year = ?
        )
    """, (season_year,))
    return cursor.rowcount


def get_all_players_on_team(
    conn: sqlite3.Connection, team_id: int,
) -> list[sqlite3.Row]:
    """Get all active players on a team."""
    return conn.execute("""
        SELECT * FROM player
        WHERE team_id = ? AND is_active = 1
        ORDER BY position, true_overall DESC
    """, (team_id,)).fetchall()


def get_all_active_players(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all active players in the league."""
    return conn.execute("""
        SELECT * FROM player WHERE is_active = 1
        ORDER BY team_id, position
    """).fetchall()


def update_player_attribute(
    conn: sqlite3.Connection,
    player_id: int,
    attribute: str,
    new_value: int,
) -> None:
    """Update a single player attribute. Only allows true_ prefixed attributes."""
    allowed = {
        'true_overall', 'true_speed', 'true_strength', 'true_football_iq',
        'true_durability', 'true_clutch', 'true_catch', 'true_route_running',
        'true_blocking', 'true_pass_rush', 'true_coverage_man',
        'true_coverage_zone', 'true_tackling', 'true_accuracy_short',
        'true_accuracy_mid', 'true_accuracy_deep', 'true_pocket_presence',
        'true_arm_strength', 'true_elusiveness', 'true_vision',
        'true_kick_accuracy', 'true_kick_power', 'true_yac',
    }
    if attribute not in allowed:
        raise ValueError(f"Cannot update attribute: {attribute}")
    conn.execute(
        f"UPDATE player SET {attribute} = ? WHERE id = ?",
        (new_value, player_id),
    )


def insert_attribute_history(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int,
    attribute_name: str,
    value_before: int,
    value_after: int,
    change_reason: str,
) -> None:
    """Record an attribute change in player_attribute_history."""
    conn.execute("""
        INSERT INTO player_attribute_history
        (player_id, season_year, attribute_name, value_before, value_after, change_reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, season_year, attribute_name, value_before, value_after, change_reason))


def update_player_age(conn: sqlite3.Connection, player_id: int) -> None:
    """Increment a player's age by 1."""
    conn.execute("UPDATE player SET age = age + 1 WHERE id = ?", (player_id,))


def increment_player_experience(conn: sqlite3.Connection, player_id: int) -> None:
    """Increment a player's years_experience by 1."""
    conn.execute(
        "UPDATE player SET years_experience = years_experience + 1 WHERE id = ?",
        (player_id,),
    )


def set_player_season_award(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int,
    award_field: str,
    value: int = 1,
) -> None:
    """Set an award flag on player_season_stats (won_mvp, made_pro_bowl, made_all_pro)."""
    allowed = {'won_mvp', 'made_pro_bowl', 'made_all_pro'}
    if award_field not in allowed:
        raise ValueError(f"Invalid award field: {award_field}")
    conn.execute(f"""
        UPDATE player_season_stats
        SET {award_field} = ?
        WHERE player_id = ? AND season_year = ?
    """, (value, player_id, season_year))


def reset_weekly_stamina(conn: sqlite3.Connection) -> None:
    """Reset all players' weekly_stamina to full."""
    from ..utils.constants import STAMINA_MAX
    conn.execute(
        "UPDATE player SET weekly_stamina = ? WHERE is_active = 1",
        (STAMINA_MAX,),
    )


def heal_injured_players(conn: sqlite3.Connection) -> int:
    """Decrement injury_weeks_remaining and clear healed players.

    Returns count of players fully healed.
    """
    # Decrement weeks
    conn.execute("""
        UPDATE player SET injury_weeks_remaining = injury_weeks_remaining - 1
        WHERE injury_weeks_remaining > 0 AND is_active = 1
    """)
    # Clear healed
    cursor = conn.execute("""
        UPDATE player SET injury_status = NULL, injury_weeks_remaining = 0
        WHERE injury_weeks_remaining <= 0 AND injury_status IS NOT NULL AND is_active = 1
    """)
    return cursor.rowcount


# ======================
# PLAYER LOOKUP
# ======================

def get_player(conn: sqlite3.Connection, player_id: int) -> Optional[sqlite3.Row]:
    """Get a player record by ID."""
    return conn.execute("SELECT * FROM player WHERE id = ?", (player_id,)).fetchone()


# ======================
# DIVISION / CONFERENCE LOOKUP
# ======================

def get_division_by_id(
    conn: sqlite3.Connection, division_id: int,
) -> Optional[sqlite3.Row]:
    """Get a division record by ID."""
    return conn.execute(
        "SELECT * FROM division WHERE id = ?", (division_id,),
    ).fetchone()


def get_conference_by_id(
    conn: sqlite3.Connection, conference_id: int,
) -> Optional[sqlite3.Row]:
    """Get a conference record by ID."""
    return conn.execute(
        "SELECT * FROM conference WHERE id = ?", (conference_id,),
    ).fetchone()


def get_team_conference_id(
    conn: sqlite3.Connection, team_id: int,
) -> Optional[int]:
    """Get the conference_id for a team via its division."""
    row = conn.execute("""
        SELECT d.conference_id FROM team t
        JOIN division d ON t.division_id = d.id
        WHERE t.id = ?
    """, (team_id,)).fetchone()
    return row['conference_id'] if row else None


# ======================
# ROSTER WITH CONTRACTS
# ======================

def get_roster_with_contracts(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all active players on a team with contract info, sorted by position."""
    return conn.execute("""
        SELECT p.*, c.total_years, c.total_value, c.signed_season,
               cy.cap_hit
        FROM player p
        LEFT JOIN contract c ON c.player_id = p.id AND c.status = 'active'
        LEFT JOIN contract_year cy ON cy.contract_id = c.id AND cy.season_year = ?
        WHERE p.team_id = ? AND p.is_active = 1
        ORDER BY p.position, p.true_overall DESC
    """, (season_year, team_id)).fetchall()


# ======================
# AWARD CANDIDATES
# ======================

def get_award_candidates(
    conn: sqlite3.Connection,
    season_year: int,
    min_games: int,
    positions: list[str] = None,
    max_experience: int = None,
) -> list[sqlite3.Row]:
    """Get candidate players for award consideration.

    Args:
        positions: Optional list of position strings to filter by.
        max_experience: Optional max years_experience (for rookie awards).
    """
    query = """
        SELECT pss.*, p.position, p.first_name, p.last_name, p.years_experience
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.id
        WHERE pss.season_year = ? AND pss.games_played >= ?
    """
    params = [season_year, min_games]

    if positions:
        placeholders = ','.join(['?' for _ in positions])
        query += f" AND p.position IN ({placeholders})"
        params.extend(positions)

    if max_experience is not None:
        query += " AND p.years_experience <= ?"
        params.append(max_experience)

    return conn.execute(query, params).fetchall()


def get_position_season_stats(
    conn: sqlite3.Connection, season_year: int, position: str,
) -> list[sqlite3.Row]:
    """Get season stats for all players at a position with games played > 0."""
    return conn.execute("""
        SELECT pss.*, p.position
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.id
        WHERE pss.season_year = ? AND p.position = ?
          AND pss.games_played > 0
        ORDER BY pss.games_played DESC
    """, (season_year, position)).fetchall()


# ======================
# SEASON STATS HELPERS
# ======================

def count_season_stats(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Count player_season_stats records for a season."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM player_season_stats WHERE season_year = ?
    """, (season_year,)).fetchone()['cnt']


def get_season_stats_for_career_update(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Get season stats joined with true_overall for career stats update."""
    return conn.execute("""
        SELECT pss.*, p.true_overall
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.id
        WHERE pss.season_year = ?
    """, (season_year,)).fetchall()


def insert_new_season(
    conn: sqlite3.Connection, year: int, salary_cap: int,
) -> int:
    """Insert a new season record. Returns the new season ID."""
    cursor = conn.execute("""
        INSERT INTO season (year, salary_cap, is_complete)
        VALUES (?, ?, 0)
    """, (year, salary_cap))
    return cursor.lastrowid


# ======================
# LEGACY QUERIES
# ======================

def get_latest_legacy_score(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Get the most recent legacy_score record."""
    return conn.execute(
        "SELECT * FROM legacy_score ORDER BY season_year DESC LIMIT 1",
    ).fetchone()


def count_team_championships(conn: sqlite3.Connection, team_id: int) -> int:
    """Count championships won by a team."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM season
        WHERE champion_team_id = ? AND is_complete = 1
    """, (team_id,)).fetchone()['cnt']


def count_team_conference_titles(conn: sqlite3.Connection, team_id: int) -> int:
    """Count conference titles (super bowl appearances) for a team."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM team_season_record
        WHERE team_id = ? AND playoff_result IN ('champion', 'superbowl_loss')
    """, (team_id,)).fetchone()['cnt']


def get_team_career_totals(
    conn: sqlite3.Connection, team_id: int,
) -> Optional[sqlite3.Row]:
    """Get career wins, losses, ties totals for a team."""
    return conn.execute("""
        SELECT SUM(wins) as total_wins, SUM(losses) as total_losses,
               SUM(ties) as total_ties
        FROM team_season_record WHERE team_id = ?
    """, (team_id,)).fetchone()


def count_stars_developed(
    conn: sqlite3.Connection, team_id: int, min_improvement: int,
) -> int:
    """Count players on team who improved true_overall by at least min_improvement."""
    return conn.execute("""
        SELECT COUNT(DISTINCT pah.player_id) as cnt
        FROM player_attribute_history pah
        JOIN player p ON pah.player_id = p.id
        WHERE p.team_id = ?
          AND pah.attribute_name = 'true_overall'
          AND pah.change_reason = 'development'
          AND pah.value_after - pah.value_before >= ?
    """, (team_id, min_improvement)).fetchone()['cnt']


def count_playoff_appearances(conn: sqlite3.Connection, team_id: int) -> int:
    """Count playoff appearances for a team."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM team_season_record
        WHERE team_id = ? AND made_playoffs = 1
    """, (team_id,)).fetchone()['cnt']


def count_team_seasons(conn: sqlite3.Connection, team_id: int) -> int:
    """Count total seasons recorded for a team."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM team_season_record
        WHERE team_id = ?
    """, (team_id,)).fetchone()['cnt']


def get_recent_season_records(
    conn: sqlite3.Connection, team_id: int, limit: int,
) -> list[sqlite3.Row]:
    """Get most recent season records for a team."""
    return conn.execute("""
        SELECT wins, losses FROM team_season_record
        WHERE team_id = ? ORDER BY season_year DESC LIMIT ?
    """, (team_id, limit)).fetchall()


def count_championships_since(
    conn: sqlite3.Connection, team_id: int, since_year: int,
) -> int:
    """Count championships won by team since a given year."""
    return conn.execute("""
        SELECT COUNT(*) as cnt FROM season
        WHERE champion_team_id = ? AND is_complete = 1
          AND year >= ?
    """, (team_id, since_year)).fetchone()['cnt']


def get_legacy_score(
    conn: sqlite3.Connection, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get legacy_score record for a season."""
    return conn.execute(
        "SELECT id FROM legacy_score WHERE season_year = ?",
        (season_year,),
    ).fetchone()


def upsert_legacy_score(
    conn: sqlite3.Connection, season_year: int, data: dict,
) -> None:
    """Insert or update legacy_score record."""
    coach_id = data.get('coach_id')
    existing = get_legacy_score(conn, season_year)
    if existing:
        conn.execute("""
            UPDATE legacy_score SET
                championships = ?, conference_titles = ?,
                career_win_pct = ?, stars_developed = ?,
                cap_efficiency_score = ?, seasons_coached = ?,
                media_legacy_score = ?, total_legacy_score = ?,
                is_dynasty = ?, hof_eligible = ?,
                coach_id = ?
            WHERE season_year = ?
        """, (
            data['championships'], data['conference_titles'],
            data['career_win_pct'], data['stars_developed'],
            data['cap_efficiency'], data['seasons_coached'],
            data['media_score'], data['total_legacy'],
            data['is_dynasty'], data['hof_eligible'],
            coach_id,
            season_year,
        ))
    else:
        conn.execute("""
            INSERT INTO legacy_score (
                season_year, championships, conference_titles,
                career_win_pct, stars_developed, cap_efficiency_score,
                seasons_coached, media_legacy_score,
                total_legacy_score, is_dynasty, hof_eligible,
                coach_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season_year, data['championships'], data['conference_titles'],
            data['career_win_pct'], data['stars_developed'],
            data['cap_efficiency'], data['seasons_coached'],
            data['media_score'], data['total_legacy'],
            data['is_dynasty'], data['hof_eligible'],
            coach_id,
        ))


# ======================
# CONTRACT QUERIES
# ======================

def get_active_contract(
    conn: sqlite3.Connection, player_id: int,
) -> Optional[sqlite3.Row]:
    """Get the active contract for a player (at most one)."""
    return conn.execute(
        "SELECT * FROM contract WHERE player_id = ? AND status = 'active'",
        (player_id,),
    ).fetchone()


def get_contract_years(
    conn: sqlite3.Connection, contract_id: int,
) -> list[sqlite3.Row]:
    """Get all contract_year rows for a contract, ordered by season."""
    return conn.execute(
        "SELECT * FROM contract_year WHERE contract_id = ? ORDER BY season_year ASC",
        (contract_id,),
    ).fetchall()


def get_contract_years_from_season(
    conn: sqlite3.Connection, contract_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get contract_year rows from a given season onward."""
    return conn.execute("""
        SELECT * FROM contract_year
        WHERE contract_id = ? AND season_year >= ?
        ORDER BY season_year ASC
    """, (contract_id, season_year)).fetchall()


def get_contract_year_for_season(
    conn: sqlite3.Connection, contract_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get the contract_year row for a specific season."""
    return conn.execute(
        "SELECT * FROM contract_year WHERE contract_id = ? AND season_year = ?",
        (contract_id, season_year),
    ).fetchone()


def get_player_for_contract(
    conn: sqlite3.Connection, player_id: int,
) -> Optional[sqlite3.Row]:
    """Get player row with fields needed for contract operations."""
    return conn.execute("""
        SELECT id, team_id, first_name, last_name, position, age,
               true_overall, satisfaction, roster_status
        FROM player WHERE id = ?
    """, (player_id,)).fetchone()


def insert_contract(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    status: str,
    total_years: int,
    total_value: int,
    signing_bonus: int,
    guaranteed_money: int,
    aav: int,
    signed_season: int,
    void_year: Optional[int],
    is_franchise_tag: int,
    is_rookie_contract: int,
) -> int:
    """Insert a contract record and return its ID."""
    cursor = conn.execute("""
        INSERT INTO contract
        (player_id, team_id, status, total_years, total_value,
         signing_bonus, guaranteed_money, aav, signed_season,
         void_year, is_franchise_tag, is_rookie_contract)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        player_id, team_id, status, total_years, total_value,
        signing_bonus, guaranteed_money, aav, signed_season,
        void_year, is_franchise_tag, is_rookie_contract,
    ))
    return cursor.lastrowid


def insert_contract_year(
    conn: sqlite3.Connection,
    contract_id: int,
    season_year: int,
    base_salary: int,
    prorated_bonus: int,
    roster_bonus: int,
    cap_hit: int,
    dead_cap_value: int,
    is_void_year: int,
    escalator_trigger: Optional[str],
    escalator_amount: int,
) -> int:
    """Insert a contract_year record and return its ID."""
    cursor = conn.execute("""
        INSERT INTO contract_year
        (contract_id, season_year, base_salary, prorated_bonus,
         roster_bonus, cap_hit, dead_cap_value, is_void_year,
         escalator_trigger, escalator_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contract_id, season_year, base_salary, prorated_bonus,
        roster_bonus, cap_hit, dead_cap_value, is_void_year,
        escalator_trigger, escalator_amount,
    ))
    return cursor.lastrowid


def update_contract_status(
    conn: sqlite3.Connection, contract_id: int, new_status: str,
) -> None:
    """Update a contract's status ('active', 'expired', 'voided', 'restructured')."""
    conn.execute(
        "UPDATE contract SET status = ? WHERE id = ?",
        (new_status, contract_id),
    )


def update_contract_year_row(
    conn: sqlite3.Connection,
    row_id: int,
    base_salary: int,
    prorated_bonus: int,
    cap_hit: int,
    dead_cap_value: int,
) -> None:
    """Update financial columns on a specific contract_year row."""
    conn.execute("""
        UPDATE contract_year
        SET base_salary = ?, prorated_bonus = ?, cap_hit = ?, dead_cap_value = ?
        WHERE id = ?
    """, (base_salary, prorated_bonus, cap_hit, dead_cap_value, row_id))


def update_contract_signing_bonus(
    conn: sqlite3.Connection, contract_id: int, new_signing_bonus: int,
) -> None:
    """Update the signing_bonus on a contract record (after restructuring)."""
    conn.execute(
        "UPDATE contract SET signing_bonus = ? WHERE id = ?",
        (new_signing_bonus, contract_id),
    )


def update_player_team(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: Optional[int],
    roster_status: str,
) -> None:
    """Update a player's team_id and roster_status."""
    conn.execute(
        "UPDATE player SET team_id = ?, roster_status = ? WHERE id = ?",
        (team_id, roster_status, player_id),
    )


def get_team_active_roster_count(
    conn: sqlite3.Connection, team_id: int,
) -> int:
    """Count active roster players on a team."""
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM player WHERE team_id = ? AND roster_status = 'active'",
        (team_id,),
    ).fetchone()
    return row['cnt']


def delete_contract_years_from_season(
    conn: sqlite3.Connection, contract_id: int, season_year: int,
) -> int:
    """Delete contract_year rows for a contract from a given season onward.

    Returns count of rows deleted.
    """
    cursor = conn.execute("""
        DELETE FROM contract_year
        WHERE contract_id = ? AND season_year > ?
    """, (contract_id, season_year))
    return cursor.rowcount


def get_team_cap_space(conn: sqlite3.Connection, team_id: int) -> int:
    """Get current cap space for a team."""
    row = conn.execute(
        "SELECT cap_space FROM team WHERE id = ?", (team_id,)
    ).fetchone()
    return row['cap_space'] if row else 0


# ======================
# SATISFACTION QUERIES
# ======================

def get_player_satisfaction(
    conn: sqlite3.Connection, player_id: int,
) -> Optional[int]:
    """Get a player's current satisfaction score."""
    row = conn.execute(
        "SELECT satisfaction FROM player WHERE id = ?", (player_id,),
    ).fetchone()
    return row['satisfaction'] if row else None


def update_player_satisfaction(
    conn: sqlite3.Connection, player_id: int, new_score: int,
) -> None:
    """Set a player's satisfaction score (caller must clamp)."""
    conn.execute(
        "UPDATE player SET satisfaction = ? WHERE id = ?",
        (new_score, player_id),
    )


def insert_satisfaction_event(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int,
    week: int,
    delta: int,
    reason: str,
    new_score: int,
) -> int:
    """Record a satisfaction change event. Returns event ID."""
    cursor = conn.execute("""
        INSERT INTO satisfaction_event
        (player_id, season_year, week, delta, reason, new_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, season_year, week, delta, reason, new_score))
    return cursor.lastrowid


def get_satisfaction_history(
    conn: sqlite3.Connection, player_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all satisfaction events for a player in a season."""
    return conn.execute("""
        SELECT * FROM satisfaction_event
        WHERE player_id = ? AND season_year = ?
        ORDER BY week ASC, id ASC
    """, (player_id, season_year)).fetchall()


def insert_player_event(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    event_type: str,
    season_year: int,
    week: int,
    metadata_json: Optional[str] = None,
) -> int:
    """Insert a player event record (holdout, trade demand, intervention, etc.).

    Returns event ID.
    """
    cursor = conn.execute("""
        INSERT INTO player_event
        (player_id, team_id, event_type, season_year, week, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, team_id, event_type, season_year, week, metadata_json))
    return cursor.lastrowid


def get_active_player_events(
    conn: sqlite3.Connection,
    player_id: int,
    event_type: Optional[str] = None,
) -> list[sqlite3.Row]:
    """Get unresolved player events, optionally filtered by type."""
    if event_type:
        return conn.execute("""
            SELECT * FROM player_event
            WHERE player_id = ? AND event_type = ? AND resolved = 0
            ORDER BY season_year DESC, week DESC
        """, (player_id, event_type)).fetchall()
    return conn.execute("""
        SELECT * FROM player_event
        WHERE player_id = ? AND resolved = 0
        ORDER BY season_year DESC, week DESC
    """, (player_id,)).fetchall()


def resolve_player_event(
    conn: sqlite3.Connection, event_id: int,
) -> None:
    """Mark a player event as resolved."""
    conn.execute(
        "UPDATE player_event SET resolved = 1 WHERE id = ?", (event_id,),
    )


def get_player_recent_box_score(
    conn: sqlite3.Connection, player_id: int, season_year: int, week: int,
) -> Optional[sqlite3.Row]:
    """Get a player's box score from the most recent completed game up to the given week."""
    return conn.execute("""
        SELECT bs.* FROM box_score bs
        JOIN game g ON bs.game_id = g.id
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE bs.player_id = ? AND s.year = ?
          AND w.week_number <= ? AND g.is_complete = 1
        ORDER BY w.week_number DESC
        LIMIT 1
    """, (player_id, season_year, week)).fetchone()


def get_top_player_overall_at_position(
    conn: sqlite3.Connection, team_id: int, position: str,
) -> Optional[int]:
    """Get the highest true_overall for a position on a team."""
    row = conn.execute("""
        SELECT MAX(true_overall) as max_ovr FROM player
        WHERE team_id = ? AND position = ? AND is_active = 1
    """, (team_id, position)).fetchone()
    return row['max_ovr'] if row and row['max_ovr'] is not None else None


def get_team_recent_playoff_appearances(
    conn: sqlite3.Connection, team_id: int, current_season: int, lookback: int,
) -> int:
    """Count playoff appearances in the last N completed seasons."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM team_season_record
        WHERE team_id = ? AND made_playoffs = 1
          AND season_year >= ? AND season_year < ?
    """, (team_id, current_season - lookback, current_season)).fetchone()
    return row['cnt']


def get_recent_intervention(
    conn: sqlite3.Connection,
    player_id: int,
    event_type: str,
    since_week: int,
    season_year: int,
) -> Optional[sqlite3.Row]:
    """Check if an intervention was applied within the cooldown window."""
    return conn.execute("""
        SELECT * FROM player_event
        WHERE player_id = ? AND event_type = ? AND season_year = ?
          AND week >= ?
        ORDER BY week DESC LIMIT 1
    """, (player_id, event_type, season_year, since_week)).fetchone()


# ======================
# FREE AGENCY QUERIES
# ======================

def get_expiring_contract_players(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Get players whose active contracts have no remaining real years.

    Finds active contracts where the maximum non-void contract_year
    season is before the given season_year (contract naturally expired).
    """
    return conn.execute("""
        SELECT c.id AS contract_id, c.player_id, c.team_id
        FROM contract c
        WHERE c.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM contract_year cy
              WHERE cy.contract_id = c.id
                AND cy.season_year >= ?
                AND cy.is_void_year = 0
          )
    """, (season_year,)).fetchall()


def get_free_agent_players(
    conn: sqlite3.Connection,
) -> list[sqlite3.Row]:
    """Get all active free agent players."""
    return conn.execute("""
        SELECT * FROM player
        WHERE roster_status = 'free_agent' AND is_active = 1
        ORDER BY true_overall DESC
    """).fetchall()


def insert_fa_interest(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    season_year: int,
    preference_score: float,
    tier: int,
) -> int:
    """Insert or replace an FA interest record. Returns row ID."""
    cursor = conn.execute("""
        INSERT OR REPLACE INTO fa_interest
        (player_id, team_id, season_year, preference_score, tier)
        VALUES (?, ?, ?, ?, ?)
    """, (player_id, team_id, season_year, preference_score, tier))
    return cursor.lastrowid


def get_fa_interest(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    season_year: int,
) -> Optional[sqlite3.Row]:
    """Get FA interest for a specific player-team-season combination."""
    return conn.execute("""
        SELECT * FROM fa_interest
        WHERE player_id = ? AND team_id = ? AND season_year = ?
    """, (player_id, team_id, season_year)).fetchone()


def get_fa_interests_for_player(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int,
) -> list[sqlite3.Row]:
    """Get all FA interests for a player, ranked by preference score."""
    return conn.execute("""
        SELECT fi.*, t.city, t.nickname, t.abbreviation
        FROM fa_interest fi
        JOIN team t ON fi.team_id = t.id
        WHERE fi.player_id = ? AND fi.season_year = ?
        ORDER BY fi.preference_score DESC
    """, (player_id, season_year)).fetchall()


def update_fa_interest_tier(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    season_year: int,
    new_tier: int,
) -> None:
    """Update the interest tier for a player-team pair."""
    conn.execute("""
        UPDATE fa_interest SET tier = ?
        WHERE player_id = ? AND team_id = ? AND season_year = ?
    """, (new_tier, player_id, team_id, season_year))


def clear_fa_interest_for_season(
    conn: sqlite3.Connection, season_year: int,
) -> None:
    """Delete all FA interest records for a season (for regeneration)."""
    conn.execute(
        "DELETE FROM fa_interest WHERE season_year = ?",
        (season_year,),
    )


def insert_fa_offer(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    season_year: int,
    round_number: int,
    years_offered: int,
    total_value: int,
    signing_bonus: int,
    guaranteed_money: int,
    status: str,
    player_tier: int,
) -> int:
    """Insert a free agent offer. Returns row ID."""
    cursor = conn.execute("""
        INSERT INTO free_agent_offer
        (player_id, offering_team_id, season_year, round_number,
         years_offered, total_value, signing_bonus, guaranteed_money,
         status, player_tier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (player_id, team_id, season_year, round_number,
          years_offered, total_value, signing_bonus, guaranteed_money,
          status, player_tier))
    return cursor.lastrowid


def get_fa_offer(
    conn: sqlite3.Connection, offer_id: int,
) -> Optional[sqlite3.Row]:
    """Get a single free agent offer by ID."""
    return conn.execute(
        "SELECT * FROM free_agent_offer WHERE id = ?",
        (offer_id,),
    ).fetchone()


def update_fa_offer_status(
    conn: sqlite3.Connection, offer_id: int, new_status: str,
) -> None:
    """Update the status of a free agent offer."""
    conn.execute(
        "UPDATE free_agent_offer SET status = ? WHERE id = ?",
        (new_status, offer_id),
    )


def get_team_coordinators(
    conn: sqlite3.Connection, team_id: int,
) -> list[sqlite3.Row]:
    """Get OC and DC staff for a team."""
    return conn.execute("""
        SELECT * FROM staff
        WHERE team_id = ? AND role IN ('OC', 'DC')
    """, (team_id,)).fetchall()


def count_unsigned_free_agents(
    conn: sqlite3.Connection,
) -> int:
    """Count players with roster_status='free_agent' and is_active=1."""
    row = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE roster_status = 'free_agent' AND is_active = 1
    """).fetchone()
    return row['cnt']


def get_unsigned_free_agents_by_position(
    conn: sqlite3.Connection,
) -> list[sqlite3.Row]:
    """Get counts of unsigned free agents grouped by position."""
    return conn.execute("""
        SELECT position, COUNT(*) AS cnt FROM player
        WHERE roster_status = 'free_agent' AND is_active = 1
        GROUP BY position
        ORDER BY cnt DESC
    """).fetchall()


def has_player_history_with_team(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
) -> bool:
    """Check if a player has any contract history with a team."""
    row = conn.execute("""
        SELECT COUNT(*) AS cnt FROM contract
        WHERE player_id = ? AND team_id = ?
    """, (player_id, team_id)).fetchone()
    return row['cnt'] > 0


def count_accepted_fa_offers(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Count accepted FA offers for a season (for market timing)."""
    row = conn.execute("""
        SELECT COUNT(*) AS cnt FROM free_agent_offer
        WHERE season_year = ? AND status = 'accepted'
    """, (season_year,)).fetchone()
    return row['cnt']


# ======================
# FRANCHISE TAG QUERIES
# ======================

def get_franchise_tags_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int, status: str = 'active'
) -> list[sqlite3.Row]:
    """Get franchise tags for a team in a season, optionally filtered by status."""
    return conn.execute("""
        SELECT ft.*, p.first_name, p.last_name, p.position, p.true_overall
        FROM franchise_tag ft
        JOIN player p ON ft.player_id = p.id
        WHERE ft.team_id = ? AND ft.season_year = ? AND ft.status = ?
    """, (team_id, season_year, status)).fetchall()


def get_active_tag_for_player(
    conn: sqlite3.Connection, player_id: int, season_year: int
) -> Optional[sqlite3.Row]:
    """Get active franchise tag for a player in a season (at most one)."""
    return conn.execute("""
        SELECT * FROM franchise_tag
        WHERE player_id = ? AND season_year = ? AND status = 'active'
    """, (player_id, season_year)).fetchone()


def get_tag_history_for_player(
    conn: sqlite3.Connection, player_id: int
) -> list[sqlite3.Row]:
    """Get all franchise tag records for a player across all seasons."""
    return conn.execute("""
        SELECT * FROM franchise_tag
        WHERE player_id = ?
        ORDER BY season_year DESC
    """, (player_id,)).fetchall()


def count_active_tags_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int
) -> int:
    """Count active franchise tags for a team in a season."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM franchise_tag
        WHERE team_id = ? AND season_year = ? AND status = 'active'
    """, (team_id, season_year)).fetchone()
    return row['cnt']


def get_consecutive_tag_count(
    conn: sqlite3.Connection, player_id: int, current_season: int
) -> int:
    """Calculate consecutive tag count for a player ending in current_season.

    Returns 0 if player was not tagged last season, otherwise returns consecutive count.
    """
    tags = conn.execute("""
        SELECT season_year, consecutive_count FROM franchise_tag
        WHERE player_id = ?
        ORDER BY season_year DESC
    """, (player_id,)).fetchall()

    if not tags:
        return 0

    # Check if most recent tag was last season
    most_recent = tags[0]
    if most_recent['season_year'] == current_season - 1:
        return most_recent['consecutive_count']

    return 0


def insert_franchise_tag(
    conn: sqlite3.Connection,
    player_id: int,
    team_id: int,
    season_year: int,
    tag_type: str,
    salary: int,
    consecutive_count: int,
) -> int:
    """Insert a franchise tag record. Returns tag ID."""
    cursor = conn.execute("""
        INSERT INTO franchise_tag
        (player_id, team_id, season_year, tag_type, salary, consecutive_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, team_id, season_year, tag_type, salary, consecutive_count))
    return cursor.lastrowid


def update_tag_status(
    conn: sqlite3.Connection, tag_id: int, new_status: str
) -> None:
    """Update franchise tag status ('active', 'signed_extension', 'rescinded')."""
    conn.execute(
        "UPDATE franchise_tag SET status = ? WHERE id = ?",
        (new_status, tag_id)
    )


def get_top_n_cap_hits_at_position(
    conn: sqlite3.Connection,
    position: str,
    season_year: int,
    top_n: int,
) -> list[int]:
    """Get the top N cap hits at a position for a season.

    Returns list of cap_hit values sorted descending.
    Used for calculating franchise tag salary.
    """
    rows = conn.execute("""
        SELECT cy.cap_hit
        FROM contract_year cy
        JOIN contract c ON cy.contract_id = c.id
        JOIN player p ON c.player_id = p.id
        WHERE p.position = ?
          AND cy.season_year = ?
          AND c.status = 'active'
          AND cy.is_void_year = 0
        ORDER BY cy.cap_hit DESC
        LIMIT ?
    """, (position, season_year, top_n)).fetchall()
    return [row['cap_hit'] for row in rows]


def get_player_contract_status(
    conn: sqlite3.Connection, player_id: int
) -> Optional[sqlite3.Row]:
    """Get player's team and contract status for tag eligibility check."""
    return conn.execute("""
        SELECT p.team_id, p.roster_status,
               c.id as contract_id, c.status as contract_status
        FROM player p
        LEFT JOIN contract c ON c.player_id = p.id AND c.status = 'active'
        WHERE p.id = ?
    """, (player_id,)).fetchone()


def get_tag_by_id(
    conn: sqlite3.Connection, tag_id: int
) -> Optional[sqlite3.Row]:
    """Get a franchise tag record by ID."""
    return conn.execute(
        "SELECT * FROM franchise_tag WHERE id = ?",
        (tag_id,)
    ).fetchone()


def get_all_tagged_players(
    conn: sqlite3.Connection, season_year: int
) -> list[sqlite3.Row]:
    """Get all players with active tags in a season."""
    return conn.execute("""
        SELECT ft.*, p.first_name, p.last_name, p.position, t.abbreviation as team_abbr
        FROM franchise_tag ft
        JOIN player p ON ft.player_id = p.id
        JOIN team t ON ft.team_id = t.id
        WHERE ft.season_year = ? AND ft.status = 'active'
        ORDER BY ft.salary DESC
    """, (season_year,)).fetchall()


def count_position_tagged_players(
    conn: sqlite3.Connection, position: str, season_year: int
) -> int:
    """Count players tagged at a position in a season (for market analysis)."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM franchise_tag ft
        JOIN player p ON ft.player_id = p.id
        WHERE p.position = ? AND ft.season_year = ? AND ft.status = 'active'
    """, (position, season_year)).fetchone()
    return row['cnt']


def get_player_basic_info(
    conn: sqlite3.Connection, player_id: int
) -> Optional[sqlite3.Row]:
    """Get basic player info (position, name) for tag operations."""
    return conn.execute(
        "SELECT position, first_name, last_name FROM player WHERE id = ?",
        (player_id,)
    ).fetchone()


def mark_contract_as_franchise_tag(
    conn: sqlite3.Connection, contract_id: int
) -> None:
    """Mark a contract as a franchise tag contract."""
    conn.execute(
        "UPDATE contract SET is_franchise_tag = 1 WHERE id = ?",
        (contract_id,)
    )


def get_team_basic_info(
    conn: sqlite3.Connection, team_id: int
) -> Optional[sqlite3.Row]:
    """Get basic team info (city, nickname, cap_space)."""
    return conn.execute(
        "SELECT city, nickname, cap_space FROM team WHERE id = ?",
        (team_id,)
    ).fetchone()


# ======================
# TRADE QUERIES
# ======================

def insert_trade(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    team_a_id: int,
    team_b_id: int,
    status: str,
    initiated_by: str,
) -> int:
    """Insert a trade record. Returns trade ID."""
    cursor = conn.execute("""
        INSERT INTO trade
        (season_year, week_number, team_a_id, team_b_id, status, initiated_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (season_year, week_number, team_a_id, team_b_id, status, initiated_by))
    return cursor.lastrowid


def insert_trade_asset(
    conn: sqlite3.Connection,
    trade_id: int,
    from_team_id: int,
    to_team_id: int,
    asset_type: str,
    player_id: Optional[int] = None,
    draft_pick_id: Optional[int] = None,
) -> int:
    """Insert a trade asset record. Returns asset ID."""
    cursor = conn.execute("""
        INSERT INTO trade_asset
        (trade_id, from_team_id, to_team_id, asset_type, player_id, draft_pick_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (trade_id, from_team_id, to_team_id, asset_type, player_id, draft_pick_id))
    return cursor.lastrowid


def update_trade_status(
    conn: sqlite3.Connection, trade_id: int, new_status: str,
) -> None:
    """Update a trade's status ('completed', 'rejected', 'countered', 'pending')."""
    conn.execute(
        "UPDATE trade SET status = ? WHERE id = ?",
        (new_status, trade_id),
    )


def get_trade_by_id(
    conn: sqlite3.Connection, trade_id: int,
) -> Optional[sqlite3.Row]:
    """Get a trade record by ID."""
    return conn.execute(
        "SELECT * FROM trade WHERE id = ?", (trade_id,),
    ).fetchone()


def get_trade_assets_for_trade(
    conn: sqlite3.Connection, trade_id: int,
) -> list[sqlite3.Row]:
    """Get all assets for a trade with player/pick details."""
    return conn.execute("""
        SELECT ta.*,
               p.first_name, p.last_name, p.position, p.true_overall,
               dp.round AS pick_round, dp.pick_number, dp.season_year AS pick_season
        FROM trade_asset ta
        LEFT JOIN player p ON ta.player_id = p.id
        LEFT JOIN draft_pick dp ON ta.draft_pick_id = dp.id
        WHERE ta.trade_id = ?
    """, (trade_id,)).fetchall()


def get_pending_trades_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get pending trades involving a team in a season."""
    return conn.execute("""
        SELECT * FROM trade
        WHERE (team_a_id = ? OR team_b_id = ?) AND season_year = ? AND status = 'pending'
        ORDER BY id DESC
    """, (team_id, team_id, season_year)).fetchall()


def get_draft_picks_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all unused draft picks owned by a team for a season."""
    return conn.execute("""
        SELECT * FROM draft_pick
        WHERE owned_by_team_id = ? AND season_year = ? AND used = 0
        ORDER BY round ASC, pick_number ASC
    """, (team_id, season_year)).fetchall()


def get_draft_pick_by_criteria(
    conn: sqlite3.Connection, team_id: int, season_year: int, round_num: int,
) -> Optional[sqlite3.Row]:
    """Get a draft pick by team, season, and round."""
    return conn.execute("""
        SELECT * FROM draft_pick
        WHERE owned_by_team_id = ? AND season_year = ? AND round = ? AND used = 0
        ORDER BY pick_number ASC
        LIMIT 1
    """, (team_id, season_year, round_num)).fetchone()


def update_draft_pick_owner(
    conn: sqlite3.Connection, pick_id: int, new_owner_id: int,
) -> None:
    """Transfer draft pick ownership and mark as traded."""
    conn.execute("""
        UPDATE draft_pick SET owned_by_team_id = ?, traded = 1
        WHERE id = ?
    """, (new_owner_id, pick_id))


def get_player_trade_info(
    conn: sqlite3.Connection, player_id: int,
) -> Optional[sqlite3.Row]:
    """Get player info needed for trade value calculation.

    Joins player + active contract + count of remaining contract years.
    Returns age, true_overall, position, team_id, contract details.
    """
    return conn.execute("""
        SELECT p.id, p.first_name, p.last_name, p.position, p.age,
               p.true_overall, p.team_id, p.satisfaction,
               c.id AS contract_id, c.total_years, c.total_value,
               c.signed_season, c.aav,
               (SELECT COUNT(*) FROM contract_year cy
                WHERE cy.contract_id = c.id
                  AND cy.season_year >= (SELECT current_season FROM league WHERE id = 1)
                  AND cy.is_void_year = 0
               ) AS years_remaining
        FROM player p
        LEFT JOIN contract c ON c.player_id = p.id AND c.status = 'active'
        WHERE p.id = ?
    """, (player_id,)).fetchone()


def update_contract_team(
    conn: sqlite3.Connection, contract_id: int, new_team_id: int,
) -> None:
    """Transfer a contract to a new team."""
    conn.execute(
        "UPDATE contract SET team_id = ? WHERE id = ?",
        (new_team_id, contract_id),
    )


def get_all_teams_ordered(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all teams ordered by ID."""
    return conn.execute("SELECT * FROM team ORDER BY id").fetchall()


def count_prospect_red_flags(
    conn: sqlite3.Connection, prospect_id: int
) -> int:
    """Count red flags for a prospect."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM scouting_flag
        WHERE prospect_id = ? AND flag_type = 'red'
    """, (prospect_id,)).fetchone()
    return row['cnt'] if row else 0


def get_completed_trades_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get completed trades involving a team in a season."""
    return conn.execute("""
        SELECT * FROM trade
        WHERE (team_a_id = ? OR team_b_id = ?) AND season_year = ? AND status = 'completed'
        ORDER BY id DESC
    """, (team_id, team_id, season_year)).fetchall()


def get_roster_position_counts(
    conn: sqlite3.Connection, team_id: int,
) -> list[sqlite3.Row]:
    """Get count of active players at each position on a team."""
    return conn.execute("""
        SELECT position, COUNT(*) as cnt FROM player
        WHERE team_id = ? AND is_active = 1
        GROUP BY position
        ORDER BY position
    """, (team_id,)).fetchall()


# ====================
# SCOUTING QUERIES
# ====================


def insert_draft_class(
    conn: sqlite3.Connection, season_year: int,
    class_strength: str, class_notes: str,
) -> int:
    """Create a draft_class record. Returns the new draft_class id."""
    cursor = conn.execute(
        "INSERT INTO draft_class (season_year, class_strength, class_notes) VALUES (?, ?, ?)",
        (season_year, class_strength, class_notes),
    )
    return cursor.lastrowid


def get_draft_class_by_year(
    conn: sqlite3.Connection, season_year: int,
) -> Optional[sqlite3.Row]:
    """Fetch a draft class row by season year."""
    return conn.execute(
        "SELECT * FROM draft_class WHERE season_year = ?",
        (season_year,),
    ).fetchone()


def insert_prospect(conn: sqlite3.Connection, prospect_dict: dict) -> int:
    """Insert a prospect via named params. Returns the new prospect id."""
    columns = list(prospect_dict.keys())
    placeholders = ', '.join(['?'] * len(columns))
    col_str = ', '.join(columns)
    cursor = conn.execute(
        f"INSERT INTO prospect ({col_str}) VALUES ({placeholders})",
        tuple(prospect_dict[c] for c in columns),
    )
    return cursor.lastrowid


def get_all_prospects(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """All prospects for a year (JOIN draft_class by season_year)."""
    return conn.execute("""
        SELECT p.* FROM prospect p
        JOIN draft_class dc ON p.draft_class_id = dc.id
        WHERE dc.season_year = ?
        ORDER BY p.true_overall DESC
    """, (season_year,)).fetchall()


def get_prospect_by_id(
    conn: sqlite3.Connection, prospect_id: int,
) -> Optional[sqlite3.Row]:
    """Single prospect by id."""
    return conn.execute(
        "SELECT * FROM prospect WHERE id = ?",
        (prospect_id,),
    ).fetchone()


def get_undrafted_prospects(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Undrafted prospects for a year."""
    return conn.execute("""
        SELECT p.* FROM prospect p
        JOIN draft_class dc ON p.draft_class_id = dc.id
        WHERE dc.season_year = ? AND p.was_drafted = 0
        ORDER BY p.true_overall DESC
    """, (season_year,)).fetchall()


def update_prospect_draft_result(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, draft_round: int, draft_pick: int,
    player_id: int,
) -> None:
    """Mark a prospect as drafted with round, pick, team, and linked player_id."""
    conn.execute("""
        UPDATE prospect
        SET was_drafted = 1, drafted_by_team_id = ?, draft_round = ?,
            draft_pick = ?, player_id = ?
        WHERE id = ?
    """, (team_id, draft_round, draft_pick, player_id, prospect_id))


def insert_scouting_assignment(
    conn: sqlite3.Connection, scout_id: int, prospect_id: int,
    season_year: int, week: int,
) -> int:
    """Create a scouting assignment. Returns the new assignment id."""
    cursor = conn.execute("""
        INSERT INTO scouting_assignment (scout_id, prospect_id, season_year, week_assigned)
        VALUES (?, ?, ?, ?)
    """, (scout_id, prospect_id, season_year, week))
    return cursor.lastrowid


def get_assignments_for_scout(
    conn: sqlite3.Connection, scout_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Scout's assignments with prospect info for a season."""
    return conn.execute("""
        SELECT sa.*, p.first_name, p.last_name, p.position, p.college
        FROM scouting_assignment sa
        JOIN prospect p ON sa.prospect_id = p.id
        WHERE sa.scout_id = ? AND sa.season_year = ?
        ORDER BY sa.week_assigned
    """, (scout_id, season_year)).fetchall()


def get_assignments_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Team's scouting assignments via staff JOIN for a season."""
    return conn.execute("""
        SELECT sa.*, p.first_name, p.last_name, p.position, p.college,
               s.first_name AS scout_first, s.last_name AS scout_last, s.role AS scout_role
        FROM scouting_assignment sa
        JOIN staff s ON sa.scout_id = s.id
        JOIN prospect p ON sa.prospect_id = p.id
        WHERE s.team_id = ? AND sa.season_year = ?
        ORDER BY sa.week_assigned
    """, (team_id, season_year)).fetchall()


def count_assignments_for_scout(
    conn: sqlite3.Connection, scout_id: int, season_year: int,
) -> int:
    """Count active (incomplete) assignments for a scout in a season."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM scouting_assignment
        WHERE scout_id = ? AND season_year = ? AND week_completed IS NULL
    """, (scout_id, season_year)).fetchone()
    return row['cnt'] if row else 0


def insert_scouted_rating(
    conn: sqlite3.Connection, prospect_id: int, scout_id: int,
    season_year: int, attribute_name: str, estimated_value: int,
    confidence_range: int, scout_grade: str, report_week: int,
    phase: Optional[str] = None, notes: Optional[str] = None,
) -> int:
    """Insert a scouted rating row. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO scouted_rating
        (prospect_id, scout_id, season_year, attribute_name,
         estimated_value, confidence_range, scout_grade, report_week,
         phase, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (prospect_id, scout_id, season_year, attribute_name,
          estimated_value, confidence_range, scout_grade, report_week,
          phase, notes))
    return cursor.lastrowid


def get_scout_by_id(conn: sqlite3.Connection, scout_id: int) -> Optional[sqlite3.Row]:
    """Get a scout (staff member) by ID."""
    return conn.execute(
        "SELECT * FROM staff WHERE id = ?", (scout_id,)
    ).fetchone()


def get_draft_class_season_year(
    conn: sqlite3.Connection, draft_class_id: int
) -> Optional[int]:
    """Get the season year for a draft class."""
    row = conn.execute(
        "SELECT season_year FROM draft_class WHERE id = ?",
        (draft_class_id,)
    ).fetchone()
    return row['season_year'] if row else None


def count_scouts_assigned_to_prospect(
    conn: sqlite3.Connection, prospect_id: int, team_id: int, season_year: int
) -> int:
    """Count how many scouts from a team are assigned to a prospect."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM scouting_assignment sa
        JOIN staff s ON sa.scout_id = s.id
        WHERE sa.prospect_id = ? AND s.team_id = ? AND sa.season_year = ?
    """, (prospect_id, team_id, season_year)).fetchone()
    return row['cnt'] if row else 0


def update_scouted_rating_notes(
    conn: sqlite3.Connection, prospect_id: int, scout_id: int,
    season_year: int, phase: str, report_week: int, notes: str
) -> None:
    """Update the notes field for a scouted_rating entry."""
    conn.execute("""
        UPDATE scouted_rating SET notes = ?
        WHERE prospect_id = ? AND scout_id = ? AND season_year = ?
              AND phase = ? AND report_week = ?
    """, (notes, prospect_id, scout_id, season_year, phase, report_week))


def get_first_scout_assignment_for_prospect(
    conn: sqlite3.Connection, prospect_id: int, season_year: int
) -> Optional[sqlite3.Row]:
    """Get the first scout assignment for a prospect (any team)."""
    return conn.execute("""
        SELECT sa.scout_id, s.team_id FROM scouting_assignment sa
        JOIN staff s ON sa.scout_id = s.id
        WHERE sa.prospect_id = ? AND sa.season_year = ?
        LIMIT 1
    """, (prospect_id, season_year)).fetchone()


def get_team_head_scout(
    conn: sqlite3.Connection, team_id: int
) -> Optional[sqlite3.Row]:
    """Get the head scout for a team."""
    return conn.execute(
        "SELECT * FROM staff WHERE team_id = ? AND role = 'head_scout' LIMIT 1",
        (team_id,)
    ).fetchone()


def get_scouted_ratings_for_prospect(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Team's scouted ratings for a prospect (via scout's team_id)."""
    return conn.execute("""
        SELECT sr.* FROM scouted_rating sr
        JOIN staff s ON sr.scout_id = s.id
        WHERE sr.prospect_id = ? AND s.team_id = ? AND sr.season_year = ?
        ORDER BY sr.report_week DESC
    """, (prospect_id, team_id, season_year)).fetchall()


def insert_scouting_flag(
    conn: sqlite3.Connection, prospect_id: int, scout_id: int,
    team_id: int, season_year: int, flag_type: str, flag_text: str,
    is_true_flag: int, report_week: int,
) -> int:
    """Insert a scouting flag discovery. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO scouting_flag
        (prospect_id, scout_id, team_id, season_year, flag_type,
         flag_text, is_true_flag, report_week)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (prospect_id, scout_id, team_id, season_year, flag_type,
          flag_text, is_true_flag, report_week))
    return cursor.lastrowid


def get_scouting_flags_for_prospect(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Team's discovered flags for a prospect."""
    return conn.execute("""
        SELECT * FROM scouting_flag
        WHERE prospect_id = ? AND team_id = ? AND season_year = ?
        ORDER BY report_week
    """, (prospect_id, team_id, season_year)).fetchall()


def get_team_scouts(
    conn: sqlite3.Connection, team_id: int,
) -> list[sqlite3.Row]:
    """All scout staff for a team."""
    return conn.execute("""
        SELECT * FROM staff
        WHERE team_id = ? AND role IN ('head_scout', 'regional_scout', 'fa_scout')
        ORDER BY role, last_name
    """, (team_id,)).fetchall()


# ====================
# SCOUTING PHASE QUERIES (Phase 3B)
# ====================


def get_scouted_ratings_by_phase(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, season_year: int, phase: str,
) -> list[sqlite3.Row]:
    """Filter scouted ratings by phase for a team's prospect."""
    return conn.execute("""
        SELECT sr.* FROM scouted_rating sr
        JOIN staff s ON sr.scout_id = s.id
        WHERE sr.prospect_id = ? AND s.team_id = ? AND sr.season_year = ? AND sr.phase = ?
        ORDER BY sr.report_week DESC
    """, (prospect_id, team_id, season_year, phase)).fetchall()


def get_latest_scouted_overall(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Most recent true_overall scouted_rating row for a team's prospect."""
    return conn.execute("""
        SELECT sr.* FROM scouted_rating sr
        JOIN staff s ON sr.scout_id = s.id
        WHERE sr.prospect_id = ? AND s.team_id = ? AND sr.season_year = ?
              AND sr.attribute_name = 'true_overall'
        ORDER BY sr.report_week DESC
        LIMIT 1
    """, (prospect_id, team_id, season_year)).fetchone()


def get_all_scouted_overalls(
    conn: sqlite3.Connection, prospect_id: int,
    team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """All true_overall scouted_rating rows ordered by report_week."""
    return conn.execute("""
        SELECT sr.* FROM scouted_rating sr
        JOIN staff s ON sr.scout_id = s.id
        WHERE sr.prospect_id = ? AND s.team_id = ? AND sr.season_year = ?
              AND sr.attribute_name = 'true_overall'
        ORDER BY sr.report_week ASC
    """, (prospect_id, team_id, season_year)).fetchall()


def insert_combine_event(
    conn: sqlite3.Connection, prospect_id: int, season_year: int,
    event_type: str, narrative: str, grade_impact: int,
) -> int:
    """Insert a combine event. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO combine_event (prospect_id, season_year, event_type, narrative, grade_impact)
        VALUES (?, ?, ?, ?, ?)
    """, (prospect_id, season_year, event_type, narrative, grade_impact))
    return cursor.lastrowid


def get_combine_event_for_prospect(
    conn: sqlite3.Connection, prospect_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Single combine event for a prospect in a year."""
    return conn.execute("""
        SELECT * FROM combine_event
        WHERE prospect_id = ? AND season_year = ?
        LIMIT 1
    """, (prospect_id, season_year)).fetchone()


def get_combine_events(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """All combine events for a season year."""
    return conn.execute("""
        SELECT * FROM combine_event WHERE season_year = ?
        ORDER BY id
    """, (season_year,)).fetchall()


def insert_competitor_intel(
    conn: sqlite3.Connection, team_id: int, prospect_id: int,
    season_year: int, phase: str, signal_type: str,
    narrative: str, is_accurate: int,
) -> int:
    """Insert a competitor intelligence signal. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO competitor_intel
        (team_id, prospect_id, season_year, phase, signal_type, narrative, is_accurate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (team_id, prospect_id, season_year, phase, signal_type, narrative, is_accurate))
    return cursor.lastrowid


def get_intel_for_prospect(
    conn: sqlite3.Connection, prospect_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """All intel signals about a prospect in a season."""
    return conn.execute("""
        SELECT * FROM competitor_intel
        WHERE prospect_id = ? AND season_year = ?
        ORDER BY id
    """, (prospect_id, season_year)).fetchall()


def get_intel_for_team_prospect(
    conn: sqlite3.Connection, team_id: int,
    prospect_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Team-specific intel signals about a prospect."""
    return conn.execute("""
        SELECT * FROM competitor_intel
        WHERE team_id = ? AND prospect_id = ? AND season_year = ?
        ORDER BY id
    """, (team_id, prospect_id, season_year)).fetchall()


def insert_mock_draft_pick(
    conn: sqlite3.Connection, season_year: int, published_week: int,
    pick_number: int, prospect_id: int, mocking_to_team_id: int,
    narrative: Optional[str] = None,
) -> int:
    """Insert a mock draft pick. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO mock_draft
        (season_year, published_week, pick_number, prospect_id, mocking_to_team_id, narrative)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (season_year, published_week, pick_number, prospect_id, mocking_to_team_id, narrative))
    return cursor.lastrowid


def get_mock_draft(
    conn: sqlite3.Connection, season_year: int, published_week: int,
) -> list[sqlite3.Row]:
    """Full mock draft for a specific week."""
    return conn.execute("""
        SELECT * FROM mock_draft
        WHERE season_year = ? AND published_week = ?
        ORDER BY pick_number
    """, (season_year, published_week)).fetchall()


def clear_mock_draft_for_week(
    conn: sqlite3.Connection, season_year: int, published_week: int,
) -> None:
    """Delete mock draft entries for a specific week (before regeneration)."""
    conn.execute("""
        DELETE FROM mock_draft
        WHERE season_year = ? AND published_week = ?
    """, (season_year, published_week))


def upsert_draft_board_entry(
    conn: sqlite3.Connection, team_id: int, prospect_id: int,
    season_year: int, board_rank: float, phase_trend: str,
    board_override: Optional[int] = None,
) -> int:
    """Insert or replace a draft board entry. Returns the id."""
    cursor = conn.execute("""
        INSERT INTO draft_board
        (team_id, prospect_id, season_year, board_rank, phase_trend, board_override, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(team_id, season_year, prospect_id) DO UPDATE SET
            board_rank = excluded.board_rank,
            phase_trend = excluded.phase_trend,
            board_override = excluded.board_override,
            updated_at = excluded.updated_at
    """, (team_id, prospect_id, season_year, board_rank, phase_trend, board_override))
    return cursor.lastrowid


def get_draft_board(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Full draft board ordered by effective rank (override if set, else board_rank)."""
    return conn.execute("""
        SELECT * FROM draft_board
        WHERE team_id = ? AND season_year = ?
        ORDER BY COALESCE(board_override, board_rank) ASC
    """, (team_id, season_year)).fetchall()


def get_draft_board_entry(
    conn: sqlite3.Connection, team_id: int,
    prospect_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Single draft board entry for a team's prospect."""
    return conn.execute("""
        SELECT * FROM draft_board
        WHERE team_id = ? AND prospect_id = ? AND season_year = ?
    """, (team_id, prospect_id, season_year)).fetchone()


def update_draft_board_override(
    conn: sqlite3.Connection, team_id: int,
    prospect_id: int, season_year: int, new_rank: int,
) -> None:
    """Set manual override rank for a board entry."""
    conn.execute("""
        UPDATE draft_board SET board_override = ?, updated_at = datetime('now')
        WHERE team_id = ? AND prospect_id = ? AND season_year = ?
    """, (new_rank, team_id, prospect_id, season_year))


def get_drafted_prospects_for_team(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Drafted prospects by a team in a season."""
    return conn.execute("""
        SELECT p.* FROM prospect p
        JOIN draft_class dc ON p.draft_class_id = dc.id
        WHERE dc.season_year = ? AND p.drafted_by_team_id = ? AND p.was_drafted = 1
        ORDER BY p.draft_round, p.draft_pick
    """, (season_year, team_id)).fetchall()


# ====================
# DRAFT STATE QUERIES
# ====================


def insert_draft_state_pick(
    conn: sqlite3.Connection, season_year: int, pick_overall: int,
    round_num: int, pick_in_round: int, team_id: int,
    original_team_id: int,
) -> int:
    """Insert a draft_state row. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO draft_state
        (season_year, pick_number_overall, round, pick_in_round,
         team_id, original_team_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (season_year, pick_overall, round_num, pick_in_round,
          team_id, original_team_id))
    return cursor.lastrowid


def get_draft_state_order(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Full draft order for a season, sorted by pick_number_overall."""
    return conn.execute("""
        SELECT * FROM draft_state
        WHERE season_year = ?
        ORDER BY pick_number_overall
    """, (season_year,)).fetchall()


def get_on_the_clock_pick(
    conn: sqlite3.Connection, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get the next pending pick in the draft."""
    return conn.execute("""
        SELECT * FROM draft_state
        WHERE season_year = ? AND status = 'pending'
        ORDER BY pick_number_overall
        LIMIT 1
    """, (season_year,)).fetchone()


def update_draft_state_used(
    conn: sqlite3.Connection, pick_id: int, prospect_id: int,
    war_room_reaction: Optional[str] = None,
) -> None:
    """Mark a draft_state pick as used with the selected prospect."""
    conn.execute("""
        UPDATE draft_state
        SET status = 'used', prospect_id = ?, war_room_reaction = ?
        WHERE id = ?
    """, (prospect_id, war_room_reaction, pick_id))


def get_draft_state_pick(
    conn: sqlite3.Connection, season_year: int, pick_overall: int,
) -> Optional[sqlite3.Row]:
    """Get a single draft_state pick by overall number."""
    return conn.execute("""
        SELECT * FROM draft_state
        WHERE season_year = ? AND pick_number_overall = ?
    """, (season_year, pick_overall)).fetchone()


def clear_draft_state(
    conn: sqlite3.Connection, season_year: int,
) -> None:
    """Delete all draft_state rows for a season (for re-initialization)."""
    conn.execute(
        "DELETE FROM draft_state WHERE season_year = ?",
        (season_year,),
    )


def get_drafted_prospect_ids(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """All prospect_ids already picked in the draft."""
    rows = conn.execute("""
        SELECT prospect_id FROM draft_state
        WHERE season_year = ? AND status = 'used' AND prospect_id IS NOT NULL
    """, (season_year,)).fetchall()
    return [r['prospect_id'] for r in rows]


def get_all_season_records(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """All team season records for a year (for draft order calculation)."""
    return conn.execute("""
        SELECT * FROM team_season_record
        WHERE season_year = ?
        ORDER BY made_playoffs ASC, wins ASC, points_for ASC
    """, (season_year,)).fetchall()


def mark_draft_pick_used(
    conn: sqlite3.Connection, pick_id: int, player_id: int,
) -> None:
    """Mark a draft_pick as used with the selected player."""
    conn.execute("""
        UPDATE draft_pick SET used = 1, player_selected_id = ?
        WHERE id = ?
    """, (player_id, pick_id))


def get_mock_draft_position(
    conn: sqlite3.Connection, prospect_id: int, season_year: int,
) -> Optional[int]:
    """Get the latest mock draft pick_number for a prospect."""
    row = conn.execute("""
        SELECT pick_number FROM mock_draft
        WHERE prospect_id = ? AND season_year = ?
        ORDER BY published_week DESC
        LIMIT 1
    """, (prospect_id, season_year)).fetchone()
    return row['pick_number'] if row else None


def insert_draft_pick(
    conn: sqlite3.Connection, owned_by_team_id: int,
    original_team_id: int, season_year: int, round_num: int,
    pick_number: Optional[int] = None,
) -> int:
    """Insert a draft_pick row. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO draft_pick
        (owned_by_team_id, original_team_id, season_year, round, pick_number)
        VALUES (?, ?, ?, ?, ?)
    """, (owned_by_team_id, original_team_id, season_year, round_num,
          pick_number))
    return cursor.lastrowid


def count_draft_picks_for_season(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Count total draft_pick rows for a season."""
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM draft_pick WHERE season_year = ?",
        (season_year,),
    ).fetchone()
    return row['cnt'] if row else 0


def get_owned_draft_picks_for_round(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    round_num: int
) -> list[sqlite3.Row]:
    """Get all unused draft picks owned by a team for a specific round."""
    return conn.execute("""
        SELECT * FROM draft_pick
        WHERE owned_by_team_id = ? AND season_year = ? AND round = ? AND used = 0
        ORDER BY id
    """, (team_id, season_year, round_num)).fetchall()


def get_draft_pick_used_by_team(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    round_num: int
) -> Optional[sqlite3.Row]:
    """Get first unused draft pick for team in a round."""
    return conn.execute("""
        SELECT id FROM draft_pick
        WHERE owned_by_team_id = ? AND season_year = ? AND round = ? AND used = 0
        ORDER BY id LIMIT 1
    """, (team_id, season_year, round_num)).fetchone()


def get_draft_state_by_id(
    conn: sqlite3.Connection, pick_id: int
) -> Optional[sqlite3.Row]:
    """Get draft_state record by ID."""
    return conn.execute(
        "SELECT * FROM draft_state WHERE id = ?", (pick_id,)
    ).fetchone()


def get_upcoming_draft_picks(
    conn: sqlite3.Connection, season_year: int, limit: int = 3
) -> list[sqlite3.Row]:
    """Get next N pending picks in draft order."""
    return conn.execute("""
        SELECT * FROM draft_state
        WHERE season_year = ? AND status = 'pending'
        ORDER BY pick_number_overall
        LIMIT ?
    """, (season_year, limit)).fetchall()


def get_unsigned_free_agents(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all unsigned free agents with full player info."""
    return conn.execute("""
        SELECT p.* FROM player p
        WHERE p.roster_status = 'free_agent' AND p.is_active = 1
        ORDER BY p.position, p.true_overall DESC
    """).fetchall()


# ====================
# OFFSEASON STATE QUERIES
# ====================


def get_offseason_state(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Fetch the offseason state row for a team and season."""
    return conn.execute(
        "SELECT * FROM offseason_state WHERE team_id = ? AND season_year = ?",
        (team_id, season_year),
    ).fetchone()


def insert_offseason_state(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    current_phase: str,
) -> int:
    """Create a new offseason state record. Returns the new id."""
    cursor = conn.execute("""
        INSERT INTO offseason_state (team_id, season_year, current_phase)
        VALUES (?, ?, ?)
    """, (team_id, season_year, current_phase))
    return cursor.lastrowid


def update_offseason_phase(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    new_phase: str,
) -> None:
    """Update the current_phase for a team's offseason."""
    conn.execute("""
        UPDATE offseason_state SET current_phase = ?
        WHERE team_id = ? AND season_year = ?
    """, (new_phase, team_id, season_year))


def mark_offseason_phase_complete(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    phase: str,
) -> None:
    """Set the completion flag for an offseason phase.

    Raises:
        ValueError: If phase is not a valid offseason phase
    """
    from ..utils.constants import OFFSEASON_PHASE_SEQUENCE

    # Validate phase against whitelist
    if phase not in OFFSEASON_PHASE_SEQUENCE:
        raise ValueError(
            f"Invalid phase '{phase}'. Must be one of {OFFSEASON_PHASE_SEQUENCE}"
        )

    # season_ready has no completion column
    if phase == 'season_ready':
        return

    # Safe to use f-string after validation
    column = f"{phase}_complete"
    conn.execute(f"""
        UPDATE offseason_state SET {column} = 1
        WHERE team_id = ? AND season_year = ?
    """, (team_id, season_year))


def get_roster_count(conn: sqlite3.Connection, team_id: int) -> int:
    """Count active roster players for a team."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM player
        WHERE team_id = ? AND roster_status = 'active'
    """, (team_id,)).fetchone()
    return row['cnt'] if row else 0


def get_cuttable_players(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get players sorted by cut priority (lowest dead cap, then lowest overall).

    Excludes players on IR. Joins contract_year to get current dead cap.
    """
    return conn.execute("""
        SELECT p.id, p.first_name, p.last_name, p.position, p.true_overall,
               COALESCE(cy.dead_cap_value, 0) as dead_cap
        FROM player p
        LEFT JOIN contract c ON c.player_id = p.id AND c.status = 'active'
        LEFT JOIN contract_year cy ON cy.contract_id = c.id AND cy.season_year = ?
        WHERE p.team_id = ? AND p.roster_status = 'active'
        ORDER BY COALESCE(cy.dead_cap_value, 0) ASC, p.true_overall ASC
    """, (season_year, team_id)).fetchall()


def get_transaction_summary_for_offseason(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all offseason transactions (week_number = 0) for a team."""
    return conn.execute("""
        SELECT * FROM transaction_log
        WHERE team_id = ? AND season_year = ? AND week_number = 0
        ORDER BY id
    """, (team_id, season_year)).fetchall()


def get_legacy_score_delta(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> dict:
    """Get legacy score change from previous season.

    Returns dict with current_score, previous_score, delta.
    """
    current = conn.execute(
        "SELECT total_legacy_score FROM legacy_score WHERE season_year = ?",
        (season_year,),
    ).fetchone()
    previous = conn.execute(
        "SELECT total_legacy_score FROM legacy_score WHERE season_year = ?",
        (season_year - 1,),
    ).fetchone()

    current_score = current['total_legacy_score'] if current else 0
    previous_score = previous['total_legacy_score'] if previous else 0

    return {
        'current_score': current_score,
        'previous_score': previous_score,
        'delta': current_score - previous_score,
    }


# ====================
# AI GM BEHAVIOR QUERIES (Phase 4 Prompt #3)
# ====================


def get_roster_average_age(
    conn: sqlite3.Connection, team_id: int,
) -> float:
    """Average age of active roster players for a team.

    Returns 0.0 if the team has no active players.
    """
    row = conn.execute("""
        SELECT AVG(age) AS avg_age FROM player
        WHERE team_id = ? AND roster_status = 'active' AND is_active = 1
    """, (team_id,)).fetchone()
    return float(row['avg_age']) if row and row['avg_age'] is not None else 0.0


def get_star_count(
    conn: sqlite3.Connection, team_id: int, threshold: int,
) -> int:
    """Count active players on team with true_overall >= threshold."""
    row = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE team_id = ? AND roster_status = 'active' AND is_active = 1
              AND true_overall >= ?
    """, (team_id, threshold)).fetchone()
    return row['cnt'] if row else 0


def get_recent_win_pct(
    conn: sqlite3.Connection, team_id: int, n_seasons: int,
) -> float:
    """Average win percentage over the N most recent completed seasons.

    Returns 0.5 if no season records exist.
    """
    rows = conn.execute("""
        SELECT wins, losses FROM team_season_record
        WHERE team_id = ?
        ORDER BY season_year DESC
        LIMIT ?
    """, (team_id, n_seasons)).fetchall()
    if not rows:
        return 0.5
    total_wins = sum(r['wins'] for r in rows)
    total_games = sum(r['wins'] + r['losses'] for r in rows)
    if total_games == 0:
        return 0.5
    return total_wins / total_games


def get_consecutive_losing_seasons(
    conn: sqlite3.Connection, team_id: int,
) -> int:
    """Count consecutive losing seasons from the most recent backward.

    A losing season has wins < losses. Returns 0 if most recent is .500+.
    """
    rows = conn.execute("""
        SELECT wins, losses FROM team_season_record
        WHERE team_id = ?
        ORDER BY season_year DESC
    """, (team_id,)).fetchall()
    streak = 0
    for row in rows:
        if row['wins'] < row['losses']:
            streak += 1
        else:
            break
    return streak


def get_consecutive_seasons_no_playoffs(
    conn: sqlite3.Connection, team_id: int,
) -> int:
    """Count consecutive seasons missing playoffs from most recent backward.

    Returns 0 if team made playoffs in most recent season.
    """
    rows = conn.execute("""
        SELECT made_playoffs FROM team_season_record
        WHERE team_id = ?
        ORDER BY season_year DESC
    """, (team_id,)).fetchall()
    streak = 0
    for row in rows:
        if not row['made_playoffs']:
            streak += 1
        else:
            break
    return streak


def get_team_coach(
    conn: sqlite3.Connection, team_id: int,
) -> Optional[sqlite3.Row]:
    """Get the active coach assigned to a team, or None."""
    return conn.execute("""
        SELECT * FROM coach_career
        WHERE current_team_id = ? AND is_active = 1
        LIMIT 1
    """, (team_id,)).fetchone()


def get_coach_tenure_length(
    conn: sqlite3.Connection, coach_id: int, current_year: int,
) -> int:
    """Years in current (open) tenure for a coach.

    Returns 0 if no open tenure exists.
    """
    row = conn.execute("""
        SELECT start_year FROM coach_tenure
        WHERE coach_id = ? AND end_year IS NULL
        LIMIT 1
    """, (coach_id,)).fetchone()
    if not row:
        return 0
    return current_year - row['start_year']


def update_team_phase(
    conn: sqlite3.Connection, team_id: int, phase: str,
) -> None:
    """Write team.team_phase for a team."""
    conn.execute(
        "UPDATE team SET team_phase = ? WHERE id = ?",
        (phase, team_id),
    )


# ==============================
# OWNER SENTIMENT (Phase 4 Prompt #4)
# ==============================

def get_owner_sentiment(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get owner sentiment record for a team-season."""
    return conn.execute("""
        SELECT * FROM owner_sentiment
        WHERE team_id = ? AND season_year = ?
    """, (team_id, season_year)).fetchone()


def insert_owner_sentiment(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    expectation_tier: Optional[str] = None, sentiment_score: int = 70,
) -> None:
    """Initialize owner sentiment for a team-season."""
    conn.execute("""
        INSERT INTO owner_sentiment
        (team_id, season_year, sentiment_score, preseason_expectation, hot_seat_tier)
        VALUES (?, ?, ?, ?, 'stable')
    """, (team_id, season_year, sentiment_score, expectation_tier))


def update_sentiment_drivers(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    **drivers,
) -> None:
    """Update individual driver scores for sentiment calculation."""
    set_clause = ', '.join([f"{key} = ?" for key in drivers.keys()])
    values = list(drivers.values()) + [team_id, season_year]
    conn.execute(f"""
        UPDATE owner_sentiment
        SET {set_clause}
        WHERE team_id = ? AND season_year = ?
    """, values)


def update_sentiment_score_and_tier(
    conn: sqlite3.Connection, team_id: int, season_year: int,
    score: int, tier: str,
) -> None:
    """Write final sentiment score and hot seat tier."""
    conn.execute("""
        UPDATE owner_sentiment
        SET sentiment_score = ?, hot_seat_tier = ?
        WHERE team_id = ? AND season_year = ?
    """, (score, tier, team_id, season_year))


def get_star_holdouts_count(conn: sqlite3.Connection, team_id: int) -> int:
    """Count active holdout events for stars (true_overall >= 90)."""
    return conn.execute("""
        SELECT COUNT(*) as cnt
        FROM player_event pe
        JOIN player p ON pe.player_id = p.id
        WHERE pe.team_id = ?
          AND pe.event_type = 'holdout'
          AND pe.resolved = 0
          AND p.true_overall >= 90
    """, (team_id,)).fetchone()['cnt']


# ==============================
# COACH JOB OFFERS (Phase 4 Prompt #4)
# ==============================

def insert_coach_job_offer(
    conn: sqlite3.Connection, coach_id: int, team_id: int,
    season_year: int, week: int, quality: str,
) -> int:
    """Create a job offer for a vacant coach."""
    cursor = conn.execute("""
        INSERT INTO coach_job_offer
        (coach_id, team_id, season_year, week_offered, offer_quality_tier)
        VALUES (?, ?, ?, ?, ?)
    """, (coach_id, team_id, season_year, week, quality))
    return cursor.lastrowid


def get_pending_offers_for_coach(
    conn: sqlite3.Connection, coach_id: int, season_year: int,
) -> list[sqlite3.Row]:
    """Get all unresolved offers for a coach in a season."""
    return conn.execute("""
        SELECT * FROM coach_job_offer
        WHERE coach_id = ? AND season_year = ?
          AND is_accepted = 0 AND is_declined = 0
        ORDER BY offer_quality_tier DESC
    """, (coach_id, season_year)).fetchall()


def accept_offer(conn: sqlite3.Connection, offer_id: int) -> None:
    """Mark an offer as accepted."""
    conn.execute(
        "UPDATE coach_job_offer SET is_accepted = 1 WHERE id = ?",
        (offer_id,),
    )


def decline_offer(conn: sqlite3.Connection, offer_id: int) -> None:
    """Mark an offer as declined."""
    conn.execute(
        "UPDATE coach_job_offer SET is_declined = 1 WHERE id = ?",
        (offer_id,),
    )


def decline_all_other_offers(
    conn: sqlite3.Connection, coach_id: int, season_year: int, except_id: int,
) -> None:
    """Decline all pending offers except the accepted one."""
    conn.execute("""
        UPDATE coach_job_offer
        SET is_declined = 1
        WHERE coach_id = ? AND season_year = ?
          AND id != ? AND is_accepted = 0 AND is_declined = 0
    """, (coach_id, season_year, except_id))


def get_coach_legacy_score(conn: sqlite3.Connection, coach_id: int) -> Optional[int]:
    """Get most recent legacy score for a coach."""
    row = conn.execute("""
        SELECT total_legacy_score FROM legacy_score
        WHERE coach_id = ?
        ORDER BY season_year DESC
        LIMIT 1
    """, (coach_id,)).fetchone()
    return row['total_legacy_score'] if row else None


def compute_legacy_quartile(conn: sqlite3.Connection, coach_id: int) -> int:
    """Compute legacy quartile (1-4) relative to all coaches.

    Returns:
        4 = top 25%, 3 = 25-50%, 2 = 50-75%, 1 = bottom 25%
    """
    my_score = get_coach_legacy_score(conn, coach_id)
    if my_score is None:
        return 1

    all_scores = conn.execute("""
        SELECT DISTINCT coach_id, MAX(total_legacy_score) as score
        FROM legacy_score
        WHERE coach_id IS NOT NULL
        GROUP BY coach_id
        ORDER BY score DESC
    """).fetchall()

    if not all_scores:
        return 1

    scores_list = [row['score'] for row in all_scores]
    rank = sum(1 for s in scores_list if s > my_score)
    percentile = rank / len(scores_list)

    if percentile < 0.25:
        return 4
    elif percentile < 0.50:
        return 3
    elif percentile < 0.75:
        return 2
    else:
        return 1


def get_coach_by_id(conn: sqlite3.Connection, coach_id: int) -> Optional[sqlite3.Row]:
    """Get a coach_career record by ID."""
    return conn.execute(
        "SELECT * FROM coach_career WHERE id = ?",
        (coach_id,),
    ).fetchone()


def get_vacant_coaches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all active coaches with no current team (vacancy state)."""
    return conn.execute("""
        SELECT * FROM coach_career
        WHERE is_active = 1 AND current_team_id IS NULL
    """).fetchall()


# ==============================
# COACH LEGACY EXPANSION (Phase 4 Prompt #7)
# ==============================

def insert_coach_legacy_score(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
    team_id: int,
    factors: dict,
    multipliers: dict,
    score: int,
) -> int:
    """Insert a coach legacy score row.

    Args:
        factors: dict with keys: championships, conference_titles, season_win_pct,
                 stars_developed, cap_efficiency_score, media_legacy_score
        multipliers: dict with keys: era_difficulty_multiplier, starting_condition_multiplier
        score: computed season_legacy_score

    Returns:
        ID of inserted row
    """
    cursor = conn.execute("""
        INSERT INTO coach_legacy_score (
            coach_id, season_year, team_id,
            championships, conference_titles, season_win_pct,
            stars_developed, cap_efficiency_score, media_legacy_score,
            era_difficulty_multiplier, starting_condition_multiplier,
            season_legacy_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        coach_id, season_year, team_id,
        factors['championships'], factors['conference_titles'], factors['season_win_pct'],
        factors['stars_developed'], factors['cap_efficiency_score'], factors['media_legacy_score'],
        multipliers['era_difficulty_multiplier'], multipliers['starting_condition_multiplier'],
        score,
    ))
    return cursor.lastrowid


def get_coach_legacy_scores(
    conn: sqlite3.Connection, coach_id: int,
) -> list[sqlite3.Row]:
    """Get all season legacy scores for a coach."""
    return conn.execute("""
        SELECT * FROM coach_legacy_score
        WHERE coach_id = ?
        ORDER BY season_year
    """, (coach_id,)).fetchall()


def get_all_active_coaches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Get all active coaches."""
    return conn.execute("""
        SELECT * FROM coach_career
        WHERE is_active = 1
    """).fetchall()


def insert_narrative_beat(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
    beat_type: str,
    text: str,
) -> int:
    """Insert a narrative beat for a coach's season."""
    cursor = conn.execute("""
        INSERT INTO coach_narrative_beat (coach_id, season_year, beat_type, text)
        VALUES (?, ?, ?, ?)
    """, (coach_id, season_year, beat_type, text))
    return cursor.lastrowid


def get_narrative_beats_for_coach(
    conn: sqlite3.Connection, coach_id: int,
) -> list[sqlite3.Row]:
    """Get all narrative beats for a coach."""
    return conn.execute("""
        SELECT * FROM coach_narrative_beat
        WHERE coach_id = ?
        ORDER BY season_year
    """, (coach_id,)).fetchall()


def insert_peer_ranking(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
    career_total: int,
    active_rank: int,
    all_time_rank: int,
    n_active: int,
    n_all_time: int,
) -> int:
    """Insert a peer ranking snapshot."""
    cursor = conn.execute("""
        INSERT INTO peer_ranking_snapshot (
            coach_id, season_year, career_legacy_total,
            active_rank, all_time_rank, n_active, n_all_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (coach_id, season_year, career_total, active_rank, all_time_rank, n_active, n_all_time))
    return cursor.lastrowid


def get_peer_ranking(
    conn: sqlite3.Connection, coach_id: int, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get peer ranking snapshot for a coach in a season."""
    return conn.execute("""
        SELECT * FROM peer_ranking_snapshot
        WHERE coach_id = ? AND season_year = ?
    """, (coach_id, season_year)).fetchone()


def get_all_team_season_records(
    conn: sqlite3.Connection, season_year: int,
) -> list[sqlite3.Row]:
    """Get all team season records for a given season."""
    return conn.execute("""
        SELECT * FROM team_season_record
        WHERE season_year = ?
    """, (season_year,)).fetchall()


def get_team_prior_season_wpct(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> Optional[float]:
    """Get a team's win percentage from the prior season.

    Args:
        season_year: Current season (will look at season_year - 1)

    Returns:
        Win percentage (0.0-1.0) or None if no record exists
    """
    prior_year = season_year - 1
    row = conn.execute("""
        SELECT wins, losses, ties FROM team_season_record
        WHERE team_id = ? AND season_year = ?
    """, (team_id, prior_year)).fetchone()

    if not row:
        return None

    total_games = row['wins'] + row['losses'] + row['ties']
    if total_games == 0:
        return None

    return (row['wins'] + row['ties'] * 0.5) / total_games


# ====================
# HISTORICAL RECORDS (Phase 4 Prompt #8)
# ====================

def upsert_league_record(
    conn: sqlite3.Connection,
    category: str,
    scope: str,
    record_value: float,
    holder_player_id: Optional[int],
    holder_team_id: Optional[int],
    holder_coach_id: Optional[int],
    holder_name: str,
    season_year: int,
    week_number: Optional[int],
) -> None:
    """Insert or replace league_record row."""
    conn.execute("""
        INSERT OR REPLACE INTO league_record
        (category, scope, record_value, holder_player_id, holder_team_id,
         holder_coach_id, holder_name, season_year, week_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (category, scope, record_value, holder_player_id, holder_team_id,
          holder_coach_id, holder_name, season_year, week_number))


def get_league_record(
    conn: sqlite3.Connection, category: str, scope: str,
) -> Optional[sqlite3.Row]:
    """Get existing record for category × scope."""
    return conn.execute("""
        SELECT * FROM league_record
        WHERE category = ? AND scope = ?
    """, (category, scope)).fetchone()


def get_max_stat_single_game(
    conn: sqlite3.Connection, column_name: str, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get MAX(stat) from box_score for given season.

    Returns row with max value, player_id, game_id, week_number.
    """
    return conn.execute(f"""
        SELECT
            bs.{column_name} AS max_value,
            bs.player_id,
            bs.game_id,
            w.week_number,
            p.first_name || ' ' || p.last_name AS player_name,
            t.abbreviation AS team_abbr
        FROM box_score bs
        JOIN game g ON bs.game_id = g.id
        JOIN week w ON g.week_id = w.id
        JOIN player p ON bs.player_id = p.id
        JOIN team t ON bs.team_id = t.id
        WHERE w.season_id = (SELECT id FROM season WHERE year = ?)
          AND bs.{column_name} > 0
        ORDER BY bs.{column_name} DESC
        LIMIT 1
    """, (season_year,)).fetchone()


def get_max_stat_single_season(
    conn: sqlite3.Connection, column_name: str, season_year: int,
) -> Optional[sqlite3.Row]:
    """Get MAX(stat) from player_season_stats for given season.

    Returns row with max value, player_id, season_year.
    """
    return conn.execute(f"""
        SELECT
            pss.{column_name} AS max_value,
            pss.player_id,
            pss.season_year,
            p.first_name || ' ' || p.last_name AS player_name,
            t.abbreviation AS team_abbr
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.id
        JOIN team t ON pss.team_id = t.id
        WHERE pss.season_year = ?
          AND pss.{column_name} > 0
        ORDER BY pss.{column_name} DESC
        LIMIT 1
    """, (season_year,)).fetchone()


def get_max_stat_career(
    conn: sqlite3.Connection, column_name: str,
) -> Optional[sqlite3.Row]:
    """Get MAX(career_{stat}) from player_career_stats (all time).

    Returns row with max value, player_id.
    """
    return conn.execute(f"""
        SELECT
            pcs.career_{column_name} AS max_value,
            pcs.player_id,
            p.first_name || ' ' || p.last_name AS player_name,
            t.abbreviation AS team_abbr
        FROM player_career_stats pcs
        JOIN player p ON pcs.player_id = p.id
        LEFT JOIN team t ON p.team_id = t.id
        WHERE pcs.career_{column_name} > 0
        ORDER BY pcs.career_{column_name} DESC
        LIMIT 1
    """).fetchone()


# ====================================
# PHASE 4 REFACTOR — TIER 1 QUERIES
# ====================================

def get_all_time_coaches_with_legacy(conn: sqlite3.Connection) -> list:
    """All coaches with at least one legacy score entry."""
    return conn.execute("""
        SELECT DISTINCT coach_id FROM coach_legacy_score
    """).fetchall()


def get_player_coach(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Get the player coach (is_player=1, is_active=1)."""
    return conn.execute("""
        SELECT id, current_team_id FROM coach_career
        WHERE is_player = 1 AND is_active = 1
    """).fetchone()


def update_owner_sentiment_expectation(
    conn: sqlite3.Connection, team_id: int, season_year: int, expectation: str
) -> None:
    """Update preseason expectation for a team."""
    conn.execute("""
        UPDATE owner_sentiment
        SET preseason_expectation = ?
        WHERE team_id = ? AND season_year = ?
    """, (expectation, team_id, season_year))


def get_coach_job_offer_by_id(conn: sqlite3.Connection, offer_id: int) -> Optional[sqlite3.Row]:
    """Get a job offer by ID."""
    return conn.execute("""
        SELECT * FROM coach_job_offer WHERE id = ?
    """, (offer_id,)).fetchone()


def create_ai_coach(
    conn: sqlite3.Connection, first_name: str, last_name: str,
    age: int, archetype: str, season_year: int
) -> int:
    """Create new AI coach. Returns coach_id."""
    cursor = conn.execute("""
        INSERT INTO coach_career
        (first_name, last_name, age, personality_archetype, career_start_year, is_player, is_active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
    """, (first_name, last_name, age, archetype, season_year))
    return cursor.lastrowid


# ====================================
# PHASE 5 — WEEKLY STATS QUERIES
# ====================================

# ========== Helper queries ==========

def get_box_scores_for_game(conn: sqlite3.Connection, game_id: int) -> list[sqlite3.Row]:
    """Get all box scores for a specific game."""
    return conn.execute("""
        SELECT * FROM box_score WHERE game_id = ?
    """, (game_id,)).fetchall()


# ========== player_week_stats ==========

def insert_player_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    is_playoff: int, stats_dict: dict
) -> int:
    """
    Insert a player week stats snapshot.

    Args:
        conn: Database connection
        season_year: Season year
        week_number: Week number
        is_playoff: 0 for regular season, 1 for playoffs
        stats_dict: Dict with keys: player_id, team_id, and all stat columns

    Returns:
        Row ID of inserted record
    """
    cursor = conn.execute("""
        INSERT INTO player_week_stats (
            season_year, week_number, player_id, team_id, is_playoff,
            pass_attempts, completions, pass_yards, pass_tds, interceptions_thrown, sacks_taken,
            carries, rush_yards, rush_tds, fumbles,
            targets, receptions, rec_yards, rec_tds,
            tackles, sacks, interceptions, pass_deflections, forced_fumbles,
            fg_attempts, fg_made, fg_long, xp_attempts, xp_made, punts, punt_yards,
            punt_returns, punt_return_yards, punt_return_tds,
            kick_returns, kick_return_yards, kick_return_tds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        season_year, week_number, stats_dict['player_id'], stats_dict['team_id'], is_playoff,
        stats_dict.get('pass_attempts', 0), stats_dict.get('completions', 0),
        stats_dict.get('pass_yards', 0), stats_dict.get('pass_tds', 0),
        stats_dict.get('interceptions_thrown', 0), stats_dict.get('sacks_taken', 0),
        stats_dict.get('carries', 0), stats_dict.get('rush_yards', 0),
        stats_dict.get('rush_tds', 0), stats_dict.get('fumbles', 0),
        stats_dict.get('targets', 0), stats_dict.get('receptions', 0),
        stats_dict.get('rec_yards', 0), stats_dict.get('rec_tds', 0),
        stats_dict.get('tackles', 0), stats_dict.get('sacks', 0.0),
        stats_dict.get('interceptions', 0), stats_dict.get('pass_deflections', 0),
        stats_dict.get('forced_fumbles', 0), stats_dict.get('fg_attempts', 0),
        stats_dict.get('fg_made', 0), stats_dict.get('fg_long', 0),
        stats_dict.get('xp_attempts', 0), stats_dict.get('xp_made', 0),
        stats_dict.get('punts', 0), stats_dict.get('punt_yards', 0),
        stats_dict.get('punt_returns', 0), stats_dict.get('punt_return_yards', 0),
        stats_dict.get('punt_return_tds', 0), stats_dict.get('kick_returns', 0),
        stats_dict.get('kick_return_yards', 0), stats_dict.get('kick_return_tds', 0)
    ))
    return cursor.lastrowid


def get_player_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    player_id: int, is_playoff: int
) -> Optional[sqlite3.Row]:
    """Get player week stats for a specific week."""
    return conn.execute("""
        SELECT * FROM player_week_stats
        WHERE season_year = ? AND week_number = ? AND player_id = ? AND is_playoff = ?
    """, (season_year, week_number, player_id, is_playoff)).fetchone()


def get_all_player_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get all player week stats for a specific week."""
    return conn.execute("""
        SELECT * FROM player_week_stats
        WHERE season_year = ? AND week_number = ? AND is_playoff = ?
    """, (season_year, week_number, is_playoff)).fetchall()


def get_player_weekly_history(
    conn: sqlite3.Connection, player_id: int, season_year: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get week-by-week stats for a player in a season."""
    return conn.execute("""
        SELECT * FROM player_week_stats
        WHERE player_id = ? AND season_year = ? AND is_playoff = ?
        ORDER BY week_number ASC
    """, (player_id, season_year, is_playoff)).fetchall()


def delete_player_week_stats_for_season(conn: sqlite3.Connection, season_year: int) -> int:
    """Delete all player week stats for a season (called at archive)."""
    cursor = conn.execute("""
        DELETE FROM player_week_stats WHERE season_year = ?
    """, (season_year,))
    return cursor.rowcount


# ========== player_season_running ==========

def insert_player_season_running(
    conn: sqlite3.Connection, season_year: int, player_id: int,
    team_id: int, is_playoff: int, stats_dict: dict
) -> int:
    """
    Insert a new running season total for a player.

    Args:
        conn: Database connection
        season_year: Season year
        player_id: Player ID
        team_id: Team ID
        is_playoff: 0 for regular season, 1 for playoffs
        stats_dict: Dict with all stat columns

    Returns:
        Row ID of inserted record
    """
    cursor = conn.execute("""
        INSERT INTO player_season_running (
            season_year, player_id, team_id, is_playoff, games_played,
            pass_attempts, completions, pass_yards, pass_tds, interceptions_thrown, sacks_taken,
            carries, rush_yards, rush_tds, fumbles,
            targets, receptions, rec_yards, rec_tds,
            tackles, sacks, interceptions, pass_deflections, forced_fumbles,
            fg_attempts, fg_made, fg_long, xp_attempts, xp_made, punts, punt_yards,
            punt_returns, punt_return_yards, punt_return_tds,
            kick_returns, kick_return_yards, kick_return_tds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        season_year, player_id, team_id, is_playoff, stats_dict.get('games_played', 0),
        stats_dict.get('pass_attempts', 0), stats_dict.get('completions', 0),
        stats_dict.get('pass_yards', 0), stats_dict.get('pass_tds', 0),
        stats_dict.get('interceptions_thrown', 0), stats_dict.get('sacks_taken', 0),
        stats_dict.get('carries', 0), stats_dict.get('rush_yards', 0),
        stats_dict.get('rush_tds', 0), stats_dict.get('fumbles', 0),
        stats_dict.get('targets', 0), stats_dict.get('receptions', 0),
        stats_dict.get('rec_yards', 0), stats_dict.get('rec_tds', 0),
        stats_dict.get('tackles', 0), stats_dict.get('sacks', 0.0),
        stats_dict.get('interceptions', 0), stats_dict.get('pass_deflections', 0),
        stats_dict.get('forced_fumbles', 0), stats_dict.get('fg_attempts', 0),
        stats_dict.get('fg_made', 0), stats_dict.get('fg_long', 0),
        stats_dict.get('xp_attempts', 0), stats_dict.get('xp_made', 0),
        stats_dict.get('punts', 0), stats_dict.get('punt_yards', 0),
        stats_dict.get('punt_returns', 0), stats_dict.get('punt_return_yards', 0),
        stats_dict.get('punt_return_tds', 0), stats_dict.get('kick_returns', 0),
        stats_dict.get('kick_return_yards', 0), stats_dict.get('kick_return_tds', 0)
    ))
    return cursor.lastrowid


def get_player_season_running(
    conn: sqlite3.Connection, season_year: int, player_id: int, is_playoff: int
) -> Optional[sqlite3.Row]:
    """Get running season stats for a player."""
    return conn.execute("""
        SELECT * FROM player_season_running
        WHERE season_year = ? AND player_id = ? AND is_playoff = ?
    """, (season_year, player_id, is_playoff)).fetchone()


def update_player_season_running_incremental(
    conn: sqlite3.Connection, running_id: int, week_stats_dict: dict
) -> None:
    """
    Update running totals by incrementing with this week's stats.

    Uses UPDATE SET col = col + ? pattern for atomic incremental updates.

    Args:
        conn: Database connection
        running_id: Row ID in player_season_running table
        week_stats_dict: Dict with this week's stat increments
    """
    conn.execute("""
        UPDATE player_season_running SET
            games_played = games_played + 1,
            pass_attempts = pass_attempts + ?,
            completions = completions + ?,
            pass_yards = pass_yards + ?,
            pass_tds = pass_tds + ?,
            interceptions_thrown = interceptions_thrown + ?,
            sacks_taken = sacks_taken + ?,
            carries = carries + ?,
            rush_yards = rush_yards + ?,
            rush_tds = rush_tds + ?,
            fumbles = fumbles + ?,
            targets = targets + ?,
            receptions = receptions + ?,
            rec_yards = rec_yards + ?,
            rec_tds = rec_tds + ?,
            tackles = tackles + ?,
            sacks = sacks + ?,
            interceptions = interceptions + ?,
            pass_deflections = pass_deflections + ?,
            forced_fumbles = forced_fumbles + ?,
            fg_attempts = fg_attempts + ?,
            fg_made = fg_made + ?,
            fg_long = CASE WHEN ? > fg_long THEN ? ELSE fg_long END,
            xp_attempts = xp_attempts + ?,
            xp_made = xp_made + ?,
            punts = punts + ?,
            punt_yards = punt_yards + ?,
            punt_returns = punt_returns + ?,
            punt_return_yards = punt_return_yards + ?,
            punt_return_tds = punt_return_tds + ?,
            kick_returns = kick_returns + ?,
            kick_return_yards = kick_return_yards + ?,
            kick_return_tds = kick_return_tds + ?
        WHERE id = ?
    """, (
        week_stats_dict.get('pass_attempts', 0), week_stats_dict.get('completions', 0),
        week_stats_dict.get('pass_yards', 0), week_stats_dict.get('pass_tds', 0),
        week_stats_dict.get('interceptions_thrown', 0), week_stats_dict.get('sacks_taken', 0),
        week_stats_dict.get('carries', 0), week_stats_dict.get('rush_yards', 0),
        week_stats_dict.get('rush_tds', 0), week_stats_dict.get('fumbles', 0),
        week_stats_dict.get('targets', 0), week_stats_dict.get('receptions', 0),
        week_stats_dict.get('rec_yards', 0), week_stats_dict.get('rec_tds', 0),
        week_stats_dict.get('tackles', 0), week_stats_dict.get('sacks', 0.0),
        week_stats_dict.get('interceptions', 0), week_stats_dict.get('pass_deflections', 0),
        week_stats_dict.get('forced_fumbles', 0), week_stats_dict.get('fg_attempts', 0),
        week_stats_dict.get('fg_made', 0),
        week_stats_dict.get('fg_long', 0), week_stats_dict.get('fg_long', 0),  # for MAX comparison
        week_stats_dict.get('xp_attempts', 0), week_stats_dict.get('xp_made', 0),
        week_stats_dict.get('punts', 0), week_stats_dict.get('punt_yards', 0),
        week_stats_dict.get('punt_returns', 0), week_stats_dict.get('punt_return_yards', 0),
        week_stats_dict.get('punt_return_tds', 0), week_stats_dict.get('kick_returns', 0),
        week_stats_dict.get('kick_return_yards', 0), week_stats_dict.get('kick_return_tds', 0),
        running_id
    ))


def get_season_running_leaders(
    conn: sqlite3.Connection, season_year: int, stat_column: str,
    is_playoff: int, limit: int = 10
) -> list[sqlite3.Row]:
    """
    Get top N players for a given stat (leaderboard query).

    Performance-critical: Uses indexes on stat columns.

    Args:
        conn: Database connection
        season_year: Season year
        stat_column: Column name (e.g., 'pass_yards', 'rush_yards')
        is_playoff: 0 for regular season, 1 for playoffs
        limit: Number of results to return

    Returns:
        List of player_season_running rows with player and team info joined
    """
    # Validate stat_column to prevent SQL injection
    from ..utils.constants import STAT_COLUMNS_PLAYER
    if stat_column not in STAT_COLUMNS_PLAYER:
        raise ValueError(f"Invalid stat column: {stat_column}")

    query = f"""
        SELECT psr.*, p.first_name, p.last_name, p.position, t.abbreviation as team_abbr
        FROM player_season_running psr
        JOIN player p ON p.id = psr.player_id
        JOIN team t ON t.id = psr.team_id
        WHERE psr.season_year = ? AND psr.is_playoff = ?
        ORDER BY psr.{stat_column} DESC
        LIMIT ?
    """
    return conn.execute(query, (season_year, is_playoff, limit)).fetchall()


def get_leaderboard_through_week(
    conn: sqlite3.Connection, season_year: int, stat_column: str,
    through_week: int, is_playoff: int = 0, limit: int = 10
) -> list[sqlite3.Row]:
    """
    Sum player_week_stats from week 1 through `through_week` and return top N by `stat_column`.

    Returns same row shape as get_season_running_leaders for UI compatibility.

    Args:
        conn: Database connection
        season_year: Season year
        stat_column: Column name (e.g., 'pass_yards', 'rush_yards')
        through_week: Maximum week number to include
        is_playoff: 0 for regular season, 1 for playoffs
        limit: Number of results to return

    Returns:
        List of aggregated player stats with player and team info joined
    """
    # Validate stat_column to prevent SQL injection
    from ..utils.constants import STAT_COLUMNS_PLAYER
    if stat_column not in STAT_COLUMNS_PLAYER:
        raise ValueError(f"Invalid stat column: {stat_column}")

    # Build SUM clauses for all stat columns
    sum_clauses = ', '.join([f'SUM(pws.{col}) as {col}' for col in STAT_COLUMNS_PLAYER])

    query = f"""
        SELECT
            pws.player_id,
            pws.team_id,
            COUNT(*) as games_played,
            {sum_clauses},
            p.first_name,
            p.last_name,
            p.position,
            t.abbreviation as team_abbr
        FROM player_week_stats pws
        JOIN player p ON p.id = pws.player_id
        JOIN team t ON t.id = pws.team_id
        WHERE pws.season_year = ?
          AND pws.week_number <= ?
          AND pws.is_playoff = ?
        GROUP BY pws.player_id, pws.team_id
        ORDER BY {stat_column} DESC
        LIMIT ?
    """
    return conn.execute(query, (season_year, through_week, is_playoff, limit)).fetchall()


def get_leaderboard_single_week(
    conn: sqlite3.Connection, season_year: int, stat_column: str,
    week_number: int, is_playoff: int = 0, limit: int = 10
) -> list[sqlite3.Row]:
    """
    Read player_week_stats for a single week and return top N by stat_column.

    Returns same row shape as get_season_running_leaders for UI compatibility.

    Args:
        conn: Database connection
        season_year: Season year
        stat_column: Column name (e.g., 'pass_yards', 'rush_yards')
        week_number: Specific week number
        is_playoff: 0 for regular season, 1 for playoffs
        limit: Number of results to return

    Returns:
        List of player week stats with player and team info joined
    """
    # Validate stat_column to prevent SQL injection
    from ..utils.constants import STAT_COLUMNS_PLAYER
    if stat_column not in STAT_COLUMNS_PLAYER:
        raise ValueError(f"Invalid stat column: {stat_column}")

    # Add games_played=1 for compatibility with UI that expects this column
    query = f"""
        SELECT
            pws.*,
            1 as games_played,
            p.first_name,
            p.last_name,
            p.position,
            t.abbreviation as team_abbr
        FROM player_week_stats pws
        JOIN player p ON p.id = pws.player_id
        JOIN team t ON t.id = pws.team_id
        WHERE pws.season_year = ?
          AND pws.week_number = ?
          AND pws.is_playoff = ?
        ORDER BY pws.{stat_column} DESC
        LIMIT ?
    """
    return conn.execute(query, (season_year, week_number, is_playoff, limit)).fetchall()


def get_position_season_running(
    conn: sqlite3.Connection, season_year: int, position: str, is_playoff: int
) -> list[sqlite3.Row]:
    """Get running season stats for all players at a position."""
    return conn.execute("""
        SELECT psr.*, p.first_name, p.last_name, p.position
        FROM player_season_running psr
        JOIN player p ON p.id = psr.player_id
        WHERE psr.season_year = ? AND p.position = ? AND psr.is_playoff = ?
    """, (season_year, position, is_playoff)).fetchall()


def verify_season_running_consistency(
    conn: sqlite3.Connection, season_year: int, player_id: int, is_playoff: int
) -> dict:
    """
    Validation helper: verify running total matches sum of weekly stats.

    Args:
        conn: Database connection
        season_year: Season year
        player_id: Player ID
        is_playoff: 0 for regular season, 1 for playoffs

    Returns:
        Dict with 'consistent': bool and details of any mismatches
    """
    running = get_player_season_running(conn, season_year, player_id, is_playoff)
    if not running:
        return {'consistent': True, 'message': 'No running total found'}

    weekly_sum = conn.execute("""
        SELECT
            SUM(pass_yards) as pass_yards, SUM(rush_yards) as rush_yards,
            SUM(rec_yards) as rec_yards, SUM(tackles) as tackles
        FROM player_week_stats
        WHERE season_year = ? AND player_id = ? AND is_playoff = ?
    """, (season_year, player_id, is_playoff)).fetchone()

    mismatches = []
    if weekly_sum['pass_yards'] != running['pass_yards']:
        mismatches.append(f"pass_yards: {running['pass_yards']} != {weekly_sum['pass_yards']}")
    if weekly_sum['rush_yards'] != running['rush_yards']:
        mismatches.append(f"rush_yards: {running['rush_yards']} != {weekly_sum['rush_yards']}")
    if weekly_sum['rec_yards'] != running['rec_yards']:
        mismatches.append(f"rec_yards: {running['rec_yards']} != {weekly_sum['rec_yards']}")
    if weekly_sum['tackles'] != running['tackles']:
        mismatches.append(f"tackles: {running['tackles']} != {weekly_sum['tackles']}")

    return {
        'consistent': len(mismatches) == 0,
        'mismatches': mismatches
    }


def delete_player_season_running_for_season(conn: sqlite3.Connection, season_year: int) -> int:
    """Delete all player season running totals for a season (called at archive)."""
    cursor = conn.execute("""
        DELETE FROM player_season_running WHERE season_year = ?
    """, (season_year,))
    return cursor.rowcount


def archive_running_to_season_stats(conn: sqlite3.Connection, season_year: int) -> int:
    """
    Copy player_season_running -> player_season_stats at season end.

    Args:
        conn: Database connection
        season_year: Season year to archive

    Returns:
        Number of rows copied
    """
    cursor = conn.execute("""
        INSERT INTO player_season_stats (
            player_id, team_id, season_year, games_played,
            pass_attempts, completions, pass_yards, pass_tds, interceptions_thrown,
            carries, rush_yards, rush_tds,
            targets, receptions, rec_yards, rec_tds,
            tackles, sacks, interceptions, pass_deflections,
            fg_made, fg_attempts, xp_attempts, xp_made, fg_long,
            sacks_taken, fumbles, punts, punt_yards,
            punt_returns, punt_return_yards, punt_return_tds,
            kick_returns, kick_return_yards, kick_return_tds
        )
        SELECT
            player_id, team_id, season_year, games_played,
            pass_attempts, completions, pass_yards, pass_tds, interceptions_thrown,
            carries, rush_yards, rush_tds,
            targets, receptions, rec_yards, rec_tds,
            tackles, sacks, interceptions, pass_deflections,
            fg_made, fg_attempts, xp_attempts, xp_made, fg_long,
            sacks_taken, fumbles, punts, punt_yards,
            punt_returns, punt_return_yards, punt_return_tds,
            kick_returns, kick_return_yards, kick_return_tds
        FROM player_season_running
        WHERE season_year = ? AND is_playoff = 0
    """, (season_year,))
    return cursor.rowcount


# ========== team_week_stats ==========

def insert_team_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    team_id: int, is_playoff: int, stats_dict: dict
) -> int:
    """Insert team week stats snapshot."""
    cursor = conn.execute("""
        INSERT INTO team_week_stats (
            season_year, week_number, team_id, is_playoff,
            points_scored, total_yards, pass_yards, rush_yards, turnovers,
            third_down_conversions, third_down_attempts,
            points_allowed, yards_allowed, sacks_recorded, takeaways, won
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        season_year, week_number, team_id, is_playoff,
        stats_dict.get('points_scored', 0), stats_dict.get('total_yards', 0),
        stats_dict.get('pass_yards', 0), stats_dict.get('rush_yards', 0),
        stats_dict.get('turnovers', 0), stats_dict.get('third_down_conversions', 0),
        stats_dict.get('third_down_attempts', 0), stats_dict.get('points_allowed', 0),
        stats_dict.get('yards_allowed', 0), stats_dict.get('sacks_recorded', 0.0),
        stats_dict.get('takeaways', 0), stats_dict.get('won', 0)
    ))
    return cursor.lastrowid


def get_team_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    team_id: int, is_playoff: int
) -> Optional[sqlite3.Row]:
    """Get team week stats for a specific week."""
    return conn.execute("""
        SELECT * FROM team_week_stats
        WHERE season_year = ? AND week_number = ? AND team_id = ? AND is_playoff = ?
    """, (season_year, week_number, team_id, is_playoff)).fetchone()


def get_all_team_week_stats(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get all team week stats for a specific week."""
    return conn.execute("""
        SELECT * FROM team_week_stats
        WHERE season_year = ? AND week_number = ? AND is_playoff = ?
    """, (season_year, week_number, is_playoff)).fetchall()


def get_team_weekly_history(
    conn: sqlite3.Connection, team_id: int, season_year: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get week-by-week stats for a team in a season."""
    return conn.execute("""
        SELECT * FROM team_week_stats
        WHERE team_id = ? AND season_year = ? AND is_playoff = ?
        ORDER BY week_number ASC
    """, (team_id, season_year, is_playoff)).fetchall()


def delete_team_week_stats_for_season(conn: sqlite3.Connection, season_year: int) -> int:
    """Delete all team week stats for a season (called at archive)."""
    cursor = conn.execute("""
        DELETE FROM team_week_stats WHERE season_year = ?
    """, (season_year,))
    return cursor.rowcount


# ========== team_season_running ==========

def insert_team_season_running(
    conn: sqlite3.Connection, season_year: int, team_id: int,
    is_playoff: int, stats_dict: dict
) -> int:
    """Insert a new running season total for a team."""
    cursor = conn.execute("""
        INSERT INTO team_season_running (
            season_year, team_id, is_playoff, games_played,
            points_scored, total_yards, pass_yards, rush_yards, turnovers,
            third_down_conversions, third_down_attempts,
            points_allowed, yards_allowed, sacks_recorded, takeaways,
            wins, losses, ties
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        season_year, team_id, is_playoff, stats_dict.get('games_played', 0),
        stats_dict.get('points_scored', 0), stats_dict.get('total_yards', 0),
        stats_dict.get('pass_yards', 0), stats_dict.get('rush_yards', 0),
        stats_dict.get('turnovers', 0), stats_dict.get('third_down_conversions', 0),
        stats_dict.get('third_down_attempts', 0), stats_dict.get('points_allowed', 0),
        stats_dict.get('yards_allowed', 0), stats_dict.get('sacks_recorded', 0.0),
        stats_dict.get('takeaways', 0), stats_dict.get('wins', 0),
        stats_dict.get('losses', 0), stats_dict.get('ties', 0)
    ))
    return cursor.lastrowid


def get_team_season_running(
    conn: sqlite3.Connection, season_year: int, team_id: int, is_playoff: int
) -> Optional[sqlite3.Row]:
    """Get running season stats for a team."""
    return conn.execute("""
        SELECT * FROM team_season_running
        WHERE season_year = ? AND team_id = ? AND is_playoff = ?
    """, (season_year, team_id, is_playoff)).fetchone()


def update_team_season_running_incremental(
    conn: sqlite3.Connection, running_id: int, week_stats_dict: dict
) -> None:
    """
    Update team running totals by incrementing with this week's stats.

    Args:
        conn: Database connection
        running_id: Row ID in team_season_running table
        week_stats_dict: Dict with this week's stat increments
    """
    conn.execute("""
        UPDATE team_season_running SET
            games_played = games_played + 1,
            points_scored = points_scored + ?,
            total_yards = total_yards + ?,
            pass_yards = pass_yards + ?,
            rush_yards = rush_yards + ?,
            turnovers = turnovers + ?,
            third_down_conversions = third_down_conversions + ?,
            third_down_attempts = third_down_attempts + ?,
            points_allowed = points_allowed + ?,
            yards_allowed = yards_allowed + ?,
            sacks_recorded = sacks_recorded + ?,
            takeaways = takeaways + ?,
            wins = wins + ?,
            losses = losses + ?,
            ties = ties + ?
        WHERE id = ?
    """, (
        week_stats_dict.get('points_scored', 0), week_stats_dict.get('total_yards', 0),
        week_stats_dict.get('pass_yards', 0), week_stats_dict.get('rush_yards', 0),
        week_stats_dict.get('turnovers', 0), week_stats_dict.get('third_down_conversions', 0),
        week_stats_dict.get('third_down_attempts', 0), week_stats_dict.get('points_allowed', 0),
        week_stats_dict.get('yards_allowed', 0), week_stats_dict.get('sacks_recorded', 0.0),
        week_stats_dict.get('takeaways', 0), week_stats_dict.get('wins', 0),
        week_stats_dict.get('losses', 0), week_stats_dict.get('ties', 0),
        running_id
    ))


def get_team_season_running_leaders(
    conn: sqlite3.Connection, season_year: int, stat_column: str,
    is_playoff: int, limit: int = 10
) -> list[sqlite3.Row]:
    """Get top N teams for a given stat."""
    from ..utils.constants import STAT_COLUMNS_TEAM
    valid_columns = STAT_COLUMNS_TEAM + ['wins', 'losses', 'ties']
    if stat_column not in valid_columns:
        raise ValueError(f"Invalid stat column: {stat_column}")

    query = f"""
        SELECT tsr.*, t.city, t.nickname, t.abbreviation
        FROM team_season_running tsr
        JOIN team t ON t.id = tsr.team_id
        WHERE tsr.season_year = ? AND tsr.is_playoff = ?
        ORDER BY tsr.{stat_column} DESC
        LIMIT ?
    """
    return conn.execute(query, (season_year, is_playoff, limit)).fetchall()


def delete_team_season_running_for_season(conn: sqlite3.Connection, season_year: int) -> int:
    """Delete all team season running totals for a season (called at archive)."""
    cursor = conn.execute("""
        DELETE FROM team_season_running WHERE season_year = ?
    """, (season_year,))
    return cursor.rowcount


# ========== weekly_award ==========

def insert_weekly_award(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    is_playoff: int, award_type: str, player_id: int, team_id: int,
    score: float, narrative: str
) -> int:
    """Insert a weekly award (Star of the Week)."""
    cursor = conn.execute("""
        INSERT INTO weekly_award (
            season_year, week_number, is_playoff, award_type,
            player_id, team_id, score, narrative_blurb
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (season_year, week_number, is_playoff, award_type, player_id, team_id, score, narrative))
    return cursor.lastrowid


def get_weekly_awards(
    conn: sqlite3.Connection, season_year: int, week_number: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get all weekly awards for a specific week."""
    return conn.execute("""
        SELECT wa.*, p.first_name, p.last_name, p.position, t.abbreviation as team_abbr
        FROM weekly_award wa
        JOIN player p ON p.id = wa.player_id
        JOIN team t ON t.id = wa.team_id
        WHERE wa.season_year = ? AND wa.week_number = ? AND wa.is_playoff = ?
        ORDER BY wa.award_type
    """, (season_year, week_number, is_playoff)).fetchall()


def get_weekly_award_by_type(
    conn: sqlite3.Connection, season_year: int, week_number: int,
    is_playoff: int, award_type: str
) -> Optional[sqlite3.Row]:
    """Get a specific weekly award by type."""
    return conn.execute("""
        SELECT wa.*, p.first_name, p.last_name, p.position, t.abbreviation as team_abbr
        FROM weekly_award wa
        JOIN player p ON p.id = wa.player_id
        JOIN team t ON t.id = wa.team_id
        WHERE wa.season_year = ? AND wa.week_number = ? AND wa.is_playoff = ? AND wa.award_type = ?
    """, (season_year, week_number, is_playoff, award_type)).fetchone()


def get_player_weekly_awards_count(
    conn: sqlite3.Connection, player_id: int, season_year: int
) -> int:
    """Count how many weekly awards a player has won in a season."""
    result = conn.execute("""
        SELECT COUNT(*) as count FROM weekly_award
        WHERE player_id = ? AND season_year = ?
    """, (player_id, season_year)).fetchone()
    return result['count']


def get_all_weekly_awards_for_season(
    conn: sqlite3.Connection, season_year: int, is_playoff: int
) -> list[sqlite3.Row]:
    """Get all weekly awards for a season."""
    return conn.execute("""
        SELECT wa.*, p.first_name, p.last_name, p.position, t.abbreviation as team_abbr
        FROM weekly_award wa
        JOIN player p ON p.id = wa.player_id
        JOIN team t ON t.id = wa.team_id
        WHERE wa.season_year = ? AND wa.is_playoff = ?
        ORDER BY wa.week_number, wa.award_type
    """, (season_year, is_playoff)).fetchall()


def get_user_team_mvp_history(
    conn: sqlite3.Connection, user_team_id: int, season_year: int
) -> list[sqlite3.Row]:
    """Get all USER_TEAM_MVP awards for user's team in a season."""
    return conn.execute("""
        SELECT wa.*, p.first_name, p.last_name, p.position
        FROM weekly_award wa
        JOIN player p ON p.id = wa.player_id
        WHERE wa.team_id = ? AND wa.season_year = ? AND wa.award_type = 'USER_TEAM_MVP'
        ORDER BY wa.week_number
    """, (user_team_id, season_year)).fetchall()


def delete_weekly_awards_for_season(conn: sqlite3.Connection, season_year: int) -> int:
    """Delete all weekly awards for a season (NOT called at archive - kept permanent)."""
    cursor = conn.execute("""
        DELETE FROM weekly_award WHERE season_year = ?
    """, (season_year,))
    return cursor.rowcount
