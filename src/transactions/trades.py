"""
Trade system for Football Simulator.

Handles player and pick exchanges between teams — both human-initiated
and AI-generated — with AI response behavior shaped by GM personality
archetypes.

All database access goes through src/db/queries.py — no raw SQL here.
All tuning constants come from src/utils/constants.py.
"""

import random
import sqlite3
from typing import Optional

from ..db.queries import (
    get_league_state,
    get_active_contract,
    get_all_players_on_team,
    get_team,
    update_player_team,
    insert_trade,
    insert_trade_asset,
    update_trade_status,
    get_trade_by_id,
    get_trade_assets_for_trade,
    get_pending_trades_for_team,
    get_draft_picks_for_team,
    get_draft_pick_by_criteria,
    update_draft_pick_owner,
    get_player_trade_info,
    update_contract_team,
    get_completed_trades_for_team,
    get_roster_position_counts,
    get_all_teams_ordered,
)
from ..db.cap import recalculate_cap_space
from ..db.transactions import log_transaction
from .contracts import calculate_dead_cap
from .franchise_tag import is_tagged
from .satisfaction import adjust_satisfaction
from ..utils.constants import (
    TRADE_VALUE_MULTIPLIER,
    TRADE_DEAD_CAP_DIVISOR,
    TRADE_AGE_MODIFIERS,
    TRADE_AGE_MODIFIER_DEFAULT,
    TRADE_YEARS_REMAINING_MODIFIERS,
    TRADE_YEARS_REMAINING_MAX,
    TRADE_PICK_VALUES,
    TRADE_PICK_TIER_EARLY_MAX,
    TRADE_PICK_TIER_MID_MAX,
    TRADE_FUTURE_PICK_DISCOUNT,
    TRADE_MAX_YEARS_FORWARD,
    TRADE_NEED_SCORE_HIGH,
    TRADE_OPPORTUNIST_IRRATIONAL_RATE,
    TRADE_COUNTER_MAX_GAP_PERCENT,
    TRADE_DEADLINE_WEEK,
    TRADE_SATISFACTION_UPGRADE,
    TRADE_SATISFACTION_LATERAL,
    TRADE_SATISFACTION_DOWNGRADE,
    TRADE_PRESTIGE_THRESHOLD,
    TRADE_LOYALTY_PENALTY_PERCENT,
    FA_IDEAL_ROSTER,
    GM_PERSONALITY_TRAITS,
    TRADE_YEARS_REMAINING_CHECK,
    TRADE_NEED_ADJUSTMENT_DIVISOR,
    TRADE_NEED_SCALE_MAX,
    TRADE_VETERAN_OVERALL_THRESHOLD,
)


# ======================================================================
# PUBLIC API
# ======================================================================

def calculate_player_trade_value(
    player_id: int, conn: sqlite3.Connection,
) -> dict:
    """
    Calculate a player's trade value in trade points.

    Formula: final_value = (true_overall * MULTIPLIER * age_mod * years_mod) - dead_cap_penalty

    Args:
        player_id: Player to value.
        conn: Database connection.

    Returns:
        Dict with player_id, base_value, age_modifier, years_modifier,
        dead_cap_penalty, final_value.

    Raises:
        ValueError: If player not found.
    """
    info = get_player_trade_info(conn, player_id)
    if not info:
        raise ValueError(f"Player {player_id} not found")

    true_overall = info['true_overall']
    age = info['age']
    years_remaining = info['years_remaining'] if info['years_remaining'] is not None else 0

    # Age modifier
    age_modifier = TRADE_AGE_MODIFIERS.get(age, TRADE_AGE_MODIFIER_DEFAULT)

    # Years remaining modifier
    if years_remaining >= TRADE_YEARS_REMAINING_CHECK:
        years_modifier = TRADE_YEARS_REMAINING_MAX
    else:
        years_modifier = TRADE_YEARS_REMAINING_MODIFIERS.get(years_remaining, 0.40)

    # Dead cap penalty
    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0
    dead_cap = calculate_dead_cap(player_id, season_year, conn)
    dead_cap_penalty = dead_cap // TRADE_DEAD_CAP_DIVISOR

    # Calculate final value
    base_value = int(true_overall * TRADE_VALUE_MULTIPLIER * age_modifier * years_modifier)
    final_value = max(0, base_value - dead_cap_penalty)

    return {
        'player_id': player_id,
        'base_value': base_value,
        'age_modifier': age_modifier,
        'years_modifier': years_modifier,
        'dead_cap_penalty': dead_cap_penalty,
        'final_value': final_value,
    }


