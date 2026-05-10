"""
Headless multi-season stress test orchestrator.

Runs N consecutive seasons without any interactive prompts, checks
invariants after each season, and produces a League Health Report.
"""

import io
import sqlite3
import time
import traceback
from contextlib import redirect_stdout

from ..db.connection import get_connection
from ..db.queries import (
    get_all_teams,
    get_league_state,
    get_offseason_state,
    get_season,
    insert_new_season,
    update_league_state,
)
from ..generation.schedule import generate_full_schedule
from ..league.archive import archive_season
from ..league.awards import assign_awards
from ..league.health_report import generate_health_report
from ..league.invariants import run_all_invariants
from ..league.legacy import update_legacy_score
from ..league.offseason import advance_phase, start_offseason
from ..league.playoffs import run_full_playoffs
from ..league.season import advance_week, is_regular_season_complete
from ..utils.constants import (
    CAP_INFLATION_RATE,
    OFFSEASON_PHASE_SEQUENCE,
    REGULAR_SEASON_WEEKS,
    STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON,
)


def run_stress_test(
    db_path: str,
    n_seasons: int,
    mode: str = 'invariants',
    starting_season_year: int = None,
    print_progress: bool = True,
) -> dict:
    """Run a multi-season stress test.

    Args:
        db_path: Path to franchise .db file.
        n_seasons: Number of seasons to simulate.
        mode: 'invariants' (full battery each season) or 'smoke' (crash detection only).
        starting_season_year: Override starting season (default: read from DB).
        print_progress: Print progress messages to stdout.

    Returns:
        Dict with completed_seasons, crashed, crash_detail,
        invariant_results_by_year, health_report, duration_seconds.
    """
    overall_start = time.time()
    conn = get_connection(db_path)

    result = {
        'completed_seasons': 0,
        'crashed': False,
        'crash_detail': None,
        'invariant_results_by_year': {},
        'health_report': None,
        'duration_seconds': 0.0,
    }

    league = get_league_state(conn)
    if starting_season_year is None:
        starting_season_year = league['current_season']

    year_one = starting_season_year
    user_team_id = league['user_team_id']

    try:
        for season_idx in range(n_seasons):
            season_start = time.time()

            # Read current league state
            league = get_league_state(conn)
            season_year = league['current_season']
            user_team_id = league['user_team_id']

            if print_progress:
                print(f"\n  Season {season_idx + 1}/{n_seasons} "
                      f"(year {season_year})...")

            # ---- REGULAR SEASON ----
            if print_progress:
                print(f"    Regular season...", end="", flush=True)

            # Ensure we're at week 1 or later
            if league['current_week'] < 1:
                with conn:
                    update_league_state(conn, season_year, 1, 'regular')

            for wk in range(REGULAR_SEASON_WEEKS):
                if is_regular_season_complete(conn, season_year):
                    break
                advance_week(conn, db_path)

                # Generate press conference for player coach (headless auto-resolve)
                # Try Tier 2 first, then Tier 1 fallback
                from src.transactions.tier2_press_conference import generate_tier2_press_event
                from src.transactions.press_conference import generate_weekly_press_event
                player_coach_row = conn.execute("""
                    SELECT id, current_team_id FROM coach_career
                    WHERE is_player = 1 AND is_active = 1
                """).fetchone()

                tier2_fired = False
                if player_coach_row and player_coach_row['current_team_id']:
                    tier2 = generate_tier2_press_event(
                        conn, season_year, wk + 1,
                        player_coach_row['current_team_id'], player_coach_row['id'],
                        headless=True
                    )
                    tier2_fired = (tier2 is not None)

                # Tier 1 only if Tier 2 did NOT fire
                if not tier2_fired and player_coach_row and player_coach_row['current_team_id']:
                    generate_weekly_press_event(
                        conn, season_year, wk + 1,
                        player_coach_row['current_team_id'], player_coach_row['id'],
                        headless=True
                    )

            if print_progress:
                print(" done")

            # ---- PLAYOFFS ----
            if print_progress:
                print(f"    Playoffs...", end="", flush=True)

            with redirect_stdout(io.StringIO()):
                champion_id = run_full_playoffs(conn, db_path, season_year)

            # Post-playoff Tier 2 triggers (championship_won, playoff_loss)
            if player_coach_row and player_coach_row['current_team_id']:
                for pw in range(18, 22):
                    generate_tier2_press_event(
                        conn, season_year, pw,
                        player_coach_row['current_team_id'], player_coach_row['id'],
                        headless=True
                    )

            if print_progress:
                print(" done")

            # ---- ARCHIVE ----
            if print_progress:
                print(f"    Archive...", end="", flush=True)

            with redirect_stdout(io.StringIO()):
                with conn:
                    archive_season(conn, season_year)

            if print_progress:
                print(" done")

            # ---- AWARDS ----
            if print_progress:
                print(f"    Awards...", end="", flush=True)

            with conn:
                assign_awards(conn, season_year)

            if print_progress:
                print(" done")

            # ---- LEGACY ----
            with conn:
                update_legacy_score(conn, season_year, user_team_id)

            # ---- NEXT SEASON SETUP ----
            next_season = season_year + 1
            with conn:
                existing = get_season(conn, next_season)
                if not existing:
                    new_cap = int(league['salary_cap'] * (1 + CAP_INFLATION_RATE))
                    next_season_id = insert_new_season(conn, next_season, new_cap)
                    team_rows = get_all_teams(conn)
                    team_ids = [t['id'] for t in team_rows]
                    generate_full_schedule(conn, next_season_id, team_ids)
                else:
                    next_season_id = existing['id']

                update_league_state(conn, next_season, 0, 'offseason')

            # ---- OFFSEASON ----
            if print_progress:
                print(f"    Offseason...", end="", flush=True)

            with redirect_stdout(io.StringIO()):
                start_offseason(user_team_id, season_year, conn)

                # Advance through all offseason phases
                max_phases = len(OFFSEASON_PHASE_SEQUENCE) + 2  # safety limit
                for _ in range(max_phases):
                    state = get_offseason_state(conn, user_team_id, season_year)
                    if not state:
                        break
                    if state['current_phase'] == 'season_ready':
                        break
                    advance_phase(user_team_id, season_year, conn)

                # Auto-resolve any vacant coaches (player coach in vacancy state)
                from ..db.queries import get_vacant_coaches
                from ..transactions.coach_offers import auto_accept_best_offer
                for coach in get_vacant_coaches(conn):
                    if coach['is_player']:
                        auto_accept_best_offer(conn, coach['id'], season_year)

            if print_progress:
                print(" done")

            # ---- RESET FOR NEXT LOOP ----
            with conn:
                update_league_state(conn, next_season, 0, 'offseason')

            # ---- INVARIANTS ----
            if mode == 'invariants':
                inv_results = run_all_invariants(conn, season_year)
                result['invariant_results_by_year'][season_year] = inv_results

                if print_progress:
                    passed = sum(1 for r in inv_results if r['passed'])
                    failed = len(inv_results) - passed
                    print(f"    Invariants: {passed} passed, {failed} failed")

            result['completed_seasons'] += 1

            # ---- TIMEOUT CHECK ----
            elapsed = time.time() - season_start
            if elapsed > STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON:
                result['crash_detail'] = (
                    f"Season {season_year} took {elapsed:.0f}s "
                    f"(limit: {STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON}s)"
                )
                if print_progress:
                    print(f"    WARNING: {result['crash_detail']}")
                # Continue but note the timeout

    except Exception as e:
        result['crashed'] = True
        result['crash_detail'] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        if print_progress:
            print(f"\n  CRASH: {e}")

    finally:
        # Generate health report
        year_final = year_one + result['completed_seasons'] - 1
        if result['completed_seasons'] > 0:
            try:
                result['health_report'] = generate_health_report(
                    conn, year_one, year_final,
                )
            except Exception as e:
                result['health_report'] = f"Failed to generate health report: {e}"

        result['duration_seconds'] = time.time() - overall_start
        conn.close()

    return result
