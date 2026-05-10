"""
Free Agency system for Football Simulator.

Manages the free agent market lifecycle: identifying expiring contracts,
generating destination preferences, interest tier scouting, pitch meetings,
offer submission, agent response resolution, AI team signings, and
market status reporting.

Layer boundary: all SQL in db/queries.py. All constants in utils/constants.py.
Cross-module calls: contracts.py (offer_contract, get_market_value) and
satisfaction.py (adjust_satisfaction, apply_intervention).
"""

import json
import random
import sqlite3
from typing import Optional

from ..db.connection import ensure_fa_tables
from ..db.queries import (
    # League / teams
    get_all_teams,
    get_team,
    get_league_state,
    # Players
    get_player_for_contract,
    get_all_players_on_team,
    # Contracts
    get_active_contract,
    update_contract_status,
    update_player_team,
    # Games
    get_completed_games_for_team,
    # Roster
    get_top_player_overall_at_position,
    # FA interest
    get_expiring_contract_players,
    get_free_agent_players,
    insert_fa_interest,
    get_fa_interest,
    get_fa_interests_for_player,
    update_fa_interest_tier,
    clear_fa_interest_for_season,
    # FA offers
    insert_fa_offer,
    get_fa_offer,
    update_fa_offer_status,
    # FA support
    get_team_coordinators,
    count_unsigned_free_agents,
    get_unsigned_free_agents_by_position,
    has_player_history_with_team,
    count_accepted_fa_offers,
)
from ..db.transactions import log_transaction
from .contracts import offer_contract, get_market_value
from .satisfaction import adjust_satisfaction, apply_intervention
from ..utils.constants import (
    INTEREST_TIER_1,
    INTEREST_TIER_2,
    INTEREST_TIER_3,
    FA_PREF_WEIGHT_WINNING,
    FA_PREF_WEIGHT_SCHEME_FIT,
    FA_PREF_WEIGHT_ROLE_CLARITY,
    FA_PREF_WEIGHT_MARKET_SIZE,
    FA_PREF_WEIGHT_COACH_HISTORY,
    FA_TIER_1_MAX_RANK,
    FA_TIER_2_MAX_RANK,
    FA_TIER_3_OVERPAY_THRESHOLD,
    FA_ACCEPT_THRESHOLD,
    FA_COUNTER_THRESHOLD,
    FA_TIER_2_ACCEPT_PREMIUM,
    FA_PITCH_FAILURE_DROP_CHANCE,
    FA_PITCH_DESPERATION_DELTA,
    FA_PITCH_EMPHASIS_TO_MOTIVATION,
    FA_FRENZY_MAX_DAY,
    FA_STEADY_MAX_DAY,
    FA_FRENZY_MODIFIER,
    FA_STEADY_MODIFIER,
    FA_BARGAIN_MODIFIER,
    FA_WIN_PCT_LOOKBACK_SEASONS,
    FA_SIGNING_SATISFACTION_TIER_1,
    FA_SIGNING_SATISFACTION_TIER_2,
    FA_SIGNING_SATISFACTION_TIER_3,
    FA_AI_NEEDS_COUNT,
    FA_AI_MAX_OFFERS,
    FA_AI_OVERPAY_BY_PERSONALITY,
    FA_IDEAL_ROSTER,
    FA_OFFENSIVE_POSITIONS,
    FA_DEFENSIVE_POSITIONS,
    FA_INTEREST_SIGNALS,
    FA_MARKET_PHASES,
    GM_PERSONALITY_TRAITS,
    MIN_CONTRACT_YEARS,
    MAX_CONTRACT_YEARS,
    MAX_SIGNING_BONUS_PERCENT,
    MAX_GUARANTEED_PERCENT,
    SATISFACTION_STARTER_CALIBER_THRESHOLD,
    FA_POSITIONAL_NEED_QUALITY_THRESHOLD,
    FA_POSITIONAL_NEED_QUALITY_SCALE,
    FA_EARLY_ACCEPTANCE_THRESHOLD,
    FA_VETERAN_PRESTIGE_THRESHOLD,
    FA_AI_TOLERANCE_MULTIPLIER,
    to_letter_grade,
)


# ================================================================
# Private helpers
# ================================================================

