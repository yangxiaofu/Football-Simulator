"""
Scouting report generation cycle (Phase 3B).

Handles multi-phase scouting reports, combine events, competitor intelligence,
and mock draft generation. Works with scouts.py for grade generation and
the query layer for persistence.
"""

import random
import sqlite3
from typing import Optional

from ..generation.players import weighted_random_choice
from ..utils.constants import (
    RATING_MAX,
    SCOUTING_PHASE_ACCURACY_BONUS,
    SCOUTING_PHASE_REPORT_WEEK,
    SCOUTING_PHASE_NOTES,
    SCOUTING_PHASE_GRADE_TREND_THRESHOLD,
    SCOUTING_PHASES_WITH_FLAG_DETECTION,
    SCOUT_DEFAULT_REGIONAL_COVERAGE,
    COMBINE_EVENT_WEIGHTS,
    COMBINE_INJURY_HISTORY_CONCERN_BOOST,
    COMBINE_BREAKOUT_EVAL_BONUS,
    COMBINE_UNDERWHELMING_EVAL_OVERRIDE,
    COMBINE_EVENT_NARRATIVES,
    MOCK_DRAFT_PICKS,
    MOCK_DRAFT_NOISE,
    MOCK_DRAFT_VOLATILITY_COUNT,
    MOCK_DRAFT_BREAKOUT_MOVE,
    MOCK_DRAFT_RED_FLAG_DROP,
    MOCK_DRAFT_NARRATIVES,
    INTEL_SIGNAL_TYPES,
    INTEL_ACCURACY_BY_COVERAGE,
    INTEL_SIGNAL_COUNT_RANGE,
    INTEL_NARRATIVES,
    INTEL_FALSE_NARRATIVES,
    to_letter_grade,
)
from ..db.queries import (
    get_assignments_for_team, get_prospect_by_id,
    get_all_prospects, get_all_teams,
    get_latest_scouted_overall,
    get_combine_event_for_prospect,
    insert_combine_event, insert_competitor_intel,
    insert_scouting_flag, insert_mock_draft_pick,
    clear_mock_draft_for_week, get_combine_events,
    update_scouted_rating_notes,
    get_draft_class_season_year,
    get_first_scout_assignment_for_prospect,
    get_team_head_scout,
)
from .scouts import generate_scouted_grade, generate_scouting_flags


def run_scouting_phase(
    team_id: int, season_year: int, phase: str,
    conn: sqlite3.Connection,
) -> dict:
    """
    Run a scouting phase for a team, generating graded reports for all assigned prospects.

    Phases progress: early → midseason → combine → predraft, each with increasing
    accuracy bonuses. During combine/predraft phases, flag detection is also re-run.

    Args:
        team_id: Team ID
        season_year: Season year
        phase: Phase name ('early', 'midseason', 'combine', 'predraft')
        conn: Database connection

    Returns:
        Dict with phase, prospects_updated, grade_changes, new_flags_surfaced
    """
    if phase not in SCOUTING_PHASE_ACCURACY_BONUS:
        raise ValueError(f"Invalid phase: {phase}. Must be one of {list(SCOUTING_PHASE_ACCURACY_BONUS.keys())}")

    assignments = get_assignments_for_team(conn, team_id, season_year)
    base_bonus = SCOUTING_PHASE_ACCURACY_BONUS[phase]
    report_week = SCOUTING_PHASE_REPORT_WEEK[phase]

    prospects_updated = 0
    grade_changes = 0
    new_flags_surfaced = 0

    for assignment in assignments:
        prospect_id = assignment['prospect_id']
        scout_id = assignment['scout_id']

        # Determine effective bonus (combine events can modify it)
        effective_bonus = base_bonus
        if phase == 'combine':
            event = get_combine_event_for_prospect(conn, prospect_id, season_year)
            if event:
                if event['event_type'] == 'breakout':
                    effective_bonus = COMBINE_BREAKOUT_EVAL_BONUS
                elif event['event_type'] == 'underwhelming':
                    effective_bonus = COMBINE_UNDERWHELMING_EVAL_OVERRIDE

        # Get previous grade for comparison
        prev_row = get_latest_scouted_overall(conn, prospect_id, team_id, season_year)
        prev_grade = prev_row['scout_grade'] if prev_row else None

        # Determine direction for notes
        direction = 'stable'
        # We'll determine direction after grading, but we need it for notes
        # Use a preliminary approach: generate grade first, then pick note
        result = generate_scouted_grade(
            prospect_id, scout_id, conn,
            talent_eval_bonus=effective_bonus,
            report_week=report_week,
            phase=phase,
            notes=None,  # will update after direction is known
        )

        # Determine direction based on grade change
        new_grade = result['display_grade']
        if prev_grade and new_grade != prev_grade:
            # Compare numeric values
            new_val = result['scouted_overall']
            prev_val = prev_row['estimated_value'] if prev_row else new_val
            diff = new_val - prev_val
            if diff >= SCOUTING_PHASE_GRADE_TREND_THRESHOLD:
                direction = 'improving'
            elif diff <= -SCOUTING_PHASE_GRADE_TREND_THRESHOLD:
                direction = 'declining'

        # Pick a note and update the record
        phase_notes = SCOUTING_PHASE_NOTES.get(phase, {})
        direction_notes = phase_notes.get(direction, [])
        note = random.choice(direction_notes) if direction_notes else None

        if note:
            # Update the just-inserted scouted_rating with the note
            update_scouted_rating_notes(
                conn, prospect_id, scout_id, season_year, phase, report_week, note
            )

        prospects_updated += 1

        # Track grade changes (moved at least 1 letter grade)
        if prev_grade and prev_grade != new_grade:
            grade_changes += 1

        # During combine/predraft, re-run flag detection
        if phase in SCOUTING_PHASES_WITH_FLAG_DETECTION:
            flags = generate_scouting_flags(prospect_id, scout_id, conn)
            new_flags_surfaced += len(flags)

    conn.commit()

    return {
        'phase': phase,
        'prospects_updated': prospects_updated,
        'grade_changes': grade_changes,
        'new_flags_surfaced': new_flags_surfaced,
    }


