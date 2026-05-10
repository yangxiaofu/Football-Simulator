#!/usr/bin/env python3
"""
Main CLI for offseason management — free agency, trades, draft, and roster cuts.

Usage:
    python run_offseason.py saves/franchise.db status
    python run_offseason.py saves/franchise.db advance
    python run_offseason.py saves/franchise.db fa-market [--position POS]
    python run_offseason.py saves/franchise.db fa-offer <player_id> --years N --aav AMT --bonus AMT --guaranteed AMT
    python run_offseason.py saves/franchise.db fa-pitch <player_id> --emphasis TYPE
    python run_offseason.py saves/franchise.db tag <player_id> --type TYPE
    python run_offseason.py saves/franchise.db tagged
    python run_offseason.py saves/franchise.db trade-offers
    python run_offseason.py saves/franchise.db propose-trade --to TEAM_ID --give-players IDS --get-players IDS ...
    python run_offseason.py saves/franchise.db board [--top N] [--position POS]
    python run_offseason.py saves/franchise.db draft
    python run_offseason.py saves/franchise.db release <player_id>
    python run_offseason.py saves/franchise.db roster
    python run_offseason.py saves/franchise.db summary
    python run_offseason.py saves/franchise.db help
"""

import argparse
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.connection import get_connection
from src.db.queries import (
    get_league_state,
    get_team,
    get_player,
    get_unsigned_free_agents,
    get_draft_board,
    get_draft_board_entry,
    get_scouting_flags_for_prospect,
    get_prospect_by_id,
    get_franchise_tags_for_team,
    get_all_tagged_players,
)
from src.league.offseason import (
    start_offseason,
    get_offseason_status,
    advance_phase,
    get_offseason_summary,
    run_offseason_week,
)
from src.transactions.free_agency import (
    get_interest_tier,
    submit_offer,
    resolve_offer,
    request_pitch_meeting,
    get_fa_market_status,
)
from src.transactions.franchise_tag import apply_franchise_tag
from src.transactions.trades import (
    propose_trade,
    receive_trade_offers,
    evaluate_trade,
    calculate_player_trade_value,
    calculate_pick_value,
)
from src.transactions.contracts import (
    get_market_value,
    calculate_dead_cap,
    release_player,
)
from src.transactions.draft import (
    get_on_the_clock,
    make_pick,
    run_ai_pick,
    generate_live_trade_offers,
    check_board_fall,
)
from src.ui.roster_display import print_roster_with_contracts
from src.utils.constants import (
    to_letter_grade,
    OFFSEASON_PHASE_SEQUENCE,
    ACTIVE_ROSTER_SIZE,
)


# ======================================================================
# PHASE NAME FORMATTING
# ======================================================================

PHASE_DISPLAY_NAMES = {
    'end_of_season_review': 'End-of-Season Review',
    'staff_evaluation': 'Staff Evaluation',
    'franchise_tag_window': 'Franchise Tag Window',
    'scouting_early': 'Early Scouting',
    'combine': 'Combine',
    'free_agency': 'Free Agency',
    'predraft': 'Pre-Draft',
    'draft': 'Draft',
    'training_camp': 'Training Camp',
    'season_ready': 'Season Ready',
}

# Map offseason phases to available CLI commands
PHASE_COMMANDS = {
    'end_of_season_review': ['advance'],
    'staff_evaluation': ['advance'],
    'franchise_tag_window': ['tag', 'tagged', 'advance'],
    'scouting_early': ['board', 'advance'],
    'combine': ['board', 'advance'],
    'free_agency': ['fa-market', 'fa-offer', 'fa-pitch', 'advance'],
    'predraft': ['board', 'advance'],
    'draft': ['board', 'draft', 'advance'],
    'training_camp': ['release', 'roster', 'advance'],
    'season_ready': [],
}

# Always-available commands
UNIVERSAL_COMMANDS = ['status', 'roster', 'summary', 'trade-offers', 'propose-trade', 'help']


# ======================================================================
# HELPER FUNCTIONS
# ======================================================================

def _get_team_and_season(conn):
    """Get user team ID and current season from league state."""
    league = get_league_state(conn)
    if not league:
        print("Error: league state not initialized", file=sys.stderr)
        sys.exit(1)

    team_id = league['user_team_id']
    season_year = league['current_season']

    if league['current_phase'] != 'offseason':
        print("Error: not currently in offseason phase", file=sys.stderr)
        print(f"  Current phase: {league['current_phase']}", file=sys.stderr)
        print("  Use run_season.py --complete-season first.", file=sys.stderr)
        sys.exit(1)

    return team_id, season_year


def _ensure_offseason_started(conn, team_id, season_year):
    """Ensure offseason state exists, starting it if needed."""
    from src.db.queries import get_offseason_state
    state = get_offseason_state(conn, team_id, season_year)
    if not state:
        start_offseason(team_id, season_year, conn)


def _format_phase_name(phase):
    """Convert internal phase name to display name."""
    return PHASE_DISPLAY_NAMES.get(phase, phase.replace('_', ' ').title())


# ======================================================================
# COMMAND IMPLEMENTATIONS
# ======================================================================

