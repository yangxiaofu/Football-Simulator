"""
Scout assignment and evaluation for the scouting system (Phase 3).

Handles scout capacity, prospect evaluation with accuracy tiers,
and flag detection/false-positive mechanics. UI-safe functions never
expose true ratings or accuracy errors.
"""

import random
import sqlite3
from typing import Optional

from ..utils.constants import (
    RATING_MIN, RATING_MAX,
    SCOUT_CAPACITY_DIVISOR,
    SCOUT_OVERCAPACITY_PENALTY,
    SCOUT_ACCURACY_ELITE_THRESHOLD,
    SCOUT_ACCURACY_GOOD_THRESHOLD,
    SCOUT_ACCURACY_AVERAGE_THRESHOLD,
    SCOUT_ACCURACY_RANGES,
    SCOUT_FLAG_DETECT_RATES,
    SCOUT_FALSE_POSITIVE_RATES,
    PROSPECT_INJURY_DESCRIPTIONS,
    PROSPECT_CHARACTER_DESCRIPTIONS,
    PROSPECT_GREEN_FLAG_DESCRIPTIONS,
    SCOUT_DEFAULT_TALENT_EVALUATION,
    SCOUT_DEFAULT_REGIONAL_COVERAGE,
    SCOUT_DEFAULT_MEDICAL_EYE,
    SCOUT_DEFAULT_CHARACTER_READ,
    SCOUT_RED_FLAG_CHARACTER_KEYWORDS,
    to_letter_grade,
)
from ..db.queries import (
    get_team_scouts, get_prospect_by_id,
    insert_scouting_assignment, get_assignments_for_team,
    count_assignments_for_scout,
    insert_scouted_rating, get_scouted_ratings_for_prospect,
    insert_scouting_flag, get_scouting_flags_for_prospect,
    get_scout_by_id, get_draft_class_season_year,
    count_scouts_assigned_to_prospect,
)


def _get_accuracy_tier(talent_eval: int) -> str:
    """
    Determine accuracy tier based on scout's talent_evaluation rating.

    Args:
        talent_eval: Scout's talent_evaluation attribute (1-99)

    Returns:
        Tier string: 'elite', 'good', 'average', or 'poor'
    """
    if talent_eval >= SCOUT_ACCURACY_ELITE_THRESHOLD:
        return 'elite'
    elif talent_eval >= SCOUT_ACCURACY_GOOD_THRESHOLD:
        return 'good'
    elif talent_eval >= SCOUT_ACCURACY_AVERAGE_THRESHOLD:
        return 'average'
    else:
        return 'poor'


def _get_detection_rate(rating: int, rate_table: dict) -> float:
    """
    Walk threshold table (descending) to find matching probability.

    Args:
        rating: Scout's relevant attribute (medical_eye or character_read)
        rate_table: Dict of {threshold: probability}, walked high-to-low

    Returns:
        Probability (0-1) matching the highest threshold ≤ rating
    """
    for threshold in sorted(rate_table.keys(), reverse=True):
        if rating >= threshold:
            return rate_table[threshold]
    # Fallback (should never reach here with 0 in table)
    return rate_table[min(rate_table.keys())]


def get_scouting_department(
    team_id: int, conn: sqlite3.Connection,
) -> dict:
    """
    Get a team's scouting department overview.

    Args:
        team_id: Team ID
        conn: Database connection

    Returns:
        Dict with head_scout, regional_scouts, fa_scout, scouts (flat list),
        total_capacity, department_rating
    """
    rows = get_team_scouts(conn, team_id)
    scouts = [dict(row) for row in rows]

    head_scout = None
    regional_scouts = []
    fa_scout = None

    for s in scouts:
        if s['role'] == 'head_scout':
            head_scout = s
        elif s['role'] == 'regional_scout':
            regional_scouts.append(s)
        elif s['role'] == 'fa_scout':
            fa_scout = s

    # Total capacity: sum of regional_coverage // SCOUT_CAPACITY_DIVISOR for all scouts
    total_capacity = sum(
        (s.get('regional_coverage') or 0) // SCOUT_CAPACITY_DIVISOR
        for s in scouts if s.get('regional_coverage')
    )

    # Department rating: average talent_evaluation across all scouts
    eval_ratings = [
        s['talent_evaluation'] for s in scouts
        if s.get('talent_evaluation') is not None
    ]
    department_rating = (
        sum(eval_ratings) // len(eval_ratings) if eval_ratings else 0
    )

    return {
        'head_scout': head_scout,
        'regional_scouts': regional_scouts,
        'fa_scout': fa_scout,
        'scouts': scouts,
        'total_capacity': total_capacity,
        'department_rating': department_rating,
    }