def calculate_pick_value(
    round_num: int,
    pick_number: Optional[int],
    years_out: int,
    conn: sqlite3.Connection,
) -> int:
    """
    Calculate a draft pick's trade value in trade points.

    Args:
        round_num: Draft round (1-7).
        pick_number: Position within the round (1-32), or None for unknown.
        years_out: How many years in the future (0 = current year).
        conn: Database connection (unused but kept for API consistency).

    Returns:
        Trade value in points.
    """
    tier = _get_pick_tier(pick_number)
    base_value = TRADE_PICK_VALUES.get((round_num, tier), 0)

    # Apply future discount
    discount_factor = (1 - TRADE_FUTURE_PICK_DISCOUNT) ** years_out
    return int(base_value * discount_factor)


def evaluate_trade(
    offering_team_id: int,
    receiving_team_id: int,
    offered_assets: dict,
    requested_assets: dict,
    conn: sqlite3.Connection,
) -> dict:
    """
    Evaluate whether a trade is fair from the receiving team's perspective.

    Args:
        offering_team_id: Team proposing the trade.
        receiving_team_id: Team evaluating the trade.
        offered_assets: {'players': [player_id, ...], 'picks': [pick_dict, ...]}
            pick_dict: {'round': int, 'year': int, 'team_id': int, 'pick_number': int|None}
        requested_assets: Same format as offered_assets.
        conn: Database connection.

    Returns:
        Dict with offered_value, requested_value, value_gap, need_modifier_applied,
        adjusted_threshold, fair (bool), verdict ('accept'|'counter'|'decline').
    """
    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0

    # Calculate offered value (what receiving team would gain)
    offered_value = _sum_asset_values(offered_assets, season_year, conn)

    # Calculate requested value (what receiving team would give up)
    requested_value = _sum_asset_values(requested_assets, season_year, conn)

    # Calculate need score for receiving team based on offered players
    need_scores = []
    for pid in offered_assets.get('players', []):
        info = get_player_trade_info(conn, pid)
        if info:
            need = _calculate_positional_need(receiving_team_id, info['position'], conn)
            need_scores.append(need)
    avg_need = sum(need_scores) / len(need_scores) if need_scores else 0

    # Apply need modifier to threshold
    adjusted_threshold = requested_value * (1 - avg_need / TRADE_NEED_ADJUSTMENT_DIVISOR)

    value_gap = offered_value - adjusted_threshold
    fair = offered_value >= adjusted_threshold

    # Determine verdict
    if fair:
        verdict = "accept"
    elif offered_value >= adjusted_threshold * (1 - TRADE_COUNTER_MAX_GAP_PERCENT):
        verdict = "counter"
    else:
        verdict = "decline"

    return {
        'offered_value': offered_value,
        'requested_value': requested_value,
        'value_gap': value_gap,
        'need_modifier_applied': avg_need,
        'adjusted_threshold': adjusted_threshold,
        'fair': fair,
        'verdict': verdict,
    }


