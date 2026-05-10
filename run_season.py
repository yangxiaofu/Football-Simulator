#!/usr/bin/env python3
"""
Main CLI for advancing weeks, viewing standings, and simulating seasons.

Usage:
    python run_season.py saves/franchise.db --advance-week
    python run_season.py saves/franchise.db --advance-to-playoffs
    python run_season.py saves/franchise.db --simulate-playoffs
    python run_season.py saves/franchise.db --standings
    python run_season.py saves/franchise.db --stats
    python run_season.py saves/franchise.db --status
    python run_season.py saves/franchise.db --complete-season
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.connection import get_connection
from src.db.queries import (
    get_league_state,
    update_league_state,
    count_season_stats,
    get_player,
    get_season,
    get_team,
    get_all_teams,
    insert_new_season,
)
from src.league.season import advance_week, is_regular_season_complete, get_current_status
from src.league.standings import update_all_standings
from src.league.playoffs import run_full_playoffs, generate_playoff_bracket
from src.league.archive import archive_season
from src.league.development import run_full_development
from src.league.awards import assign_awards
from src.league.legacy import update_legacy_score
from src.ui.standings_display import print_all_standings
from src.ui.stats_display import print_all_leaders
from src.generation.schedule import generate_full_schedule
from src.utils.constants import REGULAR_SEASON_WEEKS, CAP_INFLATION_RATE, PLAYOFF_ALREADY_COMPLETE_MSG


def cmd_status(conn):
    """Display current season status."""
    status = get_current_status(conn)

    if 'error' in status:
        print(f"Error: {status['error']}")
        return

    print(f"\n  Season {status['season']} - Week {status['week']} ({status['phase'].title()})")
    print(f"  User Team ID: {status['user_team_id']}")

    if 'matchups' in status and status['matchups']:
        print(f"\n  Week {status['week']} Games:")
        for m in status['matchups']:
            if m['is_complete']:
                print(f"    {m['away_abbr']} {m['away_score']} "
                      f"@ {m['home_abbr']} {m['home_score']} (Final)")
            else:
                print(f"    {m['away_abbr']} @ {m['home_abbr']}")
    print()


def cmd_advance_week(conn, save_path):
    """Simulate current week's games and advance."""
    league = get_league_state(conn)
    season_year = league['current_season']
    week_num = league['current_week']

    if week_num < 1:
        # Initialize to week 1
        with conn:
            update_league_state(conn, season_year, 1, 'regular')
        week_num = 1

    if week_num > REGULAR_SEASON_WEEKS:
        print(f"  Regular season is over (currently at week {week_num}).")
        print("  Use --simulate-playoffs to run the playoffs.")
        return

    print(f"  Simulating Week {week_num}...")

    result = advance_week(conn, save_path, verbose_team_id=league['user_team_id'])

    print(f"  Week {result['week_number']} Results:")
    for r in result['results']:
        print(f"    {r['away_team']} {r['away_score']} "
              f"@ {r['home_team']} {r['home_score']}")

    if result['healed_count'] > 0:
        print(f"  {result['healed_count']} player(s) recovered from injury")

    # Weekly press conference (Tier 2-first, then Tier 1 fallback)
    player_coach = conn.execute("""
        SELECT id, current_team_id FROM coach_career
        WHERE is_player = 1 AND is_active = 1
    """).fetchone()

    if player_coach and player_coach['current_team_id']:
        from src.transactions.tier2_press_conference import generate_tier2_press_event

        # Try Tier 2 first (fires for reg season + playoffs)
        tier2 = generate_tier2_press_event(
            conn, season_year, week_num,
            player_coach['current_team_id'], player_coach['id'],
            headless=False
        )

        if tier2 and not tier2['resolved']:
            # Render multi-question dramatic press (NO autopilot)
            print("\n" + "=" * 70)
            print(f"*** PRESS CONFERENCE — Week {week_num} ***")
            print(f"[{tier2['trigger_type'].upper().replace('_', ' ')}]")
            print("=" * 70)

            total_owner = 0
            total_fan = 0
            total_locker = 0

            for q in tier2['questions']:
                print(f"\nReporter: \"{q['question']}\"")
                print()
                choices_list = list(q['responses'].items())
                for i, (choice_key, text) in enumerate(choices_list, 1):
                    print(f"  {i}. [{choice_key.upper():<15}] \"{text}\"")
                print()

                raw = input("Choice (1-3): ").strip().lower()
                try:
                    idx = int(raw) - 1
                    choice = choices_list[idx][0]
                except (ValueError, IndexError):
                    print("Invalid input — defaulting to 'accountable'.")
                    choice = 'accountable'

                from src.transactions.tier2_press_conference import resolve_tier2_question
                with conn:
                    result = resolve_tier2_question(conn, q['response_id'], choice)
                total_owner += result['delta_owner']
                total_fan += result['delta_fan']
                total_locker += result['delta_locker_room']

            print(f"\n  Total effects → Owner: {total_owner:+d}, Fan: {total_fan:+d}, "
                  f"Locker: {total_locker:+d}")

        elif tier2 and tier2['resolved']:
            # Already resolved (shouldn't normally happen in interactive)
            print(f"\n[Tier 2 press already resolved for this week]")

        elif week_num <= REGULAR_SEASON_WEEKS:
            # No Tier 2 — fall through to Tier 1 (regular season only)
            from src.transactions.press_conference import (
                generate_weekly_press_event,
                resolve_press_event,
                set_autopilot_default
            )

            event = generate_weekly_press_event(
                conn, season_year, week_num,
                player_coach['current_team_id'], player_coach['id'],
                headless=False
            )

            if not event['resolved']:
                # === INTERACTIVE PROMPT ===
                print("\n" + "=" * 70)
                print(f"PRESS CONFERENCE — Week {week_num}")
                print("=" * 70)
                print(f"Reporter: \"{event['question']}\"")
                print()
                choices_list = list(event['responses'].items())
                for i, (choice_key, text) in enumerate(choices_list, 1):
                    print(f"  {i}. [{choice_key.upper():<15}] \"{text}\"")
                print("\nEnter 1-3, or prefix with 'a' (e.g., 'a2') to set autopilot default.\n")

                raw = input("Choice: ").strip().lower()
                set_default = raw.startswith('a')
                if set_default:
                    raw = raw[1:].strip()

                try:
                    idx = int(raw) - 1
                    choice = choices_list[idx][0]
                except (ValueError, IndexError):
                    print("Invalid input — defaulting to 'accountable'.")
                    choice = 'accountable'

                with conn:
                    result = resolve_press_event(conn, event['press_event_id'], choice)

                if set_default:
                    with conn:
                        set_autopilot_default(conn, player_coach['id'], choice)
                    print(f"\nAutopilot set to '{choice}'. Future pressers auto-resolve.")

                print(f"  → Owner: {result['delta_owner']:+d}, Fan: {result['delta_fan']:+d}, "
                      f"Locker: {result['delta_locker_room']:+d}")
            else:
                print(f"\n[Autopilot] Press: \"{event['responses'][event['selected_response']]}\" ({event['selected_response']})")
                print(f"  → Owner: {event['delta_owner']:+d}, Fan: {event['delta_fan']:+d}, "
                      f"Locker: {event['delta_locker_room']:+d}")

    # Check if regular season is now complete
    new_league = get_league_state(conn)
    if new_league['current_week'] > REGULAR_SEASON_WEEKS:
        print(f"\n  Regular season complete!")
        print("  Run with --simulate-playoffs to begin the postseason.")
    else:
        print(f"\n  Advanced to Week {new_league['current_week']}")


