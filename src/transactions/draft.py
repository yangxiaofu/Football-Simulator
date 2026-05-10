"""
Draft system for Football Simulator (Phase 3).

Manages the 7-round NFL draft event: initialization from standings, AI pick logic,
prospect-to-player conversion, live trade offers, rookie contracts, and completion.

All database access goes through src/db/queries.py — no raw SQL here.
All tuning constants come from src/utils/constants.py.
"""

import random
import sqlite3
from typing import Optional

from ..db.cap import recalculate_cap_space
from ..db.queries import (
    count_draft_picks_for_season,
    get_all_prospects,
    get_all_season_records,
    get_all_teams,
    get_draft_board,
    get_draft_board_entry,
    get_draft_picks_for_team,
    get_drafted_prospect_ids,
    get_drafted_prospects_for_team,
    get_league_state,
    get_mock_draft_position,
    get_on_the_clock_pick,
    get_prospect_by_id,
    get_roster_position_counts,
    get_team,
    get_undrafted_prospects,
    insert_draft_pick,
    insert_draft_state_pick,
    clear_draft_state,
    get_draft_state_order,
    mark_draft_pick_used,
    update_draft_state_used,
    update_prospect_draft_result,
    count_prospect_red_flags,
    get_owned_draft_picks_for_round,
    get_draft_pick_used_by_team,
    get_draft_state_by_id,
    get_upcoming_draft_picks,
)
from ..db.transactions import log_transaction
from ..generation.players import insert_player
from ..scouting.board import _calculate_positional_need
from ..scouting.prospects import retire_undrafted_prospects
from ..transactions.contracts import offer_contract
from ..transactions.trades import calculate_pick_value
from ..utils.constants import (
    AI_BOARD_NOISE,
    AI_PICK_WEIGHTS_BY_PERSONALITY,
    DRAFT_BOARD_FALL_THRESHOLD,
    DRAFT_EARLY_ROUND_OFFER_BOOST,
    DRAFT_LIVE_OFFER_PROBABILITIES,
    DRAFT_ROUNDS,
    MIN_PLAYER_SALARY,
    PICKS_PER_ROUND,
    POWER_5_CONFERENCES,
    PROSPECT_FA_POOL_MIN_OVR,
    ROOKIE_CONTRACT_YEARS,
    ROOKIE_GUARANTEE_BY_ROUND,
    ROOKIE_SALARY_FLOOR_MULTIPLIER,
    ROOKIE_SALARY_SCALE_DECAY,
    ROOKIE_SALARY_TOP_PICK_MULTIPLIER,
    SALARY_CAP_YEAR_ONE,
    STAMINA_MAX,
    to_letter_grade,
    DRAFT_ANALYTICS_RED_FLAG_PENALTY,
    DRAFT_LOYALTY_POWER5_BONUS,
    DRAFT_OFFER_MIN_PROBABILITY,
    DRAFT_OFFER_VALUE_PREMIUM,
    DRAFT_OFFER_VALUE_FLOOR,
    DRAFT_OFFER_VALUE_EXCELLENT,
    DRAFT_OFFER_VALUE_FAIR,
    DRAFT_POSITIONAL_NEED_THRESHOLD,
    DRAFT_ROOKIE_SALARY_DIVISOR,
    DRAFT_ROOKIE_ESCALATION_FRACTION,
    DRAFT_ROOKIE_BONUS_DIVISOR,
)


