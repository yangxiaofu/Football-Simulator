"""Phase 4 — League records and history viewer.

Usage:
    python view_records.py saves/test.db                          # show all
    python view_records.py saves/test.db --records                # record book only
    python view_records.py saves/test.db --leaders passing_yards  # all-time leaders
    python view_records.py saves/test.db --champions              # champion history
    python view_records.py saves/test.db --champions --limit 10   # last 10 champions
"""
import argparse
import sys
sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.league.historical_records import (
    get_record_book, get_all_time_leaders, get_champion_history,
)


def print_record_book(conn):
    """Print league record book in three sections."""
    print("=" * 70)
    print("LEAGUE RECORD BOOK")
    print("=" * 70)
    for scope in ('single_game', 'single_season', 'career'):
        records = get_record_book(conn, scope=scope)
        if not records:
            continue
        print(f"\n{scope.replace('_', ' ').upper()}")
        print("-" * 70)
        for r in records:
            holder = r.get('holder_player_name') or r.get('holder_team_abbr') or '—'
            year = r.get('season_year') or '—'
            print(f"  {r['category_display']:<22} {r['record_value']:>6}  "
                  f"{holder:<25} ({year})")


def print_leaders(conn, category, scope='career', top_n=10):
    """Print all-time leaders for a category."""
    print("=" * 70)
    print(f"ALL-TIME LEADERS — {category.upper().replace('_', ' ')} ({scope})")
    print("=" * 70)
    leaders = get_all_time_leaders(conn, category, scope, top_n)
    if not leaders:
        print("  No data available for this category.")
        return
    for i, l in enumerate(leaders, 1):
        year_str = f", {l['season_year']}" if l['season_year'] else ""
        print(f"  {i:>2}. {l['player_name']:<25} {l['value']:>6} "
              f"({l['team_abbr']}{year_str})")


def print_champions(conn, limit):
    """Print champion history."""
    print("=" * 70)
    print("CHAMPION HISTORY")
    print("=" * 70)
    champs = get_champion_history(conn, n=limit)
    if not champs:
        print("  No completed seasons found.")
        return
    for c in champs:
        score = c.get('final_score') or '—'
        runner_up = c.get('runner_up_team_abbr') or '—'
        mvp = c.get('mvp_player_name') or '—'
        coach = c.get('coach_name') or '—'
        print(f"  {c['season_year']}  {c['champion_team_abbr']:<4} def. "
              f"{runner_up:<4} {score}")
        if mvp != '—' or coach != '—':
            print(f"        MVP: {mvp:<25}  Coach: {coach}")


def main():
    parser = argparse.ArgumentParser(description="Historical records viewer")
    parser.add_argument('db_path')
    parser.add_argument('--records', action='store_true',
                        help='Show league record book only')
    parser.add_argument('--leaders', metavar='CATEGORY',
                        help='Show all-time leaders for category (e.g., passing_yards)')
    parser.add_argument('--champions', action='store_true',
                        help='Show champion history only')
    parser.add_argument('--limit', type=int, default=25,
                        help='Limit for champion history (default: 25)')
    parser.add_argument('--scope', default='career',
                        choices=['single_game', 'single_season', 'career'],
                        help='Scope for leaders query (default: career)')
    parser.add_argument('--top-n', type=int, default=10,
                        help='Number of leaders to show (default: 10)')

    args = parser.parse_args()
    conn = get_connection(args.db_path)

    # Default: show everything
    show_all = not (args.records or args.leaders or args.champions)

    if args.records or show_all:
        print_record_book(conn)
        if show_all:
            print()

    if args.leaders:
        print_leaders(conn, args.leaders, args.scope, args.top_n)
        if show_all:
            print()

    if args.champions or show_all:
        print_champions(conn, args.limit)


if __name__ == '__main__':
    main()