def _calc_team_win_pct(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> float:
    """Calculate a team's win percentage over the lookback window.

    Returns 0.5 (neutral) if no games have been played.
    """
    wins = 0
    total = 0
    for offset in range(FA_WIN_PCT_LOOKBACK_SEASONS):
        year = season_year - offset
        games = get_completed_games_for_team(conn, team_id, year)
        for g in games:
            total += 1
            if g['home_team_id'] == team_id:
                if g['home_score'] > g['away_score']:
                    wins += 1
            else:
                if g['away_score'] > g['home_score']:
                    wins += 1
    if total == 0:
        return 0.5
    return wins / total


def _calc_scheme_fit(
    player_position: str, team_id: int, conn: sqlite3.Connection,
) -> float:
    """Score how well a team's scheme fits a player's position.

    Uses the relevant coordinator's best scheme expertise value
    normalized to 0-1. Offensive positions use OC, defensive use DC.
    """
    coordinators = get_team_coordinators(conn, team_id)
    if not coordinators:
        return 0.5

    # Determine which coordinator matters
    if player_position in FA_OFFENSIVE_POSITIONS:
        target_role = 'OC'
    elif player_position in FA_DEFENSIVE_POSITIONS:
        target_role = 'DC'
    else:
        return 0.5  # K, P — neutral

    for coord in coordinators:
        if coord['role'] == target_role and coord['scheme_expertise']:
            try:
                schemes = json.loads(coord['scheme_expertise'])
                if schemes:
                    best_value = max(schemes.values())
                    return best_value / 99.0
            except (json.JSONDecodeError, ValueError):
                pass
    return 0.5


def _calc_role_clarity(
    player_overall: int, player_position: str,
    team_id: int, conn: sqlite3.Connection,
) -> float:
    """Score whether the FA would be a clear starter on this team.

    1.0 = FA is better than current best at position (clear starter).
    0.5 = within threshold of current best (competition).
    0.0 = significantly worse (backup).
    """
    top_ovr = get_top_player_overall_at_position(
        conn, team_id, player_position,
    )
    if top_ovr is None:
        return 1.0  # No one at position = guaranteed starter
    if player_overall > top_ovr:
        return 1.0
    if player_overall >= top_ovr - SATISFACTION_STARTER_CALIBER_THRESHOLD:
        return 0.5
    return 0.0


def _calc_coach_history(
    player_id: int, team_id: int, conn: sqlite3.Connection,
) -> float:
    """Check if a player has previous history with a team.

    Returns 1.0 if the player had a previous contract with this team,
    0.0 otherwise.
    """
    return 1.0 if has_player_history_with_team(conn, player_id, team_id) else 0.0


def _assign_tier(rank: int) -> int:
    """Assign interest tier based on team rank in preference list."""
    if rank <= FA_TIER_1_MAX_RANK:
        return INTEREST_TIER_1
    if rank <= FA_TIER_2_MAX_RANK:
        return INTEREST_TIER_2
    return INTEREST_TIER_3


def _get_market_timing(
    season_year: int, conn: sqlite3.Connection,
) -> tuple[str, float]:
    """Determine current FA market phase and pricing modifier.

    Uses accepted offer count as a proxy for market progression.
    Round 0 = frenzy, rounds 1-2 = steady, round 3+ = bargain.
    """
    accepted = count_accepted_fa_offers(conn, season_year)
    if accepted == 0:
        return FA_MARKET_PHASES[0], FA_FRENZY_MODIFIER
    elif accepted <= FA_EARLY_ACCEPTANCE_THRESHOLD:
        return FA_MARKET_PHASES[1], FA_STEADY_MODIFIER
    else:
        return FA_MARKET_PHASES[2], FA_BARGAIN_MODIFIER


def _identify_positional_needs(
    team_id: int, conn: sqlite3.Connection,
) -> list[str]:
    """Identify a team's top positional needs by roster gap and quality.

    Returns a list of position strings sorted by need (highest first).
    """
    players = get_all_players_on_team(conn, team_id)

    # Count and track best overall by position
    pos_count: dict[str, int] = {}
    pos_best: dict[str, int] = {}
    for p in players:
        pos = p['position']
        pos_count[pos] = pos_count.get(pos, 0) + 1
        if pos not in pos_best or p['true_overall'] > pos_best[pos]:
            pos_best[pos] = p['true_overall']

    # Score each position by need
    need_scores: list[tuple[str, float]] = []
    for pos, ideal in FA_IDEAL_ROSTER.items():
        current = pos_count.get(pos, 0)
        gap = max(0, ideal - current)
        # Quality factor: if best player at position is below threshold, add need
        quality_bonus = 0
        if pos in pos_best and pos_best[pos] < FA_POSITIONAL_NEED_QUALITY_THRESHOLD:
            quality_bonus = (FA_POSITIONAL_NEED_QUALITY_THRESHOLD - pos_best[pos]) / FA_POSITIONAL_NEED_QUALITY_SCALE
        elif pos not in pos_best:
            quality_bonus = 1.0  # No one at position
        score = gap + quality_bonus
        if score > 0:
            need_scores.append((pos, score))

    need_scores.sort(key=lambda x: x[1], reverse=True)
    return [pos for pos, _ in need_scores[:FA_AI_NEEDS_COUNT]]


def _satisfaction_delta_for_tier(tier: int) -> int:
    """Get satisfaction boost for signing based on interest tier."""
    if tier == INTEREST_TIER_1:
        return FA_SIGNING_SATISFACTION_TIER_1
    elif tier == INTEREST_TIER_2:
        return FA_SIGNING_SATISFACTION_TIER_2
    return FA_SIGNING_SATISFACTION_TIER_3


# ================================================================
# Public functions
# ================================================================

def generate_fa_market(
    season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """Generate the free agent market for a season.

    Called once at the start of each offseason. Identifies players
    whose contracts have expired, marks them as free agents, and
    generates destination preference scores for each FA against
    all 32 teams.

    Args:
        season_year: The season year for the FA market.
        conn: Database connection.

    Returns:
        List of dicts, one per free agent, with player info and
        top 3 preferred destinations.
    """
    ensure_fa_tables(conn)

    with conn:
        # Clear stale interest data for this season
        clear_fa_interest_for_season(conn, season_year)

        # Find and expire contracts that have run out
        expiring = get_expiring_contract_players(conn, season_year)
        for row in expiring:
            update_contract_status(conn, row['contract_id'], 'expired')
            update_player_team(conn, row['player_id'], None, 'free_agent')

    # Get full FA pool
    free_agents = get_free_agent_players(conn)
    if not free_agents:
        return []

    teams = get_all_teams(conn)
    result = []

    with conn:
        for fa in free_agents:
            # Calculate preference scores for all 32 teams
            team_scores: list[tuple[int, float, dict]] = []

            for team in teams:
                tid = team['id']
                win_pct = _calc_team_win_pct(tid, season_year, conn)
                scheme = _calc_scheme_fit(fa['position'], tid, conn)
                market = team['market_size'] / 99.0
                role = _calc_role_clarity(
                    fa['true_overall'], fa['position'], tid, conn,
                )
                coach = _calc_coach_history(fa['id'], tid, conn)

                score = (
                    win_pct * FA_PREF_WEIGHT_WINNING
                    + scheme * FA_PREF_WEIGHT_SCHEME_FIT
                    + role * FA_PREF_WEIGHT_ROLE_CLARITY
                    + market * FA_PREF_WEIGHT_MARKET_SIZE
                    + coach * FA_PREF_WEIGHT_COACH_HISTORY
                )

                team_scores.append((tid, score, team))

            # Sort by score descending to determine tier by rank
            team_scores.sort(key=lambda x: x[1], reverse=True)

            top_3 = []
            for rank, (tid, score, team) in enumerate(team_scores, start=1):
                tier = _assign_tier(rank)
                insert_fa_interest(
                    conn, fa['id'], tid, season_year, score, tier,
                )
                if rank <= 3:
                    top_3.append({
                        'team_id': tid,
                        'city': team['city'],
                        'nickname': team['nickname'],
                        'tier': tier,
                    })

            result.append({
                'player_id': fa['id'],
                'first_name': fa['first_name'],
                'last_name': fa['last_name'],
                'position': fa['position'],
                'display_grade': to_letter_grade(fa['true_overall']),
                'age': fa['age'],
                'top_3_destinations': top_3,
            })

    return result


def get_interest_tier(
    player_id: int, team_id: int, conn: sqlite3.Connection,
) -> dict:
    """Get the interest tier signal for a player-team pair.

    Returns qualitative front-office intelligence about the player's
    interest level. Never exposes raw tier integers to the UI layer.

    Args:
        player_id: Free agent player ID.
        team_id: Team to check interest for.
        conn: Database connection.

    Returns:
        Dict with tier (int for internal use), signal (narrative text),
        and actionable (bool).
    """
    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0

    interest = get_fa_interest(conn, player_id, team_id, season_year)
    if not interest:
        return {
            'tier': INTEREST_TIER_3,
            'signal': "We haven't been able to gauge his interest.",
            'actionable': False,
        }

    tier = interest['tier']
    # Deterministic signal selection based on player+team for consistency
    rng = random.Random(player_id * 31 + team_id)
    signals = FA_INTEREST_SIGNALS.get(tier, FA_INTEREST_SIGNALS[3])
    signal = rng.choice(signals)

    return {
        'tier': tier,
        'signal': signal,
        'actionable': tier <= INTEREST_TIER_2,
    }


def request_pitch_meeting(
    player_id: int,
    team_id: int,
    emphasis: str,
    conn: sqlite3.Connection,
) -> dict:
    """Request a pitch meeting with a Tier 2 free agent.

    Available only for Tier 2 players. The emphasis determines the
    pitch angle and is matched against the player's primary motivation.

    Args:
        player_id: Free agent player ID.
        team_id: Team making the pitch.
        emphasis: One of 'winning', 'scheme_fit', 'role', 'money_first'.
        conn: Database connection.

    Returns:
        Dict with outcome, tier_change, message, and new_tier.

    Raises:
        ValueError: On invalid emphasis or wrong tier.
    """
    valid_emphases = set(FA_PITCH_EMPHASIS_TO_MOTIVATION.keys())
    if emphasis not in valid_emphases:
        raise ValueError(
            f"Invalid emphasis '{emphasis}'. Valid: {valid_emphases}"
        )

    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']

    interest = get_fa_interest(conn, player_id, team_id, season_year)
    if not interest:
        raise ValueError(
            f"No FA interest record for player {player_id} / team {team_id}"
        )

    current_tier = interest['tier']
    if current_tier == INTEREST_TIER_1:
        return {
            'outcome': 'neutral',
            'tier_change': 0,
            'message': "He's already highly interested — no pitch needed.",
            'new_tier': INTEREST_TIER_1,
        }
    if current_tier == INTEREST_TIER_3:
        raise ValueError(
            "Can't schedule a pitch meeting with a Tier 3 player. "
            "His agent won't take the meeting."
        )

    # money_first always signals desperation for Tier 2
    if emphasis == 'money_first':
        with conn:
            adjust_satisfaction(
                player_id, FA_PITCH_DESPERATION_DELTA,
                'fa_pitch_desperation', conn,
            )
            if random.random() < FA_PITCH_FAILURE_DROP_CHANCE:
                new_tier = INTEREST_TIER_3
                update_fa_interest_tier(
                    conn, player_id, team_id, season_year, new_tier,
                )
                return {
                    'outcome': 'failure',
                    'tier_change': -1,
                    'message': (
                        "Leading with money came off as desperate. "
                        "His agent says they're looking elsewhere now."
                    ),
                    'new_tier': new_tier,
                }
            return {
                'outcome': 'failure',
                'tier_change': 0,
                'message': (
                    "Leading with money didn't impress. "
                    "He's still willing to listen but wasn't moved."
                ),
                'new_tier': INTEREST_TIER_2,
            }

    # Map emphasis to satisfaction motivation and call apply_intervention
    mapped_motivation = FA_PITCH_EMPHASIS_TO_MOTIVATION[emphasis]

    try:
        intervention = apply_intervention(
            player_id, 'private_meeting',
            {'message': mapped_motivation}, conn,
        )
    except ValueError as e:
        # Cooldown or other validation error
        return {
            'outcome': 'failure',
            'tier_change': 0,
            'message': str(e),
            'new_tier': INTEREST_TIER_2,
        }

    if intervention['success']:
        new_tier = INTEREST_TIER_1
        with conn:
            update_fa_interest_tier(
                conn, player_id, team_id, season_year, new_tier,
            )
        return {
            'outcome': 'success',
            'tier_change': 1,
            'message': intervention['message'],
            'new_tier': new_tier,
        }
    else:
        # Failed pitch — chance of dropping to Tier 3
        if random.random() < FA_PITCH_FAILURE_DROP_CHANCE:
            new_tier = INTEREST_TIER_3
            tier_change = -1
        else:
            new_tier = INTEREST_TIER_2
            tier_change = 0

        with conn:
            update_fa_interest_tier(
                conn, player_id, team_id, season_year, new_tier,
            )
        return {
            'outcome': 'failure',
            'tier_change': tier_change,
            'message': intervention['message'],
            'new_tier': new_tier,
        }


def submit_offer(
    player_id: int,
    team_id: int,
    years: int,
    aav: int,
    signing_bonus: int,
    guaranteed_money: int,
    conn: sqlite3.Connection,
) -> dict:
    """Submit a formal contract offer to a free agent.

    Validates basic contract structure and stores the offer as
    'pending'. The agent's response is determined by resolve_offer().

    Args:
        player_id: Free agent player ID.
        team_id: Team making the offer.
        years: Contract length in years.
        aav: Average annual value.
        signing_bonus: Upfront signing bonus.
        guaranteed_money: Total guaranteed money.
        conn: Database connection.

    Returns:
        Dict with offer details including id, aav, status, tier,
        and optional warning.

    Raises:
        ValueError: On invalid contract structure.
    """
    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']

    # Get interest tier
    interest = get_fa_interest(conn, player_id, team_id, season_year)
    tier = interest['tier'] if interest else INTEREST_TIER_3

    total_value = aav * years

    # Validate contract structure
    if years < MIN_CONTRACT_YEARS or years > MAX_CONTRACT_YEARS:
        raise ValueError(
            f"Contract years must be {MIN_CONTRACT_YEARS}-{MAX_CONTRACT_YEARS}"
        )
    if signing_bonus > int(total_value * MAX_SIGNING_BONUS_PERCENT):
        raise ValueError(
            f"Signing bonus exceeds {int(MAX_SIGNING_BONUS_PERCENT * 100)}% "
            f"of total value"
        )
    if guaranteed_money > int(total_value * MAX_GUARANTEED_PERCENT):
        raise ValueError(
            f"Guaranteed money exceeds {int(MAX_GUARANTEED_PERCENT * 100)}% "
            f"of total value"
        )

    # Check for Tier 3 without overpay — warn but still store
    warning = None
    if tier == INTEREST_TIER_3:
        market = get_market_value(player_id, None, conn)
        fair = market['fair']
        if fair > 0 and aav < int(fair * FA_TIER_3_OVERPAY_THRESHOLD):
            warning = (
                "His agent is unlikely to respond. The player isn't "
                "interested without a significantly better offer."
            )

    # Store the offer
    with conn:
        offer_id = insert_fa_offer(
            conn, player_id, team_id, season_year,
            round_number=1,
            years_offered=years,
            total_value=total_value,
            signing_bonus=signing_bonus,
            guaranteed_money=guaranteed_money,
            status='pending',
            player_tier=tier,
        )

    return {
        'id': offer_id,
        'player_id': player_id,
        'team_id': team_id,
        'years': years,
        'aav': aav,
        'total_value': total_value,
        'signing_bonus': signing_bonus,
        'guaranteed_money': guaranteed_money,
        'status': 'pending',
        'tier': tier,
        'warning': warning,
    }


def resolve_offer(
    offer_id: int, conn: sqlite3.Connection,
) -> dict:
    """Simulate the agent's response to a pending offer.

    Evaluates the offer against fair market value (adjusted for
    market timing) and the player's interest tier.

    Args:
        offer_id: ID of the pending offer.
        conn: Database connection.

    Returns:
        Dict with response ('accepted'|'countered'|'shopped'|'walked'),
        counter_terms (if countered), message, and signed (bool).

    Raises:
        ValueError: If offer not found or not pending.
    """
    offer = get_fa_offer(conn, offer_id)
    if not offer:
        raise ValueError(f"Offer {offer_id} not found")
    if offer['status'] != 'pending':
        raise ValueError(
            f"Offer {offer_id} is '{offer['status']}', not 'pending'"
        )

    player_id = offer['player_id']
    team_id = offer['offering_team_id']
    tier = offer['player_tier']
    years = offer['years_offered']
    total_value = offer['total_value']
    signing_bonus = offer['signing_bonus']
    guaranteed_money = offer['guaranteed_money']
    offered_aav = total_value // years if years > 0 else 0

    league = get_league_state(conn)
    season_year = league['current_season'] if league else 0

    # Get market value and apply timing modifier
    market = get_market_value(player_id, None, conn)
    fair_aav = market['fair']

    _, modifier = _get_market_timing(season_year, conn)
    adjusted_fair = int(fair_aav * (1 + modifier))

    if adjusted_fair > 0:
        ratio = offered_aav / adjusted_fair
    else:
        ratio = 1.0  # If fair value is 0, accept anything

    player = get_player_for_contract(conn, player_id)
    player_name = (
        f"{player['first_name']} {player['last_name']}" if player
        else f"Player {player_id}"
    )

    # Decision tree
    response = 'walked'
    counter_terms = None
    message = ''
    signed = False

    if tier == INTEREST_TIER_1:
        if ratio >= FA_ACCEPT_THRESHOLD:
            response = 'accepted'
            message = (
                f"{player_name}'s agent accepted the offer. "
                f"He's excited to join the team."
            )
        elif ratio >= FA_COUNTER_THRESHOLD:
            response = 'countered'
            counter_aav = adjusted_fair
            counter_total = counter_aav * years
            message = (
                f"{player_name}'s agent wants to negotiate. "
                f"They're looking for ${counter_aav:,} AAV."
            )
            counter_terms = {
                'aav': counter_aav,
                'years': years,
                'total_value': counter_total,
                'guaranteed_money': int(counter_total * 0.60),
                'signing_bonus': int(counter_total * 0.15),
            }
        else:
            response = 'walked'
            message = (
                f"{player_name}'s agent was offended by the offer. "
                f"They're moving on to other teams."
            )

    elif tier == INTEREST_TIER_2:
        if ratio >= FA_TIER_2_ACCEPT_PREMIUM:
            response = 'accepted'
            message = (
                f"{player_name}'s agent accepted the premium offer. "
                f"The money made up for us not being his first choice."
            )
        elif ratio >= FA_COUNTER_THRESHOLD:
            response = 'shopped'
            message = (
                f"{player_name}'s agent is shopping your offer around "
                f"the league. Other teams now know your price."
            )
        else:
            response = 'walked'
            message = (
                f"{player_name}'s agent didn't feel the offer was "
                f"serious enough to engage."
            )

    elif tier == INTEREST_TIER_3:
        if ratio >= FA_TIER_3_OVERPAY_THRESHOLD:
            response = 'accepted'
            message = (
                f"{player_name}'s agent accepted — the premium offer "
                f"was too good to pass up despite his reservations."
            )
        else:
            response = 'walked'
            message = (
                f"{player_name}'s agent declined without a counter. "
                f"He's not interested without a significantly better offer."
            )

    # Execute the response
    with conn:
        if response == 'accepted':
            update_fa_offer_status(conn, offer_id, 'accepted')
            # Sign the contract via offer_contract
            contract_result = offer_contract(
                player_id, team_id, years, offered_aav,
                signing_bonus, guaranteed_money,
                None, None, None, conn,
            )
            # Satisfaction boost for signing
            sat_delta = _satisfaction_delta_for_tier(tier)
            if sat_delta > 0:
                adjust_satisfaction(
                    player_id, sat_delta, 'fa_signing', conn,
                )
            signed = True
        elif response == 'countered':
            update_fa_offer_status(conn, offer_id, 'countered')
        elif response == 'shopped':
            update_fa_offer_status(conn, offer_id, 'shopped')
        else:
            update_fa_offer_status(conn, offer_id, 'rejected')

    return {
        'response': response,
        'counter_terms': counter_terms,
        'message': message,
        'signed': signed,
    }


def run_ai_fa_signings(
    season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """Simulate all AI teams making free agency decisions for one cycle.

    Each AI team identifies positional needs and targets free agents
    based on their GM personality archetype. Uses the same
    submit_offer/resolve_offer pipeline as the human player.

    Args:
        season_year: Current season year.
        conn: Database connection.

    Returns:
        List of signing dicts for the transaction log display.
    """
    league = get_league_state(conn)
    user_team_id = league['user_team_id'] if league else None

    teams = list(get_all_teams(conn))
    random.shuffle(teams)

    signings = []

    for team in teams:
        tid = team['id']
        if tid == user_team_id:
            continue

        personality = team['gm_personality']
        traits = GM_PERSONALITY_TRAITS.get(personality, {})
        aggression = traits.get('fa_aggression', 0.5)

        # Low-aggression GMs may skip FA entirely
        if random.random() > aggression:
            continue

        # Identify positional needs
        needs = _identify_positional_needs(tid, conn)
        if not needs:
            continue

        overpay_pct = FA_AI_OVERPAY_BY_PERSONALITY.get(personality, 0.0)
        offers_made = 0

        # Get current free agents
        free_agents = get_free_agent_players(conn)
        if not free_agents:
            break  # No more FAs available

        for need_pos in needs:
            if offers_made >= FA_AI_MAX_OFFERS:
                break

            # Filter FAs by position
            candidates = [
                fa for fa in free_agents
                if fa['position'] == need_pos
            ]
            if not candidates:
                continue

            # Personality-specific sorting
            if personality == 'win_now':
                candidates.sort(
                    key=lambda p: p['true_overall'], reverse=True,
                )
            elif personality == 'draft_purist':
                # Only target below-average players (cheap fills)
                candidates = [
                    c for c in candidates if c['true_overall'] < 75
                ]
                if not candidates:
                    continue
                candidates.sort(key=lambda p: p['true_overall'])
            elif personality == 'analytics':
                # Sort by scheme fit with this team
                def scheme_score(p):
                    interest = get_fa_interest(
                        conn, p['id'], tid, season_year,
                    )
                    return interest['preference_score'] if interest else 0
                candidates.sort(key=scheme_score, reverse=True)
            elif personality == 'loyalty':
                # Prioritize former players
                former = [
                    c for c in candidates
                    if has_player_history_with_team(conn, c['id'], tid)
                ]
                if former:
                    candidates = former + [
                        c for c in candidates if c not in former
                    ]
            else:
                # opportunist: random
                random.shuffle(candidates)

            # Try to sign the top candidate
            target = candidates[0]
            try:
                market = get_market_value(target['id'], None, conn)
            except ValueError:
                continue

            fair_aav = market['fair']
            if fair_aav <= 0:
                continue

            # Calculate offer based on personality
            offer_aav = int(fair_aav * (1 + overpay_pct))
            offer_years = min(
                max(MIN_CONTRACT_YEARS, 3), MAX_CONTRACT_YEARS,
            )
            offer_bonus = int(offer_aav * offer_years * 0.12)
            offer_guaranteed = int(offer_aav * offer_years * 0.40)

            # Check cap space (rough check)
            team_row = get_team(conn, tid)
            if team_row and team_row['cap_space'] < offer_aav:
                continue

            try:
                offer_result = submit_offer(
                    target['id'], tid, offer_years,
                    offer_aav, offer_bonus, offer_guaranteed, conn,
                )
            except ValueError:
                continue

            try:
                resolution = resolve_offer(offer_result['id'], conn)
            except ValueError:
                continue

            if resolution['signed']:
                signings.append({
                    'team_id': tid,
                    'team_abbreviation': team['abbreviation'],
                    'player_id': target['id'],
                    'player_name': (
                        f"{target['first_name']} {target['last_name']}"
                    ),
                    'position': target['position'],
                    'aav': offer_aav,
                    'years': offer_years,
                })

            offers_made += 1

    return signings


def get_fa_market_status(
    season_year: int, conn: sqlite3.Connection,
) -> dict:
    """Get a read-only snapshot of the current FA market.

    Returns remaining unsigned free agents grouped by position,
    total count, and market timing information.

    Args:
        season_year: Current season year.
        conn: Database connection.

    Returns:
        Dict with total_unsigned, by_position, timing_phase,
        and timing_modifier.
    """
    total = count_unsigned_free_agents(conn)

    position_rows = get_unsigned_free_agents_by_position(conn)
    by_position = {row['position']: row['cnt'] for row in position_rows}

    phase, modifier = _get_market_timing(season_year, conn)

    return {
        'total_unsigned': total,
        'by_position': by_position,
        'timing_phase': phase,
        'timing_modifier': modifier,
    }