def assign_scout(
    scout_id: int, prospect_ids: list[int],
    season_year: int, conn: sqlite3.Connection,
) -> dict:
    """
    Assign a scout to one or more prospects.

    Args:
        scout_id: Staff ID of the scout
        prospect_ids: List of prospect IDs to assign
        season_year: Season year
        conn: Database connection

    Returns:
        Dict with assigned count, over_capacity flag, current_count,
        capacity, and effective_talent_eval
    """
    # Get scout info
    scout = get_scout_by_id(conn, scout_id)
    if not scout:
        raise ValueError(f"Scout {scout_id} not found")

    regional_coverage = scout['regional_coverage'] or SCOUT_DEFAULT_REGIONAL_COVERAGE
    capacity = regional_coverage // SCOUT_CAPACITY_DIVISOR
    talent_eval = scout['talent_evaluation'] or SCOUT_DEFAULT_TALENT_EVALUATION

    # Current assignment count
    current_count = count_assignments_for_scout(conn, scout_id, season_year)

    # Insert assignments
    assigned = 0
    for pid in prospect_ids:
        insert_scouting_assignment(conn, scout_id, pid, season_year, 1)
        assigned += 1

    new_count = current_count + assigned
    over_capacity = new_count > capacity

    # Effective talent evaluation (degraded if over capacity)
    if over_capacity:
        effective_talent_eval = int(talent_eval / SCOUT_OVERCAPACITY_PENALTY)
    else:
        effective_talent_eval = talent_eval

    conn.commit()

    return {
        'assigned': assigned,
        'over_capacity': over_capacity,
        'current_count': new_count,
        'capacity': capacity,
        'effective_talent_eval': effective_talent_eval,
    }