def propose_trade(
    offering_team_id: int,
    receiving_team_id: int,
    offered_assets: dict,
    requested_assets: dict,
    conn: sqlite3.Connection,
) -> dict:
    """
    Human-initiated trade proposal. Validates, evaluates, applies GM personality.

    Args:
        offering_team_id: Team proposing the trade.
        receiving_team_id: Team receiving the proposal.
        offered_assets: {'players': [player_id, ...], 'picks': [pick_dict, ...]}
        requested_assets: Same format.
        conn: Database connection.

    Returns:
        Dict with response ('accept'|'counter'|'decline'), counter_assets (dict|None),
        message (str), executed (bool), evaluation (dict).

    Raises:
        ValueError: On validation failures (tagged player, deadline, etc.).
    """
    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']
    week = league['current_week']

    # --- Validation ---
    has_players = bool(offered_assets.get('players')) or bool(requested_assets.get('players'))

    # Check trade deadline for player trades
    if has_players and not check_trade_deadline(season_year, week, conn):
        raise ValueError(
            f"The trade deadline has passed (week {TRADE_DEADLINE_WEEK}). "
            f"Player trades are no longer allowed. Pick-only trades are still permitted."
        )

    # Validate offered players
    for pid in offered_assets.get('players', []):
        _validate_player_for_trade(pid, offering_team_id, season_year, conn)

    # Validate requested players
    for pid in requested_assets.get('players', []):
        _validate_player_for_trade(pid, receiving_team_id, season_year, conn)

    # Validate offered picks
    for pick in offered_assets.get('picks', []):
        _validate_pick_for_trade(pick, offering_team_id, season_year, conn)

    # Validate requested picks
    for pick in requested_assets.get('picks', []):
        _validate_pick_for_trade(pick, receiving_team_id, season_year, conn)

    # Validate cap space for incoming players
    _validate_cap_space(offering_team_id, requested_assets, season_year, conn)
    _validate_cap_space(receiving_team_id, offered_assets, season_year, conn)

    # --- Evaluation ---
    evaluation = evaluate_trade(
        offering_team_id, receiving_team_id,
        offered_assets, requested_assets, conn,
    )
    verdict = evaluation['verdict']

    # --- GM Personality Filter ---
    receiving_team = get_team(conn, receiving_team_id)
    gm_personality = receiving_team['gm_personality'] if receiving_team else 'analytics'
    verdict = _apply_gm_personality(
        verdict, gm_personality, offered_assets, requested_assets,
        evaluation, season_year, conn,
    )

    # --- Build Response ---
    counter_assets = None
    message = ""
    executed = False

    if verdict == "accept":
        result = execute_trade(
            offering_team_id, receiving_team_id,
            offered_assets, requested_assets, conn,
        )
        executed = True
        message = (
            f"Trade accepted! {result['players_moved']} player(s) and "
            f"{result['picks_moved']} pick(s) exchanged."
        )
    elif verdict == "counter":
        counter_assets = _build_counter_offer(
            offering_team_id, receiving_team_id,
            offered_assets, requested_assets,
            evaluation, season_year, conn,
        )
        message = _generate_trade_message(gm_personality, receiving_team, "counter")
    else:
        message = _generate_trade_message(gm_personality, receiving_team, "decline")

    return {
        'response': verdict,
        'counter_assets': counter_assets,
        'message': message,
        'executed': executed,
        'evaluation': evaluation,
    }


