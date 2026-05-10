"""
CLI entry point for simulating a single game.

Usage:
    python simulate_game.py saves/test_franchise.db --home CHI --away GB --week 1
    python simulate_game.py saves/test_franchise.db --game-id 1
    python simulate_game.py saves/test_franchise.db --batch 100 --stats-only
"""

import argparse
import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.game_sim import simulate_game


def find_game_by_teams(db_path: str, home_abbr: str, away_abbr: str, week: int = None) -> int:
    """Find a game ID by team abbreviations and optional week."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Find team IDs
        home = conn.execute(
            "SELECT id FROM team WHERE UPPER(abbreviation) = UPPER(?)",
            (home_abbr,),
        ).fetchone()
        away = conn.execute(
            "SELECT id FROM team WHERE UPPER(abbreviation) = UPPER(?)",
            (away_abbr,),
        ).fetchone()

        if not home:
            # Try matching by city or nickname
            home = conn.execute(
                "SELECT id FROM team WHERE UPPER(city) LIKE UPPER(?) OR UPPER(nickname) LIKE UPPER(?)",
                (f"%{home_abbr}%", f"%{home_abbr}%"),
            ).fetchone()
        if not away:
            away = conn.execute(
                "SELECT id FROM team WHERE UPPER(city) LIKE UPPER(?) OR UPPER(nickname) LIKE UPPER(?)",
                (f"%{away_abbr}%", f"%{away_abbr}%"),
            ).fetchone()

        if not home:
            print(f"Error: Could not find team '{home_abbr}'")
            sys.exit(1)
        if not away:
            print(f"Error: Could not find team '{away_abbr}'")
            sys.exit(1)

        # Find the game
        if week:
            game = conn.execute("""
                SELECT g.id FROM game g
                JOIN week w ON g.week_id = w.id
                WHERE g.home_team_id = ? AND g.away_team_id = ?
                AND w.week_number = ?
                AND g.is_complete = 0
            """, (home['id'], away['id'], week)).fetchone()

            if not game:
                # Try with teams swapped
                game = conn.execute("""
                    SELECT g.id FROM game g
                    JOIN week w ON g.week_id = w.id
                    WHERE g.home_team_id = ? AND g.away_team_id = ?
                    AND w.week_number = ?
                    AND g.is_complete = 0
                """, (away['id'], home['id'], week)).fetchone()
        else:
            game = conn.execute("""
                SELECT g.id FROM game g
                WHERE ((g.home_team_id = ? AND g.away_team_id = ?)
                   OR (g.home_team_id = ? AND g.away_team_id = ?))
                AND g.is_complete = 0
                ORDER BY g.id
                LIMIT 1
            """, (home['id'], away['id'], away['id'], home['id'])).fetchone()

        if not game:
            print(f"Error: No unplayed game found for {home_abbr} vs {away_abbr}"
                  + (f" in week {week}" if week else ""))
            sys.exit(1)

        return game['id']

    finally:
        conn.close()


def get_all_unplayed_games(db_path: str, week: int = None) -> list[int]:
    """Get all unplayed game IDs, optionally for a specific week."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if week:
            rows = conn.execute("""
                SELECT g.id FROM game g
                JOIN week w ON g.week_id = w.id
                WHERE g.is_complete = 0 AND w.week_number = ?
                ORDER BY g.id
            """, (week,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id FROM game WHERE is_complete = 0 ORDER BY id
            """).fetchall()

        return [row['id'] for row in rows]

    finally:
        conn.close()


def print_box_score(result: dict):
    """Print a formatted box score summary."""
    print("\n" + "=" * 60)
    print(f"{'BOX SCORE':^60}")
    print("=" * 60)
    print(f"  {result['away_team']:30}  {result['away_score']:>3}")
    print(f"  {result['home_team']:30}  {result['home_score']:>3}")
    print("-" * 60)

    for label, stats in [
        (result.get('away_abbr', 'AWAY'), result['away_stats']),
        (result.get('home_abbr', 'HOME'), result['home_stats']),
    ]:
        print(f"\n  {label}:")
        print(f"    Total Yards:    {stats['total_yards']:>5}")
        print(f"    Pass Yards:     {stats['pass_yards']:>5}  "
              f"({stats['completions']}/{stats['pass_attempts']}, "
              f"{stats['completion_pct']:.1%})")
        print(f"    Rush Yards:     {stats['rush_yards']:>5}  "
              f"({stats['carries']} carries, "
              f"{stats['yards_per_carry']:.1f} ypc)")
        print(f"    Sacks Taken:    {stats['sacks_taken']:>5}")
        print(f"    Turnovers:      {stats['turnovers']:>5}")
        print(f"    Total Plays:    {stats['total_plays']:>5}")

    print("=" * 60)

    if result.get('weather'):
        w = result['weather']
        print(f"  Weather: {w['condition'].replace('_', ' ').title()}, "
              f"{w['temperature']}°F, Wind: {w['wind_speed']} mph")
    print()


def main():
    parser = argparse.ArgumentParser(description='Simulate an NFL game')
    parser.add_argument('save_path', help='Path to franchise .db file')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--game-id', type=int, help='Specific game ID to simulate')
    group.add_argument('--batch', type=int, help='Number of games to simulate in batch')

    parser.add_argument('--home', help='Home team abbreviation or name')
    parser.add_argument('--away', help='Away team abbreviation or name')
    parser.add_argument('--week', type=int, help='Week number')
    parser.add_argument('--stats-only', action='store_true',
                        help='Only show stats summary (no play-by-play)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress all output except final score')

    args = parser.parse_args()

    if not os.path.exists(args.save_path):
        print(f"Error: Save file not found: {args.save_path}")
        sys.exit(1)

    if args.batch:
        # Batch mode: simulate multiple games
        game_ids = get_all_unplayed_games(args.save_path, args.week)
        if not game_ids:
            print("No unplayed games found.")
            sys.exit(0)

        games_to_sim = game_ids[:args.batch]
        print(f"Simulating {len(games_to_sim)} games...\n")

        all_results = []
        for i, gid in enumerate(games_to_sim):
            result = simulate_game(args.save_path, gid, verbose=False)
            all_results.append(result)

            if not args.quiet:
                print(f"  Game {i+1}: {result['away_team']} {result['away_score']} "
                      f"@ {result['home_team']} {result['home_score']}")

        if args.stats_only or not args.quiet:
            _print_batch_stats(all_results)

    elif args.game_id:
        # Single game by ID
        verbose = not args.stats_only and not args.quiet
        result = simulate_game(args.save_path, args.game_id, verbose=verbose)
        print_box_score(result)

    elif args.home and args.away:
        # Single game by team names
        game_id = find_game_by_teams(args.save_path, args.home, args.away, args.week)
        verbose = not args.stats_only and not args.quiet
        result = simulate_game(args.save_path, game_id, verbose=verbose)
        print_box_score(result)

    else:
        parser.error("Must specify --game-id, --batch, or both --home and --away")


def _print_batch_stats(results: list[dict]):
    """Print aggregate statistics from a batch of games."""
    if not results:
        return

    total_games = len(results)
    total_pass_yards = 0
    total_rush_yards = 0
    total_points = 0
    total_completions = 0
    total_pass_att = 0
    total_carries = 0
    total_turnovers = 0
    total_sacks = 0
    total_plays = 0

    for r in results:
        for stats in (r['home_stats'], r['away_stats']):
            total_pass_yards += stats['pass_yards']
            total_rush_yards += stats['rush_yards']
            total_completions += stats['completions']
            total_pass_att += stats['pass_attempts']
            total_carries += stats['carries']
            total_turnovers += stats['turnovers']
            total_sacks += stats['sacks_taken']
            total_plays += stats['total_plays']

        total_points += r['home_score'] + r['away_score']

    teams_total = total_games * 2  # Each game has 2 teams

    print(f"\n{'='*50}")
    print(f"{'BATCH STATISTICS':^50}")
    print(f"{'='*50}")
    print(f"  Games simulated:     {total_games}")
    print(f"  Avg points/team:     {total_points / teams_total:.1f}")
    print(f"  Avg pass yards/team: {total_pass_yards / teams_total:.1f}")
    print(f"  Avg rush yards/team: {total_rush_yards / teams_total:.1f}")
    print(f"  Avg completion %:    {total_completions / max(1, total_pass_att):.1%}")
    print(f"  Avg yards/carry:     {total_rush_yards / max(1, total_carries):.1f}")
    print(f"  Avg turnovers/team:  {total_turnovers / teams_total:.1f}")
    print(f"  Avg sacks/team:      {total_sacks / teams_total:.1f}")
    print(f"  Avg plays/team:      {total_plays / teams_total:.1f}")

    print(f"\n  {'Target Ranges:'}")
    print(f"    Points/team:       17-28 (NFL avg: 22)")
    print(f"    Pass yards/team:   180-270 (NFL avg: 225)")
    print(f"    Rush yards/team:   85-145 (NFL avg: 115)")
    print(f"    Completion %:      58-70% (NFL avg: 64.5%)")
    print(f"    Yards/carry:       3.6-5.0 (NFL avg: 4.3)")
    print(f"    Turnovers/team:    0.5-1.8 (NFL avg: 1.1)")
    print(f"    Sacks/team:        1.5-3.5 (NFL avg: 2.5)")
    print(f"    Plays/team:        55-75 (NFL avg: 65)")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
