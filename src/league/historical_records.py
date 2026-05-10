"""Phase 4 Prompt #8 — Historical Records Module.

Pure read layer that tracks:
- League-wide records (single-game, single-season, career)
- All-time leaderboards
- Champion history with detailed game information

NOT MODIFIED BY THIS MODULE:
- Stats writers (src/engine/stats.py)
- Narrative beats (src/league/narrative_beats.py)
- Legacy scoring (src/league/legacy.py)
"""

import sqlite3
from typing import Optional

from ..utils.constants import (
    LEAGUE_RECORD_CATEGORIES,
    LEAGUE_RECORD_SCOPES,
    TEAM_RECORD_CATEGORIES,
    CHAMPION_HISTORY_DEFAULT_LIMIT,
    ALL_TIME_LEADERS_DEFAULT_TOP_N,
)
from ..db.queries import (
    upsert_league_record,
    get_league_record,
    get_max_stat_single_game,
    get_max_stat_single_season,
    get_max_stat_career,
)


def update_league_records(conn: sqlite3.Connection, season_year: int) -> dict:
    """Scan stats tables at season end and update league_record rows.

    For each category × scope:
      single_game:    MAX(stat) FROM box_score WHERE game.season_year = season_year
      single_season:  MAX(stat) FROM player_season_stats WHERE season_year = season_year
      career:         MAX(stat) FROM player_career_stats (all time)

    Compare against existing league_record. If new > old (or no record exists),
    upsert with new holder, value, season_year, week_number (game only), set_at.

    Returns dict {category: {scope: bool}} of which records were broken this season.
    """
    broken_records = {}

    for category, (display_name, column_name) in LEAGUE_RECORD_CATEGORIES.items():
        broken_records[category] = {}

        # Single-game records
        scope = 'single_game'
        new_record = get_max_stat_single_game(conn, column_name, season_year)
        if new_record and new_record['max_value'] is not None:
            existing = get_league_record(conn, category, scope)
            if not existing or new_record['max_value'] > existing['record_value']:
                upsert_league_record(
                    conn,
                    category=category,
                    scope=scope,
                    record_value=float(new_record['max_value']),
                    holder_player_id=new_record['player_id'],
                    holder_team_id=None,
                    holder_coach_id=None,
                    holder_name=new_record['player_name'],
                    season_year=season_year,
                    week_number=new_record['week_number'],
                )
                broken_records[category][scope] = True
            else:
                broken_records[category][scope] = False

        # Single-season records
        scope = 'single_season'
        new_record = get_max_stat_single_season(conn, column_name, season_year)
        if new_record and new_record['max_value'] is not None:
            existing = get_league_record(conn, category, scope)
            if not existing or new_record['max_value'] > existing['record_value']:
                upsert_league_record(
                    conn,
                    category=category,
                    scope=scope,
                    record_value=float(new_record['max_value']),
                    holder_player_id=new_record['player_id'],
                    holder_team_id=None,
                    holder_coach_id=None,
                    holder_name=new_record['player_name'],
                    season_year=season_year,
                    week_number=None,
                )
                broken_records[category][scope] = True
            else:
                broken_records[category][scope] = False

        # Career records
        scope = 'career'
        # fg_long is a max stat, not cumulative - query differently
        if category == 'fg_long':
            # For fg_long, find the max fg_long across all player_season_stats
            new_record = conn.execute("""
                SELECT
                    MAX(pss.fg_long) AS max_value,
                    pss.player_id,
                    p.first_name || ' ' || p.last_name AS player_name,
                    t.abbreviation AS team_abbr
                FROM player_season_stats pss
                JOIN player p ON pss.player_id = p.id
                LEFT JOIN team t ON p.team_id = t.id
                WHERE pss.fg_long > 0
                ORDER BY pss.fg_long DESC
                LIMIT 1
            """).fetchone()
        else:
            new_record = get_max_stat_career(conn, column_name)

        if new_record and new_record['max_value'] is not None:
            existing = get_league_record(conn, category, scope)
            if not existing or new_record['max_value'] > existing['record_value']:
                upsert_league_record(
                    conn,
                    category=category,
                    scope=scope,
                    record_value=float(new_record['max_value']),
                    holder_player_id=new_record['player_id'],
                    holder_team_id=None,
                    holder_coach_id=None,
                    holder_name=new_record['player_name'],
                    season_year=season_year,
                    week_number=None,
                )
                broken_records[category][scope] = True
            else:
                broken_records[category][scope] = False

    conn.commit()
    return broken_records


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
    """Write championship details to season table.

    Called by playoffs system when Super Bowl completes.
    For pre-Prompt #8 saves, these fields stay NULL.
    """
    conn.execute("""
        UPDATE season
        SET runner_up_team_id = ?,
            championship_home_score = ?,
            championship_away_score = ?,
            championship_mvp_player_id = ?,
            championship_coach_id = ?
        WHERE year = ?
    """, (runner_up_team_id, home_score, away_score, mvp_player_id, coach_id, season_year))
    conn.commit()