def _build_player_from_prospect(prospect: sqlite3.Row, team_id: int,
                                season_year: int, draft_round: int,
                                draft_pick: int) -> dict:
    """Build a player dict from a prospect row for insert_player()."""
    return {
        'team_id': team_id,
        'first_name': prospect['first_name'],
        'last_name': prospect['last_name'],
        'position': prospect['position'],
        'age': prospect['age'],
        'years_experience': 0,
        'college': prospect['college'],
        'draft_year': season_year,
        'draft_round': draft_round,
        'draft_pick': draft_pick,
        'true_overall': prospect['true_overall'],
        'true_speed': prospect['true_speed'],
        'true_strength': prospect['true_strength'],
        'true_football_iq': prospect['true_football_iq'],
        'true_durability': prospect['true_durability'],
        'true_clutch': prospect['true_clutch'],
        'true_ceiling': prospect['true_ceiling'],
        'development_trait': prospect['development_trait'],
        'true_catch': prospect['true_catch'],
        'true_route_running': prospect['true_route_running'],
        'true_blocking': prospect['true_blocking'],
        'true_pass_rush': prospect['true_pass_rush'],
        'true_coverage_man': prospect['true_coverage_man'],
        'true_coverage_zone': prospect['true_coverage_zone'],
        'true_tackling': prospect['true_tackling'],
        'true_accuracy_short': prospect['true_accuracy_short'],
        'true_accuracy_mid': prospect['true_accuracy_mid'],
        'true_accuracy_deep': prospect['true_accuracy_deep'],
        'true_pocket_presence': prospect['true_pocket_presence'],
        'true_arm_strength': prospect['true_arm_strength'],
        'true_elusiveness': prospect['true_elusiveness'],
        'true_vision': prospect['true_vision'],
        'true_kick_accuracy': prospect['true_kick_accuracy'],
        'true_kick_power': prospect['true_kick_power'],
        'true_yac': prospect['true_yac'],
        'weekly_stamina': STAMINA_MAX,
        'season_wear': 0,
        'satisfaction': 75,
        'is_active': 1,
        'roster_status': 'active',
        'injury_status': None,
        'injury_weeks_remaining': 0,
    }


def _generate_war_room_reaction(
    prospect_id: int, prospect_name: str, pick_overall: int,
    team_id: int, picking_team_name: str, season_year: int,
    conn: sqlite3.Connection,
) -> str:
    """Generate a war room reaction for a pick."""
    # Get user team for board context
    league = get_league_state(conn)
    user_team_id = league['user_team_id'] if league else None

    # Check user's board rank for this prospect
    board_rank = None
    if user_team_id:
        board_entry = get_draft_board_entry(conn, user_team_id, prospect_id, season_year)
        if board_entry:
            board_rank = board_entry['board_override'] or int(board_entry['board_rank'])

    # Check mock position
    mock_position = get_mock_draft_position(conn, prospect_id, season_year)

    # Generate reaction
    if board_rank is not None and board_rank <= 3:
        return (
            f"Expected pick -- {prospect_name} was our #{board_rank} "
            f"rated prospect."
        )
    if board_rank is not None and board_rank <= 10:
        return (
            f"Solid value -- {prospect_name} was #{board_rank} on our "
            f"board, picked at #{pick_overall}."
        )
    if mock_position and pick_overall < mock_position - 5:
        return (
            f"Surprise -- {prospect_name} was mocked at #{mock_position}. "
            f"Either we missed something or {picking_team_name} reached."
        )
    if mock_position and pick_overall > mock_position + 10:
        return (
            f"Steal -- {prospect_name} was mocked at #{mock_position} "
            f"but fell to #{pick_overall}."
        )
    return f"{prospect_name} goes at #{pick_overall} to {picking_team_name}."