def generate_combine_event(
    prospect_id: int, conn: sqlite3.Connection,
) -> dict:
    """
    Generate a combine event for a prospect.

    Event types: breakout (8%), solid (63%), underwhelming (18%),
    red_flag_surfaces (5%), injury_concern (6%). Injury concern weight
    increases if prospect has injury history.

    Args:
        prospect_id: Prospect ID
        conn: Database connection

    Returns:
        Dict with prospect_id, event_type, narrative, grade_impact
    """
    prospect = get_prospect_by_id(conn, prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {prospect_id} not found")

    # Get season year
    season_year = get_draft_class_season_year(conn, prospect['draft_class_id']) or 0

    # Compute event weights
    weights = dict(COMBINE_EVENT_WEIGHTS)
    if prospect['has_injury_history']:
        weights['injury_concern'] += COMBINE_INJURY_HISTORY_CONCERN_BOOST
        weights['solid'] -= COMBINE_INJURY_HISTORY_CONCERN_BOOST

    # Pick event type
    event_type = weighted_random_choice(weights)

    # Grade impact
    grade_impact = 0
    if event_type == 'breakout':
        grade_impact = COMBINE_BREAKOUT_EVAL_BONUS
    elif event_type == 'underwhelming':
        grade_impact = -COMBINE_UNDERWHELMING_EVAL_OVERRIDE
    elif event_type == 'red_flag_surfaces':
        grade_impact = -10
    elif event_type == 'injury_concern':
        grade_impact = -5

    # Format narrative
    name = f"{prospect['first_name']} {prospect['last_name']}"
    narratives = COMBINE_EVENT_NARRATIVES.get(event_type, [])
    narrative_template = random.choice(narratives) if narratives else f"{name} had a combine event."
    narrative = narrative_template.format(name=name)

    # Insert into DB
    insert_combine_event(conn, prospect_id, season_year, event_type, narrative, grade_impact)

    # If red_flag_surfaces: insert a red scouting_flag (bypasses detection roll)
    if event_type == 'red_flag_surfaces':
        # Get any scout assigned to this prospect (for flag insertion)
        assignment = get_first_scout_assignment_for_prospect(conn, prospect_id, season_year)
        if assignment:
            insert_scouting_flag(
                conn, prospect_id, assignment['scout_id'],
                assignment['team_id'], season_year,
                'red', f"Combine red flag: {narrative}", 1,
                SCOUTING_PHASE_REPORT_WEEK['combine'],
            )

    conn.commit()

    return {
        'prospect_id': prospect_id,
        'event_type': event_type,
        'narrative': narrative,
        'grade_impact': grade_impact,
    }


def generate_competitor_intelligence(
    team_id: int, target_prospect_id: int, season_year: int,
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate competitor intelligence signals about a target prospect.

    Uses the user team's head scout coverage rating to determine signal
    accuracy. Generates 2-4 signals from random AI teams.

    Args:
        team_id: User's team ID (receiving intel)
        target_prospect_id: Prospect to gather intel about
        season_year: Season year
        conn: Database connection

    Returns:
        List of intel signal dicts with signal_type, team_name, prospect_name,
        narrative, is_accurate
    """
    prospect = get_prospect_by_id(conn, target_prospect_id)
    if not prospect:
        raise ValueError(f"Prospect {target_prospect_id} not found")

    # Get user's head scout for accuracy determination
    head_scout = get_team_head_scout(conn, team_id)

    coverage_rating = (head_scout['regional_coverage'] or SCOUT_DEFAULT_REGIONAL_COVERAGE) if head_scout else SCOUT_DEFAULT_REGIONAL_COVERAGE

    # Determine accuracy rate from coverage thresholds
    accuracy_rate = 0.40
    for threshold in sorted(INTEL_ACCURACY_BY_COVERAGE.keys(), reverse=True):
        if coverage_rating >= threshold:
            accuracy_rate = INTEL_ACCURACY_BY_COVERAGE[threshold]
            break

    # Get all AI teams (not user's team)
    all_teams = get_all_teams(conn)
    ai_teams = [t for t in all_teams if t['id'] != team_id]

    # Generate signals (2-4 per prospect)
    num_signals = random.randint(*INTEL_SIGNAL_COUNT_RANGE)
    signal_teams = random.sample(ai_teams, min(num_signals, len(ai_teams)))

    prospect_name = f"{prospect['first_name']} {prospect['last_name']}"
    college = prospect['college'] or "Unknown"

    signals = []
    for signal_team in signal_teams:
        is_accurate = 1 if random.random() < accuracy_rate else 0
        team_name = f"{signal_team['city']} {signal_team['nickname']}"

        if is_accurate:
            signal_type = random.choice(INTEL_SIGNAL_TYPES)
            narratives = INTEL_NARRATIVES.get(signal_type, [])
            template = random.choice(narratives) if narratives else "{team} showed interest in {name}."
        else:
            signal_type = random.choice(INTEL_SIGNAL_TYPES)
            template = random.choice(INTEL_FALSE_NARRATIVES)

        narrative = template.format(
            team=team_name, name=prospect_name, college=college,
        )

        insert_competitor_intel(
            conn, team_id, target_prospect_id, season_year,
            'predraft', signal_type, narrative, is_accurate,
        )

        signals.append({
            'signal_type': signal_type,
            'team_name': team_name,
            'prospect_name': prospect_name,
            'narrative': narrative,
            'is_accurate': bool(is_accurate),
        })

    conn.commit()
    return signals


def generate_mock_draft(
    season_year: int, week: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate a public mock draft for a given week.

    Applies noise to prospect ratings, adjusts for combine events,
    adds volatility, and assigns prospects to draft slots.

    Args:
        season_year: Season year
        week: Published week number
        conn: Database connection

    Returns:
        List of 32 mock pick dicts with pick_number, prospect_id, team_id, narrative
    """
    # Clear existing mock for this week
    clear_mock_draft_for_week(conn, season_year, week)

    # Get all prospects
    prospects = get_all_prospects(conn, season_year)
    if not prospects:
        return []

    # Build noisy grade list
    prospect_scores = []
    for p in prospects:
        noise = random.randint(-MOCK_DRAFT_NOISE, MOCK_DRAFT_NOISE)
        score = p['true_overall'] + noise
        prospect_scores.append({
            'prospect_id': p['id'],
            'score': score,
            'position': p['position'],
            'name': f"{p['first_name']} {p['last_name']}",
        })

    # Apply combine event adjustments
    combine_events = get_combine_events(conn, season_year)
    event_map = {e['prospect_id']: e for e in combine_events}
    for ps in prospect_scores:
        event = event_map.get(ps['prospect_id'])
        if event:
            if event['event_type'] == 'breakout':
                move_up = random.randint(*MOCK_DRAFT_BREAKOUT_MOVE)
                ps['score'] += move_up
            elif event['event_type'] in ('red_flag_surfaces', 'injury_concern'):
                drop = random.randint(*MOCK_DRAFT_RED_FLAG_DROP)
                ps['score'] -= drop

    # Sort by score descending
    prospect_scores.sort(key=lambda x: x['score'], reverse=True)

    # Apply volatility (random position swaps in top 32)
    volatility_count = random.randint(*MOCK_DRAFT_VOLATILITY_COUNT)
    top_n = min(MOCK_DRAFT_PICKS, len(prospect_scores))
    for _ in range(volatility_count):
        if top_n < 2:
            break
        i = random.randint(0, top_n - 1)
        j = random.randint(0, top_n - 1)
        prospect_scores[i], prospect_scores[j] = prospect_scores[j], prospect_scores[i]

    # Get draft order (first-round picks = 32 teams)
    all_teams = get_all_teams(conn)
    # Use waiver_priority as proxy for draft order (higher priority = earlier pick)
    teams_sorted = sorted(all_teams, key=lambda t: t['waiver_priority'])
    draft_order = teams_sorted[:MOCK_DRAFT_PICKS]

    # Assign picks
    mock_picks = []
    for pick_num in range(1, min(MOCK_DRAFT_PICKS + 1, len(prospect_scores) + 1)):
        if pick_num > len(draft_order):
            break

        team = draft_order[pick_num - 1]
        prospect_entry = prospect_scores[pick_num - 1]

        # Generate narrative
        team_name = f"{team['city']} {team['nickname']}"
        template = random.choice(MOCK_DRAFT_NARRATIVES)
        narrative = template.format(
            team=team_name,
            name=prospect_entry['name'],
            position=prospect_entry['position'],
        )

        insert_mock_draft_pick(
            conn, season_year, week, pick_num,
            prospect_entry['prospect_id'], team['id'], narrative,
        )

        mock_picks.append({
            'pick_number': pick_num,
            'prospect_id': prospect_entry['prospect_id'],
            'team_id': team['id'],
            'narrative': narrative,
        })

    conn.commit()
    return mock_picks
