"""Phase 5 — Sentiment viewer.

Usage:
    python view_sentiment.py saves/save.db --owner
    python view_sentiment.py saves/save.db --owner --week 5
    python view_sentiment.py saves/save.db --player <player_id>
    python view_sentiment.py saves/save.db --all-players
    python view_sentiment.py saves/save.db --all-players --threshold 30
"""
import argparse
import sys
sys.path.insert(0, '.')

from src.db.connection import (
    get_connection,
    ensure_owner_sentiment_tables,
    ensure_satisfaction_tables,
)
from src.db.queries import (
    get_league_state,
    get_team_coach,
    get_player,
)
from src.league.sentiment_explainer import (
    explain_owner_sentiment,
    explain_player_satisfaction,
    get_all_player_satisfaction_concerns,
)
from src.ui.sentiment_view import (
    print_owner_sentiment,
    print_player_satisfaction,
    print_all_players_concerns,
)


def _get_player_name(conn, player_id: int) -> str:
    row = get_player(conn, player_id)
    if row:
        return f"{row['first_name']} {row['last_name']}"
    return f"Player #{player_id}"


def main():
    parser = argparse.ArgumentParser(description="Sentiment viewer")
    parser.add_argument('db_path', help='Path to franchise .db file')

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--owner', action='store_true',
                      help='Show owner sentiment for the user team')
    mode.add_argument('--player', metavar='PLAYER_ID', type=int,
                      help='Show satisfaction history for a specific player')
    mode.add_argument('--all-players', action='store_true',
                      help='List players with low satisfaction')

    parser.add_argument('--week', metavar='WEEK_NUMBER', type=int,
                        help='Filter owner sentiment to a specific week (--owner only)')
    parser.add_argument('--threshold', metavar='N', type=int, default=40,
                        help='Satisfaction threshold for --all-players (default: 40)')

    args = parser.parse_args()

    conn = get_connection(args.db_path)

    # Run migrations so old saves get the new columns
    ensure_owner_sentiment_tables(conn)
    ensure_satisfaction_tables(conn)

    league = get_league_state(conn)
    if not league:
        print("Error: League not initialized in this save.")
        sys.exit(1)

    season_year = league['current_season']
    user_team_id = league['user_team_id']

    if args.owner:
        # Get coach name for display
        coach = get_team_coach(conn, user_team_id) if user_team_id else None
        if coach:
            coach_name = f"{coach['first_name']} {coach['last_name']}"
        else:
            coach_name = 'Unknown'

        result = explain_owner_sentiment(
            conn, user_team_id, season_year,
            week_filter=args.week,
        )
        print_owner_sentiment(result, coach_name, season_year)

    elif args.player:
        player_name = _get_player_name(conn, args.player)
        result = explain_player_satisfaction(conn, args.player, season_year)
        print_player_satisfaction(result, player_name, season_year)

    elif args.all_players:
        concerns = get_all_player_satisfaction_concerns(
            conn, season_year, threshold=args.threshold
        )
        print_all_players_concerns(concerns, season_year, args.threshold)

    conn.close()


if __name__ == '__main__':
    main()
