"""Coach career and season summary viewer (Phase 4 Prompt #9).

Usage:
    python view_career.py saves/test.db                      # player coach career
    python view_career.py saves/test.db --coach-id 7         # specific coach
    python view_career.py saves/test.db --season 2026        # season summary
    python view_career.py saves/test.db --no-color           # disable ANSI
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.connection import get_connection
from src.ui.career_view import render_career_view
from src.ui.season_summary import render_season_summary


def main():
    parser = argparse.ArgumentParser(description="Coach career and season summary viewer")
    parser.add_argument('db_path', help="Path to franchise database")
    parser.add_argument('--coach-id', type=int, default=None, help="Coach ID (default: player coach)")
    parser.add_argument('--season', type=int, default=None, help="Season year for summary view")
    parser.add_argument('--no-color', action='store_true', help="Disable ANSI colors")

    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        print(f"Error: Database file not found: {args.db_path}")
        return 1

    conn = get_connection(args.db_path)
    use_color = not args.no_color

    coach_id = args.coach_id
    if coach_id is None:
        # Find player coach
        row = conn.execute("SELECT id FROM coach_career WHERE is_player=1").fetchone()
        if row is None:
            print("Error: No player coach found in this save.")
            conn.close()
            return 1
        coach_id = row['id']

    if args.season is not None:
        # Season summary view
        print(render_season_summary(conn, args.season, coach_id, use_color))
    else:
        # Career view
        print(render_career_view(conn, coach_id, use_color))

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