def initialize_draft(
    season_year: int, conn: sqlite3.Connection,
) -> dict:
    """
    Initialize the draft event by building the pick order from standings.

    Creates draft_state rows from draft_pick ownership data, ordered by
    previous season's standings (worst record first, non-playoff teams
    before playoff teams).

    Args:
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Dict with total_picks, rounds, picks_by_team.
    """
    # Defensive table creation for direct sqlite3 connections
    conn.execute("""
        CREATE TABLE IF NOT EXISTS draft_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER NOT NULL,
            pick_number_overall INTEGER NOT NULL,
            round INTEGER NOT NULL,
            pick_in_round INTEGER NOT NULL,
            team_id INTEGER NOT NULL REFERENCES team(id),
            original_team_id INTEGER NOT NULL REFERENCES team(id),
            prospect_id INTEGER REFERENCES prospect(id),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','used','traded')),
            war_room_reaction TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(season_year, pick_number_overall)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_state_season
        ON draft_state(season_year, status)
    """)

    # Clear existing draft state for idempotency
    clear_draft_state(conn, season_year)

    # Reset any previously used draft picks for this season (idempotent re-init)
    conn.execute("""
        UPDATE draft_pick SET used = 0, player_selected_id = NULL
        WHERE season_year = ?
    """, (season_year,))

    # Reset prospects that may have been drafted in a previous init
    conn.execute("""
        UPDATE prospect SET was_drafted = 0, drafted_by_team_id = NULL,
            draft_round = NULL, draft_pick = NULL, player_id = NULL
        WHERE draft_class_id IN (
            SELECT id FROM draft_class WHERE season_year = ?
        ) AND was_drafted = 1
    """, (season_year,))

    # Get previous season records for draft order
    prev_season = season_year - 1
    records = get_all_season_records(conn, prev_season)

    # Build team ordering: non-playoff by wins ASC, then playoff by wins ASC
    if records:
        non_playoff = [r for r in records if not r['made_playoffs']]
        playoff = [r for r in records if r['made_playoffs']]
        # Within each group, sort by wins ASC then points_for ASC
        non_playoff.sort(key=lambda r: (r['wins'], r['points_for']))
        playoff.sort(key=lambda r: (r['wins'], r['points_for']))
        draft_order_teams = [r['team_id'] for r in non_playoff + playoff]
    else:
        # No previous season — use team ID order (franchise start)
        all_teams = get_all_teams(conn)
        draft_order_teams = [t['id'] for t in all_teams]
        random.shuffle(draft_order_teams)

    # Map original team position in draft order (1-indexed)
    team_position = {tid: idx + 1 for idx, tid in enumerate(draft_order_teams)}

    # Generate draft_pick rows if they don't exist for this season
    existing_pick_count = count_draft_picks_for_season(conn, season_year)
    if existing_pick_count == 0:
        for round_num in range(1, DRAFT_ROUNDS + 1):
            for idx, tid in enumerate(draft_order_teams):
                pick_num = idx + 1
                insert_draft_pick(
                    conn, tid, tid, season_year, round_num, pick_num,
                )

    # Build picks per round from draft_pick table
    pick_overall = 0
    picks_by_team = {}

    for round_num in range(1, DRAFT_ROUNDS + 1):
        # Collect all picks for this round, keyed by original team
        round_picks = []
        for orig_team_id in draft_order_teams:
            # Find all draft_pick rows for this original team and round
            # Note: We need picks by original_team but get_owned_draft_picks_for_round uses owned_by
            # So we still need this raw SQL for now (filtered by original_team_id)
            all_picks = conn.execute("""
                SELECT * FROM draft_pick
                WHERE original_team_id = ? AND season_year = ? AND round = ?
                      AND used = 0
                ORDER BY id
            """, (orig_team_id, season_year, round_num)).fetchall()

            for dp in all_picks:
                owning_team = dp['owned_by_team_id']
                round_picks.append({
                    'original_team_id': orig_team_id,
                    'owning_team_id': owning_team,
                    'draft_pick_id': dp['id'],
                    'sort_key': team_position.get(orig_team_id, 32),
                })

        # Sort by original team's draft position
        round_picks.sort(key=lambda x: x['sort_key'])

        pick_in_round = 0
        for rp in round_picks:
            pick_overall += 1
            pick_in_round += 1
            insert_draft_state_pick(
                conn, season_year, pick_overall, round_num, pick_in_round,
                rp['owning_team_id'], rp['original_team_id'],
            )
            # Track picks by team
            tid = rp['owning_team_id']
            picks_by_team[tid] = picks_by_team.get(tid, 0) + 1

    conn.commit()

    return {
        'total_picks': pick_overall,
        'rounds': DRAFT_ROUNDS,
        'picks_by_team': picks_by_team,
    }


