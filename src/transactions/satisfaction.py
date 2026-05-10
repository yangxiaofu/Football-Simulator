"""
Player Satisfaction System for Football Simulator.

Tracks and manages player happiness. Satisfaction is influenced by
contract fairness, playing time, team performance, franchise tags,
and playoff history. Low satisfaction triggers warning signals,
holdouts, trade demands, and locker room contagion.

Layer boundary: all SQL in db/queries.py. All constants in utils/constants.py.
Cross-module call: get_market_value() from .contracts is the only permitted
import from another transactions submodule.
"""

import json
import random
import sqlite3
from typing import Optional

from ..db.queries import (
    get_player_satisfaction,
    update_player_satisfaction,
    insert_satisfaction_event,
    get_satisfaction_history,
    insert_player_event,
    get_active_player_events,
    resolve_player_event,
    get_player_recent_box_score,
    get_top_player_overall_at_position,
    get_team_recent_playoff_appearances,
    get_recent_intervention,
    get_league_state,
    get_active_contract,
    get_completed_games_for_team,
    get_player_for_contract,
    get_all_players_on_team,
)
from ..db.transactions import log_transaction
from .contracts import get_market_value
from ..utils.constants import (
    SATISFACTION_MIN,
    SATISFACTION_MAX,
    SATISFACTION_CHANGE_RATES,
    SATISFACTION_HOLDOUT_THRESHOLD,
    SATISFACTION_TRADE_DEMAND_THRESHOLD,
    SATISFACTION_WARNING_TIERS,
    SATISFACTION_SIGNAL_MESSAGES,
    SATISFACTION_UNDERPAID_THRESHOLD,
    SATISFACTION_OVERPAID_THRESHOLD,
    SATISFACTION_FRANCHISE_TAG_PENALTY,
    SATISFACTION_PLAYOFF_BONUS,
    SATISFACTION_PLAYOFF_LOOKBACK,
    SATISFACTION_STARTER_CALIBER_THRESHOLD,
    SATISFACTION_INTERVENTION,
    CONTAGION_SATISFACTION_THRESHOLD,
    CONTAGION_VETERAN_MIN_OVERALL,
    CONTAGION_VETERAN_MIN_EXPERIENCE,
    CONTAGION_TARGET_MAX_EXPERIENCE,
    CONTAGION_WEEKLY_PROBABILITY,
    CONTAGION_DELTA_RANGE,
    MOTIVATION_YOUNG_AGE_MAX,
    MOTIVATION_VETERAN_AGE_MIN,
    POSITION_TO_GROUP,
    SATISFACTION_LEGACY_THRESHOLD,
)


def get_satisfaction(player_id: int, conn: sqlite3.Connection) -> int:
    """Read a player's current satisfaction score.

    Args:
        player_id: Player to query.
        conn: Database connection.

    Returns:
        Satisfaction score (0-100).

    Raises:
        ValueError: If player not found.
    """
    score = get_player_satisfaction(conn, player_id)
    if score is None:
        raise ValueError(f"Player {player_id} not found")
    return score


def adjust_satisfaction(
    player_id: int,
    delta: int,
    reason: str,
    conn: sqlite3.Connection,
) -> int:
    """Apply a satisfaction delta, clamping to [0, 100], and log the event.

    This is the single mutation point for satisfaction scores. All other
    functions call this rather than writing directly.

    Args:
        player_id: Player to adjust.
        delta: Change amount (positive or negative).
        reason: Short reason string for the event log.
        conn: Database connection.

    Returns:
        New satisfaction score after clamping.
    """
    current = get_satisfaction(player_id, conn)
    new_score = max(SATISFACTION_MIN, min(SATISFACTION_MAX, current + delta))

    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0
    week = league['current_week'] if league else 0

    update_player_satisfaction(conn, player_id, new_score)
    insert_satisfaction_event(
        conn, player_id, season_year, week, delta, reason, new_score,
    )

    return new_score


