"""
Phase 5 — In-season stats display (presentation layer).

All functions are pure display — no SQL, all queries via src/db/queries.py.
"""

import sqlite3
from typing import Optional

from ..db.queries import (
    get_season_running_leaders,
    get_leaderboard_through_week,
    get_leaderboard_single_week,
    get_player_weekly_history,
    get_player,
    get_team,
    get_team_by_abbreviation,
    get_team_season_running,
    get_all_player_week_stats,
    get_weekly_awards_display,
    get_league_state,
)
from ..utils.constants import (
    LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME,
    LEADERBOARD_QUALIFIER_RUSH_CAR_PER_GAME,
    LEADERBOARD_STAT_MAP,
    LEADERBOARD_RANK_WIDTH,
    LEADERBOARD_NAME_WIDTH,
    LEADERBOARD_TEAM_WIDTH,
    LEADERBOARD_STAT_WIDTH,
)


def print_leaderboard(
    conn: sqlite3.Connection,
    season_year: int,
    category: str,
    limit: int = 10,
    through_week: Optional[int] = None,
    single_week: Optional[int] = None
) -> None:
    """
    Display top N players in a stat category with NFL-style qualifiers.

    Args:
        conn: Database connection
        season_year: Season year
        category: Category key from LEADERBOARD_STAT_MAP (e.g., 'passing', 'rushing')
        limit: Number of players to display (default 10)
        through_week: Show stats through this week (SUM weeks 1-N)
        single_week: Show stats for only this week
    """
    stat_column = LEADERBOARD_STAT_MAP[category]

    # Choose query function based on week filter
    if through_week:
        raw_leaders = get_leaderboard_through_week(
            conn, season_year, stat_column, through_week, is_playoff=0, limit=limit * 2
        )
        scope_desc = f"Through Week {through_week}"
    elif single_week:
        raw_leaders = get_leaderboard_single_week(
            conn, season_year, stat_column, single_week, is_playoff=0, limit=limit * 2
        )
        scope_desc = f"Week {single_week}"
    else:
        # Over-fetch to account for filtered players
        raw_leaders = get_season_running_leaders(
            conn, season_year, stat_column, is_playoff=0, limit=limit * 2
        )
        scope_desc = "Season-to-Date"

    if not raw_leaders:
        print("=" * 70)
        print(f"IN-SEASON LEADERBOARD — {category.upper()} ({season_year} {scope_desc})")
        print("=" * 70)
        print("  No data available yet.")
        return

    # Enrich with player/team metadata and apply qualifiers
    leaders = []
    filtered_count = 0

    for row in raw_leaders:
        player = get_player(conn, row['player_id'])
        team = get_team(conn, row['team_id'])

        if not player or not team:
            continue

        # Apply qualifiers for passing/rushing
        if category == 'passing':
            min_att = LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME * row['games_played']
            if row['pass_attempts'] < min_att:
                filtered_count += 1
                continue
        elif category == 'rushing':
            min_car = LEADERBOARD_QUALIFIER_RUSH_CAR_PER_GAME * row['games_played']
            if row['carries'] < min_car:
                filtered_count += 1
                continue

        leaders.append({
            'player': player,
            'team': team,
            'stats': row,
        })

        if len(leaders) >= limit:
            break

    # Print header
    print("=" * 70)
    print(f"IN-SEASON LEADERBOARD — {category.upper()} ({season_year} {scope_desc})")
    print("=" * 70)

    # Print table based on category
    if category == 'passing':
        _print_passing_leaderboard(leaders)
    elif category == 'rushing':
        _print_rushing_leaderboard(leaders)
    elif category == 'receiving':
        _print_receiving_leaderboard(leaders)
    elif category in ('defense', 'tackles'):
        _print_defense_leaderboard(leaders)
    elif category == 'sacks':
        _print_sacks_leaderboard(leaders)
    elif category == 'interceptions':
        _print_interceptions_leaderboard(leaders)
    else:
        _print_generic_leaderboard(leaders, stat_column)

    # Print qualifier note if applicable
    if filtered_count > 0:
        if category == 'passing':
            min_att = int(LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME * leaders[0]['stats']['games_played']) if leaders else 0
            print(f"\n({filtered_count} players excluded: minimum {min_att} attempts required)")
        elif category == 'rushing':
            min_car = int(LEADERBOARD_QUALIFIER_RUSH_CAR_PER_GAME * leaders[0]['stats']['games_played']) if leaders else 0
            print(f"\n({filtered_count} players excluded: minimum {min_car} carries required)")