def get_draft_order(
    season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Get the full draft order.

    Args:
        season_year: The draft year.
        conn: Database connection.

    Returns:
        List of pick dicts ordered by pick_number_overall.
    """
    rows = get_draft_state_order(conn, season_year)
    return [dict(r) for r in rows]


def get_on_the_clock(
    season_year: int, conn: sqlite3.Connection,
) -> Optional[dict]:
    """
    Get the next pending pick.

    Args:
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Pick dict or None if draft is complete.
    """
    row = get_on_the_clock_pick(conn, season_year)
    return dict(row) if row else None


def make_pick(
    team_id: int, prospect_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    Make a draft pick: convert prospect to player, update records.

    Args:
        team_id: Team making the pick (must be on the clock).
        prospect_id: Prospect being selected.
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Dict with pick details, prospect info, and war room reaction.

    Raises:
        ValueError: If team is not on the clock or prospect already drafted.
    """
    # Validate team is on the clock
    current = get_on_the_clock_pick(conn, season_year)
    if not current:
        raise ValueError("No pending picks — draft may be complete.")
    if current['team_id'] != team_id:
        raise ValueError(
            f"Team {team_id} is not on the clock. "
            f"Team {current['team_id']} has pick #{current['pick_number_overall']}."
        )

    # Validate prospect not already drafted
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} does not exist.")
    if prospect['was_drafted']:
        raise ValueError(
            f"{prospect['first_name']} {prospect['last_name']} "
            f"has already been drafted."
        )

    pick_overall = current['pick_number_overall']
    round_num = current['round']
    pick_in_round = current['pick_in_round']

    # Get team info for narrative
    team_row = get_team(conn, team_id)
    team_name = (
        f"{team_row['city']} {team_row['nickname']}"
        if team_row else f"Team {team_id}"
    )

    # Convert prospect to player
    player_dict = _build_player_from_prospect(
        prospect, team_id, season_year, round_num, pick_overall,
    )
    player_id = insert_player(conn, player_dict)

    # Update prospect record
    update_prospect_draft_result(
        conn, prospect_id, team_id, round_num, pick_overall, player_id,
    )

    # Update draft_pick record (find matching pick)
    draft_picks = get_draft_pick_used_by_team(conn, team_id, season_year, round_num)
    if draft_picks:
        mark_draft_pick_used(conn, draft_picks['id'], player_id)

    # Generate war room reaction
    prospect_name = f"{prospect['first_name']} {prospect['last_name']}"
    reaction = _generate_war_room_reaction(
        prospect_id, prospect_name, pick_overall,
        team_id, team_name, season_year, conn,
    )

    # Update draft_state
    update_draft_state_used(conn, current['id'], prospect_id, reaction)

    # Log transaction
    log_transaction(
        conn,
        season_year=season_year,
        week_number=0,
        transaction_type='drafted',
        team_id=team_id,
        player_id=player_id,
        description=(
            f"Drafted {prospect['position']} {prospect_name} "
            f"(Round {round_num}, Pick #{pick_overall})"
        ),
        cap_impact=0,
    )

    display_grade = to_letter_grade(prospect['true_overall'])

    conn.commit()

    return {
        'pick_number': pick_overall,
        'round': round_num,
        'pick_in_round': pick_in_round,
        'team_id': team_id,
        'prospect_id': prospect_id,
        'player_id': player_id,
        'prospect_name': prospect_name,
        'position': prospect['position'],
        'display_grade': display_grade,
        'war_room_reaction': reaction,
    }