def cmd_advance_to_playoffs(conn, save_path):
    """Simulate all remaining regular season weeks."""
    league = get_league_state(conn)
    season_year = league['current_season']
    week_num = league['current_week']

    if week_num < 1:
        with conn:
            update_league_state(conn, season_year, 1, 'regular')
        week_num = 1

    if week_num > REGULAR_SEASON_WEEKS:
        print("  Regular season is already complete.")
        return

    remaining = REGULAR_SEASON_WEEKS - week_num + 1
    print(f"  Simulating {remaining} remaining regular season week(s)...\n")

    for wk in range(week_num, REGULAR_SEASON_WEEKS + 1):
        result = advance_week(conn, save_path)
        wins_losses = {}
        for r in result['results']:
            # Just show scores briefly
            pass
        print(f"  Week {result['week_number']} complete "
              f"({len(result['results'])} games)")

    print(f"\n  Regular season complete!")
    print("  Run with --simulate-playoffs to begin the postseason.")


def cmd_simulate_playoffs(conn, save_path, force=False):
    """Run the full playoff bracket."""
    league = get_league_state(conn)
    season_year = league['current_season']

    # Idempotency guard
    season = get_season(conn, season_year)
    if season['champion_team_id'] is not None and not force:
        champion = get_team(conn, season['champion_team_id'])
        print(PLAYOFF_ALREADY_COMPLETE_MSG.format(
            year=season_year,
            team_city=champion['city'],
            team_nickname=champion['nickname']
        ))
        return  # Exit without error

    if not is_regular_season_complete(conn, season_year):
        print("  Regular season is not complete. Use --advance-to-playoffs first.")
        return

    print(f"\n  {season_year} Playoffs")
    print("=" * 50)

    champion_id = run_full_playoffs(conn, save_path, season_year)

    # Post-playoff Tier 2 check (championship_won, playoff_loss)
    player_coach = conn.execute("""
        SELECT id, current_team_id FROM coach_career
        WHERE is_player = 1 AND is_active = 1
    """).fetchone()

    if player_coach and player_coach['current_team_id']:
        from src.transactions.tier2_press_conference import (
            generate_tier2_press_event, resolve_tier2_question
        )
        for pw in range(18, 22):
            tier2 = generate_tier2_press_event(
                conn, season_year, pw,
                player_coach['current_team_id'], player_coach['id'],
                headless=False
            )
            if tier2 and not tier2['resolved']:
                print("\n" + "=" * 70)
                print(f"*** PRESS CONFERENCE — Playoff Week {pw} ***")
                print(f"[{tier2['trigger_type'].upper().replace('_', ' ')}]")
                print("=" * 70)

                for q in tier2['questions']:
                    print(f"\nReporter: \"{q['question']}\"")
                    print()
                    choices_list = list(q['responses'].items())
                    for i, (choice_key, text) in enumerate(choices_list, 1):
                        print(f"  {i}. [{choice_key.upper():<15}] \"{text}\"")
                    print()

                    raw = input("Choice (1-3): ").strip().lower()
                    try:
                        idx = int(raw) - 1
                        choice = choices_list[idx][0]
                    except (ValueError, IndexError):
                        choice = 'accountable'

                    with conn:
                        resolve_tier2_question(conn, q['response_id'], choice)

    champion = get_team(conn, champion_id)
    print(f"\n  🏆 {champion['city']} {champion['nickname']} win the Super Bowl!")
    print(f"\n  Season {season_year} is complete.")
    print(f"  Next steps:")
    print(f"    1. View awards: python run_season.py {save_path} --standings")
    print(f"    2. Begin offseason: python run_offseason.py {save_path} --start")
    print(f"\n{'='*50}")