def cmd_status(conn):
    """Display current offseason status."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    status = get_offseason_status(team_id, season_year, conn)
    if 'error' in status:
        print(f"Error: {status['error']}", file=sys.stderr)
        sys.exit(1)

    team = get_team(conn, team_id)
    team_name = f"{team['city']} {team['nickname']}" if team else f"Team {team_id}"

    print(f"\n{'=' * 55}")
    print(f"  OFFSEASON STATUS — {season_year}")
    print(f"{'=' * 55}")
    print(f"  Team: {team_name} | Cap Space: ${status['cap_space']:,} "
          f"| Roster: {status['roster_count']}/{ACTIVE_ROSTER_SIZE}")
    print()
    print(f"  Current Phase: {_format_phase_name(status['current_phase']).upper()}")

    # Completed phases
    completed = [_format_phase_name(p) for p in status['phases_complete']]
    if completed:
        print(f"  Completed: {' · '.join(completed)}")

    # Remaining phases
    remaining = [_format_phase_name(p) for p in status['phases_remaining']]
    if remaining:
        print(f"  Remaining: {' · '.join(remaining)}")

    # Available actions
    current_phase = status['current_phase']
    phase_cmds = PHASE_COMMANDS.get(current_phase, [])
    if phase_cmds:
        print()
        print("  Available Actions:")
        cmd_descriptions = {
            'advance': 'Advance to next phase',
            'fa-market': 'View free agent market',
            'fa-offer': 'Submit an offer to a free agent',
            'fa-pitch': 'Request pitch meeting (Tier 2 only)',
            'tag': 'Apply franchise/transition tag',
            'tagged': 'View tagged players',
            'trade-offers': 'View incoming trade offers',
            'propose-trade': 'Submit trade proposal',
            'board': 'View draft board',
            'draft': 'Enter interactive draft',
            'release': 'Release a player',
            'roster': 'View roster with contracts',
        }
        for cmd in phase_cmds:
            desc = cmd_descriptions.get(cmd, '')
            print(f"    {cmd:<16} {desc}")

    if current_phase == 'season_ready':
        print()
        print("  Offseason complete! Use run_season.py to start the new season.")

    print()


def cmd_advance(conn):
    """Advance to next offseason phase."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    try:
        result = advance_phase(team_id, season_year, conn)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'=' * 55}")
    print(f"  PHASE TRANSITION")
    print(f"{'=' * 55}")
    print(f"  Previous: {_format_phase_name(result['old_phase'])}")
    print(f"  Next: {_format_phase_name(result['new_phase'])}")

    # Summarize automated actions
    on_leave = result.get('on_leave_results', {})
    on_enter = result.get('on_enter_results', {})

    actions = []
    if on_leave.get('ai_signings'):
        actions.append(f"AI teams completed free agency — {on_leave['ai_signings']} players signed")
    if on_leave.get('draft_completion'):
        actions.append("Draft completed — all picks used")
    if on_leave.get('rookies_signed'):
        actions.append(f"Rookie contracts signed — {on_leave['rookies_signed']} players")
    if on_leave.get('players_cut'):
        cut_count = len(on_leave['players_cut'])
        actions.append(f"Roster trimmed to {ACTIVE_ROSTER_SIZE} — {cut_count} player(s) cut")
    if on_enter.get('draft_class_year'):
        actions.append(f"Draft class generated for {on_enter['draft_class_year']}")
    if on_enter.get('combine_complete'):
        actions.append("Combine evaluation complete")
    if on_enter.get('fa_market_created'):
        fa_count = on_enter.get('fa_count', 0)
        actions.append(f"FA market opened — {fa_count} players available")
    if on_enter.get('board_built'):
        actions.append("Draft board built from scouting reports")
    if on_enter.get('draft_initialized'):
        total_picks = on_enter.get('total_picks', 0)
        actions.append(f"Draft initialized — {total_picks} total picks")

    if actions:
        print()
        print("  Automated Actions:")
        for action in actions:
            print(f"    * {action}")

    # Narrative
    narrative = result.get('narrative', '')
    if narrative:
        print()
        print(f"  \"{narrative}\"")

    print()


def cmd_roster(conn):
    """Display roster with contracts."""
    team_id, season_year = _get_team_and_season(conn)
    print_roster_with_contracts(conn, team_id, season_year)