def execute_trade(
    team_a_id: int,
    team_b_id: int,
    a_gives: dict,
    b_gives: dict,
    conn: sqlite3.Connection,
) -> dict:
    """
    Commit a trade to the database. Called on acceptance.

    Args:
        team_a_id: First team in the trade.
        team_b_id: Second team in the trade.
        a_gives: Assets team A sends to team B.
        b_gives: Assets team B sends to team A.
        conn: Database connection.

    Returns:
        Dict with players_moved, picks_moved, dead_cap_by_team, cap_space_after.
    """
    league = get_league_state(conn)
    season_year = league['current_season']
    week = league['current_week']

    players_moved = 0
    picks_moved = 0
    dead_cap_by_team = {team_a_id: 0, team_b_id: 0}

    # Record the trade
    trade_id = insert_trade(
        conn, season_year, week, team_a_id, team_b_id, 'completed', 'user',
    )

    # Move players from A to B
    for pid in a_gives.get('players', []):
        _transfer_player(pid, team_a_id, team_b_id, trade_id, season_year, conn)
        dead_cap_by_team[team_a_id] += calculate_dead_cap(pid, season_year, conn)
        players_moved += 1

    # Move players from B to A
    for pid in b_gives.get('players', []):
        _transfer_player(pid, team_b_id, team_a_id, trade_id, season_year, conn)
        dead_cap_by_team[team_b_id] += calculate_dead_cap(pid, season_year, conn)
        players_moved += 1

    # Move picks from A to B
    for pick in a_gives.get('picks', []):
        pick_row = get_draft_pick_by_criteria(
            conn, team_a_id, pick['year'], pick['round'],
        )
        if pick_row:
            update_draft_pick_owner(conn, pick_row['id'], team_b_id)
            insert_trade_asset(
                conn, trade_id, team_a_id, team_b_id,
                'pick', draft_pick_id=pick_row['id'],
            )
            picks_moved += 1

    # Move picks from B to A
    for pick in b_gives.get('picks', []):
        pick_row = get_draft_pick_by_criteria(
            conn, team_b_id, pick['year'], pick['round'],
        )
        if pick_row:
            update_draft_pick_owner(conn, pick_row['id'], team_a_id)
            insert_trade_asset(
                conn, trade_id, team_b_id, team_a_id,
                'pick', draft_pick_id=pick_row['id'],
            )
            picks_moved += 1

    # Recalculate cap space for both teams
    cap_a = recalculate_cap_space(team_a_id, season_year, conn)
    cap_b = recalculate_cap_space(team_b_id, season_year, conn)

    # Build description strings for transaction log
    team_a = get_team(conn, team_a_id)
    team_b = get_team(conn, team_b_id)
    a_abbr = team_a['abbreviation'] if team_a else str(team_a_id)
    b_abbr = team_b['abbreviation'] if team_b else str(team_b_id)

    a_gives_desc = _describe_assets(a_gives, conn)
    b_gives_desc = _describe_assets(b_gives, conn)

    log_transaction(
        conn, season_year, week, 'traded', team_a_id, None,
        f"Traded {a_gives_desc} to {b_abbr} for {b_gives_desc}",
    )
    log_transaction(
        conn, season_year, week, 'traded', team_b_id, None,
        f"Traded {b_gives_desc} to {a_abbr} for {a_gives_desc}",
    )

    return {
        'players_moved': players_moved,
        'picks_moved': picks_moved,
        'dead_cap_by_team': dead_cap_by_team,
        'cap_space_after': {team_a_id: cap_a, team_b_id: cap_b},
    }