def cmd_standings(conn):
    """Display current standings."""
    league = get_league_state(conn)
    season_year = league['current_season']
    print_all_standings(conn, season_year)


def cmd_stats(conn):
    """Display stat leaderboards."""
    league = get_league_state(conn)
    season_year = league['current_season']
    phase = league['current_phase']

    # If in offseason, show stats from the most recently completed season
    if phase == 'offseason':
        season_year = season_year - 1

    # Check if season stats exist
    count = count_season_stats(conn, season_year)

    if count > 0:
        print_all_leaders(conn, season_year)
    else:
        print("  No season stats available yet.")
        print("  Stats are aggregated at season end (--complete-season).")


def cmd_complete_season(conn, save_path):
    """Run a full season: regular season + playoffs + archive."""
    league = get_league_state(conn)
    season_year = league['current_season']

    print(f"\n  {season_year} Season Simulation")
    print("=" * 50)

    # Phase 1: Regular season
    if not is_regular_season_complete(conn, season_year):
        week_num = league['current_week']
        if week_num < 1:
            with conn:
                update_league_state(conn, season_year, 1, 'regular')
            week_num = 1

        remaining = REGULAR_SEASON_WEEKS - week_num + 1
        print(f"\n  Regular Season ({remaining} weeks to simulate)...")

        for wk in range(week_num, REGULAR_SEASON_WEEKS + 1):
            result = advance_week(conn, save_path)
            print(f"    Week {result['week_number']} complete "
                  f"({len(result['results'])} games)")

        print("  Regular season complete!")
    else:
        print("  Regular season already complete.")

    # Phase 2: Playoffs
    print(f"\n  Playoffs...")
    champion_id = run_full_playoffs(conn, save_path, season_year)

    # Phase 3: Archive
    print(f"\n  Season Archive...")
    with conn:
        archive_result = archive_season(conn, season_year)

    # Phase 4: Awards
    print(f"\n  Awards...")
    with conn:
        award_result = assign_awards(conn, season_year)

    # Print award winners
    if award_result.get('mvp'):
        mvp = get_player(conn, award_result['mvp'])
        if mvp:
            print(f"    MVP: {mvp['first_name']} {mvp['last_name']} ({mvp['position']})")

    if award_result.get('opoy'):
        opoy = get_player(conn, award_result['opoy'])
        if opoy:
            print(f"    OPOY: {opoy['first_name']} {opoy['last_name']} ({opoy['position']})")

    if award_result.get('dpoy'):
        dpoy = get_player(conn, award_result['dpoy'])
        if dpoy:
            print(f"    DPOY: {dpoy['first_name']} {dpoy['last_name']} ({dpoy['position']})")

    print(f"    Pro Bowl selections: {award_result['pro_bowl_count']}")
    print(f"    All-Pro selections: {award_result['all_pro_count']}")

    # Phase 5: Development
    print(f"\n  Player Development...")
    with conn:
        dev_result = run_full_development(conn, season_year)
    print(f"    {dev_result['players_developed']} players developed")
    print(f"    {dev_result['players_aged']} players aged/declined")
    print(f"    {dev_result['total_attribute_changes']} total attribute changes")

    # Phase 6: Legacy
    print(f"\n  Legacy Score...")
    with conn:
        legacy = update_legacy_score(conn, season_year, league['user_team_id'])

    # Phase 4 Prompt #9: Display layer integration
    from src.ui.season_summary import render_season_summary
    from src.ui.dramatic_moments import maybe_render_dynasty_moment, maybe_render_hof_moment

    player_coach = conn.execute("""
        SELECT id FROM coach_career
        WHERE is_player = 1 AND is_active = 1
    """).fetchone()

    if player_coach:
        coach_id = player_coach['id']

        # Dramatic moments first (rare, deserve spotlight)
        dynasty_screen = maybe_render_dynasty_moment(conn, season_year, coach_id, use_color=True)
        if dynasty_screen:
            print('\n')
            print(dynasty_screen)
            input()  # pause for player

        hof_screen = maybe_render_hof_moment(conn, season_year, coach_id, use_color=True)
        if hof_screen:
            print('\n')
            print(hof_screen)
            input()

        # Then standard season summary
        print('\n')
        print(render_season_summary(conn, season_year, coach_id, use_color=True))
    else:
        # Fallback to old display if no player coach (shouldn't happen)
        print(f"    Total Legacy Score: {legacy['total_legacy_score']}")
        print(f"    Championships: {legacy['championships']}")
        print(f"    Career Win %: {legacy['career_win_pct']:.3f}")
        if legacy['is_dynasty']:
            print(f"    DYNASTY STATUS ACHIEVED!")

    # Prepare for next season
    next_season = season_year + 1
    with conn:
        # Create next season record
        existing = get_season(conn, next_season)
        if not existing:
            new_cap = int(league['salary_cap'] * (1 + CAP_INFLATION_RATE))
            next_season_id = insert_new_season(conn, next_season, new_cap)

            # Get team IDs for schedule generation
            team_rows = get_all_teams(conn)
            team_ids = [t['id'] for t in team_rows]

            # Generate schedule for next season (creates weeks + games)
            total_games = generate_full_schedule(conn, next_season_id, team_ids)
            print(f"    Generated {total_games} games for {next_season} season")

        # Update league state to next season
        update_league_state(conn, next_season, 0, 'offseason')

    print(f"\n{'='*50}")

    champ = get_team(conn, champion_id)
    if champ:
        print(f"  {season_year} Champion: {champ['city']} {champ['nickname']}")

    print(f"  Ready for {next_season} season (currently in offseason)")
    print(f"{'='*50}\n")