def _print_passing_leaderboard(leaders):
    """Print passing leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'ATT':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'CMP':>{LEADERBOARD_STAT_WIDTH}} {'YDS':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'TD':>{LEADERBOARD_STAT_WIDTH}} {'INT':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'RTG':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']

        # Calculate passer rating if not available
        passer_rating = _calculate_passer_rating(
            s['pass_attempts'], s['completions'], s['pass_yards'],
            s['pass_tds'], s['interceptions_thrown']
        )

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['pass_attempts']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['completions']:>{LEADERBOARD_STAT_WIDTH}} {s['pass_yards']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['pass_tds']:>{LEADERBOARD_STAT_WIDTH}} {s['interceptions_thrown']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{passer_rating:>{LEADERBOARD_STAT_WIDTH}.1f}")


def _print_rushing_leaderboard(leaders):
    """Print rushing leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'CAR':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'YDS':>{LEADERBOARD_STAT_WIDTH}} {'TD':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'YPC':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']
        ypc = s['rush_yards'] / s['carries'] if s['carries'] > 0 else 0.0

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['carries']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['rush_yards']:>{LEADERBOARD_STAT_WIDTH}} {s['rush_tds']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{ypc:>{LEADERBOARD_STAT_WIDTH}.1f}")


def _print_receiving_leaderboard(leaders):
    """Print receiving leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'TGT':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'REC':>{LEADERBOARD_STAT_WIDTH}} {'YDS':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'TD':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['targets']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['receptions']:>{LEADERBOARD_STAT_WIDTH}} {s['rec_yards']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['rec_tds']:>{LEADERBOARD_STAT_WIDTH}}")


def _print_defense_leaderboard(leaders):
    """Print defense leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'TKL':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'SCK':>{LEADERBOARD_STAT_WIDTH}} {'INT':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'PD':>{LEADERBOARD_STAT_WIDTH}} {'FF':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['tackles']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['sacks']:>{LEADERBOARD_STAT_WIDTH}.1f} {s['interceptions']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['pass_deflections']:>{LEADERBOARD_STAT_WIDTH}} {s['forced_fumbles']:>{LEADERBOARD_STAT_WIDTH}}")


def _print_sacks_leaderboard(leaders):
    """Print sacks leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'SCK':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'TKL':>{LEADERBOARD_STAT_WIDTH}} {'FF':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['sacks']:>{LEADERBOARD_STAT_WIDTH}.1f} "
              f"{s['tackles']:>{LEADERBOARD_STAT_WIDTH}} {s['forced_fumbles']:>{LEADERBOARD_STAT_WIDTH}}")


def _print_interceptions_leaderboard(leaders):
    """Print interceptions leaderboard table."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {'INT':>{LEADERBOARD_STAT_WIDTH}} "
          f"{'PD':>{LEADERBOARD_STAT_WIDTH}} {'TKL':>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {s['interceptions']:>{LEADERBOARD_STAT_WIDTH}} "
              f"{s['pass_deflections']:>{LEADERBOARD_STAT_WIDTH}} {s['tackles']:>{LEADERBOARD_STAT_WIDTH}}")


def _print_generic_leaderboard(leaders, stat_column):
    """Print generic leaderboard table for any stat."""
    print(f"{'Rank':<{LEADERBOARD_RANK_WIDTH}} {'Player':<{LEADERBOARD_NAME_WIDTH}} "
          f"{'Team':<{LEADERBOARD_TEAM_WIDTH}} {stat_column.upper():>{LEADERBOARD_STAT_WIDTH}}")
    print("-" * 70)

    for i, entry in enumerate(leaders, 1):
        p = entry['player']
        t = entry['team']
        s = entry['stats']

        player_name = f"{p['first_name']} {p['last_name']}"
        team_abbr = t['abbreviation']
        value = s.get(stat_column, 0)

        print(f"{i:<{LEADERBOARD_RANK_WIDTH}} {player_name:<{LEADERBOARD_NAME_WIDTH}} "
              f"{team_abbr:<{LEADERBOARD_TEAM_WIDTH}} {value:>{LEADERBOARD_STAT_WIDTH}}")


