"""
Terminal display for team rosters with contract info.
"""

import sqlite3

from ..db.queries import get_team, get_roster_with_contracts
from ..utils.constants import to_letter_grade


def print_roster_with_contracts(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
) -> None:
    """Print a team roster showing letter grades and contract status."""
    team = get_team(conn, team_id)
    if not team:
        print(f"  Team {team_id} not found.")
        return

    players = get_roster_with_contracts(conn, team_id, season_year)

    print(f"\n  {team['city']} {team['nickname']} Roster")
    print(f"  Cap Space: ${team['cap_space']:,}")
    print(f"  {'Pos':<4} {'Player':<25} {'Age':>4} {'OVR':<4} "
          f"{'Exp':>4} {'Status':<10} {'Cap Hit':>12}")
    print(f"  {'-'*67}")

    current_pos = None
    for p in players:
        if p['position'] != current_pos:
            if current_pos is not None:
                print()  # Blank line between position groups
            current_pos = p['position']

        name = f"{p['first_name']} {p['last_name']}"
        grade = to_letter_grade(p['true_overall'])

        # Injury indicator
        status = p['roster_status']
        if p['injury_status']:
            status = p['injury_status']

        cap_hit = p['cap_hit'] or 0
        cap_str = f"${cap_hit:,}" if cap_hit else "-"

        print(f"  {p['position']:<4} {name:<25} {p['age']:>4} {grade:<4} "
              f"{p['years_experience']:>4} {status:<10} {cap_str:>12}")

    print(f"\n  Total players: {len(players)}")