def cmd_depth_chart(conn, team_id: int, position_filter: str = None):
    """Display depth chart for user's team, optionally filtered to one position."""
    from src.db.queries import get_team, get_league_state, get_depth_chart, get_player
    from src.utils.constants import DEPTH_CHART_POSITIONS

    team = get_team(conn, team_id)
    if not team:
        print(f"Error: Team not found")
        return

    league = get_league_state(conn)
    season_year = league['current_season']

    entries = get_depth_chart(conn, team_id, season_year, position_slot=position_filter)

    print(f"\n{'='*70}")
    print(f"DEPTH CHART — {team['city']} {team['nickname']} ({season_year})")
    print(f"{'='*70}\n")

    # Group by position
    by_position = {}
    for entry in entries:
        pos = entry['position_slot']
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(entry)

    # Display in order
    for position_slot in DEPTH_CHART_POSITIONS:
        if position_slot not in by_position:
            continue

        print(f"{position_slot:8}", end="")
        entries_at_pos = sorted(by_position[position_slot], key=lambda e: e['slot_order'])

        for entry in entries_at_pos:
            player = get_player(conn, entry['player_id'])
            flag = " *" if entry['is_user_set'] else ""
            print(f"  {entry['slot_order']}. {player['first_name']} {player['last_name']}{flag}", end="")
        print()

    print(f"\n{'='*70}")
    print("* = user-set (permanent)")
    print()