def evaluate_satisfaction_factors(
    player_id: int,
    team_id: int,
    season_year: int,
    week: int,
    conn: sqlite3.Connection,
) -> dict:
    """Evaluate all satisfaction factors for a player and return the breakdown.

    Read-only — does NOT apply changes. The caller decides whether to
    commit via adjust_satisfaction().

    Factors evaluated:
    1. Contract fairness vs market value
    2. Franchise tag penalty (one-time)
    3. Team winning/losing record
    4. Playing time vs expected role
    5. Playoff history (last 2 seasons)

    Args:
        player_id: Player to evaluate.
        team_id: Player's current team.
        season_year: Current season year.
        week: Current week number.
        conn: Database connection.

    Returns:
        Dict with net_delta, factors list, current_score, projected_score.
    """
    player = get_player_for_contract(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found")

    current_score = player['satisfaction']
    factors = []

    # --- Factor 1: Contract fairness ---
    contract = get_active_contract(conn, player_id)
    if contract:
        market = get_market_value(player_id, player['position'], conn)
        fair_aav = market['fair']
        player_aav = contract['aav']

        if fair_aav > 0:
            ratio = player_aav / fair_aav
            if ratio < SATISFACTION_UNDERPAID_THRESHOLD:
                factors.append({
                    'name': 'contract_fairness',
                    'delta': SATISFACTION_CHANGE_RATES['underpaid'],
                    'reason': f'underpaid (AAV ratio {ratio:.2f})',
                })
            elif ratio >= SATISFACTION_OVERPAID_THRESHOLD:
                factors.append({
                    'name': 'contract_fairness',
                    'delta': SATISFACTION_CHANGE_RATES['overpaid'],
                    'reason': f'overpaid (AAV ratio {ratio:.2f})',
                })

        # --- Factor 2: Franchise tag penalty (one-time) ---
        if contract['is_franchise_tag']:
            history = get_satisfaction_history(conn, player_id, season_year)
            already_applied = any(
                e['reason'] == 'franchise_tag' for e in history
            )
            if not already_applied:
                factors.append({
                    'name': 'franchise_tag',
                    'delta': SATISFACTION_FRANCHISE_TAG_PENALTY,
                    'reason': 'franchise tagged (one-time)',
                })

    # --- Factor 3: Team winning/losing ---
    games = get_completed_games_for_team(conn, team_id, season_year)
    if games:
        wins = 0
        losses = 0
        for g in games:
            if g['home_team_id'] == team_id:
                my_score, opp_score = g['home_score'], g['away_score']
            else:
                my_score, opp_score = g['away_score'], g['home_score']
            if my_score > opp_score:
                wins += 1
            elif my_score < opp_score:
                losses += 1

        if wins > losses:
            factors.append({
                'name': 'team_record',
                'delta': SATISFACTION_CHANGE_RATES['winning'],
                'reason': f'winning record ({wins}-{losses})',
            })
        elif losses > wins:
            factors.append({
                'name': 'team_record',
                'delta': SATISFACTION_CHANGE_RATES['losing'],
                'reason': f'losing record ({wins}-{losses})',
            })

    # --- Factor 4: Playing time / role ---
    top_ovr = get_top_player_overall_at_position(
        conn, team_id, player['position'],
    )
    is_starter_caliber = False
    if top_ovr is not None:
        is_starter_caliber = (
            player['true_overall']
            >= top_ovr - SATISFACTION_STARTER_CALIBER_THRESHOLD
        )

    if is_starter_caliber and games:
        recent_bs = get_player_recent_box_score(
            conn, player_id, season_year, week,
        )
        if recent_bs:
            has_stats = (
                recent_bs['pass_attempts'] > 0
                or recent_bs['carries'] > 0
                or recent_bs['targets'] > 0
                or recent_bs['tackles'] > 0
            )
            if has_stats:
                factors.append({
                    'name': 'playing_time',
                    'delta': SATISFACTION_CHANGE_RATES['starter_role'],
                    'reason': 'starting role maintained',
                })
            else:
                factors.append({
                    'name': 'playing_time',
                    'delta': SATISFACTION_CHANGE_RATES['backup_role'],
                    'reason': 'benched despite starter-caliber rating',
                })
        else:
            factors.append({
                'name': 'playing_time',
                'delta': SATISFACTION_CHANGE_RATES['backup_role'],
                'reason': 'not seeing the field',
            })

    # --- Factor 5: Playoff history ---
    playoff_count = get_team_recent_playoff_appearances(
        conn, team_id, season_year, SATISFACTION_PLAYOFF_LOOKBACK,
    )
    if playoff_count > 0:
        factors.append({
            'name': 'playoff_history',
            'delta': SATISFACTION_PLAYOFF_BONUS * playoff_count,
            'reason': (
                f'{playoff_count} playoff appearance(s) in last '
                f'{SATISFACTION_PLAYOFF_LOOKBACK} seasons'
            ),
        })

    net_delta = sum(f['delta'] for f in factors)
    projected = max(
        SATISFACTION_MIN, min(SATISFACTION_MAX, current_score + net_delta),
    )

    return {
        'net_delta': net_delta,
        'factors': factors,
        'current_score': current_score,
        'projected_score': projected,
    }


def get_warning_signal(
    player_id: int, conn: sqlite3.Connection,
) -> Optional[dict]:
    """Map a player's satisfaction score to a warning signal tier.

    Returns None if the player is in the 'healthy' range (70-100).
    Never exposes the raw satisfaction score to UI callers — UI reads
    the tier and message only.

    Args:
        player_id: Player to check.
        conn: Database connection.

    Returns:
        Dict with tier, message, satisfaction, player_id, player_name.
        None if score >= 70.
    """
    score = get_satisfaction(player_id, conn)
    player = get_player_for_contract(conn, player_id)
    if not player:
        return None

    player_name = f"{player['first_name']} {player['last_name']}"

    for tier_name, (low, high) in SATISFACTION_WARNING_TIERS.items():
        if low <= score <= high:
            if tier_name == 'healthy':
                return None
            message = SATISFACTION_SIGNAL_MESSAGES.get(tier_name, '')
            return {
                'tier': tier_name,
                'message': message.format(name=player_name),
                'satisfaction': score,
                'player_id': player_id,
                'player_name': player_name,
            }

    return None


def process_weekly_satisfaction(
    team_id: int,
    season_year: int,
    week: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """Run the weekly satisfaction heartbeat for all players on a team.

    Called once per week per team during season simulation. Evaluates
    all satisfaction factors, applies deltas, generates warning signals,
    creates player events at critical thresholds, and runs locker room
    contagion.

    Args:
        team_id: Team to process.
        season_year: Current season year.
        week: Current week number.
        conn: Database connection.

    Returns:
        List of warning signal dicts for the front office briefing.
    """
    players = get_all_players_on_team(conn, team_id)
    alerts = []

    for player in players:
        pid = player['id']

        # Evaluate factors
        evaluation = evaluate_satisfaction_factors(
            pid, team_id, season_year, week, conn,
        )

        # Apply net delta
        if evaluation['net_delta'] != 0:
            new_score = adjust_satisfaction(
                pid, evaluation['net_delta'],
                _summarize_reasons(evaluation['factors']),
                conn,
            )
        else:
            new_score = evaluation['current_score']

        # Check for warning signal
        warning = get_warning_signal(pid, conn)

        # Generate events at critical thresholds
        if new_score <= SATISFACTION_HOLDOUT_THRESHOLD:
            existing = get_active_player_events(conn, pid, 'holdout')
            if not existing:
                insert_player_event(
                    conn, pid, team_id, 'holdout',
                    season_year, week,
                    json.dumps({'triggered_at_score': new_score}),
                )
                log_transaction(
                    conn, season_year, week, 'holdout',
                    team_id, pid,
                    f"{player['first_name']} {player['last_name']} "
                    f"is refusing to participate in team activities",
                )
        elif new_score <= SATISFACTION_TRADE_DEMAND_THRESHOLD:
            existing = get_active_player_events(conn, pid, 'trade_demand')
            if not existing:
                insert_player_event(
                    conn, pid, team_id, 'trade_demand',
                    season_year, week,
                    json.dumps({'triggered_at_score': new_score}),
                )
                log_transaction(
                    conn, season_year, week, 'trade_demand',
                    team_id, pid,
                    f"{player['first_name']} {player['last_name']} "
                    f"has formally requested a trade through his agent",
                )

        if warning:
            alerts.append({
                'player_id': pid,
                'player_name': warning['player_name'],
                'warning': warning,
                'factors': evaluation['factors'],
                'new_score': new_score,
            })

    # Run locker room contagion after individual evaluations
    contagion_results = check_locker_room_influence(team_id, conn)
    for cr in contagion_results:
        warning = get_warning_signal(cr['affected_player_id'], conn)
        if warning:
            alerts.append({
                'player_id': cr['affected_player_id'],
                'player_name': cr['affected_player_name'],
                'warning': warning,
                'factors': [{
                    'name': 'contagion',
                    'delta': cr['delta'],
                    'reason': cr['reason'],
                }],
                'new_score': cr['new_score'],
            })

    return alerts


def apply_intervention(
    player_id: int,
    intervention_type: str,
    context: dict,
    conn: sqlite3.Connection,
) -> dict:
    """Apply a GM intervention to address a player's dissatisfaction.

    Supported intervention types:
    - 'private_meeting': context={'message': 'role'|'money'|'winning'|'legacy'}.
      Matched against derived motivation. Right match: +10-20. Wrong: -5 to 0.
    - 'extension_offer': context={'aav': int}. Compared to market value.
      Fair offer: +15-25. Lowball: -10.
    - 'role_adjustment': Effective if role-based dissatisfaction (+5-15),
      minimal effect otherwise (+0-3).

    Args:
        player_id: Player to intervene with.
        intervention_type: One of the supported types.
        context: Parameters specific to the intervention type.
        conn: Database connection.

    Returns:
        Dict with success, delta, new_score, message, event_id.

    Raises:
        ValueError: On invalid type, missing player, or cooldown violation.
    """
    if intervention_type not in SATISFACTION_INTERVENTION:
        raise ValueError(
            f"Invalid intervention type: {intervention_type}. "
            f"Valid: {list(SATISFACTION_INTERVENTION.keys())}"
        )

    player = get_player_for_contract(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found")

    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']
    week = league['current_week']

    # Check cooldown for private meetings
    if intervention_type == 'private_meeting':
        params = SATISFACTION_INTERVENTION['private_meeting']
        cooldown = params['cooldown_weeks']
        recent = get_recent_intervention(
            conn, player_id, 'private_meeting',
            max(1, week - cooldown), season_year,
        )
        if recent:
            raise ValueError(
                f"Private meeting cooldown: {cooldown} weeks must pass "
                f"between meetings (last meeting was week {recent['week']})"
            )

    motivation = _derive_motivation(player)
    delta = 0
    success = False
    message = ''

    if intervention_type == 'private_meeting':
        params = SATISFACTION_INTERVENTION['private_meeting']
        chosen_message = context.get('message', '')
        if chosen_message == motivation:
            delta = random.randint(*params['success_range'])
            success = True
            message = (
                f"Meeting resonated with player "
                f"(motivation: {motivation})"
            )
        else:
            delta = random.randint(*params['failure_range'])
            success = False
            message = (
                f"Meeting fell flat (chose '{chosen_message}', "
                f"player motivated by '{motivation}')"
            )

    elif intervention_type == 'extension_offer':
        params = SATISFACTION_INTERVENTION['extension_offer']
        offered_aav = context.get('aav', 0)
        market = get_market_value(player_id, player['position'], conn)
        fair_aav = market['fair']

        if (fair_aav > 0
                and offered_aav >= fair_aav * SATISFACTION_UNDERPAID_THRESHOLD):
            delta = random.randint(*params['fair_range'])
            success = True
            message = "Extension offer was at or above fair market value"
        else:
            delta = params['lowball_penalty']
            success = False
            message = "Extension offer was perceived as a lowball"

    elif intervention_type == 'role_adjustment':
        params = SATISFACTION_INTERVENTION['role_adjustment']
        history = get_satisfaction_history(conn, player_id, season_year)
        role_based = any(
            'playing_time' in e['reason'] or 'backup' in e['reason']
            or 'benched' in e['reason']
            for e in history
        )
        if role_based:
            delta = random.randint(*params['effective_range'])
            success = True
            message = "Role adjustment addressed the player's primary concern"
        else:
            delta = random.randint(*params['ineffective_range'])
            success = False
            message = (
                "Role adjustment didn't address the player's actual concern"
            )

    # Apply the delta
    new_score = adjust_satisfaction(
        player_id, delta, f'intervention_{intervention_type}', conn,
    )

    # Log the event
    event_id = insert_player_event(
        conn, player_id, player['team_id'],
        intervention_type, season_year, week,
        json.dumps({
            'context': context,
            'success': success,
            'delta': delta,
            'message': message,
            'motivation': motivation,
        }),
    )

    # Auto-resolve holdout/trade demand if score rises above thresholds
    if new_score > SATISFACTION_TRADE_DEMAND_THRESHOLD:
        for demand in get_active_player_events(conn, player_id, 'trade_demand'):
            resolve_player_event(conn, demand['id'])

    if new_score > SATISFACTION_HOLDOUT_THRESHOLD:
        for holdout in get_active_player_events(conn, player_id, 'holdout'):
            resolve_player_event(conn, holdout['id'])

    return {
        'success': success,
        'delta': delta,
        'new_score': new_score,
        'message': message,
        'event_id': event_id,
    }


def check_locker_room_influence(
    team_id: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """Check for locker room contagion from dissatisfied veterans.

    A veteran (years_experience >= 5, true_overall >= 80) with
    satisfaction < 30 can spread negativity to younger players
    (years_experience <= 3) in the same position group. Each affected
    player has a 30% chance per week of being influenced.

    Args:
        team_id: Team to check.
        conn: Database connection.

    Returns:
        List of dicts with affected_player_id, affected_player_name,
        influencer_id, influencer_name, delta, new_score, reason.
    """
    players = get_all_players_on_team(conn, team_id)
    results = []

    # Identify dissatisfied influential veterans
    influencers = [
        p for p in players
        if (p['satisfaction'] < CONTAGION_SATISFACTION_THRESHOLD
            and p['true_overall'] >= CONTAGION_VETERAN_MIN_OVERALL
            and p['years_experience'] >= CONTAGION_VETERAN_MIN_EXPERIENCE)
    ]

    if not influencers:
        return results

    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0
    week = league['current_week'] if league else 0

    for inf in influencers:
        inf_group = POSITION_TO_GROUP.get(inf['position'])
        if not inf_group:
            continue

        inf_name = f"{inf['first_name']} {inf['last_name']}"

        for p in players:
            if p['id'] == inf['id']:
                continue
            if p['years_experience'] > CONTAGION_TARGET_MAX_EXPERIENCE:
                continue

            p_group = POSITION_TO_GROUP.get(p['position'])
            if p_group != inf_group:
                continue

            if random.random() > CONTAGION_WEEKLY_PROBABILITY:
                continue

            delta = random.randint(*CONTAGION_DELTA_RANGE)
            reason = f"locker room influence from {inf_name}"
            new_score = adjust_satisfaction(p['id'], delta, reason, conn)

            insert_player_event(
                conn, p['id'], team_id, 'contagion',
                season_year, week,
                json.dumps({
                    'influencer_id': inf['id'],
                    'influencer_name': inf_name,
                    'delta': delta,
                }),
            )

            p_name = f"{p['first_name']} {p['last_name']}"
            results.append({
                'affected_player_id': p['id'],
                'affected_player_name': p_name,
                'influencer_id': inf['id'],
                'influencer_name': inf_name,
                'delta': delta,
                'new_score': new_score,
                'reason': reason,
            })

    return results


def _summarize_reasons(factors: list[dict]) -> str:
    """Build a compact reason string from multiple factors for event logging."""
    if not factors:
        return 'weekly_update'
    return '; '.join(f['name'] for f in factors)


def _derive_motivation(player: sqlite3.Row) -> str:
    """Derive a player's primary motivation from age and overall rating.

    Since player motivations aren't tracked in the schema, we use a heuristic:
    - Young players (<=25): role-focused (want playing time)
    - Mid-career (26-29): winning-focused (want championships)
    - Veterans (30+) with high overall (85+): legacy-focused
    - Veterans (30+) with lower overall: money-focused
    """
    age = player['age']
    overall = player['true_overall']

    if age <= MOTIVATION_YOUNG_AGE_MAX:
        return 'role'
    elif age < MOTIVATION_VETERAN_AGE_MIN:
        return 'winning'
    else:
        if overall >= SATISFACTION_LEGACY_THRESHOLD:
            return 'legacy'
        return 'money'
