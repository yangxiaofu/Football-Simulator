"""
Season loop orchestrator.

Handles week-by-week advancement through the regular season:
simulate all games for a week, update standings, heal injuries,
advance the league calendar.
"""

import sqlite3

from ..db.queries import (
    get_league_state,
    update_league_state,
    get_week,
    mark_week_complete,
    get_unplayed_games_for_week,
    get_all_games_for_week,
    reset_weekly_stamina,
    heal_injured_players,
    get_team,
)
from ..utils.constants import REGULAR_SEASON_WEEKS
from .standings import update_all_standings


def advance_week(
    conn: sqlite3.Connection,
    save_path: str,
    verbose_team_id: int = None,
) -> dict:
    """Simulate all games for the current week and advance the calendar.

    Args:
        conn: Database connection
        save_path: Path to .db file (needed by simulate_game)
        verbose_team_id: If set, print play-by-play for this team's game

    Returns:
        dict with 'week_number', 'results' (list of game result dicts),
        'healed_count' (injuries cleared)
    """
    league = get_league_state(conn)
    if not league:
        raise RuntimeError("League not initialized")

    season_year = league['current_season']
    week_num = league['current_week']

    if week_num < 1:
        # Start of season: set to week 1
        week_num = 1
        with conn:
            update_league_state(conn, season_year, week_num, 'regular')

    # Get the week record
    week_row = get_week(conn, season_year, week_num)
    if not week_row:
        raise RuntimeError(
            f"No week record found for season {season_year}, week {week_num}"
        )

    if week_row['is_complete']:
        raise RuntimeError(
            f"Week {week_num} is already complete. "
            "Advance to next week first."
        )

    # Simulate all unplayed games for this week
    results = simulate_week_games(
        conn, save_path, week_num, season_year, verbose_team_id,
    )

    with conn:
        # Mark week complete
        mark_week_complete(conn, week_row['id'])

        # Update standings
        update_all_standings(conn, season_year)

        # Heal injuries (decrement weeks remaining)
        healed = heal_injured_players(conn)

        # Reset weekly stamina
        reset_weekly_stamina(conn)

        # Advance to next week
        next_week = week_num + 1
        if next_week > REGULAR_SEASON_WEEKS:
            # Regular season complete — transition to playoffs
            update_league_state(conn, season_year, next_week, 'playoffs')
        else:
            update_league_state(conn, season_year, next_week, 'regular')

    return {
        'week_number': week_num,
        'results': results,
        'healed_count': healed,
    }


def simulate_week_games(
    conn: sqlite3.Connection,
    save_path: str,
    week_number: int,
    season_year: int,
    verbose_team_id: int = None,
) -> list[dict]:
    """Simulate all unplayed games for a given week.

    Args:
        conn: Database connection
        save_path: Path to .db file
        week_number: Week number to simulate
        season_year: Season year
        verbose_team_id: Optional team ID for verbose output

    Returns:
        List of game result dicts from simulate_game
    """
    from ..engine.game_sim import simulate_game

    games = get_unplayed_games_for_week(conn, season_year, week_number)
    results = []

    for game in games:
        # Determine verbosity
        verbose = False
        if verbose_team_id:
            if (game['home_team_id'] == verbose_team_id or
                    game['away_team_id'] == verbose_team_id):
                verbose = True

        result = simulate_game(save_path, game['id'], verbose=verbose)
        results.append(result)

    return results


def is_regular_season_complete(
    conn: sqlite3.Connection, season_year: int,
) -> bool:
    """Check if all regular season weeks (1-17) are complete."""
    for wk in range(1, REGULAR_SEASON_WEEKS + 1):
        week_row = get_week(conn, season_year, wk)
        if not week_row or not week_row['is_complete']:
            return False
    return True


def get_current_status(conn: sqlite3.Connection) -> dict:
    """Get current season status for display.

    Returns dict with season, week, phase, and upcoming matchups.
    """
    league = get_league_state(conn)
    if not league:
        return {'error': 'League not initialized'}

    season_year = league['current_season']
    week_num = league['current_week']
    phase = league['current_phase']

    status = {
        'season': season_year,
        'week': week_num,
        'phase': phase,
        'user_team_id': league['user_team_id'],
    }

    # Get upcoming games for the current week
    if week_num >= 1:
        games = get_all_games_for_week(conn, season_year, week_num)
        matchups = []
        for g in games:
            home = get_team(conn, g['home_team_id'])
            away = get_team(conn, g['away_team_id'])
            matchup = {
                'game_id': g['id'],
                'home_team': f"{home['city']} {home['nickname']}",
                'home_abbr': home['abbreviation'],
                'away_team': f"{away['city']} {away['nickname']}",
                'away_abbr': away['abbreviation'],
                'is_complete': bool(g['is_complete']),
            }
            if g['is_complete']:
                matchup['home_score'] = g['home_score']
                matchup['away_score'] = g['away_score']
            matchups.append(matchup)
        status['matchups'] = matchups

    return status