def cmd_summary(conn):
    """Display full offseason summary."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    summary = get_offseason_summary(team_id, season_year, conn)

    print(f"\n{'=' * 55}")
    print(f"  OFFSEASON SUMMARY — {season_year}")
    print(f"{'=' * 55}")

    # FA Signings
    fa = summary['fa_signings']
    if fa:
        print(f"\n  FREE AGENT SIGNINGS ({len(fa)})")
        for s in fa:
            print(f"    {s['description']}")
    else:
        print("\n  FREE AGENT SIGNINGS (0)")
        print("    None")

    # Releases
    releases = summary['releases']
    if releases:
        print(f"\n  RELEASES ({len(releases)})")
        for r in releases:
            print(f"    {r['description']}")
    else:
        print("\n  RELEASES (0)")
        print("    None")

    # Trades
    trades = summary['trades']
    if trades:
        print(f"\n  TRADES ({len(trades)})")
        for t in trades:
            print(f"    {t['description']}")
    else:
        print("\n  TRADES (0)")
        print("    None")

    # Draft Picks
    picks = summary['draft_picks']
    if picks:
        print(f"\n  DRAFT PICKS ({len(picks)})")
        for p in picks:
            print(f"    Rd {p['round']}, Pick {p['pick']} — "
                  f"{p['name']} ({p['position']}) — {p['grade']}")
    else:
        print("\n  DRAFT PICKS (0)")
        print("    None")

    # Cap Summary
    print(f"\n  CAP SUMMARY")
    print(f"    Starting Cap: ${summary['starting_cap']:,}")
    print(f"    Net Spending: ${summary['net_cap_change']:,}")
    print(f"    Ending Cap: ${summary['ending_cap']:,}")
    print(f"    Roster Count: {summary['roster_count']}/{ACTIVE_ROSTER_SIZE}")
    print()


def cmd_fa_market(conn, position_filter=None):
    """Display free agent market."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    # Get market status
    try:
        market_status = get_fa_market_status(season_year, conn)
    except Exception:
        market_status = {'timing_phase': 'unknown', 'total_unsigned': 0}

    # Get all unsigned FAs
    free_agents = get_unsigned_free_agents(conn)
    if not free_agents:
        print("\n  No free agents available.")
        return

    # Filter by position if requested
    if position_filter:
        pos_upper = position_filter.upper()
        free_agents = [fa for fa in free_agents if fa['position'] == pos_upper]
        if not free_agents:
            print(f"\n  No free agents at position {pos_upper}.")
            return

    timing = market_status.get('timing_phase', 'unknown').upper()

    print(f"\n{'=' * 55}")
    print(f"  FREE AGENT MARKET — {timing}")
    print(f"{'=' * 55}")

    # Group by position
    by_position = {}
    for fa in free_agents:
        pos = fa['position']
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(fa)

    for pos in sorted(by_position.keys()):
        players = by_position[pos]
        print(f"\n  {pos} ({len(players)} available)")
        print(f"  {'ID':<6} {'Name':<25} {'Age':>4} {'Grade':<5} {'Market Value':<20} Signal")
        print(f"  {'-' * 70}")

        for fa in players[:10]:  # Show top 10 per position
            name = f"{fa['first_name']} {fa['last_name']}"[:25]
            grade = to_letter_grade(fa['true_overall'])

            # Get market value
            try:
                market = get_market_value(fa['id'], None, conn)
                low = market['low']
                premium = market['premium']
                value_str = f"${low // 1_000_000:.1f}M–${premium // 1_000_000:.1f}M"
            except (ValueError, Exception):
                value_str = "N/A"

            # Get interest signal
            interest = get_interest_tier(fa['id'], team_id, conn)
            signal = interest.get('signal', '')[:30]

            print(f"  {fa['id']:<6} {name:<25} {fa['age']:>4} {grade:<5} "
                  f"{value_str:<20} {signal}")

    total = market_status.get('total_unsigned', len(free_agents))
    print(f"\n  Total unsigned: {total} players")
    print()


def cmd_fa_offer(conn, player_id, years, aav, bonus, guaranteed):
    """Submit a contract offer to a free agent."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    # Validate player exists and is FA
    player = get_player(conn, player_id)
    if not player:
        print(f"Error: player {player_id} not found", file=sys.stderr)
        sys.exit(1)
    if player['roster_status'] != 'free_agent':
        print(f"Error: player {player_id} is not a free agent "
              f"(status: {player['roster_status']})", file=sys.stderr)
        sys.exit(1)

    name = f"{player['first_name']} {player['last_name']}"
    grade = to_letter_grade(player['true_overall'])

    print(f"\n{'=' * 55}")
    print(f"  CONTRACT OFFER SUBMITTED")
    print(f"{'=' * 55}")
    print(f"  Player: {name} ({player['position']}, {player['age']}) | Overall: {grade}")
    print(f"  Offer: {years} years / ${aav:,} AAV | "
          f"${guaranteed:,} guaranteed | ${bonus:,} signing bonus")

    # Submit offer
    try:
        offer_result = submit_offer(player_id, team_id, years, aav, bonus, guaranteed, conn)
    except ValueError as e:
        print(f"\n  Error: {e}", file=sys.stderr)
        sys.exit(1)

    if offer_result.get('warning'):
        print(f"\n  Warning: {offer_result['warning']}")

    # Resolve offer immediately
    try:
        resolution = resolve_offer(offer_result['id'], conn)
    except ValueError as e:
        print(f"\n  Error resolving offer: {e}", file=sys.stderr)
        sys.exit(1)

    response = resolution['response'].upper()
    print(f"\n  Agent Response: {response}")
    print(f"  \"{resolution['message']}\"")

    if resolution.get('counter_terms'):
        counter = resolution['counter_terms']
        print(f"\n  Counter terms: {counter['years']} years / "
              f"${counter['aav']:,} AAV | ${counter['guaranteed_money']:,} guaranteed")
        print(f"\n  [To accept: fa-offer {player_id} --years {counter['years']} "
              f"--aav {counter['aav']} --bonus {counter['signing_bonus']} "
              f"--guaranteed {counter['guaranteed_money']}]")

    if resolution['signed']:
        print("\n  Contract signed! Cap space updated.")
        team = get_team(conn, team_id)
        if team:
            print(f"  New cap space: ${team['cap_space']:,}")

    print()


def cmd_fa_pitch(conn, player_id, emphasis):
    """Request pitch meeting with a free agent."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    player = get_player(conn, player_id)
    if not player:
        print(f"Error: player {player_id} not found", file=sys.stderr)
        sys.exit(1)

    name = f"{player['first_name']} {player['last_name']}"

    try:
        result = request_pitch_meeting(player_id, team_id, emphasis, conn)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'=' * 55}")
    print(f"  PITCH MEETING — {name}")
    print(f"{'=' * 55}")
    print(f"  Emphasis: {emphasis.upper()}")
    print()
    print(f"  Outcome: {result['outcome'].upper()}")
    print(f"  \"{result['message']}\"")

    if result['tier_change'] > 0:
        print(f"\n  Interest Level: Improved (Tier {result['new_tier']})")
    elif result['tier_change'] < 0:
        print(f"\n  Interest Level: Declined (Tier {result['new_tier']})")
    else:
        print(f"\n  Interest Level: Unchanged (Tier {result['new_tier']})")

    print()