def get_record_book(
    conn: sqlite3.Connection,
    scope: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Return league records with player/team names joined.

    Each dict: {
        'category', 'category_display', 'scope', 'record_value',
        'holder_player_id', 'holder_player_name', 'holder_team_abbr',
        'season_year', 'week_number'
    }
    """
    where_clauses = []
    params = []

    if scope:
        where_clauses.append("lr.scope = ?")
        params.append(scope)
    if category:
        where_clauses.append("lr.category = ?")
        params.append(category)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT
            lr.category,
            lr.scope,
            lr.record_value,
            lr.holder_player_id,
            lr.holder_team_id,
            lr.holder_name,
            lr.season_year,
            lr.week_number,
            p.first_name || ' ' || p.last_name AS holder_player_name,
            t.abbreviation AS holder_team_abbr
        FROM league_record lr
        LEFT JOIN player p ON lr.holder_player_id = p.id
        LEFT JOIN team t ON lr.holder_team_id = t.id
        WHERE {where_sql}
        ORDER BY lr.category, lr.scope
    """

    rows = conn.execute(query, params).fetchall()
    results = []
    for row in rows:
        # Look up display name
        category_display = LEAGUE_RECORD_CATEGORIES.get(row['category'], (row['category'], ''))[0]
        results.append({
            'category': row['category'],
            'category_display': category_display,
            'scope': row['scope'],
            'record_value': row['record_value'],
            'holder_player_id': row['holder_player_id'],
            'holder_player_name': row['holder_player_name'] or row['holder_name'],
            'holder_team_abbr': row['holder_team_abbr'] or '—',
            'season_year': row['season_year'],
            'week_number': row['week_number'],
        })

    return results


def get_all_time_leaders(
    conn: sqlite3.Connection,
    category: str,
    scope: str = 'career',
    top_n: int = ALL_TIME_LEADERS_DEFAULT_TOP_N,
) -> list[dict]:
    """Return top N for a stat category at given scope.

    scope='career': read from player_career_stats (order by career_{column_name})
    scope='single_season': read from player_season_stats (can repeat same player)
    scope='single_game': read from box_score

    Returns sorted descending by value.
    """
    if category not in LEAGUE_RECORD_CATEGORIES:
        return []

    display_name, column_name = LEAGUE_RECORD_CATEGORIES[category]

    if scope == 'career':
        # fg_long is a max stat, not cumulative
        if category == 'fg_long':
            query = f"""
                SELECT
                    MAX(pss.{column_name}) AS value,
                    pss.player_id,
                    p.first_name || ' ' || p.last_name AS player_name,
                    COALESCE(t.abbreviation, 'FA') AS team_abbr,
                    NULL AS season_year
                FROM player_season_stats pss
                JOIN player p ON pss.player_id = p.id
                LEFT JOIN team t ON p.team_id = t.id
                WHERE pss.{column_name} > 0
                GROUP BY pss.player_id
                ORDER BY value DESC
                LIMIT ?
            """
        else:
            query = f"""
                SELECT
                    pcs.career_{column_name} AS value,
                    pcs.player_id,
                    p.first_name || ' ' || p.last_name AS player_name,
                    COALESCE(t.abbreviation, 'FA') AS team_abbr,
                    NULL AS season_year
                FROM player_career_stats pcs
                JOIN player p ON pcs.player_id = p.id
                LEFT JOIN team t ON p.team_id = t.id
                WHERE pcs.career_{column_name} > 0
                ORDER BY pcs.career_{column_name} DESC
                LIMIT ?
            """
        params = (top_n,)
    elif scope == 'single_season':
        query = f"""
            SELECT
                pss.{column_name} AS value,
                pss.player_id,
                p.first_name || ' ' || p.last_name AS player_name,
                t.abbreviation AS team_abbr,
                pss.season_year
            FROM player_season_stats pss
            JOIN player p ON pss.player_id = p.id
            JOIN team t ON pss.team_id = t.id
            WHERE pss.{column_name} > 0
            ORDER BY pss.{column_name} DESC
            LIMIT ?
        """
        params = (top_n,)
    elif scope == 'single_game':
        query = f"""
            SELECT
                bs.{column_name} AS value,
                bs.player_id,
                p.first_name || ' ' || p.last_name AS player_name,
                t.abbreviation AS team_abbr,
                s.year AS season_year,
                w.week_number
            FROM box_score bs
            JOIN game g ON bs.game_id = g.id
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            JOIN player p ON bs.player_id = p.id
            JOIN team t ON bs.team_id = t.id
            WHERE bs.{column_name} > 0
            ORDER BY bs.{column_name} DESC
            LIMIT ?
        """
        params = (top_n,)
    else:
        return []

    rows = conn.execute(query, params).fetchall()
    results = []
    for row in rows:
        # Check if week_number column exists (only for single_game scope)
        week_number = None
        if 'week_number' in row.keys():
            week_number = row['week_number']

        results.append({
            'value': row['value'],
            'player_id': row['player_id'],
            'player_name': row['player_name'],
            'team_abbr': row['team_abbr'],
            'season_year': row['season_year'],
            'week_number': week_number,
        })

    return results


def get_champion_history(
    conn: sqlite3.Connection,
    n: int = CHAMPION_HISTORY_DEFAULT_LIMIT,
) -> list[dict]:
    """Return last N seasons' champion details.

    Each dict: {
        'season_year', 'champion_team_id', 'champion_team_abbr',
        'runner_up_team_id', 'runner_up_team_abbr',
        'final_score', 'mvp_player_id', 'mvp_player_name',
        'coach_id', 'coach_name'
    }

    For pre-Prompt #8 seasons, runner_up/MVP/coach are None.
    Sorted descending by season_year.
    """
    query = """
        SELECT
            s.year AS season_year,
            s.champion_team_id,
            t_champ.abbreviation AS champion_team_abbr,
            s.runner_up_team_id,
            t_runner.abbreviation AS runner_up_team_abbr,
            s.championship_home_score,
            s.championship_away_score,
            s.championship_mvp_player_id,
            p.first_name || ' ' || p.last_name AS mvp_player_name,
            s.championship_coach_id,
            cc.first_name || ' ' || cc.last_name AS coach_name
        FROM season s
        JOIN team t_champ ON s.champion_team_id = t_champ.id
        LEFT JOIN team t_runner ON s.runner_up_team_id = t_runner.id
        LEFT JOIN player p ON s.championship_mvp_player_id = p.id
        LEFT JOIN coach_career cc ON s.championship_coach_id = cc.id
        WHERE s.is_complete = 1
        ORDER BY s.year DESC
        LIMIT ?
    """

    rows = conn.execute(query, (n,)).fetchall()
    results = []
    for row in rows:
        # Construct final score string
        final_score = None
        if row['championship_home_score'] is not None and row['championship_away_score'] is not None:
            # Determine which is champion (higher score)
            if row['championship_home_score'] > row['championship_away_score']:
                final_score = f"{row['championship_home_score']}-{row['championship_away_score']}"
            else:
                final_score = f"{row['championship_away_score']}-{row['championship_home_score']}"

        results.append({
            'season_year': row['season_year'],
            'champion_team_id': row['champion_team_id'],
            'champion_team_abbr': row['champion_team_abbr'],
            'runner_up_team_id': row['runner_up_team_id'],
            'runner_up_team_abbr': row['runner_up_team_abbr'],
            'final_score': final_score,
            'mvp_player_id': row['championship_mvp_player_id'],
            'mvp_player_name': row['mvp_player_name'],
            'coach_id': row['championship_coach_id'],
            'coach_name': row['coach_name'],
        })

    return results


def get_team_record_book(conn: sqlite3.Connection, team_id: int) -> dict:
    """Return team-specific franchise records.

    Future use for narrative beats that reference 'broke franchise record'.
    Not wired into anything in this prompt, but API exists.
    """
    # Query team_season_record for team_id
    records = {}

    for category, (display_name, column_name) in TEAM_RECORD_CATEGORIES.items():
        row = conn.execute(f"""
            SELECT MAX({column_name}) AS max_value, season_year
            FROM team_season_record
            WHERE team_id = ?
            GROUP BY team_id
            ORDER BY max_value DESC
            LIMIT 1
        """, (team_id,)).fetchone()

        if row and row['max_value']:
            records[category] = {
                'display_name': display_name,
                'value': row['max_value'],
                'season_year': row['season_year'],
            }

    return records


def determine_championship_mvp(conn: sqlite3.Connection, game_id: int) -> Optional[int]:
    """Return player_id with highest impact stat in championship game.

    Priority: passing_yards > rushing_yards > receiving_yards > sacks
    """
    # Find top passer
    passer = conn.execute("""
        SELECT player_id, pass_yards
        FROM box_score
        WHERE game_id = ? AND pass_yards > 0
        ORDER BY pass_yards DESC
        LIMIT 1
    """, (game_id,)).fetchone()

    # Find top rusher
    rusher = conn.execute("""
        SELECT player_id, rush_yards
        FROM box_score
        WHERE game_id = ? AND rush_yards > 0
        ORDER BY rush_yards DESC
        LIMIT 1
    """, (game_id,)).fetchone()

    # Find top receiver
    receiver = conn.execute("""
        SELECT player_id, rec_yards
        FROM box_score
        WHERE game_id = ? AND rec_yards > 0
        ORDER BY rec_yards DESC
        LIMIT 1
    """, (game_id,)).fetchone()

    # Find top defender (by sacks)
    defender = conn.execute("""
        SELECT player_id, sacks
        FROM box_score
        WHERE game_id = ? AND sacks > 0
        ORDER BY sacks DESC
        LIMIT 1
    """, (game_id,)).fetchone()

    # Priority: passing_yards > rushing_yards > receiving_yards > sacks
    candidates = []
    if passer:
        candidates.append((passer['player_id'], passer['pass_yards'], 4))
    if rusher:
        candidates.append((rusher['player_id'], rusher['rush_yards'], 3))
    if receiver:
        candidates.append((receiver['player_id'], receiver['rec_yards'], 2))
    if defender:
        candidates.append((defender['player_id'], defender['sacks'] * 20, 1))  # Scale sacks

    if not candidates:
        return None

    # Sort by priority (higher is better), then by value
    candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
    return candidates[0][0]
