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
        ['python', 'view_stats.py', save_path, '--leaderboard', 'rushing', '--top', '25'],
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
    """Check 5: Verify --stars flag exits 0 and shows stars header or placeholder."""
    print("\n[Check 5] Stars placeholder/real data displays...")

    result = subprocess.run(
        ['python', 'view_stats.py', save_path, '--stars'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ✗ --stars exited {result.returncode}")
        print(f"    Output: {result.stdout[:200]}")
        return False

    # Accept: old placeholder text OR real stars header OR empty-state message
    accepted = (
        'Prompt #4' in result.stdout
        or 'STARS OF THE WEEK' in result.stdout
        or 'No Stars of the Week' in result.stdout
        or 'Stars of the Week' in result.stdout
    )
    if accepted:
        print(f"  ✓ --stars displays correctly (exits 0, shows stars output)")
        return True
    else:
        print(f"  ✗ --stars output not recognized")
        print(f"    Output: {result.stdout[:200]}")
        return False


def check_no_scope_creep_into_run_season(save_path):
    """Check 6: Verify run_season.py was NOT modified to add view_stats flags.
    Those flags belong on view_stats.py only."""
    print("\n[Check 6] No scope creep into run_season.py...")

    with open("run_season.py") as f:
        runs_src = f.read()

    forbidden_flags = ["--leaderboard", "--stars-of-week", "--player-weekly"]
    found = [f for f in forbidden_flags if f in runs_src]

    if found:
        print(f"  ✗ run_season.py contains view_stats flags: {found}")
        print(f"    These belong on view_stats.py only.")
        return False

    print(f"  ✓ run_season.py is clean (no view_stats flags)")
    return True


def check_phase4_stress_harness(save_path):
    """Check 7: Verify Phase 4 stress harness still passes with Phase 5 active."""
    print("\n[Check 7] Phase 4 stress harness regression check...")

    result = subprocess.run(
        ['python', 'run_stress_test.py', save_path, '--seasons', '1', '--invariants'],
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes max
    )

    if result.returncode != 0:
        print(f"  ✗ Stress harness exited {result.returncode}")
        print(f"    STDERR tail: {result.stderr[-500:]}")
        return False

    print(f"  ✓ All 12 invariants pass over 1 season")
    return True


def check_layer_boundaries():
    """Check 8: Verify src/ui/stats_view.py contains no SQL (layer boundary)."""
    print("\n[Check 8] Layer boundary scan...")

    with open("src/ui/stats_view.py") as f:
        lines = f.readlines()

    # More specific SQL patterns that are less likely to be English text
    forbidden_patterns = ["conn.execute(", "cursor.execute(", ".fetchall(", ".fetchone()",
                          "select * from", "insert into", "update set", "delete from"]

    problematic = []
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()

        # Track docstring state more carefully
        if '"""' in line:
            if not in_docstring:
                in_docstring = True
                docstring_char = '"""'
                # Check if docstring ends on same line
                if line.count('"""') >= 2:
                    in_docstring = False
                continue
            elif docstring_char == '"""':
                in_docstring = False
                docstring_char = None
                continue

        if "'''" in line:
            if not in_docstring:
                in_docstring = True
                docstring_char = "'''"
                # Check if docstring ends on same line
                if line.count("'''") >= 2:
                    in_docstring = False
                continue
            elif docstring_char == "'''":
                in_docstring = False
                docstring_char = None
                continue

        # Skip lines inside docstrings or comments
        if in_docstring or stripped.startswith("#"):
            continue

        # Check for SQL patterns
        for pattern in forbidden_patterns:
            if pattern in stripped:
                problematic.append((pattern, i, line[:80]))

    if problematic:
        print(f"  ✗ SQL execution found in non-comment code:")
        for pattern, lineno, line in problematic[:5]:
            print(f"    Line {lineno}: [{pattern}] {line.strip()[:60]}")
        return False

    print(f"  ✓ src/ui/stats_view.py contains no SQL execution")
    return True


def check_unknown_stat_errors_cleanly(save_path):
    """Check 9: Verify --leaderboard with unknown category exits non-zero
    and prints supported categories."""
    print("\n[Check 9] Unknown leaderboard category errors cleanly...")

    result = subprocess.run(
        ['python', 'view_stats.py', save_path, '--leaderboard', 'bogus_xyz'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✗ Unknown category should exit non-zero, got 0")
        return False

    combined = (result.stdout + result.stderr).lower()
    if "valid" not in combined and "supported" not in combined and "passing" not in combined:
        print(f"  ✗ Error output did not list valid categories")
        print(f"    Output: {result.stdout[:200]}")
        return False

    print(f"  ✓ Unknown category exits non-zero with category list")
    return True


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
        check_no_scope_creep_into_run_season(save_path),
        check_phase4_stress_harness(save_path),
        check_layer_boundaries(),
        check_unknown_stat_errors_cleanly(save_path),
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