def cmd_tag(conn, player_id, tag_type):
    """Apply franchise or transition tag."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    try:
        result = apply_franchise_tag(player_id, team_id, tag_type, season_year, conn)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    player = get_player(conn, player_id)
    name = f"{player['first_name']} {player['last_name']}" if player else f"Player {player_id}"
    grade = to_letter_grade(player['true_overall']) if player else "?"

    print(f"\n{'=' * 55}")
    print(f"  FRANCHISE TAG APPLIED")
    print(f"{'=' * 55}")
    print(f"  Player: {name} ({player['position'] if player else '?'}) | Overall: {grade}")
    print(f"  Tag Type: {tag_type.upper()}")
    print(f"  Salary: ${result['salary']:,} (fully guaranteed)")
    print(f"  Cap Hit: ${result['cap_hit']:,}")
    print()
    print(f"  Consecutive Tag Count: {result['consecutive_tag_count']}")
    print(f"  Satisfaction Impact: {result['satisfaction_delta']}")
    print()
    print(f"  Tag successfully applied.")

    team = get_team(conn, team_id)
    if team:
        print(f"  New cap space: ${team['cap_space']:,}")
    print()


def cmd_tagged(conn):
    """List all tagged players."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    tags = get_franchise_tags_for_team(conn, team_id, season_year)

    if not tags:
        print("\n  No franchise tags applied this offseason.\n")
        return

    print(f"\n{'=' * 55}")
    print(f"  FRANCHISE TAGGED PLAYERS — {season_year}")
    print(f"{'=' * 55}")
    print(f"\n  {'Player':<25} {'Pos':<5} {'Type':<12} {'Salary':>14} {'Consecutive'}")
    print(f"  {'-' * 65}")

    for tag in tags:
        name = f"{tag['first_name']} {tag['last_name']}"[:25]
        tag_type = tag['tag_type'].title() if 'tag_type' in tag.keys() else 'Unknown'
        salary = tag['salary'] if 'salary' in tag.keys() else 0
        consec = tag['consecutive_count'] if 'consecutive_count' in tag.keys() else 1
        ordinal = {1: '1st', 2: '2nd', 3: '3rd'}.get(consec, f'{consec}th')
        print(f"  {name:<25} {tag['position']:<5} {tag_type:<12} "
              f"${salary:>12,} {ordinal} tag")

    print(f"\n  Total: {len(tags)} tagged player(s)")
    print()


