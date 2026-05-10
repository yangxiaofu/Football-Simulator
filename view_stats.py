"""Phase 5 — In-season stats viewer.

Usage:
    python view_stats.py saves/test.db --leaderboard passing          # top 10 passers
    python view_stats.py saves/test.db --leaderboard rushing --limit 25  # top 25 rushers
    python view_stats.py saves/test.db --player 123                   # player weekly history
    python view_stats.py saves/test.db --team CHI                     # team season stats
    python view_stats.py saves/test.db --week 5                       # Week 5 top performers
    python view_stats.py saves/test.db --stars                        # Stars of the Week (placeholder)
"""
import argparse
import sys
sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.db.queries import get_league_state
from src.ui.stats_view import (
    print_leaderboard,
    print_player_weekly_history,
    print_team_season_stats,
    print_week_stats,
    print_stars_of_week,
)
from src.utils.constants import LEADERBOARD_MAX_LIMIT, LEADERBOARD_STAT_MAP


def main():
    parser = argparse.ArgumentParser(description="In-season stats viewer")
    parser.add_argument('db_path', help='Path to franchise .db file')
    parser.add_argument('--leaderboard', metavar='CATEGORY',
                        help='Show leaderboard (passing, rushing, receiving, defense, sacks, interceptions)')
    parser.add_argument('--player', metavar='PLAYER_ID', type=int,
                        help='Show player week-by-week history')
    parser.add_argument('--team', metavar='TEAM_ABBR',
                        help='Show team season stats (e.g., CHI, DAL, GB)')
    parser.add_argument('--week', metavar='WEEK_NUMBER', type=int,
                        help='Show all stats from specific week')
    parser.add_argument('--stars', action='store_true',
                        help='Show Stars of the Week (placeholder)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of players to show in leaderboards (default: 10, max: 50)')

    args = parser.parse_args()

    # Validate limit
    if args.limit > LEADERBOARD_MAX_LIMIT:
        print(f"Error: Limit cannot exceed {LEADERBOARD_MAX_LIMIT}")
        sys.exit(1)

    conn = get_connection(args.db_path)
    league = get_league_state(conn)
    season_year = league['current_season']

    # Dispatch to handlers
    if args.leaderboard:
        if args.leaderboard not in LEADERBOARD_STAT_MAP:
            print(f"Error: Unknown category '{args.leaderboard}'")
            print(f"Valid categories: {', '.join(sorted(LEADERBOARD_STAT_MAP.keys()))}")
            sys.exit(1)
        print_leaderboard(conn, season_year, args.leaderboard, args.limit)

    elif args.player:
        print_player_weekly_history(conn, args.player, season_year)

    elif args.team:
        print_team_season_stats(conn, args.team.upper(), season_year)

    elif args.week:
        print_week_stats(conn, season_year, args.week)

    elif args.stars:
        # Placeholder for Prompt #4
        print_stars_of_week(conn, season_year, week_number=None)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
