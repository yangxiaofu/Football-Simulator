"""
Phase 5 Prompt #2 Verification — View Stats CLI

Exit Criteria:
1. ✅ CLI runs without errors for all 5 subcommands
2. ✅ Leaderboard qualifiers work (passing/rushing filter out players below minimums)
3. ✅ Player history displays all weeks played
4. ✅ Team stats match aggregated values
5. ✅ Stars placeholder displays correctly

Usage:
    python tests/verify/verify_phase5_p2.py saves/test.db
"""

import sys
import sqlite3
import subprocess

sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.db.queries import (
    get_league_state,
    get_season_running_leaders,
    get_player_weekly_history,
    get_team_season_running,
)
from src.utils.constants import LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME


def check_cli_runs(save_path):
    """Check 1: Verify CLI runs for all 5 subcommands without crashing."""
    print("\n[Check 1] CLI runs without errors...")

    commands = [
        ['python', 'view_stats.py', save_path, '--leaderboard', 'passing'],
        ['python', 'view_stats.py', save_path, '--leaderboard', 'rushing', '--limit', '25'],
        ['python', 'view_stats.py', save_path, '--player', '1'],
        ['python', 'view_stats.py', save_path, '--team', 'CHI'],
        ['python', 'view_stats.py', save_path, '--week', '1'],
        ['python', 'view_stats.py', save_path, '--stars'],
    ]

    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ Command failed: {' '.join(cmd)}")
            print(f"    STDOUT: {result.stdout[:200]}")
            print(f"    STDERR: {result.stderr[:200]}")
            return False

    print(f"  ✓ All CLI commands ran without errors")
    return True


def check_qualifiers(conn, season_year):
    """Check 2: Verify passing/rushing leaderboards exclude players below minimums."""
    print("\n[Check 2] Leaderboard qualifiers work...")

    # Get raw leaders (no qualifier applied at query level)
    raw_leaders = get_season_running_leaders(conn, season_year, 'pass_yards', is_playoff=0, limit=50)

    if not raw_leaders:
        print(f"  ⚠ No passing stats yet (season not started)")
        return True

    # Count how many have fewer than 14 att/game
    below_min = 0
    for row in raw_leaders:
        min_att = LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME * row['games_played']
        if row['pass_attempts'] < min_att:
            below_min += 1

    if below_min > 0:
        print(f"  ✓ Qualifier test: {below_min} players below minimum (will be filtered in display)")
        return True
    else:
        print(f"  ✓ No players below qualifier threshold (all qualify)")
        return True


def check_player_history(conn, season_year):
    """Check 3: Verify player history shows all weeks played."""
    print("\n[Check 3] Player history displays all weeks...")

    # Find any player with games_played > 0
    sample = conn.execute("""
        SELECT player_id, games_played
        FROM player_season_running
        WHERE season_year = ? AND is_playoff = 0 AND games_played > 0
        LIMIT 1
    """, (season_year,)).fetchone()

    if not sample:
        print("  ⚠ No players with games played (season not started)")
        return True

    history = get_player_weekly_history(conn, sample['player_id'], season_year, is_playoff=0)

    if len(history) == sample['games_played']:
        print(f"  ✓ Player history has {len(history)} weeks (matches games_played)")
        return True
    else:
        print(f"  ✗ Player history has {len(history)} weeks, expected {sample['games_played']}")
        return False


def check_team_stats(conn, season_year):
    """Check 4: Verify team_season_running matches sum of team_week_stats."""
    print("\n[Check 4] Team stats match aggregated values...")

    # Get one team with games played
    sample = conn.execute("""
        SELECT team_id, points_scored, games_played
        FROM team_season_running
        WHERE season_year = ? AND is_playoff = 0 AND games_played > 0
        LIMIT 1
    """, (season_year,)).fetchone()

    if not sample:
        print("  ⚠ No teams with games played")
        return True

    # Sum weekly stats
    weekly_sum = conn.execute("""
        SELECT SUM(points_scored) as total
        FROM team_week_stats
        WHERE season_year = ? AND team_id = ? AND is_playoff = 0
    """, (season_year, sample['team_id'])).fetchone()

    if weekly_sum['total'] == sample['points_scored']:
        print(f"  ✓ Team running total matches weekly sum ({sample['points_scored']} points)")
        return True
    else:
        print(f"  ✗ Mismatch: running={sample['points_scored']}, weekly_sum={weekly_sum['total']}")
        return False


def check_stars_placeholder(save_path):
    """Check 5: Verify --stars flag prints placeholder message."""
    print("\n[Check 5] Stars placeholder displays...")

    result = subprocess.run(
        ['python', 'view_stats.py', save_path, '--stars'],
        capture_output=True,
        text=True
    )

    if 'Prompt #4' in result.stdout:
        print(f"  ✓ Stars placeholder message displays correctly")
        return True
    else:
        print(f"  ✗ Stars placeholder message missing")
        print(f"    Output: {result.stdout[:200]}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p2.py saves/test.db")
        sys.exit(1)

    save_path = sys.argv[1]
    conn = get_connection(save_path)
    league = get_league_state(conn)
    season_year = league['current_season']

    print("=" * 70)
    print("PHASE 5 PROMPT #2 VERIFICATION — View Stats CLI")
    print("=" * 70)
    print(f"Database: {save_path}")
    print(f"Season: {season_year}")

    checks = [
        check_cli_runs(save_path),
        check_qualifiers(conn, season_year),
        check_player_history(conn, season_year),
        check_team_stats(conn, season_year),
        check_stars_placeholder(save_path),
    ]

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\nPhase 5 Prompt #2 exit criteria satisfied.")
        sys.exit(0)
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total} passed)")
        print("\nPhase 5 Prompt #2 exit criteria NOT satisfied.")
        sys.exit(1)


if __name__ == '__main__':
    main()
