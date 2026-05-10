"""
Job offer generation and acceptance for vacant player coaches.

When a player coach is fired, they enter a vacancy state. This module generates
1-3 job offers based on their legacy score, then handles offer acceptance.
"""

import sqlite3
import random
from typing import Optional

from ..db.queries import (
    insert_coach_job_offer,
    get_pending_offers_for_coach,
    accept_offer,
    decline_offer,
    decline_all_other_offers,
    compute_legacy_quartile,
    get_team_basic_info,
    get_recent_win_pct,
    get_all_teams_ordered,
)
from ..utils.constants import (
    VACANCY_OFFER_WINDOW_WEEKS,
    VACANCY_MIN_OFFERS,
    VACANCY_MAX_OFFERS,
    OFFER_QUALITY_TIERS,
    OFFER_QUALITY_THRESHOLDS,
    OFFER_COUNT_BY_LEGACY_QUARTILE,
)


def generate_offers_for_vacant_coach(
    conn: sqlite3.Connection, coach_id: int, season_year: int, current_week: int,
) -> None:
    """Create 1-3 offers for a vacant player coach based on legacy quartile.

    Args:
        conn: Database connection
        coach_id: Coach in vacancy state
        season_year: Current season
        current_week: Week offers are generated (typically 0 = offseason)
    """
    # Determine number of offers based on legacy quartile
    quartile = compute_legacy_quartile(conn, coach_id)
    num_offers = OFFER_COUNT_BY_LEGACY_QUARTILE.get(quartile, 1)

    # Get all teams and score them
    teams = get_all_teams_ordered(conn)
    team_scores = []

    for team in teams:
        quality = compute_offer_quality(conn, team['id'])
        # Convert quality to numeric score for sorting
        quality_rank = {'elite': 4, 'good': 3, 'average': 2, 'struggling': 1}.get(quality, 1)
        team_scores.append({
            'team_id': team['id'],
            'quality': quality,
            'quality_rank': quality_rank,
        })

    # Sort by quality descending
    team_scores.sort(key=lambda x: x['quality_rank'], reverse=True)

    # Take top N teams and create offers
    for i in range(min(num_offers, len(team_scores))):
        team_data = team_scores[i]
        insert_coach_job_offer(
            conn, coach_id, team_data['team_id'],
            season_year, current_week, team_data['quality'],
        )


def compute_offer_quality(conn: sqlite3.Connection, team_id: int) -> str:
    """Classify team as elite/good/average/struggling based on cap + W%.

    Args:
        conn: Database connection
        team_id: Team to evaluate

    Returns:
        'elite'|'good'|'average'|'struggling'
    """
    team_info = get_team_basic_info(conn, team_id)
    if not team_info:
        return 'struggling'

    cap_space = team_info['cap_space']
    wpct = get_recent_win_pct(conn, team_id, n_seasons=2)

    # Check elite tier
    elite_thresholds = OFFER_QUALITY_THRESHOLDS['elite']
    if cap_space >= elite_thresholds['cap_min'] and wpct >= elite_thresholds['wpct_min']:
        return 'elite'

    # Check good tier
    good_thresholds = OFFER_QUALITY_THRESHOLDS['good']
    if cap_space >= good_thresholds['cap_min'] and wpct >= good_thresholds['wpct_min']:
        return 'good'

    # Check average tier
    average_thresholds = OFFER_QUALITY_THRESHOLDS['average']
    if cap_space >= average_thresholds['cap_min'] and wpct >= average_thresholds['wpct_min']:
        return 'average'

    return 'struggling'


def accept_offer_action(
    conn: sqlite3.Connection, offer_id: int, season_year: int,
) -> None:
    """Mark offer as accepted, decline others, assign coach to team.

    Args:
        conn: Database connection
        offer_id: Offer to accept
        season_year: Current season
    """
    from ..transactions.coaching import assign_coach_to_team

    # Get offer details
    offer_row = conn.execute(
        "SELECT coach_id, team_id FROM coach_job_offer WHERE id = ?",
        (offer_id,),
    ).fetchone()

    if not offer_row:
        return

    coach_id = offer_row['coach_id']
    team_id = offer_row['team_id']

    # Mark accepted
    accept_offer(conn, offer_id)

    # Decline all other pending offers
    decline_all_other_offers(conn, coach_id, season_year, except_id=offer_id)

    # Assign coach to team
    assign_coach_to_team(conn, coach_id, team_id, season_year)


def auto_accept_best_offer(
    conn: sqlite3.Connection, coach_id: int, season_year: int,
) -> None:
    """Auto-accept the best pending offer for a coach (stress harness).

    Selects the offer with the highest quality tier. If multiple offers
    have the same quality, picks randomly.

    Args:
        conn: Database connection
        coach_id: Coach with pending offers
        season_year: Current season
    """
    offers = get_pending_offers_for_coach(conn, coach_id, season_year)
    if not offers:
        return

    # Group by quality tier
    quality_order = ['elite', 'good', 'average', 'struggling']
    best_offers = []
    best_quality_rank = -1

    for offer in offers:
        quality = offer['offer_quality_tier']
        rank = quality_order.index(quality) if quality in quality_order else 999
        if best_quality_rank == -1 or rank < best_quality_rank:
            best_quality_rank = rank
            best_offers = [offer]
        elif rank == best_quality_rank:
            best_offers.append(offer)

    # Pick randomly from tied best offers
    chosen = random.choice(best_offers)
    accept_offer_action(conn, chosen['id'], season_year)