def print_player_weekly_history(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int
) -> None:
    """
    Display week-by-week stats for one player across the season.

    Args:
        conn: Database connection
        player_id: Player ID
        season_year: Season year
    """
    player = get_player(conn, player_id)
    if not player:
        print(f"Error: Player {player_id} not found.")
        return

    team = get_team(conn, player['team_id'])
    if not team:
        print(f"Error: Team not found for player {player_id}.")
        return

    history = get_player_weekly_history(conn, player_id, season_year, is_playoff=0)

    if not history:
        print("=" * 70)
        print(f"PLAYER WEEKLY HISTORY — {player['first_name']} {player['last_name']} "
              f"({player['position']}, {team['city']} {team['nickname']})")
        print("=" * 70)
        print(f"{season_year} Regular Season\n")
        print("  No games played yet.")
        return

    # Print header
    print("=" * 70)
    print(f"PLAYER WEEKLY HISTORY — {player['first_name']} {player['last_name']} "
          f"({player['position']}, {team['city']} {team['nickname']})")
    print("=" * 70)
    print(f"{season_year} Regular Season\n")

    # Print table based on position
    position = player['position']
    if position == 'QB':
        _print_qb_history(history)
    elif position in ('RB', 'FB'):
        _print_rb_history(history)
    elif position in ('WR', 'TE'):
        _print_receiver_history(history)
    elif position in ('CB', 'S', 'LB', 'DE', 'DT', 'OLB', 'MLB', 'ILB'):
        _print_defense_history(history)
    else:
        _print_generic_history(history, position)


def _print_qb_history(history):
    """Print QB weekly history table."""
    print(f"{'Week':>6}  {'ATT':>5} {'CMP':>5} {'YDS':>6} {'TD':>4} {'INT':>4} {'RTG':>6}")
    print("-" * 45)

    totals = {
        'pass_attempts': 0,
        'completions': 0,
        'pass_yards': 0,
        'pass_tds': 0,
        'interceptions_thrown': 0,
    }

    for week in history:
        # Calculate weekly passer rating
        week_rating = _calculate_passer_rating(
            week['pass_attempts'], week['completions'], week['pass_yards'],
            week['pass_tds'], week['interceptions_thrown']
        )

        print(f"{week['week_number']:>6}  {week['pass_attempts']:>5} {week['completions']:>5} "
              f"{week['pass_yards']:>6} {week['pass_tds']:>4} "
              f"{week['interceptions_thrown']:>4} {week_rating:>6.1f}")

        totals['pass_attempts'] += week['pass_attempts']
        totals['completions'] += week['completions']
        totals['pass_yards'] += week['pass_yards']
        totals['pass_tds'] += week['pass_tds']
        totals['interceptions_thrown'] += week['interceptions_thrown']

    # Calculate season passer rating
    season_rating = _calculate_passer_rating(
        totals['pass_attempts'],
        totals['completions'],
        totals['pass_yards'],
        totals['pass_tds'],
        totals['interceptions_thrown']
    )

    print("-" * 45)
    print(f"{'TOTAL':>6}  {totals['pass_attempts']:>5} {totals['completions']:>5} "
          f"{totals['pass_yards']:>6} {totals['pass_tds']:>4} "
          f"{totals['interceptions_thrown']:>4} {season_rating:>6.1f}")