def run_ai_pick(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """
    Execute an AI team's draft pick using personality-weighted scoring.

    AI teams use true_overall with noise (not scouted ratings) to build
    their board. GM personality determines talent vs. need weighting.

    Args:
        team_id: AI team making the pick.
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Same dict as make_pick().
    """
    # Get all undrafted prospects
    all_prospects = get_all_prospects(conn, season_year)
    drafted_ids = set(get_drafted_prospect_ids(conn, season_year))
    available = [p for p in all_prospects if p['id'] not in drafted_ids]

    if not available:
        raise ValueError("No undrafted prospects remaining.")

    # Get GM personality and phase-aware behavior
    team_row = get_team(conn, team_id)
    gm_personality = team_row['gm_personality'] if team_row else 'analytics'

    # Phase-aware draft strategy
    from ..utils.ai_behavior_matrix import get_behavior_signature
    from ..utils.constants import DRAFT_STRATEGY_WEIGHTS, DRAFT_UPSIDE_NOISE_BOOST
    if team_row:
        try:
            team_phase = team_row['team_phase'] or 'bridge'
        except (IndexError, KeyError):
            team_phase = 'bridge'
    else:
        team_phase = 'bridge'
    profile = get_behavior_signature(gm_personality, team_phase)
    draft_strategy = profile['draft_strategy']

    # Use behavior matrix strategy weights instead of personality-only weights
    strategy_weights = DRAFT_STRATEGY_WEIGHTS.get(draft_strategy, DRAFT_STRATEGY_WEIGHTS['bpa'])

    if gm_personality == 'opportunist':
        # Randomize weights each pick (personality override)
        talent_w = random.uniform(0.40, 0.80)
        need_w = 1.0 - talent_w
    else:
        talent_w = strategy_weights['talent']
        need_w = strategy_weights['need']

    # Extra noise for upside strategy (higher ceiling, more variance)
    extra_noise = DRAFT_UPSIDE_NOISE_BOOST if draft_strategy == 'upside' else 0

    # Score each available prospect
    scored = []
    for prospect in available:
        # AI board: true_overall + noise
        noise = random.randint(-AI_BOARD_NOISE - extra_noise, AI_BOARD_NOISE + extra_noise)
        talent_score = prospect['true_overall'] + noise

        # Positional need
        need_score = _calculate_positional_need(
            team_id, prospect['position'], conn,
        )

        composite = talent_score * talent_w + need_score * need_w

        # Personality-specific filters
        if gm_personality == 'analytics':
            # Skip prospects with 2+ red flags
            red_flag_count = count_prospect_red_flags(conn, prospect['id'])
            if red_flag_count >= 2:
                composite -= DRAFT_ANALYTICS_RED_FLAG_PENALTY

        if gm_personality == 'loyalty':
            # Bonus for Power 5 conferences
            if prospect['college_conference'] in POWER_5_CONFERENCES:
                composite += DRAFT_LOYALTY_POWER5_BONUS

        scored.append((prospect, composite))

    # Select highest-scored prospect
    scored.sort(key=lambda x: x[1], reverse=True)
    best_prospect = scored[0][0]

    return make_pick(team_id, best_prospect['id'], season_year, conn)


def generate_live_trade_offers(
    team_id: int, pick_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate trade offers from AI teams for the current pick.

    Args:
        team_id: Team currently on the clock.
        pick_id: draft_state row id for the current pick.
        season_year: The draft year.
        conn: Database connection.

    Returns:
        List of offer dicts (may be empty).
    """
    # Get current pick info
    current = get_draft_state_by_id(conn, pick_id)
    if not current:
        return []

    round_num = current['round']

    # Determine number of offers
    boosted_probs = dict(DRAFT_LIVE_OFFER_PROBABILITIES)
    if round_num <= 2:
        # Boost probability of getting offers in early rounds
        boost = DRAFT_EARLY_ROUND_OFFER_BOOST
        # Reduce probability of 0 offers, increase others
        zero_prob = max(DRAFT_OFFER_MIN_PROBABILITY, boosted_probs[0] - boost * 3)
        extra = boosted_probs[0] - zero_prob
        boosted_probs[0] = zero_prob
        boosted_probs[1] = boosted_probs.get(1, 0.25) + extra * 0.5
        boosted_probs[2] = boosted_probs.get(2, 0.12) + extra * 0.3
        boosted_probs[3] = boosted_probs.get(3, 0.03) + extra * 0.2

    counts = list(boosted_probs.keys())
    weights = list(boosted_probs.values())
    num_offers = random.choices(counts, weights=weights, k=1)[0]

    if num_offers == 0:
        return []

    # Get all teams except the one on the clock
    all_teams = get_all_teams(conn)
    other_teams = [t for t in all_teams if t['id'] != team_id]
    random.shuffle(other_teams)

    # Current pick value
    current_pick_value = calculate_pick_value(
        round_num, current['pick_in_round'], 0, conn,
    )

    offers = []
    used_teams = set()

    for i in range(min(num_offers, len(other_teams))):
        ai_team = other_teams[i]
        if ai_team['id'] in used_teams:
            continue
        used_teams.add(ai_team['id'])

        ai_team_name = f"{ai_team['city']} {ai_team['nickname']}"

        # Get AI team's available picks
        ai_picks = get_draft_picks_for_team(conn, ai_team['id'], season_year)
        if not ai_picks:
            continue

        # Find AI picks that are in later rounds than current
        later_picks = [
            p for p in ai_picks
            if p['round'] > round_num or (
                p['round'] == round_num
                and (p['pick_number'] or 32) > current['pick_in_round']
            )
        ]
        if not later_picks:
            continue

        # Build an offer: combine picks to approximate current pick value
        offered_picks = []
        offered_value = 0
        for lp in later_picks:
            pv = calculate_pick_value(
                lp['round'], lp['pick_number'], 0, conn,
            )
            offered_picks.append({
                'round': lp['round'],
                'pick_number': lp['pick_number'],
                'draft_pick_id': lp['id'],
                'value': pv,
            })
            offered_value += pv
            # Offer premium above fair value to sweeten the deal
            if offered_value >= current_pick_value * DRAFT_OFFER_VALUE_PREMIUM:
                break

        if offered_value < current_pick_value * DRAFT_OFFER_VALUE_FLOOR:
            continue  # Can't build a worthwhile offer

        value_ratio = offered_value / current_pick_value if current_pick_value > 0 else 0
        if value_ratio >= DRAFT_OFFER_VALUE_EXCELLENT:
            assessment = "Above fair value"
        elif value_ratio >= DRAFT_OFFER_VALUE_FAIR:
            assessment = "Approximately fair"
        else:
            assessment = "Below fair value"

        pick_descriptions = [
            f"Round {op['round']}" + (f" (#{op['pick_number']})" if op['pick_number'] else "")
            for op in offered_picks
        ]

        narrative = (
            f"The {ai_team_name} want to move up to #{current['pick_number_overall']}. "
            f"They're offering {', '.join(pick_descriptions)}."
        )

        offers.append({
            'offering_team_id': ai_team['id'],
            'offering_team_name': ai_team_name,
            'offer_type': 'trade_up',
            'assets_offered': offered_picks,
            'assets_requested': [{
                'round': round_num,
                'pick_number': current['pick_in_round'],
                'draft_state_id': pick_id,
            }],
            'value_assessment': assessment,
            'narrative': narrative,
        })

    return offers


def check_board_fall(
    prospect_id: int, pick_number: int, season_year: int,
    conn: sqlite3.Connection,
) -> Optional[dict]:
    """
    Check if a prospect has fallen significantly from their mock position.

    Args:
        prospect_id: Prospect to check.
        pick_number: Current pick number in the draft.
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Dict with fall info, or None if no significant fall.
    """
    mock_position = get_mock_draft_position(conn, prospect_id, season_year)
    if mock_position is None:
        return None

    picks_fallen = pick_number - mock_position
    if picks_fallen < DRAFT_BOARD_FALL_THRESHOLD:
        return None

    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        return None

    prospect_name = f"{prospect['first_name']} {prospect['last_name']}"

    # Check upcoming picks for teams with need at this position
    upcoming = get_upcoming_draft_picks(conn, season_year, 3)

    urgency_window = 0
    for pick in upcoming:
        need = _calculate_positional_need(
            pick['team_id'], prospect['position'], conn,
        )
        if need >= DRAFT_POSITIONAL_NEED_THRESHOLD:
            urgency_window += 1

    narrative = (
        f"{prospect_name} ({prospect['position']}) was mocked at "
        f"#{mock_position} but is still available at pick #{pick_number} "
        f"({picks_fallen} spots below projection)."
    )
    if urgency_window > 0:
        narrative += (
            f" {urgency_window} of the next 3 teams have significant "
            f"need at {prospect['position']}."
        )

    return {
        'prospect_id': prospect_id,
        'fall_detected': True,
        'picks_fallen': picks_fallen,
        'narrative': narrative,
        'urgency_window': urgency_window,
    }


def sign_rookie_contracts(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Sign rookie contracts for all players drafted by a team.

    Salary is calculated based on pick position using exponential decay
    from the top pick multiplier down to a floor.

    Args:
        team_id: Team whose rookies to sign.
        season_year: The draft year.
        conn: Database connection.

    Returns:
        List of signed contract dicts.
    """
    drafted = get_drafted_prospects_for_team(conn, team_id, season_year)
    if not drafted:
        return []

    # Get salary cap for base calculation
    league = get_league_state(conn)
    salary_cap = league['salary_cap'] if league else SALARY_CAP_YEAR_ONE
    base_salary = salary_cap // DRAFT_ROOKIE_SALARY_DIVISOR

    signed = []
    for prospect in drafted:
        player_id = prospect['player_id']
        if not player_id:
            continue

        overall_pick = prospect['draft_pick']  # pick_number_overall
        round_num = prospect['draft_round']

        # Calculate salary multiplier with decay
        multiplier = max(
            ROOKIE_SALARY_FLOOR_MULTIPLIER,
            ROOKIE_SALARY_TOP_PICK_MULTIPLIER * (
                ROOKIE_SALARY_SCALE_DECAY ** (overall_pick - 1)
            ),
        )
        aav = max(MIN_PLAYER_SALARY, int(base_salary * multiplier))

        years = ROOKIE_CONTRACT_YEARS.get(round_num, 4)
        guaranteed_years = ROOKIE_GUARANTEE_BY_ROUND.get(round_num, 1)
        guaranteed_money = aav * guaranteed_years

        # Signing bonus must leave enough base salary per year above minimum
        # after back-loaded escalation. Year 1 gets fraction of average base
        # with 5% escalation over 4 years, so we need extra headroom.
        min_base_pool_per_year = int(MIN_PLAYER_SALARY / DRAFT_ROOKIE_ESCALATION_FRACTION)
        max_signing_bonus = max(0, (aav - min_base_pool_per_year) * years)
        signing_bonus = min(aav // DRAFT_ROOKIE_BONUS_DIVISOR, max_signing_bonus)

        result = offer_contract(
            player_id=player_id,
            team_id=team_id,
            years=years,
            aav=aav,
            signing_bonus=signing_bonus,
            guaranteed_money=guaranteed_money,
            roster_bonuses=None,
            escalators=None,
            void_years=None,
            conn=conn,
            is_rookie_contract=True,
        )

        prospect_name = f"{prospect['first_name']} {prospect['last_name']}"
        cap_hit_y1 = (
            result['cap_hit_schedule'][0]['cap_hit']
            if result['cap_hit_schedule'] else aav
        )

        signed.append({
            'player_id': player_id,
            'name': prospect_name,
            'position': prospect['position'],
            'round': round_num,
            'pick': overall_pick,
            'years': years,
            'aav': aav,
            'total_value': aav * years,
            'cap_hit_year1': cap_hit_y1,
        })

    # Recalculate cap after all signings
    recalculate_cap_space(team_id, season_year, conn)

    return signed


def complete_draft(
    season_year: int, conn: sqlite3.Connection,
) -> dict:
    """
    Finalize the draft: verify all picks used, retire undrafted prospects.

    Args:
        season_year: The draft year.
        conn: Database connection.

    Returns:
        Dict with total_picks_made, undrafted_fa_pool_count,
        undrafted_retired_count.

    Raises:
        ValueError: If not all picks have been made.
    """
    order = get_draft_state_order(conn, season_year)
    used = [p for p in order if p['status'] == 'used']
    pending = [p for p in order if p['status'] == 'pending']

    if pending:
        raise ValueError(
            f"Draft incomplete: {len(pending)} picks remaining "
            f"(next: #{pending[0]['pick_number_overall']})."
        )

    # Retire undrafted prospects below FA pool threshold
    retired_count = retire_undrafted_prospects(season_year, conn)

    # Count undrafted prospects above threshold (FA pool)
    undrafted = get_undrafted_prospects(conn, season_year)
    fa_pool = [
        p for p in undrafted
        if p['true_overall'] >= PROSPECT_FA_POOL_MIN_OVR
    ]

    conn.commit()

    return {
        'total_picks_made': len(used),
        'undrafted_fa_pool_count': len(fa_pool),
        'undrafted_retired_count': retired_count,
    }
