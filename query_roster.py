#!/usr/bin/env python3
"""
Query and display a team's roster.

Phase 0 exit criteria: This script must successfully print a team's
53-player roster with positions, ages, overall grades, and cap hits.

Usage:
    python query_roster.py saves/my_franchise.db --team CHI
    python query_roster.py saves/my_franchise.db --team "Green Bay"
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db import get_connection, get_team_by_abbreviation, get_roster
from src.utils.constants import to_letter_grade


def format_cap_hit(cap_hit: int) -> str:
    """Format cap hit as readable string."""
    if cap_hit >= 1_000_000:
        return f"${cap_hit / 1_000_000:.2f}M"
    elif cap_hit >= 1_000:
        return f"${cap_hit / 1_000:.0f}K"
    else:
        return f"${cap_hit}"


def display_roster(conn, team_abbr: str):
    """Display a team's roster."""
    # Find team
    team = get_team_by_abbreviation(conn, team_abbr)
    if not team:
        print(f"❌ Team '{team_abbr}' not found")
        return False

    # Get roster
    roster = get_roster(conn, team['id'], roster_status='active')

    if not roster:
        print(f"❌ No players found for {team['city']} {team['nickname']}")
        return False

    # Display team info
    print(f"\n{'=' * 90}")
    print(f"  {team['city']} {team['nickname']} ({team['abbreviation']})")
    print(f"  Salary Cap Space: {format_cap_hit(team['cap_space'])}")
    print(f"  Stadium: {team['stadium_type'].title()}")
    print(f"  Climate: {team['home_city_climate'].title()}")
    print(f"={'=' * 90}\n")

    # Get current season for cap hit lookup
    league = conn.execute("SELECT current_season FROM league WHERE id = 1").fetchone()
    season_year = league[0] if league else 2024

    # Group by position
    by_position = {}
    for player in roster:
        pos = player['position']
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(player)

    # Display by position
    position_order = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P']

    print(f"{'POS':<4} {'NAME':<25} {'AGE':<4} {'YRS':<4} {'OVERALL':<8} {'CAP HIT':<12} {'COLLEGE':<20}")
    print(f"{'-' * 90}")

    total_on_roster = 0

    for pos in position_order:
        if pos not in by_position:
            continue

        players = by_position[pos]
        # Sort by overall rating (descending)
        players.sort(key=lambda p: p['true_overall'], reverse=True)

        for player in players:
            name = f"{player['first_name']} {player['last_name']}"
            age = player['age']
            yrs = player['years_experience']
            overall_grade = to_letter_grade(player['true_overall'])

            # Get cap hit
            cap_hit_row = conn.execute("""
                SELECT cy.cap_hit
                FROM contract c
                JOIN contract_year cy ON cy.contract_id = c.id
                WHERE c.player_id = ? AND cy.season_year = ? AND c.status = 'active'
            """, (player['id'], season_year)).fetchone()

            cap_hit = cap_hit_row[0] if cap_hit_row else 0
            cap_str = format_cap_hit(cap_hit)

            college = player['college'] or "N/A"

            print(f"{pos:<4} {name:<25} {age:<4} {yrs:<4} {overall_grade:<8} {cap_str:<12} {college:<20}")
            total_on_roster += 1

    print(f"{'-' * 90}")
    print(f"Total players: {total_on_roster}")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(description='Query a team roster from a franchise database')
    parser.add_argument('save_path', help='Path to the .db file')
    parser.add_argument('--team', required=True, help='Team abbreviation (e.g., CHI, DAL) or city name')
    args = parser.parse_args()

    save_path = args.save_path
    team_abbr = args.team

    # Check if file exists
    if not Path(save_path).exists():
        print(f"❌ Database file not found: {save_path}")
        print(f"\nTo generate a new franchise, run:")
        print(f"  python generate.py {save_path}")
        return 1

    # Connect and query
    conn = get_connection(save_path)

    try:
        success = display_roster(conn, team_abbr)
        return 0 if success else 1

    except Exception as e:
        print(f"❌ Error querying roster: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