def receive_trade_offers(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate unsolicited AI trade offers targeting the given team.

    Called once per simulated week. Returns up to 3 offers from AI teams
    that have high positional needs matching the target team's roster.

    Args:
        team_id: The human player's team ID.
        season_year: Current season year.
        conn: Database connection.

    Returns:
        List of offer dicts with from_team_id, from_team_name, offered_assets,
        requested_player_id, requested_player_name, message.
    """
    league = get_league_state(conn)
    if not league:
        return []
    week = league['current_week']

    if not check_trade_deadline(season_year, week, conn):
        return []

    # Get all teams
    all_teams = get_all_teams_ordered(conn)
    human_players = get_all_players_on_team(conn, team_id)

    offers = []
    for ai_team in all_teams:
        if ai_team['id'] == team_id:
            continue

        gm = ai_team['gm_personality']
        traits = GM_PERSONALITY_TRAITS.get(gm, GM_PERSONALITY_TRAITS['analytics'])

        # GM willingness check
        if random.random() > traits['trade_willingness']:
            continue

        # Find high-need positions for this AI team
        position_counts = {row['position']: row['cnt']
                          for row in get_roster_position_counts(conn, ai_team['id'])}
        high_needs = []
        for pos, ideal in FA_IDEAL_ROSTER.items():
            actual = position_counts.get(pos, 0)
            need = max(0, min(TRADE_NEED_SCALE_MAX, int((ideal - actual) / ideal * TRADE_NEED_SCALE_MAX))) if ideal > 0 else 0
            if need >= TRADE_NEED_SCORE_HIGH:
                high_needs.append(pos)

        if not high_needs:
            continue

        # Find candidates on human roster at those positions
        for player in human_players:
            if player['position'] not in high_needs:
                continue
            if is_tagged(player['id'], season_year, conn):
                continue

            player_value = calculate_player_trade_value(player['id'], conn)
            offer = _construct_ai_offer(
                ai_team, player, player_value, season_year, conn,
            )
            if offer:
                offers.append(offer)
                break  # one offer per AI team

        if len(offers) >= 3:
            break

    return offers


def check_trade_deadline(
    season_year: int, week: int, conn: sqlite3.Connection,
) -> bool:
    """
    Check if the player trade window is currently open.

    During the offseason (week 0), trades are always allowed.
    During the regular season, trades are allowed up to TRADE_DEADLINE_WEEK.
    Playoffs (weeks 18+) are always past the deadline.

    Args:
        season_year: Current season year.
        week: Current week number (0 = offseason).
        conn: Database connection (unused but kept for API consistency).

    Returns:
        True if player trades are allowed.
    """
    if week == 0:
        return True
    return week <= TRADE_DEADLINE_WEEK


# ======================================================================
# PRIVATE HELPERS
# ======================================================================

def _get_pick_tier(pick_number: Optional[int]) -> str:
    """Map a pick number (1-32) to a tier string."""
    if pick_number is None:
        return "mid"
    if pick_number <= TRADE_PICK_TIER_EARLY_MAX:
        return "early"
    if pick_number <= TRADE_PICK_TIER_MID_MAX:
        return "mid"
    return "late"


def _calculate_positional_need(
    team_id: int, position: str, conn: sqlite3.Connection,
) -> int:
    """Calculate 0-100 need score for a position on a team."""
    ideal = FA_IDEAL_ROSTER.get(position, 3)
    counts = {row['position']: row['cnt']
              for row in get_roster_position_counts(conn, team_id)}
    actual = counts.get(position, 0)
    if ideal <= 0:
        return 0
    return max(0, min(TRADE_NEED_SCALE_MAX, int((ideal - actual) / ideal * TRADE_NEED_SCALE_MAX)))


def _sum_asset_values(
    assets: dict, season_year: int, conn: sqlite3.Connection,
) -> int:
    """Sum up trade values for a set of assets."""
    total = 0
    for pid in assets.get('players', []):
        val = calculate_player_trade_value(pid, conn)
        total += val['final_value']

    for pick in assets.get('picks', []):
        years_out = pick.get('year', season_year) - season_year
        years_out = max(0, years_out)
        pick_val = calculate_pick_value(
            pick['round'], pick.get('pick_number'), years_out, conn,
        )
        total += pick_val

    return total


def _validate_player_for_trade(
    player_id: int, expected_team_id: int,
    season_year: int, conn: sqlite3.Connection,
) -> None:
    """Validate a player can be traded."""
    info = get_player_trade_info(conn, player_id)
    if not info:
        raise ValueError(f"Player {player_id} not found")
    if info['team_id'] != expected_team_id:
        raise ValueError(
            f"Player {info['first_name']} {info['last_name']} "
            f"is not on team {expected_team_id}"
        )
    if is_tagged(player_id, season_year, conn):
        raise ValueError(
            f"Player {info['first_name']} {info['last_name']} "
            f"has an active franchise tag and cannot be traded"
        )


def _validate_pick_for_trade(
    pick: dict, expected_team_id: int,
    season_year: int, conn: sqlite3.Connection,
) -> None:
    """Validate a draft pick can be traded."""
    years_out = pick.get('year', season_year) - season_year
    if years_out > TRADE_MAX_YEARS_FORWARD:
        raise ValueError(
            f"Cannot trade picks more than {TRADE_MAX_YEARS_FORWARD} years "
            f"in the future (Stepien Rule)"
        )
    pick_row = get_draft_pick_by_criteria(
        conn, expected_team_id, pick['year'], pick['round'],
    )
    if not pick_row:
        raise ValueError(
            f"Team {expected_team_id} does not own a round {pick['round']} "
            f"pick in {pick['year']}"
        )


def _validate_cap_space(
    team_id: int, incoming_assets: dict,
    season_year: int, conn: sqlite3.Connection,
) -> None:
    """Validate a team has cap space for incoming player contracts."""
    team = get_team(conn, team_id)
    if not team:
        raise ValueError(f"Team {team_id} not found")

    incoming_cap = 0
    for pid in incoming_assets.get('players', []):
        contract = get_active_contract(conn, pid)
        if contract:
            from ..db.cap import get_player_cap_hit
            cap_hit = get_player_cap_hit(pid, season_year, conn)
            incoming_cap += cap_hit

    if incoming_cap > 0 and team['cap_space'] < incoming_cap:
        raise ValueError(
            f"Team {team['abbreviation']} has insufficient cap space: "
            f"${team['cap_space']:,} available, ${incoming_cap:,} needed"
        )


def _transfer_player(
    player_id: int, from_team_id: int, to_team_id: int,
    trade_id: int, season_year: int, conn: sqlite3.Connection,
) -> None:
    """Transfer a player and their contract from one team to another."""
    # Transfer contract
    contract = get_active_contract(conn, player_id)
    if contract:
        update_contract_team(conn, contract['id'], to_team_id)

    # Transfer player
    update_player_team(conn, player_id, to_team_id, 'active')

    # Record trade asset
    insert_trade_asset(
        conn, trade_id, from_team_id, to_team_id,
        'player', player_id=player_id,
    )

    # Fire satisfaction adjustment based on prestige difference
    from_team = get_team(conn, from_team_id)
    to_team = get_team(conn, to_team_id)
    if from_team and to_team:
        prestige_diff = to_team['prestige'] - from_team['prestige']
        if prestige_diff >= TRADE_PRESTIGE_THRESHOLD:
            delta = TRADE_SATISFACTION_UPGRADE
            reason = "traded_upgrade"
        elif prestige_diff <= -TRADE_PRESTIGE_THRESHOLD:
            delta = TRADE_SATISFACTION_DOWNGRADE
            reason = "traded_downgrade"
        else:
            delta = TRADE_SATISFACTION_LATERAL
            reason = "traded_lateral"
        adjust_satisfaction(player_id, delta, reason, conn)


def _apply_gm_personality(
    base_verdict: str,
    gm_personality: str,
    offered_assets: dict,
    requested_assets: dict,
    evaluation: dict,
    season_year: int,
    conn: sqlite3.Connection,
) -> str:
    """Apply GM personality filter to modify the base verdict."""
    if gm_personality == 'opportunist':
        if random.random() < TRADE_OPPORTUNIST_IRRATIONAL_RATE:
            return "accept"

    if gm_personality == 'draft_purist':
        # Rejects trades that include their 1st-round pick
        for pick in requested_assets.get('picks', []):
            if pick.get('round') == 1:
                if base_verdict == "accept":
                    return "counter"
                return "decline"
        # Bumps toward accept if receiving draft picks
        if offered_assets.get('picks') and base_verdict == "counter":
            return "accept"

    if gm_personality == 'win_now':
        # Readily trades future picks, values proven veterans
        has_veteran_incoming = False
        for pid in offered_assets.get('players', []):
            info = get_player_trade_info(conn, pid)
            if info and info['true_overall'] >= TRADE_VETERAN_OVERALL_THRESHOLD:
                has_veteran_incoming = True
                break
        if has_veteran_incoming and base_verdict == "counter":
            return "accept"

    if gm_personality == 'loyalty':
        # Reluctant to trade own players
        if requested_assets.get('players'):
            if base_verdict == "accept":
                # Apply loyalty penalty: require higher value
                gap_pct = (evaluation['offered_value'] - evaluation['adjusted_threshold'])
                threshold_with_penalty = evaluation['adjusted_threshold'] * (1 + TRADE_LOYALTY_PENALTY_PERCENT)
                if evaluation['offered_value'] < threshold_with_penalty:
                    return "counter"

    # 'analytics' uses base verdict as-is
    return base_verdict


def _build_counter_offer(
    offering_team_id: int,
    receiving_team_id: int,
    offered_assets: dict,
    requested_assets: dict,
    evaluation: dict,
    season_year: int,
    conn: sqlite3.Connection,
) -> Optional[dict]:
    """Build a counter-offer by suggesting additional assets to close the gap."""
    gap = evaluation['adjusted_threshold'] - evaluation['offered_value']
    if gap <= 0:
        return None

    # Try to find a pick from the offering team that closes the gap
    for round_num in range(7, 0, -1):
        for year_offset in range(TRADE_MAX_YEARS_FORWARD + 1):
            target_year = season_year + year_offset
            pick = get_draft_pick_by_criteria(
                conn, offering_team_id, target_year, round_num,
            )
            if pick:
                pick_val = calculate_pick_value(
                    round_num, pick['pick_number'], year_offset, conn,
                )
                if pick_val >= gap:
                    return {
                        'add_to_offered': {
                            'picks': [{'round': round_num, 'year': target_year,
                                       'team_id': offering_team_id,
                                       'pick_number': pick['pick_number']}],
                        },
                        'gap_remaining': gap - pick_val,
                        'message': (
                            f"We'd need you to add a round {round_num} "
                            f"pick ({target_year}) to make this work."
                        ),
                    }

    # Couldn't find a pick to close the gap — suggest removing a requested asset
    if requested_assets.get('players'):
        least_valuable_pid = None
        least_value = float('inf')
        for pid in requested_assets['players']:
            val = calculate_player_trade_value(pid, conn)
            if val['final_value'] < least_value:
                least_value = val['final_value']
                least_valuable_pid = pid

        if least_valuable_pid is not None:
            info = get_player_trade_info(conn, least_valuable_pid)
            name = f"{info['first_name']} {info['last_name']}" if info else f"Player {least_valuable_pid}"
            return {
                'remove_from_requested': {'players': [least_valuable_pid]},
                'gap_remaining': gap,
                'message': f"We'd reconsider if you took {name} off the table.",
            }

    return None


def _construct_ai_offer(
    ai_team: sqlite3.Row,
    player: sqlite3.Row,
    player_value: dict,
    season_year: int,
    conn: sqlite3.Connection,
) -> Optional[dict]:
    """Build an AI offer for a specific player using the AI team's picks."""
    target_value = player_value['final_value']
    if target_value <= 0:
        return None

    # Try to build a pick package that meets the value
    offer_picks = []
    accumulated_value = 0

    picks = get_draft_picks_for_team(conn, ai_team['id'], season_year)
    # Also check next year's picks
    future_picks = get_draft_picks_for_team(conn, ai_team['id'], season_year + 1)
    all_picks = list(picks) + list(future_picks)

    # Sort by value descending so we try big picks first
    pick_values = []
    for p in all_picks:
        years_out = p['season_year'] - season_year
        val = calculate_pick_value(p['round'], p['pick_number'], years_out, conn)
        pick_values.append((p, val, years_out))
    pick_values.sort(key=lambda x: x[1], reverse=True)

    for pick_row, val, years_out in pick_values:
        if accumulated_value >= target_value:
            break
        offer_picks.append({
            'round': pick_row['round'],
            'year': pick_row['season_year'],
            'team_id': ai_team['id'],
            'pick_number': pick_row['pick_number'],
        })
        accumulated_value += val

    # Check if the package meets the target value (within 20% tolerance)
    if accumulated_value < target_value * 0.80:
        return None

    return {
        'from_team_id': ai_team['id'],
        'from_team_name': f"{ai_team['city']} {ai_team['nickname']}",
        'offered_assets': {'players': [], 'picks': offer_picks},
        'requested_player_id': player['id'],
        'requested_player_name': f"{player['first_name']} {player['last_name']}",
        'message': _generate_trade_message(
            ai_team['gm_personality'], ai_team, "offer",
            player_name=f"{player['first_name']} {player['last_name']}",
            position=player['position'],
        ),
    }


def _generate_trade_message(
    gm_personality: str,
    team: sqlite3.Row,
    response_type: str,
    player_name: str = "",
    position: str = "",
) -> str:
    """Generate a narrative-flavored trade response message."""
    team_name = f"{team['city']} {team['nickname']}" if team else "Unknown"

    messages = {
        'draft_purist': {
            'accept': f"The {team_name} front office agrees to the deal after careful evaluation.",
            'counter': f"The {team_name} are interested but want to protect their draft capital.",
            'decline': f"The {team_name} prefer to build through the draft and pass on this deal.",
            'offer': f"The {team_name} are looking to add {position} {player_name} to fill a roster gap.",
        },
        'win_now': {
            'accept': f"The {team_name} quickly accept — they're in win-now mode.",
            'counter': f"The {team_name} like the idea but want a better return for their window.",
            'decline': f"The {team_name} don't see how this helps them compete right now.",
            'offer': f"The {team_name} are aggressively pursuing {position} {player_name} to bolster their roster.",
        },
        'analytics': {
            'accept': f"The {team_name} analytics department signs off on the deal.",
            'counter': f"The {team_name} ran the numbers and want a slight adjustment.",
            'decline': f"The {team_name} don't see the value aligning in their models.",
            'offer': f"The {team_name} have identified {position} {player_name} as a target based on their evaluation model.",
        },
        'loyalty': {
            'accept': f"The {team_name} reluctantly agree to part with their player.",
            'counter': f"The {team_name} are hesitant but willing to talk if the price is right.",
            'decline': f"The {team_name} aren't interested in moving their guys.",
            'offer': f"The {team_name} are quietly inquiring about {position} {player_name}.",
        },
        'opportunist': {
            'accept': f"The {team_name} jump at the deal immediately.",
            'counter': f"The {team_name} see an opportunity but want to squeeze out more value.",
            'decline': f"Even the {team_name} don't see this as a good deal.",
            'offer': f"The {team_name} are making a play for {position} {player_name} — they smell an opportunity.",
        },
    }

    personality_msgs = messages.get(gm_personality, messages['analytics'])
    return personality_msgs.get(response_type, f"The {team_name} have responded to your trade proposal.")


def _describe_assets(assets: dict, conn: sqlite3.Connection) -> str:
    """Build a human-readable description of trade assets."""
    parts = []
    for pid in assets.get('players', []):
        info = get_player_trade_info(conn, pid)
        if info:
            parts.append(f"{info['position']} {info['first_name']} {info['last_name']}")
        else:
            parts.append(f"Player #{pid}")

    for pick in assets.get('picks', []):
        rd = pick.get('round', '?')
        yr = pick.get('year', '?')
        parts.append(f"Round {rd} pick ({yr})")

    return ", ".join(parts) if parts else "nothing"