def get_assignments(
    team_id: int, season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Get all scouting assignments for a team in a season.

    Args:
        team_id: Team ID
        season_year: Season year
        conn: Database connection

    Returns:
        List of assignment dicts
    """
    rows = get_assignments_for_team(conn, team_id, season_year)
    return [dict(row) for row in rows]


def generate_scouted_grade(
    prospect_id: int, scout_id: int, conn: sqlite3.Connection,
    talent_eval_bonus: int = 0,
    report_week: int = 1,
    phase: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Generate a scouted overall grade for a prospect.

    Core accuracy engine per GDD Section 13.3:
    - Determines accuracy tier from scout's talent_evaluation
    - Applies overcapacity penalty if scout is overloaded
    - Samples error within tier range, applies randomly ±
    - Returns scouted grade with confidence range

    ⚠️ IMPORTANT: This function returns true_overall and accuracy_error
    for internal simulation/logging use. UI display functions MUST
    strip these fields before rendering. Use get_scouted_prospect()
    for UI-safe views.

    Args:
        prospect_id: Prospect ID
        scout_id: Staff ID of the scout
        conn: Database connection
        talent_eval_bonus: Additional bonus to talent_evaluation (phase accuracy)
        report_week: Week number for this scouting report
        phase: Scouting phase name ('early', 'midseason', 'combine', 'predraft')
        notes: Phase-specific narrative note

    Returns:
        Dict with scouted_overall, display_grade, confidence_range,
        AND internal fields (true_overall, accuracy_error) that must
        be filtered before UI display.
    """
    # Get prospect's true overall
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} not found")
    true_overall = prospect['true_overall']

    # Get scout info
    scout = get_scout_by_id(conn, scout_id)
    if not scout:
        raise ValueError(f"Scout {scout_id} not found")

    talent_eval = min(RATING_MAX, (scout['talent_evaluation'] or SCOUT_DEFAULT_TALENT_EVALUATION) + talent_eval_bonus)

    # Get season year from draft class
    season_year = get_draft_class_season_year(conn, prospect['draft_class_id']) or 0

    # Check overcapacity
    current_count = count_assignments_for_scout(conn, scout_id, season_year)
    regional_coverage = scout['regional_coverage'] or SCOUT_DEFAULT_REGIONAL_COVERAGE
    capacity = regional_coverage // SCOUT_CAPACITY_DIVISOR
    over_capacity = current_count > capacity

    # Determine accuracy tier
    effective_eval = talent_eval
    if over_capacity:
        effective_eval = int(talent_eval / SCOUT_OVERCAPACITY_PENALTY)

    tier = _get_accuracy_tier(effective_eval)
    error_min, error_max = SCOUT_ACCURACY_RANGES[tier]

    # Apply overcapacity penalty to widen range
    if over_capacity:
        error_max = int(error_max * SCOUT_OVERCAPACITY_PENALTY)

    # Sample error
    direction = random.choice([-1, 1])
    error = direction * random.randint(error_min, error_max)
    scouted_overall = max(RATING_MIN, min(RATING_MAX, true_overall + error))

    # Confidence range (same as accuracy range for this tier)
    confidence = error_max

    # Convert to letter grades
    display_grade = to_letter_grade(scouted_overall)
    conf_low = max(RATING_MIN, scouted_overall - confidence)
    conf_high = min(RATING_MAX, scouted_overall + confidence)
    confidence_range_str = f"{to_letter_grade(conf_low)} to {to_letter_grade(conf_high)}"

    # Insert scouted_rating row
    insert_scouted_rating(
        conn, prospect_id, scout_id, season_year,
        'true_overall', scouted_overall, confidence,
        display_grade, report_week,
        phase=phase, notes=notes,
    )
    conn.commit()

    return {
        'prospect_id': prospect_id,
        'scout_id': scout_id,
        'scouted_overall': scouted_overall,
        'true_overall': true_overall,
        'display_grade': display_grade,
        'confidence_range': confidence_range_str,
        'accuracy_error': error,
        'report_week': report_week,
        'phase': phase,
        'notes': notes,
    }