def cmd_set_starter(conn, team_id: int, position_slot: str, player_id: int):
    """Set a player as starter at a position on user's team."""
    from src.db.queries import get_league_state
    from src.transactions.depth_chart import set_depth_chart_entry

    league = get_league_state(conn)
    season_year = league['current_season']

    success, message = set_depth_chart_entry(
        conn, team_id, season_year, position_slot.upper(), 1, player_id, is_user_set=True
    )

    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")


def cmd_swap_depth(conn, team_id: int, position_slot: str, slot_a: int, slot_b: int):
    """Swap two players at different depth slots on user's team."""
    from src.db.queries import get_league_state
    from src.transactions.depth_chart import swap_depth_chart_positions

    league = get_league_state(conn)
    season_year = league['current_season']

    success, message = swap_depth_chart_positions(
        conn, team_id, season_year, position_slot.upper(), slot_a, slot_b
    )

    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")


def cmd_reset_depth(conn, team_id: int, position_filter: str = None):
    """Reset depth chart to auto-fill for user's team, optionally one position."""
    from src.db.queries import get_league_state
    from src.transactions.depth_chart import reset_team_depth_chart, initialize_depth_chart_for_team

    league = get_league_state(conn)
    season_year = league['current_season']

    # TODO: position_filter support - currently resets entire depth chart
    success, message = reset_team_depth_chart(conn, team_id, season_year)
    if success:
        # Re-initialize with auto-fill
        initialize_depth_chart_for_team(conn, team_id, season_year)
        print(f"✓ {message}")
        print(f"  Depth chart re-initialized with rating-based defaults")
    else:
        print(f"✗ {message}")


