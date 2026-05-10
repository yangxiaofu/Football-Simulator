#!/usr/bin/env python3
"""
Main generation script for Phase 0.

Creates a new franchise database with:
- 32 teams with divisions and conferences
- 53-man rosters for all teams (1,696 players)
- Coaching staff and scouts for all teams
- 17-game regular season schedule

Usage:
    python generate.py saves/my_franchise.db
    python generate.py saves/my_franchise.db --season 2024
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db import get_connection, init_database
from src.generation import (
    generate_all_teams,
    generate_all_rosters,
    generate_all_staff,
    generate_full_schedule
)


def main():
    parser = argparse.ArgumentParser(description='Generate a new Football Simulator franchise')
    parser.add_argument('save_path', help='Path to save the .db file (e.g., saves/my_franchise.db)')
    parser.add_argument('--season', type=int, default=2024, help='Starting season year (default: 2024)')
    args = parser.parse_args()

    save_path = args.save_path
    season_year = args.season

    print(f"🏈 Football Simulator — Franchise Generator")
    print(f"=" * 60)
    print(f"Save path: {save_path}")
    print(f"Starting season: {season_year}")
    print()

    # Check if file already exists
    if Path(save_path).exists():
        response = input(f"⚠️  File {save_path} already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        Path(save_path).unlink()

    # Initialize database
    print("Creating database schema...")
    init_database(save_path)
    print("✓ Schema created")
    print()

    # Connect and generate
    conn = get_connection(save_path)

    try:
        with conn:
            print("Generating league structure and teams...")
            team_ids = generate_all_teams(conn, season_year)
            print(f"✓ Generated {len(team_ids)} teams")
            print()

            print("Generating players (53-man rosters for all teams)...")
            total_players = generate_all_rosters(conn, team_ids)
            print(f"✓ Generated {total_players} players")
            print()

            print("Generating coaching staff and scouts...")
            total_staff = generate_all_staff(conn, team_ids)
            print(f"✓ Generated {total_staff} staff members")
            print()

            print("Generating regular season schedule...")
            # Get season_id
            season_row = conn.execute("SELECT id FROM season WHERE year = ?", (season_year,)).fetchone()
            season_id = season_row[0]
            total_games = generate_full_schedule(conn, season_id, team_ids)
            print(f"✓ Generated {total_games} games across {17} weeks")
            print()

        print("=" * 60)
        print("✅ Franchise generation complete!")
        print()
        print("To query a roster, run:")
        print(f"  python query_roster.py {save_path} --team CHI")

    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
