"""
Contract management system for Football Simulator.

Handles contract creation, restructuring, release/dead cap, and market valuation.
All database access goes through src/db/queries.py — no raw SQL here.
All tuning constants come from src/utils/constants.py.
"""

import sqlite3
from typing import Optional

from ..db.cap import recalculate_cap_space
from ..db.queries import (
    get_active_contract,
    get_contract_years,
    get_contract_years_from_season,
    get_contract_year_for_season,
    get_league_state,
    get_player_for_contract,
    insert_contract,
    insert_contract_year,
    update_contract_status,
    update_contract_year_row,
    update_contract_signing_bonus,
    update_player_team,
    delete_contract_years_from_season,
    get_team_cap_space,
)
from ..db.transactions import log_transaction
from ..utils.constants import (
    MIN_CONTRACT_YEARS,
    MAX_CONTRACT_YEARS,
    VOID_YEAR_MAX,
    CONTRACT_SALARY_ESCALATION_RATE,
    RESTRUCTURE_MIN_REMAINING_YEARS,
    RESTRUCTURE_MAX_CONVERSION_PERCENT,
    POSITION_MARKET_MULTIPLIER,
    MARKET_VALUE_LOW_MULTIPLIER,
    MARKET_VALUE_PREMIUM_MULTIPLIER,
    MARKET_BASE_AAV,
    MARKET_RATING_EXPONENT,
    MARKET_RATING_BASELINE,
    MARKET_RATING_SCALE_FACTOR,
    MIN_PLAYER_SALARY,
    MAX_SIGNING_BONUS_PERCENT,
    MAX_GUARANTEED_PERCENT,
    MARKET_RATING_DIFFERENTIAL_EXPONENT,
    CONTRACT_ROUNDING_UNIT,
)


def calculate_cap_hit(
    player_id: int, season_year: int, conn: sqlite3.Connection,
) -> dict:
    """
    Calculate a player's cap hit breakdown for a given season.

    Read-only — no mutations.

    Returns:
        Dict with base_salary, prorated_bonus, roster_bonus, escalator_amount,
        total_cap_hit, contract_id, season_year. All zeros if no active contract.
    """
    zero_result = {
        'base_salary': 0,
        'prorated_bonus': 0,
        'roster_bonus': 0,
        'escalator_amount': 0,
        'total_cap_hit': 0,
        'contract_id': None,
        'season_year': season_year,
    }

    contract = get_active_contract(conn, player_id)
    if not contract:
        return zero_result

    year_row = get_contract_year_for_season(conn, contract['id'], season_year)
    if not year_row:
        return zero_result

    escalator_amt = (
        year_row['escalator_amount']
        if year_row['escalator_triggered']
        else 0
    )

    return {
        'base_salary': year_row['base_salary'],
        'prorated_bonus': year_row['prorated_bonus'],
        'roster_bonus': year_row['roster_bonus'],
        'escalator_amount': escalator_amt,
        'total_cap_hit': year_row['cap_hit'],
        'contract_id': contract['id'],
        'season_year': season_year,
    }


def calculate_dead_cap(
    player_id: int, release_year: int, conn: sqlite3.Connection,
) -> int:
    """
    Calculate dead cap if a player were released in the given year.

    Dead cap = sum of remaining prorated_bonus across all future contract years
    (from release_year onward). This matches NFL CBA rules where unearned
    prorated signing bonus accelerates into the release year.

    Read-only — no mutations.

    Returns:
        Dead cap amount in dollars (0 if no active contract).
    """
    contract = get_active_contract(conn, player_id)
    if not contract:
        return 0

    remaining_years = get_contract_years_from_season(
        conn, contract['id'], release_year,
    )
    if not remaining_years:
        return 0

    dead_cap = sum(row['prorated_bonus'] for row in remaining_years)
    return dead_cap