def _print_rb_history(history):
    """Print RB weekly history table."""
    print(f"{'Week':>6}  {'CAR':>5} {'YDS':>6} {'TD':>4} {'YPC':>6}  "
          f"{'REC':>5} {'REC_YDS':>7}")
    print("-" * 50)

    totals = {
        'carries': 0,
        'rush_yards': 0,
        'rush_tds': 0,
        'receptions': 0,
        'rec_yards': 0,
    }

    for week in history:
        ypc = week['rush_yards'] / week['carries'] if week['carries'] > 0 else 0.0
        print(f"{week['week_number']:>6}  {week['carries']:>5} {week['rush_yards']:>6} "
              f"{week['rush_tds']:>4} {ypc:>6.1f}  "
              f"{week['receptions']:>5} {week['rec_yards']:>7}")

        totals['carries'] += week['carries']
        totals['rush_yards'] += week['rush_yards']
        totals['rush_tds'] += week['rush_tds']
        totals['receptions'] += week['receptions']
        totals['rec_yards'] += week['rec_yards']

    season_ypc = totals['rush_yards'] / totals['carries'] if totals['carries'] > 0 else 0.0

    print("-" * 50)
    print(f"{'TOTAL':>6}  {totals['carries']:>5} {totals['rush_yards']:>6} "
          f"{totals['rush_tds']:>4} {season_ypc:>6.1f}  "
          f"{totals['receptions']:>5} {totals['rec_yards']:>7}")


def _print_receiver_history(history):
    """Print WR/TE weekly history table."""
    print(f"{'Week':>6}  {'TGT':>5} {'REC':>5} {'YDS':>6} {'TD':>4}")
    print("-" * 35)

    totals = {
        'targets': 0,
        'receptions': 0,
        'rec_yards': 0,
        'rec_tds': 0,
    }

    for week in history:
        print(f"{week['week_number']:>6}  {week['targets']:>5} {week['receptions']:>5} "
              f"{week['rec_yards']:>6} {week['rec_tds']:>4}")

        totals['targets'] += week['targets']
        totals['receptions'] += week['receptions']
        totals['rec_yards'] += week['rec_yards']
        totals['rec_tds'] += week['rec_tds']

    print("-" * 35)
    print(f"{'TOTAL':>6}  {totals['targets']:>5} {totals['receptions']:>5} "
          f"{totals['rec_yards']:>6} {totals['rec_tds']:>4}")


def _print_defense_history(history):
    """Print defensive player weekly history table."""
    print(f"{'Week':>6}  {'TKL':>5} {'SCK':>5} {'INT':>4} {'PD':>4} {'FF':>4}")
    print("-" * 40)

    totals = {
        'tackles': 0,
        'sacks': 0.0,
        'interceptions': 0,
        'pass_deflections': 0,
        'forced_fumbles': 0,
    }

    for week in history:
        print(f"{week['week_number']:>6}  {week['tackles']:>5} {week['sacks']:>5.1f} "
              f"{week['interceptions']:>4} {week['pass_deflections']:>4} "
              f"{week['forced_fumbles']:>4}")

        totals['tackles'] += week['tackles']
        totals['sacks'] += week['sacks']
        totals['interceptions'] += week['interceptions']
        totals['pass_deflections'] += week['pass_deflections']
        totals['forced_fumbles'] += week['forced_fumbles']

    print("-" * 40)
    print(f"{'TOTAL':>6}  {totals['tackles']:>5} {totals['sacks']:>5.1f} "
          f"{totals['interceptions']:>4} {totals['pass_deflections']:>4} "
          f"{totals['forced_fumbles']:>4}")


def _print_generic_history(history, position):
    """Print generic weekly history for other positions."""
    print(f"Week-by-week stats for {position} (limited data available)\n")
    print(f"{'Week':>6}  {'Games Played':>13}")
    print("-" * 25)

    for week in history:
        print(f"{week['week_number']:>6}  {'Yes':>13}")

    print("-" * 25)
    print(f"{'TOTAL':>6}  {len(history):>13}")


def _calculate_passer_rating(attempts, completions, yards, tds, ints):
    """Calculate NFL passer rating."""
    if attempts == 0:
        return 0.0

    a = max(0, min(2.375, (completions / attempts - 0.3) * 5))
    b = max(0, min(2.375, (yards / attempts - 3) * 0.25))
    c = max(0, min(2.375, (tds / attempts) * 20))
    d = max(0, min(2.375, 2.375 - (ints / attempts * 25)))

    return ((a + b + c + d) / 6) * 100


