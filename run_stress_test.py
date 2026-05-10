#!/usr/bin/env python3
"""
Multi-season stress test CLI.

Usage:
    python run_stress_test.py saves/franchise.db --invariants
    python run_stress_test.py saves/franchise.db --invariants --seasons 5
    python run_stress_test.py saves/franchise.db --smoke
    python run_stress_test.py saves/franchise.db --smoke --seasons 10

Exit codes:
    0 = all pass (or smoke completes without crash)
    1 = invariant failures (findings, not bugs in this prompt)
    2 = crash
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.league.stress_harness import run_stress_test
from src.utils.constants import (
    STRESS_TEST_DEFAULT_SEASONS,
    STRESS_TEST_SMOKE_SEASONS,
)


def main():
    parser = argparse.ArgumentParser(
        description='Football Simulator -- Multi-Season Stress Test',
    )
    parser.add_argument('save_path', help='Path to franchise .db file')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--invariants', action='store_true',
                       help=f'Run invariant battery after each season '
                            f'(default: {STRESS_TEST_DEFAULT_SEASONS} seasons)')
    group.add_argument('--smoke', action='store_true',
                       help=f'Crash-detection only '
                            f'(default: {STRESS_TEST_SMOKE_SEASONS} seasons)')

    parser.add_argument('--seasons', type=int, default=None,
                        help='Override default season count')

    args = parser.parse_args()

    if not os.path.exists(args.save_path):
        print(f"Error: Save file not found: {args.save_path}")
        sys.exit(2)

    # Determine mode and season count
    if args.invariants:
        mode = 'invariants'
        n_seasons = args.seasons or STRESS_TEST_DEFAULT_SEASONS
    else:
        mode = 'smoke'
        n_seasons = args.seasons or STRESS_TEST_SMOKE_SEASONS

    print(f"\n  Football Simulator -- Stress Test")
    print(f"  Mode: {mode}")
    print(f"  Seasons: {n_seasons}")
    print(f"  Save: {args.save_path}")
    print(f"{'='*50}")

    result = run_stress_test(
        db_path=args.save_path,
        n_seasons=n_seasons,
        mode=mode,
    )

    # Print summary
    print(f"\n{'='*50}")
    print(f"  STRESS TEST COMPLETE")
    print(f"{'='*50}")
    print(f"  Seasons completed: {result['completed_seasons']}/{n_seasons}")
    print(f"  Duration: {result['duration_seconds']:.1f}s")
    print(f"  Crashed: {'YES' if result['crashed'] else 'No'}")

    if result['crash_detail']:
        print(f"\n  Crash/Warning Detail:")
        print(f"  {result['crash_detail']}")

    # Print invariant results
    any_failed = False
    if result['invariant_results_by_year']:
        print(f"\n  INVARIANT RESULTS")
        print(f"  {'-'*46}")

        for year, inv_results in sorted(result['invariant_results_by_year'].items()):
            print(f"\n  Season {year}:")
            for inv in inv_results:
                status = "PASS" if inv['passed'] else "FAIL"
                marker = "  " if inv['passed'] else ">>"
                print(f"  {marker} [{status}] {inv['name']}")
                print(f"         {inv['detail']}")
                if not inv['passed']:
                    any_failed = True

    # Print health report
    if result['health_report']:
        print(f"\n{result['health_report']}")

    # Exit code
    if result['crashed']:
        sys.exit(2)
    elif any_failed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
