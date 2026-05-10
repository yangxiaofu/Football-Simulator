"""
Offseason loop orchestrator.

Sequences all Phase 3 subsystems into a playable offseason cycle:
end-of-season review → staff evaluation → franchise tags → scouting →
combine → free agency → predraft → draft → training camp → season ready.

Pure orchestration layer — all domain logic lives in the subsystem modules.
Follows the same pattern as season.py for consistency.
"""

import sqlite3

from ..db.queries import (
    get_all_teams,
    get_drafted_prospects_for_team,
    get_league_state,
    get_legacy_score_delta,
    get_offseason_state,
    get_roster_count,
    get_cuttable_players,
    get_team,
    insert_offseason_state,
    mark_offseason_phase_complete,
    update_league_state,
    update_offseason_phase,
    get_transaction_summary_for_offseason,
)
from ..db.cap import recalculate_cap_space
from ..utils.constants import (
    OFFSEASON_PHASE_SEQUENCE,
    OFFSEASON_PHASE_NARRATIVES,
    OFFSEASON_WEEK,
    TRAINING_CAMP_ROSTER_LIMIT,
    POSITION_MINIMUM_ROSTER,
    to_letter_grade,
)


def start_offseason(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Begin the offseason after the season/playoffs complete.

    Entry point called after archive_season() finishes. Creates the
    offseason_state record, runs player development, and sets the
    league phase to 'offseason'.

    Args:
        team_id: User's team ID.
        season_year: The season that just ended.
        conn: Database connection.

    Returns:
        Dict with season_year, team_id, current_phase, narrative,
        and development_results.
    """
    # Idempotency: return existing state if already started
    existing = get_offseason_state(conn, team_id, season_year)
    if existing:
        narrative = OFFSEASON_PHASE_NARRATIVES['end_of_season_review'].format(
            season_year=season_year,
        )
        return {
            'season_year': season_year,
            'team_id': team_id,
            'current_phase': existing['current_phase'],
            'narrative': narrative,
        }

    from ..league.development import run_full_development
    from ..league.team_phase import update_all_team_phases
    from ..transactions.coaching_carousel import run_coaching_carousel
    from ..league.owner_sentiment import set_preseason_expectation, finalize_season_sentiment
    # Phase 4 Prompt #7 imports
    from ..league.legacy import update_all_coach_legacy_scores, evaluate_dynasty_and_hof
    from ..league.peer_ranking import update_peer_rankings
    from ..league.narrative_beats import generate_all_narrative_beats

    first_phase = OFFSEASON_PHASE_SEQUENCE[0]

    with conn:
        # Phase classification
        phase_results = update_all_team_phases(conn, season_year)

        # Initialize sentiment for next season and finalize for season that just ended
        for team in get_all_teams(conn):
            tid = team['id']
            # Initialize sentiment for upcoming season (season_year + 1)
            from ..league.owner_sentiment import initialize_sentiment
            initialize_sentiment(conn, tid, season_year + 1)
            set_preseason_expectation(conn, tid, season_year + 1)
            # Finalize sentiment for season that just ended
            finalize_season_sentiment(conn, tid, season_year)

        # PHASE 4 PROMPT #7: Coach legacy expansion
        # (Must run before coaching carousel, as narrative beats reference sentiment)

        # 1. Update per-coach legacy with multipliers
        update_all_coach_legacy_scores(conn, season_year)

        # 2. Check dynasty/HOF triggers for all active coaches
        from ..db.queries import get_all_active_coaches
        active_coaches = get_all_active_coaches(conn)
        for coach in active_coaches:
            evaluate_dynasty_and_hof(conn, coach['id'], season_year)

        # 3. Compute peer rankings
        update_peer_rankings(conn, season_year)

        # 4. Generate narrative beats
        generate_all_narrative_beats(conn, season_year)

        # Coaching carousel (now uses sentiment-aware firing)
        carousel_results = run_coaching_carousel(conn, season_year)

        # Run player development and aging for all players
        dev_results = run_full_development(conn, season_year)

        # Create offseason state record
        insert_offseason_state(conn, team_id, season_year, first_phase)

        # Set league to offseason mode
        update_league_state(conn, season_year, OFFSEASON_WEEK, 'offseason')

    # Build narrative
    legacy = get_legacy_score_delta(conn, team_id, season_year)
    narrative = OFFSEASON_PHASE_NARRATIVES[first_phase].format(
        season_year=season_year,
    )

    return {
        'season_year': season_year,
        'team_id': team_id,
        'current_phase': first_phase,
        'narrative': narrative,
        'development_results': dev_results,
        'legacy_delta': legacy,
        'phase_results': phase_results,
        'carousel_results': carousel_results,
    }


def get_offseason_status(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Get current offseason status for CLI display.

    Read-only query that builds a comprehensive status dict including
    phase progress, available actions, cap space, and roster count.

    Args:
        team_id: User's team ID.
        season_year: Current offseason year.
        conn: Database connection.

    Returns:
        Dict with current_phase, phases_complete, phases_remaining,
        available_actions, cap_space, roster_count, and phase-specific data.
    """
    state = get_offseason_state(conn, team_id, season_year)
    if not state:
        return {'error': 'Offseason not started'}

    current_phase = state['current_phase']

    # Build completion status
    phases_complete = []
    phases_remaining = []
    found_current = False
    for phase in OFFSEASON_PHASE_SEQUENCE:
        col = f"{phase}_complete"
        # season_ready has no completion column
        if phase == 'season_ready':
            if current_phase == 'season_ready':
                phases_complete.append(phase)
            else:
                phases_remaining.append(phase)
            continue
        if state[col]:
            phases_complete.append(phase)
        elif phase == current_phase:
            found_current = True
            phases_remaining.append(phase)
        elif found_current:
            phases_remaining.append(phase)
        else:
            phases_remaining.append(phase)

    # Available actions per phase
    action_map = {
        'end_of_season_review': ["Review legacy score", "Advance phase"],
        'staff_evaluation': ["Evaluate coaching staff", "Advance phase"],
        'franchise_tag_window': [
            "View eligible players", "Apply franchise tag", "Advance phase",
        ],
        'scouting_early': ["View scouting reports", "Advance phase"],
        'combine': ["View combine results", "Advance phase"],
        'free_agency': [
            "View FA market", "Sign free agent", "Release player",
            "Advance phase",
        ],
        'predraft': ["View draft board", "Advance phase"],
        'draft': ["View draft board", "Make pick", "Advance phase"],
        'training_camp': ["View roster", "Cut player", "Advance phase"],
        'season_ready': ["Start season"],
    }
    available_actions = action_map.get(current_phase, ["Advance phase"])

    # Team snapshot
    team = get_team(conn, team_id)
    cap_space = team['cap_space'] if team else 0
    roster_count = get_roster_count(conn, team_id)

    status = {
        'current_phase': current_phase,
        'phases_complete': phases_complete,
        'phases_remaining': phases_remaining,
        'available_actions': available_actions,
        'cap_space': cap_space,
        'roster_count': roster_count,
        'season_year': season_year,
    }

    # Phase-specific enrichment
    if current_phase == 'free_agency':
        from ..transactions.free_agency import get_fa_market_status
        try:
            fa_status = get_fa_market_status(season_year, conn)
            status['fa_market'] = fa_status
        except (ValueError, sqlite3.Error):
            status['fa_market'] = None

    return status


def advance_phase(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Advance to the next offseason phase.

    Runs automated actions when leaving the current phase and
    entering the next phase. All mutations wrapped in a transaction.

    Args:
        team_id: User's team ID.
        season_year: Current offseason year.
        conn: Database connection.

    Returns:
        Dict with old_phase, new_phase, on_leave_results,
        on_enter_results, and narrative.

    Raises:
        RuntimeError: If offseason not started or already at season_ready.
    """
    state = get_offseason_state(conn, team_id, season_year)
    if not state:
        raise RuntimeError("Offseason not started for this team/season")

    current_phase = state['current_phase']
    current_idx = OFFSEASON_PHASE_SEQUENCE.index(current_phase)

    if current_idx >= len(OFFSEASON_PHASE_SEQUENCE) - 1:
        raise RuntimeError("Already at final phase (season_ready)")

    next_phase = OFFSEASON_PHASE_SEQUENCE[current_idx + 1]

    # Execute all mutations atomically
    with conn:
        on_leave = _execute_phase_on_leave(current_phase, team_id, season_year, conn)
        mark_offseason_phase_complete(conn, team_id, season_year, current_phase)
        update_offseason_phase(conn, team_id, season_year, next_phase)
        on_enter = _execute_phase_on_enter(next_phase, team_id, season_year, conn)

    # Build narrative for the new phase
    draft_year = season_year + 1
    narrative_kwargs = {
        'season_year': season_year,
        'draft_year': draft_year,
        'next_season': season_year + 1,
        'fa_count': on_enter.get('fa_count', 0),
    }
    narrative = OFFSEASON_PHASE_NARRATIVES.get(next_phase, '').format(
        **narrative_kwargs,
    )

    return {
        'old_phase': current_phase,
        'new_phase': next_phase,
        'on_leave_results': on_leave,
        'on_enter_results': on_enter,
        'narrative': narrative,
    }


def enforce_roster_cuts(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Cut roster to 53 players while protecting positional minimums.

    Called automatically when leaving training_camp phase. Releases
    the lowest-value players (by dead cap, then overall) until the
    roster reaches the limit. A player is skipped if cutting them
    would leave the position below POSITION_MINIMUM_ROSTER.

    Args:
        team_id: Team to trim.
        season_year: Current season year.
        conn: Database connection.

    Returns:
        Dict with players_cut, dead_cap_incurred, roster_count,
        flagged_uncuttable.
    """
    from ..transactions.contracts import release_player

    roster_count = get_roster_count(conn, team_id)
    if roster_count <= TRAINING_CAMP_ROSTER_LIMIT:
        return {
            'players_cut': [],
            'dead_cap_incurred': 0,
            'roster_count': roster_count,
            'flagged_uncuttable': [],
        }

    cuts_needed = roster_count - TRAINING_CAMP_ROSTER_LIMIT
    cuttable = get_cuttable_players(conn, team_id, season_year)

    # Build live position counts from the cuttable list (all active players)
    position_counts = {}
    for player in cuttable:
        pos = player['position']
        position_counts[pos] = position_counts.get(pos, 0) + 1

    players_cut = []
    flagged_uncuttable = []
    dead_cap_total = 0

    for player in cuttable:
        if len(players_cut) >= cuts_needed:
            break

        pos = player['position']
        minimum = POSITION_MINIMUM_ROSTER.get(pos, 1)

        # Skip this player if cutting would drop below positional minimum
        if position_counts.get(pos, 0) <= minimum:
            flagged_uncuttable.append({
                'player_id': player['id'],
                'name': f"{player['first_name']} {player['last_name']}",
                'position': pos,
            })
            continue

        try:
            result = release_player(
                player['id'], team_id, season_year, conn,
            )
            players_cut.append({
                'player_id': player['id'],
                'name': f"{player['first_name']} {player['last_name']}",
                'position': pos,
                'dead_cap': result.get('dead_cap', 0),
            })
            dead_cap_total += result.get('dead_cap', 0)
            position_counts[pos] -= 1
        except ValueError:
            flagged_uncuttable.append({
                'player_id': player['id'],
                'name': f"{player['first_name']} {player['last_name']}",
                'position': pos,
            })

    final_count = get_roster_count(conn, team_id)

    return {
        'players_cut': players_cut,
        'dead_cap_incurred': dead_cap_total,
        'roster_count': final_count,
        'flagged_uncuttable': flagged_uncuttable,
    }


def run_offseason_week(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Run background offseason systems for one heartbeat cycle.

    Called periodically during offseason to process satisfaction
    and generate trade offers.

    Args:
        team_id: User's team ID.
        season_year: Current offseason year.
        conn: Database connection.

    Returns:
        Dict with satisfaction_warnings and trade_offers.
    """
    from ..transactions.satisfaction import process_weekly_satisfaction
    from ..transactions.trades import receive_trade_offers

    warnings = process_weekly_satisfaction(
        team_id, season_year, OFFSEASON_WEEK, conn,
    )
    offers = receive_trade_offers(team_id, season_year, conn)

    return {
        'satisfaction_warnings': warnings,
        'trade_offers': offers,
    }


def get_offseason_summary(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Generate a comprehensive offseason recap.

    Read-only summary of all offseason activity for the team,
    suitable for display at the end of the offseason.

    Args:
        team_id: User's team ID.
        season_year: Current offseason year.
        conn: Database connection.

    Returns:
        Dict with fa_signings, releases, trades, draft_picks,
        net_cap_change, starting_cap, ending_cap, roster_count.
    """
    transactions = get_transaction_summary_for_offseason(
        conn, team_id, season_year,
    )

    fa_signings = []
    releases = []
    trades = []

    for txn in transactions:
        txn_type = txn['transaction_type']
        if txn_type == 'signed':
            fa_signings.append({
                'description': txn['description'],
                'cap_impact': txn['cap_impact'],
            })
        elif txn_type == 'released':
            releases.append({
                'description': txn['description'],
                'cap_impact': txn['cap_impact'],
            })
        elif txn_type == 'traded':
            trades.append({
                'description': txn['description'],
            })

    # Draft picks
    draft_year = season_year + 1
    drafted = get_drafted_prospects_for_team(conn, team_id, draft_year)
    draft_picks = []
    for prospect in drafted:
        draft_picks.append({
            'round': prospect['draft_round'],
            'pick': prospect['draft_pick'],
            'name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'grade': to_letter_grade(prospect['true_overall']),
        })

    # Cap calculations
    team = get_team(conn, team_id)
    ending_cap = team['cap_space'] if team else 0
    total_cap_impact = sum(t['cap_impact'] for t in transactions)
    starting_cap = ending_cap - total_cap_impact

    roster_count = get_roster_count(conn, team_id)

    return {
        'fa_signings': fa_signings,
        'releases': releases,
        'trades': trades,
        'draft_picks': draft_picks,
        'net_cap_change': total_cap_impact,
        'starting_cap': starting_cap,
        'ending_cap': ending_cap,
        'roster_count': roster_count,
    }


# ======================
# PRIVATE HELPERS
# ======================


def _execute_phase_on_leave(
    phase: str, team_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """Run automated actions when leaving a phase."""
    if phase == 'free_agency':
        from ..transactions.free_agency import run_ai_fa_signings
        signings = run_ai_fa_signings(season_year, conn)
        return {'ai_signings': len(signings)}

    if phase == 'draft':
        from ..transactions.draft import complete_draft, sign_rookie_contracts

        draft_year = season_year + 1
        # Run all remaining AI picks before completing
        _auto_complete_draft_picks(draft_year, team_id, conn)

        completion = complete_draft(draft_year, conn)

        # Sign rookie contracts for all teams
        teams = get_all_teams(conn)
        rookies_signed = 0
        for team in teams:
            signed = sign_rookie_contracts(team['id'], draft_year, conn)
            rookies_signed += len(signed)

        return {
            'draft_completion': completion,
            'rookies_signed': rookies_signed,
        }

    if phase == 'training_camp':
        # Apply roster cuts for ALL teams (not just user team)
        # This was previously gated to only team_id (user team), causing AI roster bloat
        teams = get_all_teams(conn)
        total_cuts = 0
        for team in teams:
            result = enforce_roster_cuts(team['id'], season_year, conn)
            total_cuts += len(result.get('players_cut', []))

        return {
            'total_players_cut': total_cuts,
            'teams_processed': len(teams),
        }

    return {}


def _execute_phase_on_enter(
    phase: str, team_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """Run automated actions when entering a phase.

    Note: Imports are lazy (inside conditionals) to avoid circular
    dependency issues between offseason, scouting, and transaction modules.
    """
    if phase == 'scouting_early':
        from ..scouting.prospects import generate_draft_class
        from ..scouting.reports import run_scouting_phase

        draft_year = season_year + 1
        try:
            generate_draft_class(draft_year, conn)
        except ValueError:
            pass  # Already exists

        # Auto-assign scouts and run early phase
        _auto_assign_scouts(team_id, draft_year, conn)
        run_scouting_phase(team_id, draft_year, 'early', conn)
        return {'draft_class_year': draft_year}

    if phase == 'combine':
        from ..scouting.reports import run_scouting_phase, generate_mock_draft

        draft_year = season_year + 1
        run_scouting_phase(team_id, draft_year, 'combine', conn)
        generate_mock_draft(draft_year, week=1, conn=conn)
        return {'combine_complete': True}

    if phase == 'free_agency':
        from ..transactions.free_agency import (
            generate_fa_market, get_fa_market_status,
        )

        generate_fa_market(season_year, conn)
        try:
            status = get_fa_market_status(season_year, conn)
            return {
                'fa_market_created': True,
                'fa_count': status['total_unsigned'],
            }
        except (ValueError, sqlite3.Error):
            return {'fa_market_created': True, 'fa_count': 0}

    if phase == 'predraft':
        from ..scouting.reports import run_scouting_phase
        from ..scouting.board import build_draft_board

        draft_year = season_year + 1
        run_scouting_phase(team_id, draft_year, 'predraft', conn)
        build_draft_board(team_id, draft_year, conn)
        return {'board_built': True}

    if phase == 'draft':
        from ..transactions.draft import initialize_draft

        draft_year = season_year + 1
        init_result = initialize_draft(draft_year, conn)
        return {'draft_initialized': True, 'total_picks': init_result.get('total_picks', 0)}

    return {}


def _auto_assign_scouts(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> None:
    """Auto-assign scouts to top prospects if no assignments exist.

    Ensures the scouting phase has prospects to evaluate even
    if the user hasn't manually assigned scouts.
    """
    from ..db.queries import get_assignments_for_team, get_all_prospects
    from ..scouting.scouts import assign_scout, get_scouting_department
    from ..utils.constants import SCOUT_CAPACITY_DIVISOR

    existing = get_assignments_for_team(conn, team_id, season_year)
    if existing:
        return  # Already assigned

    dept = get_scouting_department(team_id, conn)
    scout_list = dept.get('scouts', [])
    if not scout_list:
        return

    prospects = get_all_prospects(conn, season_year)
    if not prospects:
        return

    # Assign each scout to a batch of top prospects
    prospect_idx = 0
    for scout in scout_list:
        regional_coverage = scout.get('regional_coverage') or 0
        capacity = regional_coverage // SCOUT_CAPACITY_DIVISOR
        if capacity <= 0:
            continue

        # Collect prospect IDs for this scout
        batch_ids = []
        for _ in range(capacity):
            if prospect_idx >= len(prospects):
                break
            batch_ids.append(prospects[prospect_idx]['id'])
            prospect_idx += 1

        if batch_ids:
            try:
                assign_scout(scout['id'], batch_ids, season_year, conn)
            except ValueError:
                pass  # Skip errors


def _auto_complete_draft_picks(
    season_year: int, user_team_id: int, conn: sqlite3.Connection,
) -> None:
    """Run AI picks for all remaining pending draft picks.

    In the automated offseason flow, all picks (including user picks)
    are handled by AI to allow batch processing.
    """
    from ..transactions.draft import run_ai_pick, get_on_the_clock

    while True:
        pick = get_on_the_clock(season_year, conn)
        if not pick:
            break
        try:
            run_ai_pick(pick['team_id'], season_year, conn)
        except ValueError:
            break  # No more prospects or error