def print_team_season_stats(
    conn: sqlite3.Connection,
    team_abbr: str,
    season_year: int
) -> None:
    """
    Display team offensive/defensive stats for current season.

    Args:
        conn: Database connection
        team_abbr: Team abbreviation (e.g., 'CHI', 'DAL')
        season_year: Season year
    """
    team = get_team_by_abbreviation(conn, team_abbr)
    if not team:
        print(f"Error: Team '{team_abbr}' not found.")
        return

    stats = get_team_season_running(conn, season_year, team['id'], is_playoff=0)
    if not stats or stats['games_played'] == 0:
        print("=" * 70)
        print(f"TEAM STATS — {team['city']} {team['nickname']} ({season_year} Regular Season)")
        print("=" * 70)
        print("  No games played yet.")
        return

    games = stats['games_played']

    # Print header
    print("=" * 70)
    print(f"TEAM STATS — {team['city']} {team['nickname']} ({season_year} Regular Season)")
    print("=" * 70)
    print()

    # Offense section
    print(f"OFFENSE ({games} games)")
    print(f"  Points Scored:    {stats['points_scored']:>5}  ({stats['points_scored']/games:.1f} per game)")
    print(f"  Total Yards:      {stats['total_yards']:>5}  ({stats['total_yards']/games:.1f} per game)")
    print(f"  Pass Yards:       {stats['pass_yards']:>5}  ({stats['pass_yards']/games:.1f} per game)")
    print(f"  Rush Yards:       {stats['rush_yards']:>5}  ({stats['rush_yards']/games:.1f} per game)")
    print(f"  Turnovers:        {stats['turnovers']:>5}  ({stats['turnovers']/games:.1f} per game)")
    print()

    # Defense section
    print(f"DEFENSE ({games} games)")
    print(f"  Points Allowed:   {stats['points_allowed']:>5}  ({stats['points_allowed']/games:.1f} per game)")
    print(f"  Yards Allowed:    {stats['yards_allowed']:>5}  ({stats['yards_allowed']/games:.1f} per game)")
    print(f"  Sacks:            {stats['sacks_recorded']:>5.1f}  ({stats['sacks_recorded']/games:.1f} per game)")
    print(f"  Takeaways:        {stats['takeaways']:>5}  ({stats['takeaways']/games:.1f} per game)")
    print()

    # Record
    wins = stats['wins']
    losses = stats['losses']
    ties = stats['ties']
    total = wins + losses + ties
    win_pct = wins / total if total > 0 else 0.0
    print(f"RECORD: {wins}-{losses}-{ties} (Win %, {win_pct:.3f})")