def cmd_trade_offers(conn):
    """View incoming AI trade offers."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    offers = receive_trade_offers(team_id, season_year, conn)

    if not offers:
        print("\n  No incoming trade offers at this time.\n")
        return

    print(f"\n{'=' * 55}")
    print(f"  INCOMING TRADE OFFERS")
    print(f"{'=' * 55}")

    for i, offer in enumerate(offers, 1):
        print(f"\n  Offer #{i} — {offer.get('from_team_name', offer.get('offering_team_name', 'Unknown'))}")

        # What they want
        if offer.get('requested_player_name'):
            print(f"    They want:  {offer['requested_player_name']}")
        elif offer.get('assets_requested'):
            req_desc = _describe_offer_assets(offer['assets_requested'])
            print(f"    They want:  {req_desc}")

        # What they offer
        if offer.get('offered_assets'):
            off_desc = _describe_offer_assets(offer['offered_assets'])
            print(f"    They offer: {off_desc}")

        if offer.get('message'):
            print(f"    Message: \"{offer['message']}\"")

    print()


def cmd_propose_trade(conn, to_team_id, give_players, give_picks, get_players, get_picks):
    """Submit a trade proposal to an AI team."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    # Build asset dicts
    offered_assets = {
        'players': give_players or [],
        'picks': give_picks or [],
    }
    requested_assets = {
        'players': get_players or [],
        'picks': get_picks or [],
    }

    # Validate target team
    target_team = get_team(conn, to_team_id)
    if not target_team:
        print(f"Error: team {to_team_id} not found", file=sys.stderr)
        sys.exit(1)

    target_name = f"{target_team['city']} {target_team['nickname']}"

    print(f"\n{'=' * 55}")
    print(f"  TRADE PROPOSAL TO {target_name.upper()}")
    print(f"{'=' * 55}")

    # Display what's being traded
    if offered_assets['players']:
        for pid in offered_assets['players']:
            p = get_player(conn, pid)
            if p:
                print(f"  You give: {p['first_name']} {p['last_name']} "
                      f"({p['position']}, {to_letter_grade(p['true_overall'])})")
    if offered_assets['picks']:
        for pick in offered_assets['picks']:
            print(f"  You give: {pick['year']} Round {pick['round']} Pick")

    if requested_assets['players']:
        for pid in requested_assets['players']:
            p = get_player(conn, pid)
            if p:
                print(f"  You get:  {p['first_name']} {p['last_name']} "
                      f"({p['position']}, {to_letter_grade(p['true_overall'])})")
    if requested_assets['picks']:
        for pick in requested_assets['picks']:
            print(f"  You get:  {pick['year']} Round {pick['round']} Pick")

    # Execute trade proposal
    try:
        result = propose_trade(
            team_id, to_team_id, offered_assets, requested_assets, conn,
        )
    except ValueError as e:
        print(f"\n  Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Display result
    eval_data = result.get('evaluation', {})
    offered_value = eval_data.get('offered_value', 0)
    requested_value = eval_data.get('requested_value', 0)
    print(f"\n  Value Assessment: offered {offered_value}pts | requested {requested_value}pts")

    response = result['response'].upper()
    print(f"\n  AI Response: {response}")
    print(f"  \"{result['message']}\"")

    if result['executed']:
        print("\n  Trade executed! Rosters and draft picks updated.")
        team = get_team(conn, team_id)
        if team:
            print(f"  Cap space: ${team['cap_space']:,}")

    if result.get('counter_assets'):
        print(f"\n  Counter proposal received — rerun with adjusted assets.")

    print()


def cmd_board(conn, top_n=50, position_filter=None):
    """Display draft board."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    # Draft board uses next season's draft year
    draft_year = season_year + 1

    board = get_draft_board(conn, team_id, draft_year)
    if not board:
        print("\n  Draft board not yet built. Advance to Pre-Draft phase first.\n")
        return

    # Join with prospect info
    board_entries = []
    for entry in board:
        prospect = get_prospect_by_id(conn, entry['prospect_id'])
        if not prospect:
            continue
        if prospect['was_drafted']:
            continue  # Skip already-drafted prospects

        if position_filter and prospect['position'] != position_filter.upper():
            continue

        # Get flags for this prospect
        flags = get_scouting_flags_for_prospect(conn, entry['prospect_id'], team_id, draft_year)
        green_count = sum(1 for f in flags if f['flag_type'] == 'green')
        caution_count = sum(1 for f in flags if f['flag_type'] == 'caution')
        red_count = sum(1 for f in flags if f['flag_type'] == 'red')

        # Determine trend arrow
        trend = entry['phase_trend'] if entry['phase_trend'] else 'stable'
        trend_arrow = {'improving': '\u2191', 'stable': '\u2192', 'declining': '\u2193'}.get(
            trend, '\u2192')

        rank = int(entry['board_override'] or entry['board_rank'])
        grade = to_letter_grade(prospect['true_overall'])

        board_entries.append({
            'rank': rank,
            'name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'college': prospect['college'] or '',
            'grade': grade,
            'trend': trend_arrow,
            'green': green_count,
            'caution': caution_count,
            'red': red_count,
            'prospect_id': prospect['id'],
        })

    if not board_entries:
        print("\n  No prospects on draft board matching criteria.\n")
        return

    # Limit to top N
    board_entries = board_entries[:top_n]

    print(f"\n{'=' * 55}")
    print(f"  YOUR DRAFT BOARD — {draft_year}")
    print(f"{'=' * 55}")
    print(f"  Showing top {len(board_entries)} prospects")
    print()
    print(f"  {'RK':<4} {'ID':<5} {'NAME':<22} {'POS':<4} {'COLLEGE':<16} "
          f"{'GRD':<4} {'TR':<3} FLAGS")
    print(f"  {'-' * 68}")

    for e in board_entries:
        name = e['name'][:22]
        college = e['college'][:16]

        flag_str = ''
        if e['green']:
            flag_str += 'G' * e['green']
        if e['caution']:
            flag_str += 'Y' * e['caution']
        if e['red']:
            flag_str += 'R' * e['red']

        print(f"  {e['rank']:<4} {e['prospect_id']:<5} {name:<22} {e['position']:<4} "
              f"{college:<16} {e['grade']:<4} {e['trend']:<3} {flag_str}")

    print(f"\n  Legend: G=Green flag | Y=Caution flag | R=Red flag")
    print(f"  Trend: \u2191=Improving | \u2192=Stable | \u2193=Declining")
    print()


def cmd_draft(conn):
    """Interactive draft loop."""
    team_id, season_year = _get_team_and_season(conn)
    _ensure_offseason_started(conn, team_id, season_year)

    draft_year = season_year + 1

    print(f"\n{'=' * 55}")
    print(f"  {draft_year} NFL DRAFT")
    print(f"{'=' * 55}")
    print("  Commands: pick <id>, board, skip, quit")
    print()

    while True:
        pick = get_on_the_clock(draft_year, conn)
        if not pick:
            print("\n  Draft complete!")
            break

        pick_team_id = pick['team_id']
        pick_overall = pick['pick_number_overall']
        round_num = pick['round']
        pick_in_round = pick['pick_in_round']

        if pick_team_id == team_id:
            # User's turn
            team = get_team(conn, team_id)
            team_name = f"{team['city']} {team['nickname']}" if team else "Your Team"

            print(f"\n  === ROUND {round_num} | PICK {pick_overall} OVERALL | "
                  f"YOU ARE ON THE CLOCK ===")

            # Show top 5 from board
            board = get_draft_board(conn, team_id, draft_year)
            available = []
            for entry in board:
                prospect = get_prospect_by_id(conn, entry['prospect_id'])
                if prospect and not prospect['was_drafted']:
                    grade = to_letter_grade(prospect['true_overall'])
                    available.append({
                        'id': prospect['id'],
                        'name': f"{prospect['first_name']} {prospect['last_name']}",
                        'position': prospect['position'],
                        'grade': grade,
                    })
                if len(available) >= 5:
                    break

            if available:
                print("\n  Top Available (from board):")
                for i, a in enumerate(available, 1):
                    print(f"    {i}. #{a['id']} {a['name']} ({a['position']}) — {a['grade']}")

            # Check for board falls
            for a in available[:3]:
                fall = check_board_fall(a['id'], pick_overall, draft_year, conn)
                if fall:
                    print(f"\n  BOARD FALL: {a['name']} has fallen "
                          f"{fall.get('picks_fallen', '?')} spots below mock position.")

            # Check for trade offers
            offers = generate_live_trade_offers(team_id, pick['id'], draft_year, conn)
            if offers:
                print(f"\n  TRADE OFFER(S): {len(offers)} team(s) want to trade up.")
                for off in offers[:2]:
                    print(f"    {off['offering_team_name']}: {off['narrative']}")

            print(f"\n  Actions: pick <prospect_id> | board | skip | quit")

            # Interactive input loop
            while True:
                try:
                    user_input = input("  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n  Draft exited. Remaining picks will be auto-simulated.")
                    _auto_complete_remaining(draft_year, team_id, conn)
                    return

                if not user_input:
                    continue

                parts = user_input.split()
                cmd = parts[0].lower()

                if cmd == 'quit':
                    print("  Exiting draft. Remaining picks will be auto-simulated.")
                    _auto_complete_remaining(draft_year, team_id, conn)
                    return

                elif cmd == 'skip':
                    print("  Simulating until your next pick...")
                    _skip_to_next_user_pick(draft_year, team_id, conn)
                    break

                elif cmd == 'board':
                    top = 10
                    if len(parts) > 1:
                        try:
                            top = int(parts[1])
                        except ValueError:
                            pass
                    cmd_board(conn, top_n=top)
                    continue

                elif cmd == 'pick':
                    if len(parts) < 2:
                        print("  Usage: pick <prospect_id>")
                        continue
                    try:
                        prospect_id = int(parts[1])
                    except ValueError:
                        print("  Invalid prospect ID")
                        continue

                    try:
                        pick_result = make_pick(team_id, prospect_id, draft_year, conn)
                    except ValueError as e:
                        print(f"  Error: {e}")
                        continue

                    print(f"\n  With pick #{pick_result['pick_number']}, "
                          f"you select...")
                    print(f"  {pick_result['prospect_name']}, "
                          f"{pick_result['position']} — {pick_result['display_grade']}")
                    print(f"\n  War Room: \"{pick_result['war_room_reaction']}\"")
                    break

                else:
                    print("  Unknown command. Use: pick <id>, board, skip, quit")

        else:
            # AI team's turn
            ai_team = get_team(conn, pick_team_id)
            ai_name = f"{ai_team['city']} {ai_team['nickname']}" if ai_team else f"Team {pick_team_id}"

            try:
                ai_result = run_ai_pick(pick_team_id, draft_year, conn)
                print(f"  Pick #{pick_overall} — {ai_name} select "
                      f"{ai_result['prospect_name']} ({ai_result['position']}) — "
                      f"{ai_result['display_grade']}")
            except (ValueError, Exception) as e:
                print(f"  Pick #{pick_overall} — {ai_name} — error: {e}")
                break

            time.sleep(0.3)

    # Draft summary
    _print_draft_summary(team_id, draft_year, conn)


def cmd_release(conn, player_id):
    """Release a player from the roster."""
    team_id, season_year = _get_team_and_season(conn)

    player = get_player(conn, player_id)
    if not player:
        print(f"Error: player {player_id} not found", file=sys.stderr)
        sys.exit(1)
    if player['team_id'] != team_id:
        print(f"Error: player {player_id} is not on your roster", file=sys.stderr)
        sys.exit(1)

    name = f"{player['first_name']} {player['last_name']}"
    grade = to_letter_grade(player['true_overall'])

    # Preview dead cap
    dead_cap = calculate_dead_cap(player_id, season_year, conn)
    team = get_team(conn, team_id)
    current_cap = team['cap_space'] if team else 0

    print(f"\n{'=' * 55}")
    print(f"  RELEASE PLAYER")
    print(f"{'=' * 55}")
    print(f"  Player: {name} ({player['position']}) | Overall: {grade} | Age: {player['age']}")
    print(f"\n  Dead Cap Impact: ${dead_cap:,}")
    print(f"  Current Cap Space: ${current_cap:,}")

    # Confirm
    try:
        confirm = input("\n  Are you sure? This cannot be undone. [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if confirm != 'y':
        print("  Cancelled.")
        return

    try:
        result = release_player(player_id, team_id, season_year, conn)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  {name} has been released.")
    print(f"  Dead cap: ${result['dead_cap']:,}")
    print(f"  Remaining cap: ${result['new_cap_space']:,}")
    print()


def cmd_help():
    """Display command reference."""
    print(f"\n{'=' * 55}")
    print(f"  OFFSEASON COMMANDS")
    print(f"{'=' * 55}")

    print("""
  UNIVERSAL
    status              Display current offseason status
    advance             Advance to next phase
    roster              View team roster with contracts
    summary             Full offseason recap
    help                Show this help message

  FREE AGENCY
    fa-market           View available free agents
    fa-offer            Submit contract offer to FA
    fa-pitch            Request pitch meeting (Tier 2 only)

  FRANCHISE TAGS
    tag                 Apply franchise/transition tag
    tagged              List tagged players

  TRADES
    trade-offers        View incoming AI trade offers
    propose-trade       Submit trade proposal

  DRAFT
    board               View draft board
    draft               Enter interactive draft

  ROSTER MANAGEMENT
    release             Release a player from roster

  For detailed help: python run_offseason.py <save> <command> --help
""")


# ======================================================================
# DRAFT HELPERS
# ======================================================================

def _skip_to_next_user_pick(draft_year, team_id, conn):
    """Simulate AI picks until it's the user's turn again."""
    while True:
        pick = get_on_the_clock(draft_year, conn)
        if not pick:
            break
        if pick['team_id'] == team_id:
            break
        try:
            ai_team = get_team(conn, pick['team_id'])
            ai_name = f"{ai_team['city']} {ai_team['nickname']}" if ai_team else "AI"
            ai_result = run_ai_pick(pick['team_id'], draft_year, conn)
            print(f"  Pick #{pick['pick_number_overall']} — {ai_name} select "
                  f"{ai_result['prospect_name']} ({ai_result['position']}) — "
                  f"{ai_result['display_grade']}")
            time.sleep(0.1)
        except (ValueError, Exception):
            break


def _auto_complete_remaining(draft_year, team_id, conn):
    """Auto-simulate all remaining draft picks (including user's)."""
    while True:
        pick = get_on_the_clock(draft_year, conn)
        if not pick:
            break
        try:
            run_ai_pick(pick['team_id'], draft_year, conn)
        except (ValueError, Exception):
            break
    _print_draft_summary(team_id, draft_year, conn)


def _print_draft_summary(team_id, draft_year, conn):
    """Print summary of user's draft picks."""
    from src.db.queries import get_drafted_prospects_for_team

    picks = get_drafted_prospects_for_team(conn, team_id, draft_year)
    if picks:
        print(f"\n  === YOUR {draft_year} DRAFT SELECTIONS ===")
        for p in picks:
            grade = to_letter_grade(p['true_overall'])
            print(f"    Rd {p['draft_round']}, Pick {p['draft_pick']} — "
                  f"{p['first_name']} {p['last_name']} ({p['position']}) — {grade}")
    print()


def _describe_offer_assets(assets):
    """Format a list of trade offer assets for display."""
    parts = []
    if isinstance(assets, list):
        for a in assets:
            if isinstance(a, dict):
                if 'round' in a:
                    pick_str = f"Round {a['round']}"
                    if a.get('pick_number'):
                        pick_str += f" (#{a['pick_number']})"
                    parts.append(pick_str)
                elif 'player_name' in a:
                    parts.append(a['player_name'])
            else:
                parts.append(str(a))
    return ', '.join(parts) if parts else 'Unknown assets'


# ======================================================================
# ARG PARSING
# ======================================================================

def _parse_picks(pick_str):
    """Parse pick format 'round:year' into list of pick dicts."""
    if not pick_str:
        return []
    picks = []
    for item in pick_str.split(','):
        item = item.strip()
        if ':' in item:
            parts = item.split(':')
            try:
                round_num = int(parts[0])
                year = int(parts[1])
                picks.append({'round': round_num, 'year': year})
            except (ValueError, IndexError):
                print(f"Error: invalid pick format '{item}'. Use round:year (e.g., 2:2026)",
                      file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Error: invalid pick format '{item}'. Use round:year (e.g., 2:2026)",
                  file=sys.stderr)
            sys.exit(1)
    return picks


def _parse_player_ids(id_str):
    """Parse comma-separated player IDs."""
    if not id_str:
        return []
    ids = []
    for item in id_str.split(','):
        item = item.strip()
        try:
            ids.append(int(item))
        except ValueError:
            print(f"Error: invalid player ID '{item}'", file=sys.stderr)
            sys.exit(1)
    return ids


def main():
    parser = argparse.ArgumentParser(
        description='Football Simulator — Offseason Management',
    )
    parser.add_argument('save_path', help='Path to franchise .db file')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Universal commands
    subparsers.add_parser('status', help='Display offseason status')
    subparsers.add_parser('advance', help='Advance to next phase')
    subparsers.add_parser('roster', help='View roster')
    subparsers.add_parser('summary', help='Offseason recap')
    subparsers.add_parser('help', help='Show command reference')

    # FA commands
    fa_market = subparsers.add_parser('fa-market', help='View FA market')
    fa_market.add_argument('--position', help='Filter by position (e.g., QB, WR)')

    fa_offer = subparsers.add_parser('fa-offer', help='Submit FA offer')
    fa_offer.add_argument('player_id', type=int, help='Player ID to offer')
    fa_offer.add_argument('--years', type=int, required=True, help='Contract years')
    fa_offer.add_argument('--aav', type=int, required=True, help='Average annual value')
    fa_offer.add_argument('--bonus', type=int, required=True, help='Signing bonus')
    fa_offer.add_argument('--guaranteed', type=int, required=True, help='Guaranteed money')

    fa_pitch = subparsers.add_parser('fa-pitch', help='Request pitch meeting')
    fa_pitch.add_argument('player_id', type=int, help='Player ID')
    fa_pitch.add_argument('--emphasis', required=True,
                          choices=['winning', 'scheme_fit', 'role', 'money_first'],
                          help='Pitch emphasis')

    # Franchise tag commands
    tag_parser = subparsers.add_parser('tag', help='Apply franchise/transition tag')
    tag_parser.add_argument('player_id', type=int, help='Player ID to tag')
    tag_parser.add_argument('--type', required=True, dest='tag_type',
                            choices=['exclusive', 'transition'],
                            help='Tag type')

    subparsers.add_parser('tagged', help='List tagged players')

    # Trade commands
    subparsers.add_parser('trade-offers', help='View incoming trade offers')

    trade = subparsers.add_parser('propose-trade', help='Submit trade proposal')
    trade.add_argument('--to', type=int, required=True, dest='to_team_id',
                       help='Target team ID')
    trade.add_argument('--give-players', type=str, default='',
                       help='Comma-separated player IDs to give')
    trade.add_argument('--give-picks', type=str, default='',
                       help='Picks to give (format: round:year, e.g., 2:2026,4:2025)')
    trade.add_argument('--get-players', type=str, default='',
                       help='Comma-separated player IDs to get')
    trade.add_argument('--get-picks', type=str, default='',
                       help='Picks to get (format: round:year)')

    # Draft commands
    board_parser = subparsers.add_parser('board', help='View draft board')
    board_parser.add_argument('--top', type=int, default=50, help='Number of prospects to show')
    board_parser.add_argument('--position', help='Filter by position')

    subparsers.add_parser('draft', help='Enter interactive draft')

    # Roster management
    release_parser = subparsers.add_parser('release', help='Release a player')
    release_parser.add_argument('player_id', type=int, help='Player ID to release')

    args = parser.parse_args()

    if args.command == 'help':
        cmd_help()
        return

    if not os.path.exists(args.save_path):
        print(f"Error: save file not found at {args.save_path}", file=sys.stderr)
        sys.exit(1)

    conn = get_connection(args.save_path)

    try:
        if args.command == 'status':
            cmd_status(conn)
        elif args.command == 'advance':
            cmd_advance(conn)
        elif args.command == 'roster':
            cmd_roster(conn)
        elif args.command == 'summary':
            cmd_summary(conn)
        elif args.command == 'fa-market':
            cmd_fa_market(conn, position_filter=args.position)
        elif args.command == 'fa-offer':
            cmd_fa_offer(conn, args.player_id, args.years, args.aav,
                         args.bonus, args.guaranteed)
        elif args.command == 'fa-pitch':
            cmd_fa_pitch(conn, args.player_id, args.emphasis)
        elif args.command == 'tag':
            cmd_tag(conn, args.player_id, args.tag_type)
        elif args.command == 'tagged':
            cmd_tagged(conn)
        elif args.command == 'trade-offers':
            cmd_trade_offers(conn)
        elif args.command == 'propose-trade':
            give_players = _parse_player_ids(args.give_players)
            give_picks = _parse_picks(args.give_picks)
            get_players = _parse_player_ids(args.get_players)
            get_picks = _parse_picks(args.get_picks)
            cmd_propose_trade(conn, args.to_team_id,
                              give_players, give_picks,
                              get_players, get_picks)
        elif args.command == 'board':
            cmd_board(conn, top_n=args.top, position_filter=args.position)
        elif args.command == 'draft':
            cmd_draft(conn)
        elif args.command == 'release':
            cmd_release(conn, args.player_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
