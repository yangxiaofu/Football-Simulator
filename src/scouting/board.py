"""
Draft board management (Phase 3B).

Builds and maintains a ranked prospect list for a team based on scouted grades,
positional need, and character assessment. Provides UI-safe board entries and
post-draft accuracy review.
"""

import sqlite3
from typing import Optional

from ..utils.constants import (
    RATING_MIN, RATING_MAX,
    BOARD_WEIGHT_GRADE, BOARD_WEIGHT_NEED, BOARD_WEIGHT_CHARACTER,
    BOARD_CHARACTER_SCORE_NEUTRAL,
    SCOUTING_PHASE_GRADE_TREND_THRESHOLD,
    POSTDRAFT_ACCURATE_THRESHOLD, POSTDRAFT_CLOSE_THRESHOLD,
    to_letter_grade,
)
from ..db.queries import (
    get_all_prospects,
    get_latest_scouted_overall, get_all_scouted_overalls,
    get_scouting_flags_for_prospect,
    get_intel_for_team_prospect,
    upsert_draft_board_entry, get_draft_board,
    get_draft_board_entry, update_draft_board_override,
    get_drafted_prospects_for_team, get_prospect_by_id,
    get_roster_position_counts,
)
from ..utils.constants import FA_IDEAL_ROSTER


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
    return max(0, min(100, int((ideal - actual) / ideal * 100)))


def _calculate_phase_trend(ratings_rows: list) -> str:
    """
    Determine phase trend from earliest to latest scouted overall.

    Args:
        ratings_rows: List of scouted_rating rows ordered by report_week ASC

    Returns:
        'improving', 'declining', or 'stable'
    """
    if len(ratings_rows) < 2:
        return 'stable'

    earliest = ratings_rows[0]['estimated_value']
    latest = ratings_rows[-1]['estimated_value']
    diff = latest - earliest

    if diff >= SCOUTING_PHASE_GRADE_TREND_THRESHOLD:
        return 'improving'
    elif diff <= -SCOUTING_PHASE_GRADE_TREND_THRESHOLD:
        return 'declining'
    return 'stable'


def build_draft_board(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Build or rebuild the draft board for a team.

    Composite score = (scouted_overall * 0.70) + (need_score * 0.20)
                    + (character_score * 0.10)

    Character score is derived from the ratio of green flags to total flags,
    scaled 0-100. No flags = 50 (neutral).

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        List of UI-safe board entry dicts ordered by board_rank (1 = best)
    """
    prospects = get_all_prospects(conn, season_year)
    board_entries = []

    for prospect in prospects:
        prospect_id = prospect['id']

        # Get latest scouted overall for this team
        latest = get_latest_scouted_overall(conn, prospect_id, team_id, season_year)
        if not latest:
            continue  # Not scouted by this team — skip

        scouted_overall = latest['estimated_value']

        # Calculate positional need
        need_score = _calculate_positional_need(team_id, prospect['position'], conn)

        # Calculate character score from flags
        flags = get_scouting_flags_for_prospect(conn, prospect_id, team_id, season_year)
        if flags:
            green_count = sum(1 for f in flags if f['flag_type'] == 'green')
            total_count = len(flags)
            character_score = int((green_count / total_count) * 100)
        else:
            character_score = BOARD_CHARACTER_SCORE_NEUTRAL

        # Composite score
        composite = (
            scouted_overall * BOARD_WEIGHT_GRADE
            + need_score * BOARD_WEIGHT_NEED
            + character_score * BOARD_WEIGHT_CHARACTER
        )

        # Calculate phase trend
        all_ratings = get_all_scouted_overalls(conn, prospect_id, team_id, season_year)
        phase_trend = _calculate_phase_trend(all_ratings)

        board_entries.append({
            'prospect_id': prospect_id,
            'composite': composite,
            'phase_trend': phase_trend,
            'scouted_overall': scouted_overall,
            'need_score': need_score,
            'character_score': character_score,
            'name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'college': prospect['college'],
            'age': prospect['age'],
            'display_grade': latest['scout_grade'],
        })

    # Sort by composite descending
    board_entries.sort(key=lambda x: x['composite'], reverse=True)

    # Assign board ranks and upsert into DB
    result = []
    for rank, entry in enumerate(board_entries, 1):
        upsert_draft_board_entry(
            conn, team_id, entry['prospect_id'], season_year,
            rank, entry['phase_trend'],
        )

        # Build UI-safe dict (no true_overall, no accuracy_error)
        result.append({
            'prospect_id': entry['prospect_id'],
            'board_rank': rank,
            'name': entry['name'],
            'position': entry['position'],
            'college': entry['college'],
            'age': entry['age'],
            'display_grade': entry['display_grade'],
            'phase_trend': entry['phase_trend'],
            'need_score': entry['need_score'],
            'composite': round(entry['composite'], 2),
        })

    conn.commit()
    return result


def get_board_entry(
    prospect_id: int, team_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    Get a single UI-safe draft board entry with full enrichment.

    Includes prospect info, scouted grade, confidence range, flags,
    intel signals, and phase trend. Never exposes true_overall or
    accuracy_error.

    Args:
        prospect_id: Prospect ID
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        UI-safe dict with all board entry details

    Raises:
        ValueError: If prospect or board entry not found
    """
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} not found")

    board_row = get_draft_board_entry(conn, team_id, prospect_id, season_year)

    # Get latest scouted grade
    latest = get_latest_scouted_overall(conn, prospect_id, team_id, season_year)
    if latest:
        display_grade = latest['scout_grade']
        conf = latest['confidence_range']
        est = latest['estimated_value']
        conf_low = max(RATING_MIN, est - conf)
        conf_high = min(RATING_MAX, est + conf)
        confidence_range = f"{to_letter_grade(conf_low)} to {to_letter_grade(conf_high)}"
    else:
        display_grade = '??'
        confidence_range = None

    # Flags (UI-safe: no is_true_flag)
    flag_rows = get_scouting_flags_for_prospect(conn, prospect_id, team_id, season_year)
    flags = [
        {'flag_type': f['flag_type'], 'flag_text': f['flag_text']}
        for f in flag_rows
    ]

    # Intel signals
    intel_rows = get_intel_for_team_prospect(conn, team_id, prospect_id, season_year)
    intel = [
        {'signal_type': i['signal_type'], 'narrative': i['narrative']}
        for i in intel_rows
    ]

    # Phase trend
    if board_row:
        phase_trend = board_row['phase_trend']
        board_rank = board_row['board_override'] or board_row['board_rank']
        board_override = board_row['board_override']
    else:
        all_ratings = get_all_scouted_overalls(conn, prospect_id, team_id, season_year)
        phase_trend = _calculate_phase_trend(all_ratings)
        board_rank = None
        board_override = None

    # Need score
    need_score = _calculate_positional_need(team_id, prospect['position'], conn)

    entry = {
        'prospect_id': prospect_id,
        'name': f"{prospect['first_name']} {prospect['last_name']}",
        'position': prospect['position'],
        'college': prospect['college'],
        'age': prospect['age'],
        'board_rank': board_rank,
        'display_grade': display_grade,
        'confidence_range': confidence_range,
        'phase_trend': phase_trend,
        'flags': flags,
        'intel': intel,
        'need_score': need_score,
        'board_override': board_override,
    }

    # Safety assertion: never leak true ratings
    assert 'true_overall' not in entry
    assert 'accuracy_error' not in entry

    return entry