def generate_scouting_flags(
    prospect_id: int, scout_id: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate flag discoveries for a prospect based on scout abilities.

    For each true flag category (injury, character), the scout rolls
    detection based on medical_eye/character_read. For absent categories,
    there's a false positive chance.

    Args:
        prospect_id: Prospect ID
        scout_id: Staff ID of the scout
        conn: Database connection

    Returns:
        List of discovered flag dicts (may include false positives)
    """
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} not found")

    scout = get_scout_by_id(conn, scout_id)
    if not scout:
        raise ValueError(f"Scout {scout_id} not found")

    team_id = scout['team_id']
    medical_eye = scout['medical_eye'] or SCOUT_DEFAULT_MEDICAL_EYE
    character_read = scout['character_read'] or SCOUT_DEFAULT_CHARACTER_READ

    # Get season year
    season_year = get_draft_class_season_year(conn, prospect['draft_class_id']) or 0

    flags = []
    report_week = 1

    # --- Injury flags ---
    if prospect['has_injury_history']:
        detect_rate = _get_detection_rate(medical_eye, SCOUT_FLAG_DETECT_RATES)
        if random.random() < detect_rate:
            flag_text = prospect['injury_history_desc'] or "Injury history detected"
            flag_id = insert_scouting_flag(
                conn, prospect_id, scout_id, team_id, season_year,
                'red', flag_text, 1, report_week,
            )
            flags.append({
                'id': flag_id, 'flag_type': 'red', 'flag_text': flag_text,
                'is_true_flag': True,
            })
    else:
        # False positive check for injury
        fp_rate = _get_detection_rate(medical_eye, SCOUT_FALSE_POSITIVE_RATES)
        if random.random() < fp_rate:
            flag_text = random.choice(PROSPECT_INJURY_DESCRIPTIONS)
            flag_id = insert_scouting_flag(
                conn, prospect_id, scout_id, team_id, season_year,
                'caution', flag_text, 0, report_week,
            )
            flags.append({
                'id': flag_id, 'flag_type': 'caution', 'flag_text': flag_text,
                'is_true_flag': False,
            })

    # --- Character flags ---
    if prospect['has_character_flag']:
        detect_rate = _get_detection_rate(character_read, SCOUT_FLAG_DETECT_RATES)
        if random.random() < detect_rate:
            flag_text = prospect['character_flag_desc'] or "Character concern detected"
            # Severity: some descriptions are worse than others
            flag_type = 'red' if any(
                kw in flag_text.lower() for kw in SCOUT_RED_FLAG_CHARACTER_KEYWORDS
            ) else 'caution'
            flag_id = insert_scouting_flag(
                conn, prospect_id, scout_id, team_id, season_year,
                flag_type, flag_text, 1, report_week,
            )
            flags.append({
                'id': flag_id, 'flag_type': flag_type, 'flag_text': flag_text,
                'is_true_flag': True,
            })
    else:
        # False positive check for character
        fp_rate = _get_detection_rate(character_read, SCOUT_FALSE_POSITIVE_RATES)
        if random.random() < fp_rate:
            flag_text = random.choice(PROSPECT_CHARACTER_DESCRIPTIONS)
            flag_id = insert_scouting_flag(
                conn, prospect_id, scout_id, team_id, season_year,
                'caution', flag_text, 0, report_week,
            )
            flags.append({
                'id': flag_id, 'flag_type': 'caution', 'flag_text': flag_text,
                'is_true_flag': False,
            })

    conn.commit()
    return flags


def get_scouted_prospect(
    prospect_id: int, team_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> dict:
    """
    UI-safe prospect view for a team. Never returns true_overall,
    true_ceiling, accuracy_error, or hidden flags.

    Args:
        prospect_id: Prospect ID
        team_id: Team ID requesting the view
        season_year: Season year
        conn: Database connection

    Returns:
        Dict with prospect_id, name, position, college, college_conference,
        age, is_scouted, display_grade, confidence_range, flags, combine,
        scouts_assigned
    """
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} not found")

    # Base info (safe to expose)
    result = {
        'prospect_id': prospect_id,
        'name': f"{prospect['first_name']} {prospect['last_name']}",
        'position': prospect['position'],
        'college': prospect['college'],
        'college_conference': prospect['college_conference'],
        'age': prospect['age'],
    }

    # Scouted ratings for this team
    scouted_rows = get_scouted_ratings_for_prospect(
        conn, prospect_id, team_id, season_year,
    )
    if scouted_rows:
        # Find latest true_overall scouted rating
        overall_row = None
        for row in scouted_rows:
            if row['attribute_name'] == 'true_overall':
                overall_row = row
                break
        if overall_row:
            result['is_scouted'] = True
            result['display_grade'] = overall_row['scout_grade']
            conf = overall_row['confidence_range']
            est = overall_row['estimated_value']
            conf_low = max(RATING_MIN, est - conf)
            conf_high = min(RATING_MAX, est + conf)
            result['confidence_range'] = (
                f"{to_letter_grade(conf_low)} to {to_letter_grade(conf_high)}"
            )
        else:
            result['is_scouted'] = False
            result['display_grade'] = '??'
            result['confidence_range'] = None
    else:
        result['is_scouted'] = False
        result['display_grade'] = '??'
        result['confidence_range'] = None

    # Flags discovered by this team
    flag_rows = get_scouting_flags_for_prospect(
        conn, prospect_id, team_id, season_year,
    )
    result['flags'] = [
        {'flag_type': f['flag_type'], 'flag_text': f['flag_text']}
        for f in flag_rows
    ]

    # Combine data (public info if attended)
    if prospect['combine_attended']:
        result['combine'] = {
            'forty': prospect['combine_forty'],
            'bench': prospect['combine_bench'],
            'vertical': prospect['combine_vertical'],
            'wonderlic': prospect['combine_wonderlic'],
        }
    else:
        result['combine'] = None

    # Count scouts assigned from this team
    result['scouts_assigned'] = count_scouts_assigned_to_prospect(
        conn, prospect_id, team_id, season_year
    )

    return result