def offer_contract(
    player_id: int,
    team_id: int,
    years: int,
    aav: int,
    signing_bonus: int,
    guaranteed_money: int,
    roster_bonuses: Optional[dict[int, int]],
    escalators: Optional[list[dict]],
    void_years: Optional[int],
    conn: sqlite3.Connection,
    is_rookie_contract: bool = False,
) -> dict:
    """
    Create and sign a contract for a player.

    Args:
        player_id: Player to sign.
        team_id: Team offering the contract.
        years: Number of real playing years.
        aav: Average annual value (total_value = aav * years).
        signing_bonus: Upfront bonus prorated across all years (real + void).
        guaranteed_money: Total guaranteed dollars in the deal.
        roster_bonuses: {year_number: amount} mapping (1-indexed), or None.
        escalators: List of {'year': int, 'trigger': str, 'amount': int}, or None.
        void_years: Number of void years to append (0 or None = none).
        conn: Database connection.

    Returns:
        Dict with contract_id, total_value, cap_hit_schedule, new_cap_space.

    Raises:
        ValueError: On invalid inputs or insufficient cap space.
    """
    if void_years is None:
        void_years = 0
    if roster_bonuses is None:
        roster_bonuses = {}
    if escalators is None:
        escalators = []

    # --- Validation ---
    player = get_player_for_contract(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} does not exist")

    if years < MIN_CONTRACT_YEARS or years > MAX_CONTRACT_YEARS:
        raise ValueError(
            f"Contract years must be between {MIN_CONTRACT_YEARS} and "
            f"{MAX_CONTRACT_YEARS}, got {years}"
        )

    if void_years > VOID_YEAR_MAX:
        raise ValueError(
            f"Void years cannot exceed {VOID_YEAR_MAX}, got {void_years}"
        )

    total_proration_years = years + void_years
    if total_proration_years > MAX_CONTRACT_YEARS + VOID_YEAR_MAX:
        raise ValueError(
            f"Total years (real + void) cannot exceed "
            f"{MAX_CONTRACT_YEARS + VOID_YEAR_MAX}, got {total_proration_years}"
        )

    total_value = aav * years

    if signing_bonus > int(total_value * MAX_SIGNING_BONUS_PERCENT):
        raise ValueError(
            f"Signing bonus ${signing_bonus:,} exceeds "
            f"{int(MAX_SIGNING_BONUS_PERCENT * 100)}% of total value ${total_value:,}"
        )

    if guaranteed_money > int(total_value * MAX_GUARANTEED_PERCENT):
        raise ValueError(
            f"Guaranteed money ${guaranteed_money:,} exceeds "
            f"{int(MAX_GUARANTEED_PERCENT * 100)}% of total value ${total_value:,}"
        )

    # --- Calculate year-by-year structure ---
    prorated_per_year = signing_bonus // total_proration_years if total_proration_years > 0 else 0

    # Distribute base salary across real years (back-loaded with escalation)
    base_pool = total_value - signing_bonus
    # Calculate escalation weights: year 1 = 1.0, year 2 = 1.05, year 3 = 1.1025, etc.
    weights = []
    for i in range(years):
        weights.append((1 + CONTRACT_SALARY_ESCALATION_RATE) ** i)
    weight_sum = sum(weights)
    base_salaries = [int(base_pool * w / weight_sum) for w in weights]

    # Adjust rounding so total base adds up exactly to base_pool
    rounding_diff = base_pool - sum(base_salaries)
    if base_salaries:
        base_salaries[-1] += rounding_diff

    # Validate minimum salary per year
    for i, bs in enumerate(base_salaries):
        if bs < MIN_PLAYER_SALARY:
            raise ValueError(
                f"Year {i + 1} base salary ${bs:,} is below league minimum "
                f"${MIN_PLAYER_SALARY:,}"
            )

    # Get league state for season info
    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']

    # Build cap hit schedule
    cap_hit_schedule = []
    for i in range(years):
        rb = roster_bonuses.get(i + 1, 0)
        cap_hit = base_salaries[i] + prorated_per_year + rb
        cap_hit_schedule.append({
            'year_number': i + 1,
            'season_year': season_year + i,
            'base_salary': base_salaries[i],
            'prorated_bonus': prorated_per_year,
            'roster_bonus': rb,
            'cap_hit': cap_hit,
            'is_void_year': 0,
        })

    # Void years
    for i in range(void_years):
        cap_hit_schedule.append({
            'year_number': years + i + 1,
            'season_year': season_year + years + i,
            'base_salary': 0,
            'prorated_bonus': prorated_per_year,
            'roster_bonus': 0,
            'cap_hit': prorated_per_year,
            'is_void_year': 1,
        })

    # Calculate dead_cap_value for each year (sum of prorated bonus from that year onward)
    for idx in range(len(cap_hit_schedule)):
        dead_cap = sum(
            yr['prorated_bonus'] for yr in cap_hit_schedule[idx:]
        )
        cap_hit_schedule[idx]['dead_cap_value'] = dead_cap

    # Check cap space for year 1
    year_1_hit = cap_hit_schedule[0]['cap_hit']
    cap_space = get_team_cap_space(conn, team_id)
    if cap_space == 0:
        raise ValueError(f"Team {team_id} does not exist")
    if cap_space < year_1_hit:
        raise ValueError(
            f"Insufficient cap space: team has ${cap_space:,}, "
            f"year 1 cap hit is ${year_1_hit:,}"
        )

    # --- Write to database ---
    with conn:
        # Expire any existing active contract for this player
        existing = get_active_contract(conn, player_id)
        if existing:
            update_contract_status(conn, existing['id'], 'expired')

        # Insert contract
        contract_id = insert_contract(
            conn,
            player_id=player_id,
            team_id=team_id,
            status='active',
            total_years=years,
            total_value=total_value,
            signing_bonus=signing_bonus,
            guaranteed_money=guaranteed_money,
            aav=aav,
            signed_season=season_year,
            void_year=void_years if void_years > 0 else None,
            is_franchise_tag=0,
            is_rookie_contract=1 if is_rookie_contract else 0,
        )

        # Insert contract year rows
        for yr in cap_hit_schedule:
            # Find escalator for this year if any
            esc_trigger = None
            esc_amount = 0
            for esc in escalators:
                if esc['year'] == yr['year_number']:
                    esc_trigger = esc['trigger']
                    esc_amount = esc['amount']

            insert_contract_year(
                conn,
                contract_id=contract_id,
                season_year=yr['season_year'],
                base_salary=yr['base_salary'],
                prorated_bonus=yr['prorated_bonus'],
                roster_bonus=yr['roster_bonus'],
                cap_hit=yr['cap_hit'],
                dead_cap_value=yr['dead_cap_value'],
                is_void_year=yr['is_void_year'],
                escalator_trigger=esc_trigger,
                escalator_amount=esc_amount,
            )

        # Update player's team assignment (handles free agent signings)
        if player['team_id'] != team_id:
            update_player_team(conn, player_id, team_id, 'active')

        # Recalculate cap space
        new_cap_space = recalculate_cap_space(team_id, season_year, conn)

        # Log transaction
        player_name = f"{player['first_name']} {player['last_name']}"
        log_transaction(
            conn,
            season_year=season_year,
            week_number=league['current_week'],
            transaction_type='signed',
            team_id=team_id,
            player_id=player_id,
            description=(
                f"Signed {player['position']} {player_name} to a "
                f"{years}-year, ${total_value:,} contract"
            ),
            cap_impact=year_1_hit,
        )

    return {
        'contract_id': contract_id,
        'total_value': total_value,
        'cap_hit_schedule': cap_hit_schedule,
        'new_cap_space': new_cap_space,
    }