def update_board_rank(
    prospect_id: int, team_id: int, new_rank: int,
    season_year: int, conn: sqlite3.Connection,
) -> None:
    """
    Manually override a prospect's board position.

    Args:
        prospect_id: Prospect ID
        team_id: Team ID
        new_rank: New manual rank position
        season_year: Season year
        conn: Database connection
    """
    update_draft_board_override(conn, team_id, prospect_id, season_year, new_rank)
    conn.commit()


def run_postdraft_review(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Run post-draft accuracy review for all prospects drafted by a team.

    Compares scouted grades to true ratings and categorizes accuracy.
    This is the first time the player sees how close their scouting was,
    presented as grade comparison narrative (not raw numbers).

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        List of review entry dicts with accuracy assessment
    """
    drafted = get_drafted_prospects_for_team(conn, team_id, season_year)
    reviews = []

    for prospect in drafted:
        prospect_id = prospect['id']
        true_overall = prospect['true_overall']

        # Get team's latest scouted overall
        latest = get_latest_scouted_overall(conn, prospect_id, team_id, season_year)
        if not latest:
            continue

        scouted_overall = latest['estimated_value']
        error = abs(scouted_overall - true_overall)

        # Determine accuracy label
        if error <= POSTDRAFT_ACCURATE_THRESHOLD:
            accuracy_label = "accurate"
        elif error <= POSTDRAFT_CLOSE_THRESHOLD:
            accuracy_label = "close"
        else:
            accuracy_label = "miss"

        # Generate narrative using letter grades
        scouted_grade = to_letter_grade(scouted_overall)
        true_grade = to_letter_grade(true_overall)

        if scouted_grade == true_grade:
            narrative = f"We had him at {scouted_grade}. Camp confirms — spot on."
        elif error <= POSTDRAFT_ACCURATE_THRESHOLD:
            narrative = f"We had him at {scouted_grade}. Camp suggests he's right in that range."
        else:
            narrative = f"We had him at {scouted_grade}. Camp suggests he's more of a {true_grade}."

        # Check flags
        flags = get_scouting_flags_for_prospect(conn, prospect_id, team_id, season_year)
        flag_assessment = []
        for f in flags:
            if f['is_true_flag']:
                flag_assessment.append({
                    'flag_text': f['flag_text'],
                    'result': 'confirmed',
                })
            else:
                flag_assessment.append({
                    'flag_text': f['flag_text'],
                    'result': 'false_alarm',
                })

        reviews.append({
            'prospect_id': prospect_id,
            'name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'draft_round': prospect['draft_round'],
            'draft_pick': prospect['draft_pick'],
            'scouted_grade': scouted_grade,
            'true_grade': true_grade,
            'accuracy_label': accuracy_label,
            'narrative': narrative,
            'flag_assessment': flag_assessment,
        })

    return reviews