def main():
    parser = argparse.ArgumentParser(
        description='Football Simulator — Season Management',
    )
    parser.add_argument('save_path', help='Path to franchise .db file')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--advance-week', action='store_true',
                       help='Simulate current week and advance')
    group.add_argument('--advance-to-playoffs', action='store_true',
                       help='Simulate all remaining regular season weeks')
    group.add_argument('--simulate-playoffs', action='store_true',
                       help='Run the full playoff bracket')
    group.add_argument('--standings', action='store_true',
                       help='Display current standings')
    group.add_argument('--stats', action='store_true',
                       help='Display stat leaderboards')
    group.add_argument('--status', action='store_true',
                       help='Show current season/week/phase')
    group.add_argument('--complete-season', action='store_true',
                       help='Run full season + playoffs + archive')
    group.add_argument('--depth-chart', nargs='?', const='ALL', metavar='POSITION',
                       help='Display your team\'s depth chart, optionally filtered to one POSITION')
    group.add_argument('--set-starter', nargs=2, metavar=('POSITION', 'PLAYER_ID'),
                       help='Set your team\'s starter: --set-starter QB 123')
    group.add_argument('--swap-depth', nargs=3, metavar=('POSITION', 'SLOT_A', 'SLOT_B'),
                       help='Swap depth positions on your team: --swap-depth WR1 1 2')
    group.add_argument('--reset-depth', nargs='?', const='ALL', metavar='POSITION',
                       help='Reset your team\'s depth chart, optionally one POSITION')

    parser.add_argument('--force-playoffs', action='store_true',
                        help='Force re-simulation of playoffs (overrides idempotency check)')

    args = parser.parse_args()

    if not os.path.exists(args.save_path):
        print(f"Error: Save file not found: {args.save_path}")
        sys.exit(1)

    conn = get_connection(args.save_path)

    try:
        if args.status:
            cmd_status(conn)
        elif args.standings:
            cmd_standings(conn)
        elif args.stats:
            cmd_stats(conn)
        elif args.advance_week:
            cmd_advance_week(conn, args.save_path)
        elif args.advance_to_playoffs:
            cmd_advance_to_playoffs(conn, args.save_path)
        elif args.simulate_playoffs:
            cmd_simulate_playoffs(conn, args.save_path, force=args.force_playoffs)
        elif args.complete_season:
            cmd_complete_season(conn, args.save_path)
        elif args.depth_chart is not None:
            # Get user's team (Phase 5 Prompt #3 cleanup)
            league = get_league_state(conn)
            user_team_id = league['user_team_id']
            position_filter = None if args.depth_chart == 'ALL' else args.depth_chart
            cmd_depth_chart(conn, user_team_id, position_filter)
        elif args.set_starter:
            # Get user's team (Phase 5 Prompt #3 cleanup)
            league = get_league_state(conn)
            user_team_id = league['user_team_id']
            position, player_id = args.set_starter
            cmd_set_starter(conn, user_team_id, position, int(player_id))
        elif args.swap_depth:
            # Get user's team (Phase 5 Prompt #3 cleanup)
            league = get_league_state(conn)
            user_team_id = league['user_team_id']
            position, slot_a, slot_b = args.swap_depth
            cmd_swap_depth(conn, user_team_id, position, int(slot_a), int(slot_b))
        elif args.reset_depth is not None:
            # Get user's team (Phase 5 Prompt #3 cleanup)
            league = get_league_state(conn)
            user_team_id = league['user_team_id']
            position_filter = None if args.reset_depth == 'ALL' else args.reset_depth
            cmd_reset_depth(conn, user_team_id, position_filter)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