def restructure_contract(
    player_id: int,
    team_id: int,
    amount_to_convert: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    Restructure a player's contract by converting base salary to signing bonus.

    This reduces the current year's cap hit by spreading the converted amount
    across all remaining contract years as prorated bonus.

    Args:
        player_id: Player whose contract to restructure.
        team_id: Team that owns the contract (verified).
        amount_to_convert: Dollar amount of base salary to convert.
        conn: Database connection.

    Returns:
        Dict with cap_savings_current_year, new_cap_space, updated_schedule.

    Raises:
        ValueError: On invalid inputs or contract state.
    """
    contract = get_active_contract(conn, player_id)
    if not contract:
        raise ValueError(f"Player {player_id} has no active contract")
    if contract['team_id'] != team_id:
        raise ValueError(
            f"Contract belongs to team {contract['team_id']}, not {team_id}"
        )

    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")
    season_year = league['current_season']

    current_year_row = get_contract_year_for_season(
        conn, contract['id'], season_year,
    )
    if not current_year_row:
        raise ValueError(
            f"No contract year found for season {season_year}"
        )

    remaining_years = get_contract_years_from_season(
        conn, contract['id'], season_year,
    )
    if len(remaining_years) < RESTRUCTURE_MIN_REMAINING_YEARS:
        raise ValueError(
            f"Need at least {RESTRUCTURE_MIN_REMAINING_YEARS} remaining years "
            f"to restructure, have {len(remaining_years)}"
        )

    max_convertible = int(
        current_year_row['base_salary'] * RESTRUCTURE_MAX_CONVERSION_PERCENT
    )
    if amount_to_convert > max_convertible:
        raise ValueError(
            f"Can convert at most ${max_convertible:,} "
            f"({int(RESTRUCTURE_MAX_CONVERSION_PERCENT * 100)}% of "
            f"${current_year_row['base_salary']:,} base salary)"
        )
    if amount_to_convert > current_year_row['base_salary']:
        raise ValueError(
            f"Cannot convert ${amount_to_convert:,} — base salary is only "
            f"${current_year_row['base_salary']:,}"
        )

    # Calculate new proration spread across remaining years
    num_remaining = len(remaining_years)
    additional_proration_per_year = amount_to_convert // num_remaining

    old_cap_hit = current_year_row['cap_hit']
    updated_schedule = []

    with conn:
        for row in remaining_years:
            new_prorated = row['prorated_bonus'] + additional_proration_per_year
            if row['id'] == current_year_row['id']:
                # Current year: reduce base salary, increase prorated bonus
                new_base = row['base_salary'] - amount_to_convert
                new_cap_hit = new_base + new_prorated + row['roster_bonus']
            else:
                # Future years: only prorated bonus changes
                new_base = row['base_salary']
                new_cap_hit = new_base + new_prorated + row['roster_bonus']

            updated_schedule.append({
                'season_year': row['season_year'],
                'base_salary': new_base,
                'prorated_bonus': new_prorated,
                'cap_hit': new_cap_hit,
            })

            # Will update dead_cap after all rows are computed
            update_contract_year_row(
                conn, row['id'], new_base, new_prorated, new_cap_hit, 0,
            )

        # Recalculate dead_cap_value for each remaining year
        # dead_cap = sum of prorated_bonus from that year onward
        for idx, row in enumerate(remaining_years):
            dead_cap = sum(
                s['prorated_bonus'] for s in updated_schedule[idx:]
            )
            # Re-update with correct dead_cap
            s = updated_schedule[idx]
            update_contract_year_row(
                conn, row['id'], s['base_salary'], s['prorated_bonus'],
                s['cap_hit'], dead_cap,
            )
            updated_schedule[idx]['dead_cap_value'] = dead_cap

        # Update contract's signing_bonus total
        new_signing_bonus = contract['signing_bonus'] + amount_to_convert
        update_contract_signing_bonus(conn, contract['id'], new_signing_bonus)

        # Recalculate cap
        new_cap_space = recalculate_cap_space(team_id, season_year, conn)

        # Log transaction
        player = get_player_for_contract(conn, player_id)
        player_name = (
            f"{player['first_name']} {player['last_name']}"
            if player else f"Player {player_id}"
        )
        cap_savings = old_cap_hit - updated_schedule[0]['cap_hit']
        log_transaction(
            conn,
            season_year=season_year,
            week_number=league['current_week'],
            transaction_type='restructured',
            team_id=team_id,
            player_id=player_id,
            description=(
                f"Restructured {player_name}'s contract, converting "
                f"${amount_to_convert:,} base salary to bonus "
                f"(${cap_savings:,} cap savings)"
            ),
            cap_impact=-cap_savings,
        )

    return {
        'cap_savings_current_year': cap_savings,
        'new_cap_space': new_cap_space,
        'updated_schedule': updated_schedule,
    }


def release_player(
    player_id: int,
    team_id: int,
    season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    Release a player from a team, handling dead cap.

    The current year's contract_year is modified to reflect dead cap,
    future contract_year rows are deleted, and the contract stays 'active'
    through the current season so cap accounting picks it up. The player
    becomes a free agent.

    Args:
        player_id: Player to release.
        team_id: Team releasing the player (verified).
        season_year: Current season year.
        conn: Database connection.

    Returns:
        Dict with dead_cap, new_cap_space, player_name.

    Raises:
        ValueError: If player has no active contract or contract doesn't
                    belong to team.
    """
    contract = get_active_contract(conn, player_id)
    if not contract:
        raise ValueError(f"Player {player_id} has no active contract")
    if contract['team_id'] != team_id:
        raise ValueError(
            f"Contract belongs to team {contract['team_id']}, not {team_id}"
        )

    player = get_player_for_contract(conn, player_id)
    player_name = (
        f"{player['first_name']} {player['last_name']}"
        if player else f"Player {player_id}"
    )

    # Calculate dead cap before modifying anything
    dead_cap = calculate_dead_cap(player_id, season_year, conn)

    league = get_league_state(conn)
    if not league:
        raise ValueError("League not initialized")

    with conn:
        # Modify current year's contract_year to reflect dead cap charge
        current_year_row = get_contract_year_for_season(
            conn, contract['id'], season_year,
        )
        if current_year_row:
            update_contract_year_row(
                conn,
                current_year_row['id'],
                base_salary=0,
                prorated_bonus=dead_cap,
                cap_hit=dead_cap,
                dead_cap_value=dead_cap,
            )

        # Delete all future contract_year rows
        delete_contract_years_from_season(conn, contract['id'], season_year)

        # Set player as free agent
        update_player_team(conn, player_id, None, 'free_agent')

        # Recalculate cap (contract still 'active' with dead cap hit)
        new_cap_space = recalculate_cap_space(team_id, season_year, conn)

        # Now expire the contract (after cap recalculation picked up dead cap)
        update_contract_status(conn, contract['id'], 'expired')

        # Recalculate again without the expired contract
        # The dead cap was already accounted for in the transaction log
        new_cap_space = recalculate_cap_space(team_id, season_year, conn)

        # Log transaction
        log_transaction(
            conn,
            season_year=season_year,
            week_number=league['current_week'],
            transaction_type='released',
            team_id=team_id,
            player_id=player_id,
            description=(
                f"Released {player['position']} {player_name} "
                f"(${dead_cap:,} dead cap)"
            ),
            cap_impact=dead_cap,
        )

    return {
        'dead_cap': dead_cap,
        'new_cap_space': new_cap_space,
        'player_name': player_name,
    }


def get_market_value(
    player_id: int,
    position: Optional[str],
    conn: sqlite3.Connection,
) -> dict:
    """
    Estimate a player's market value based on overall rating and position.

    Read-only — no mutations. This is the only function that reads true_overall
    directly (justified because it drives contract valuation in the engine layer).

    Args:
        player_id: Player to evaluate.
        position: Position override (uses player's position if None).
        conn: Database connection.

    Returns:
        Dict with low, fair, premium AAV values, position, and overall.

    Raises:
        ValueError: If player not found.
    """
    player = get_player_for_contract(conn, player_id)
    if not player:
        raise ValueError(f"Player {player_id} does not exist")

    pos = position if position else player['position']
    overall = player['true_overall']

    pos_multiplier = POSITION_MARKET_MULTIPLIER.get(pos, 1.0)

    rating_diff = overall - MARKET_RATING_BASELINE
    if rating_diff > 0:
        rating_factor = (
            (rating_diff ** MARKET_RATING_EXPONENT) * MARKET_RATING_SCALE_FACTOR
        )
    else:
        rating_factor = -(
            (abs(rating_diff) ** MARKET_RATING_DIFFERENTIAL_EXPONENT) * MARKET_RATING_SCALE_FACTOR * 0.5
        )

    fair_aav = max(
        MIN_PLAYER_SALARY,
        int((MARKET_BASE_AAV + rating_factor) * pos_multiplier),
    )

    # Round to nearest unit for realism
    fair_aav = (fair_aav // CONTRACT_ROUNDING_UNIT) * CONTRACT_ROUNDING_UNIT
    fair_aav = max(MIN_PLAYER_SALARY, fair_aav)

    low = max(MIN_PLAYER_SALARY, int(fair_aav * MARKET_VALUE_LOW_MULTIPLIER))
    low = (low // CONTRACT_ROUNDING_UNIT) * CONTRACT_ROUNDING_UNIT
    low = max(MIN_PLAYER_SALARY, low)

    premium = int(fair_aav * MARKET_VALUE_PREMIUM_MULTIPLIER)
    premium = (premium // CONTRACT_ROUNDING_UNIT) * CONTRACT_ROUNDING_UNIT
    premium = max(MIN_PLAYER_SALARY, premium)

    return {
        'low': low,
        'fair': fair_aav,
        'premium': premium,
        'position': pos,
        'overall': overall,
    }
