"""
Terminal display for division and conference standings.
"""

import sqlite3

from ..db.queries import (
    get_all_divisions,
    get_conferences,
    get_conference_divisions,
    get_division_teams,
    get_team,
    get_division_by_id,
    get_conference_by_id,
)
from ..league.standings import (
    get_division_standings,
    get_conference_standings,
    get_playoff_seeds,
)


def print_division_standings(
    conn: sqlite3.Connection,
    division_id: int,
    season_year: int,
) -> None:
    """Print formatted standings for a single division."""
    div = get_division_by_id(conn, division_id)
    standings = get_division_standings(conn, division_id, season_year)

    print(f"\n  {div['name']}")
    print(f"  {'Team':<25} {'W':>3} {'L':>3} {'T':>3} {'PF':>5} {'PA':>5} {'DIFF':>5}")
    print(f"  {'-'*49}")

    for rec in standings:
        team = get_team(conn, rec['team_id'])
        name = f"{team['city']} {team['nickname']}"
        diff = rec['point_diff']
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"  {name:<25} {rec['wins']:>3} {rec['losses']:>3} "
              f"{rec['ties']:>3} {rec['points_for']:>5} "
              f"{rec['points_against']:>5} {diff_str:>5}")


def print_conference_standings(
    conn: sqlite3.Connection,
    conference_id: int,
    season_year: int,
) -> None:
    """Print formatted standings for a conference with playoff seeding."""
    conf = get_conference_by_id(conn, conference_id)

    print(f"\n{'='*55}")
    print(f"  {conf['name']} Standings")
    print(f"{'='*55}")

    # Print each division
    divisions = get_conference_divisions(conn, conference_id)
    for div in divisions:
        print_division_standings(conn, div['id'], season_year)

    # Print playoff picture
    seeds = get_playoff_seeds(conn, conference_id, season_year)
    if seeds:
        print(f"\n  {conf['name']} Playoff Seeds:")
        for s in seeds:
            team = get_team(conn, s['team_id'])
            rec = s['record']
            tag = " (BYE)" if s['seed'] == 1 else ""
            wc = " *" if s['seed'] >= 5 else ""
            print(f"    {s['seed']}. {team['city']} {team['nickname']} "
                  f"({rec['wins']}-{rec['losses']}-{rec['ties']}){tag}{wc}")
        print(f"    * = Wild Card")


def print_all_standings(
    conn: sqlite3.Connection, season_year: int,
) -> None:
    """Print full league standings (all 8 divisions, both conferences)."""
    conferences = get_conferences(conn)
    for conf in conferences:
        print_conference_standings(conn, conf['id'], season_year)
    print()