def print_week_stats(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int
) -> None:
    """
    Display all stats from a specific completed week (top performances).

    Args:
        conn: Database connection
        season_year: Season year
        week_number: Week number
    """
    all_stats = get_all_player_week_stats(conn, season_year, week_number, is_playoff=0)

    if not all_stats:
        print("=" * 70)
        print(f"WEEK {week_number} STATS — {season_year} Regular Season")
        print("=" * 70)
        print("  No games played this week yet.")
        return

    # Separate by position groups
    qbs = []
    rbs = []
    receivers = []
    defenders = []

    for stat_row in all_stats:
        player = get_player(conn, stat_row['player_id'])
        team = get_team(conn, stat_row['team_id'])

        if not player or not team:
            continue

        entry = {
            'player': player,
            'team': team,
            'stats': stat_row,
        }

        pos = player['position']
        if pos == 'QB':
            qbs.append(entry)
        elif pos in ('RB', 'FB'):
            rbs.append(entry)
        elif pos in ('WR', 'TE'):
            receivers.append(entry)
        elif pos in ('CB', 'S', 'LB', 'DE', 'DT', 'OLB', 'MLB', 'ILB'):
            defenders.append(entry)

    # Sort each group and take top 3
    qbs.sort(key=lambda x: x['stats']['pass_yards'], reverse=True)
    rbs.sort(key=lambda x: x['stats']['rush_yards'], reverse=True)
    receivers.sort(key=lambda x: x['stats']['rec_yards'], reverse=True)
    defenders.sort(key=lambda x: x['stats']['tackles'], reverse=True)

    top_qbs = qbs[:3]
    top_rbs = rbs[:3]
    top_receivers = receivers[:3]
    top_defenders = defenders[:3]

    # Print header
    print("=" * 70)
    print(f"WEEK {week_number} STATS — {season_year} Regular Season")
    print("=" * 70)
    print()

    # Print top passers
    if top_qbs:
        print("TOP PASSERS")
        for i, entry in enumerate(top_qbs, 1):
            p = entry['player']
            t = entry['team']
            s = entry['stats']
            print(f"  {i}. {p['first_name']} {p['last_name']} ({t['abbreviation']})  "
                  f"{s['pass_yards']} yards, {s['pass_tds']} TD, "
                  f"{s['interceptions_thrown']} INT")
        print()

    # Print top rushers
    if top_rbs:
        print("TOP RUSHERS")
        for i, entry in enumerate(top_rbs, 1):
            p = entry['player']
            t = entry['team']
            s = entry['stats']
            print(f"  {i}. {p['first_name']} {p['last_name']} ({t['abbreviation']})  "
                  f"{s['rush_yards']} yards, {s['rush_tds']} TD")
        print()

    # Print top receivers
    if top_receivers:
        print("TOP RECEIVERS")
        for i, entry in enumerate(top_receivers, 1):
            p = entry['player']
            t = entry['team']
            s = entry['stats']
            print(f"  {i}. {p['first_name']} {p['last_name']} ({t['abbreviation']})  "
                  f"{s['rec_yards']} yards, {s['rec_tds']} TD")
        print()

    # Print top defenders
    if top_defenders:
        print("TOP DEFENDERS")
        for i, entry in enumerate(top_defenders, 1):
            p = entry['player']
            t = entry['team']
            s = entry['stats']
            sacks_str = f", {s['sacks']:.1f} sacks" if s['sacks'] > 0 else ""
            ints_str = f", {s['interceptions']} INT" if s['interceptions'] > 0 else ""
            pd_str = f", {s['pass_deflections']} PD" if s['pass_deflections'] > 0 else ""
            print(f"  {i}. {p['first_name']} {p['last_name']} ({t['abbreviation']})  "
                  f"{s['tackles']} tackles{sacks_str}{ints_str}{pd_str}")


def print_stars_of_week(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: Optional[int] = None
) -> None:
    """Display Stars of the Week awards."""
    awards = get_weekly_awards_display(conn, season_year, week_number)

    if not awards:
        print("=" * 70)
        if week_number:
            print(f"STARS OF THE WEEK — Week {week_number}, {season_year}")
        else:
            print(f"STARS OF THE WEEK — {season_year}")
        print("=" * 70)
        print()
        print("No Stars of the Week available for that range.")
        return

    league = get_league_state(conn)
    user_team_id = league['user_team_id'] if league else None

    # Group by week_number
    weeks_seen = []
    by_week: dict[int, list] = {}
    for row in awards:
        wk = row['week_number']
        if wk not in by_week:
            by_week[wk] = []
            weeks_seen.append(wk)
        by_week[wk].append(row)

    award_label = {
        'OFFENSE': 'Offensive Player',
        'DEFENSE': 'Defensive Player',
        'SPECIAL_TEAMS': 'Special Teams Player',
        'USER_TEAM_MVP': 'Your Team MVP',
    }

    for wk in weeks_seen:
        print("=" * 70)
        label = f"STARS OF THE WEEK — Week {wk}, {season_year}"
        print(label)
        print("=" * 70)
        for row in by_week[wk]:
            award_type = row['award_type']
            name = f"{row['first_name']} {row['last_name']}"
            team = row['team_abbr']
            pos = row['position']
            is_user = (row['team_id'] == user_team_id)
            marker = " ◄ YOUR TEAM" if is_user else ""
            category = award_label.get(award_type, award_type)
            print(f"  {category}: {name} ({team}, {pos}){marker}")
            if row['narrative_blurb']:
                print(f"    {row['narrative_blurb']}")
        print()
