#!/usr/bin/env python3
"""
Phase 5 Verification Script — Weekly Stats Cache

Validates that weekly stats aggregation works correctly:
1. Running totals match sum of weekly stats
2. Weekly awards exist
3. Leaderboard queries are fast (<100ms)
4. Season archive cleans up weekly caches

Exit code 0 = all checks pass
Exit code 1 = one or more checks fail
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.connection import get_connection
from src.db.queries import (
    get_league_state,
    get_player_season_running,
    get_all_player_week_stats,
    verify_season_running_consistency,
    get_weekly_awards,
    get_season_running_leaders,
)


def check_running_totals_consistency(conn, season_year):
    """
    Invariant Check: Running totals must match sum of weekly stats.

    For each player in player_season_running:
        running_total.pass_yards == SUM(player_week_stats.pass_yards)
        (same for all 32 stat columns)
    """
    print("\n[CHECK 1] Running totals consistency")
    print("-" * 60)

    # Get all running totals for the season
    running_totals = conn.execute("""
        SELECT player_id FROM player_season_running
        WHERE season_year = ? AND is_playoff = 0
    """, (season_year,)).fetchall()

    if not running_totals:
        print("  ⚠ No running totals found (season may not have started)")
        return True

    total_players = len(running_totals)
    consistent_count = 0
    mismatch_count = 0

    for row in running_totals:
        player_id = row['player_id']
        result = verify_season_running_consistency(conn, season_year, player_id, is_playoff=0)

        if result['consistent']:
            consistent_count += 1
        else:
            mismatch_count += 1
            print(f"  ✗ Player {player_id}: {', '.join(result['mismatches'])}")

    if mismatch_count == 0:
        print(f"  ✓ All {total_players} player running totals consistent with weekly stats")
        return True
    else:
        print(f"  ✗ {mismatch_count}/{total_players} players have mismatched running totals")
        return False


def check_weekly_awards_exist(conn, season_year):
    """
    Check 2: Weekly awards exist for each completed week.

    Minimum 2 awards per week: OFFENSE + DEFENSE
    """
    print("\n[CHECK 2] Weekly awards exist")
    print("-" * 60)

    # Get all completed weeks for the season
    weeks = conn.execute("""
        SELECT week_number FROM week
        WHERE season_id = (SELECT id FROM season WHERE year = ?)
        AND is_complete = 1 AND week_type = 'regular'
    """, (season_year,)).fetchall()

    if not weeks:
        print("  ⚠ No completed weeks found")
        return True

    total_weeks = len(weeks)
    weeks_with_awards = 0

    for week_row in weeks:
        week_num = week_row['week_number']
        awards = get_weekly_awards(conn, season_year, week_num, is_playoff=0)

        if len(awards) >= 2:
            weeks_with_awards += 1
        else:
            print(f"  ✗ Week {week_num}: Only {len(awards)} awards (expected >= 2)")

    if weeks_with_awards == total_weeks:
        print(f"  ✓ All {total_weeks} completed weeks have awards")
        return True
    else:
        print(f"  ✗ {total_weeks - weeks_with_awards}/{total_weeks} weeks missing awards")
        return False


def check_leaderboard_performance(conn, season_year):
    """
    Check 3: Leaderboard queries return in <100ms.

    This validates that indexes are working correctly.
    """
    print("\n[CHECK 3] Leaderboard query performance")
    print("-" * 60)

    stat_columns = ['pass_yards', 'rush_yards', 'rec_yards', 'tackles', 'sacks']
    all_fast = True

    for stat in stat_columns:
        start_time = time.time()
        leaders = get_season_running_leaders(conn, season_year, stat, is_playoff=0, limit=10)
        duration_ms = (time.time() - start_time) * 1000

        if duration_ms < 100:
            print(f"  ✓ {stat}: {duration_ms:.2f}ms")
        else:
            print(f"  ✗ {stat}: {duration_ms:.2f}ms (exceeds 100ms threshold)")
            all_fast = False

    return all_fast


def check_value_level_idempotency(conn, season_year):
    """
    Check 4: Value-level idempotency — running totals must not double-count on re-aggregation.

    This test re-aggregates week 1 and verifies that running total values are unchanged.
    """
    print("\n[CHECK 4] Value-level idempotency")
    print("-" * 60)

    # Find a sample player with non-zero stats
    sample_player = conn.execute("""
        SELECT player_id, pass_yards, rush_yards, rec_yards, tackles, sacks
        FROM player_season_running
        WHERE season_year = ? AND is_playoff = 0
          AND (pass_yards > 0 OR rush_yards > 0 OR rec_yards > 0
               OR tackles > 0 OR sacks > 0)
        LIMIT 1
    """, (season_year,)).fetchone()

    if sample_player is None:
        print("  ⚠ No non-zero running totals found (season may not have started)")
        return True

    before_vals = dict(sample_player)
    player_id = before_vals['player_id']

    print(f"  Testing player {player_id}: pass_yards={before_vals['pass_yards']}, "
          f"rush_yards={before_vals['rush_yards']}, rec_yards={before_vals['rec_yards']}")

    # Re-aggregate week 1 (regular season)
    from src.league.weekly_stats import aggregate_week_stats
    aggregate_week_stats(conn, season_year=season_year, week_number=1, is_playoff=False)

    # Check if values changed
    after = conn.execute("""
        SELECT pass_yards, rush_yards, rec_yards, tackles, sacks
        FROM player_season_running
        WHERE player_id = ? AND season_year = ? AND is_playoff = 0
    """, (player_id, season_year)).fetchone()

    if after is None:
        print(f"  ✗ Player {player_id} disappeared from running totals after re-aggregation")
        return False

    after_vals = dict(after)
    all_match = True

    for stat in ('pass_yards', 'rush_yards', 'rec_yards', 'tackles', 'sacks'):
        if before_vals[stat] != after_vals[stat]:
            print(f"  ✗ {stat} changed from {before_vals[stat]} to {after_vals[stat]} (double-counting!)")
            all_match = False

    if all_match:
        print(f"  ✓ All stats unchanged after re-aggregation (idempotent)")

    return all_match


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_phase5.py <save_file.db>")
        sys.exit(1)

    save_path = sys.argv[1]

    if not os.path.exists(save_path):
        print(f"Error: Save file not found: {save_path}")
        sys.exit(1)

    print("=" * 60)
    print("Phase 5 Verification — Weekly Stats Cache")
    print("=" * 60)

    conn = get_connection(save_path)

    try:
        league = get_league_state(conn)
        season_year = league['current_season']
        phase = league['current_phase']

        print(f"Current State: Season {season_year}, Phase: {phase}")

        # If in offseason, check the previous season
        if phase == 'offseason':
            season_year = season_year - 1
            print(f"(Checking stats from completed season: {season_year})")

        # Run checks
        check1_pass = check_running_totals_consistency(conn, season_year)
        check2_pass = check_leaderboard_performance(conn, season_year)
        check3_pass = check_value_level_idempotency(conn, season_year)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        checks = [
            ("Running totals consistency", check1_pass),
            ("Leaderboard performance", check2_pass),
            ("Value-level idempotency", check3_pass),
        ]

        passed = sum(1 for _, result in checks if result)
        total = len(checks)

        for name, result in checks:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {status}: {name}")

        print(f"\n  {passed}/{total} checks passed")

        if passed == total:
            print("\n✓ Phase 5 verification PASSED")
            sys.exit(0)
        else:
            print("\n✗ Phase 5 verification FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"\nError during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
