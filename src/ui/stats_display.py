"""
Terminal display for stat leaderboards.
"""

import sqlite3

from ..db.queries import get_season_stats_leaders


def print_passing_leaders(
    conn: sqlite3.Connection, season_year: int, limit: int = 10,
) -> None:
    """Print top passers by yards."""
    leaders = get_season_stats_leaders(conn, season_year, 'pass_yards', limit)

    print(f"\n  Passing Leaders — {season_year}")
    print(f"  {'Rank':<5} {'Player':<25} {'Team':<5} {'ATT':>5} {'CMP':>5} "
          f"{'YDS':>6} {'TD':>4} {'INT':>4} {'RTG':>6}")
    print(f"  {'-'*65}")

    for i, row in enumerate(leaders, 1):
        name = f"{row['first_name']} {row['last_name']}"
        rating = row['passer_rating'] or 0.0
        print(f"  {i:<5} {name:<25} {row['team_abbr']:<5} "
              f"{row['pass_attempts']:>5} {row['completions']:>5} "
              f"{row['pass_yards']:>6} {row['pass_tds']:>4} "
              f"{row['interceptions_thrown']:>4} {rating:>6.1f}")


def print_rushing_leaders(
    conn: sqlite3.Connection, season_year: int, limit: int = 10,
) -> None:
    """Print top rushers by yards."""
    leaders = get_season_stats_leaders(conn, season_year, 'rush_yards', limit)

    print(f"\n  Rushing Leaders — {season_year}")
    print(f"  {'Rank':<5} {'Player':<25} {'Team':<5} {'CAR':>5} "
          f"{'YDS':>6} {'TD':>4} {'YPC':>5}")
    print(f"  {'-'*55}")

    for i, row in enumerate(leaders, 1):
        name = f"{row['first_name']} {row['last_name']}"
        ypc = row['yards_per_carry'] or 0.0
        print(f"  {i:<5} {name:<25} {row['team_abbr']:<5} "
              f"{row['carries']:>5} {row['rush_yards']:>6} "
              f"{row['rush_tds']:>4} {ypc:>5.1f}")


def print_receiving_leaders(
    conn: sqlite3.Connection, season_year: int, limit: int = 10,
) -> None:
    """Print top receivers by yards."""
    leaders = get_season_stats_leaders(conn, season_year, 'rec_yards', limit)

    print(f"\n  Receiving Leaders — {season_year}")
    print(f"  {'Rank':<5} {'Player':<25} {'Team':<5} {'TGT':>5} {'REC':>5} "
          f"{'YDS':>6} {'TD':>4}")
    print(f"  {'-'*55}")

    for i, row in enumerate(leaders, 1):
        name = f"{row['first_name']} {row['last_name']}"
        print(f"  {i:<5} {name:<25} {row['team_abbr']:<5} "
              f"{row['targets']:>5} {row['receptions']:>5} "
              f"{row['rec_yards']:>6} {row['rec_tds']:>4}")


def print_defensive_leaders(
    conn: sqlite3.Connection, season_year: int, limit: int = 10,
) -> None:
    """Print top defenders by tackles."""
    leaders = get_season_stats_leaders(conn, season_year, 'tackles', limit)

    print(f"\n  Defensive Leaders (Tackles) — {season_year}")
    print(f"  {'Rank':<5} {'Player':<25} {'Team':<5} {'TKL':>5} "
          f"{'SCK':>5} {'INT':>4} {'PD':>4}")
    print(f"  {'-'*55}")

    for i, row in enumerate(leaders, 1):
        name = f"{row['first_name']} {row['last_name']}"
        sacks = row['sacks'] or 0.0
        print(f"  {i:<5} {name:<25} {row['team_abbr']:<5} "
              f"{row['tackles']:>5} {sacks:>5.1f} "
              f"{row['interceptions']:>4} {row['pass_deflections']:>4}")

    # Also show sack leaders
    sack_leaders = get_season_stats_leaders(conn, season_year, 'sacks', limit)

    print(f"\n  Sack Leaders — {season_year}")
    print(f"  {'Rank':<5} {'Player':<25} {'Team':<5} {'SCK':>5} "
          f"{'TKL':>5}")
    print(f"  {'-'*45}")

    for i, row in enumerate(sack_leaders, 1):
        name = f"{row['first_name']} {row['last_name']}"
        sacks = row['sacks'] or 0.0
        print(f"  {i:<5} {name:<25} {row['team_abbr']:<5} "
              f"{sacks:>5.1f} {row['tackles']:>5}")


def print_all_leaders(
    conn: sqlite3.Connection, season_year: int, limit: int = 10,
) -> None:
    """Print all stat leaderboards."""
    print_passing_leaders(conn, season_year, limit)
    print_rushing_leaders(conn, season_year, limit)
    print_receiving_leaders(conn, season_year, limit)
    print_defensive_leaders(conn, season_year, limit)
    print()
