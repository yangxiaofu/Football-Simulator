"""
Draft class generation for the scouting system (Phase 3).

Generates 300-400 prospects per draft class with position-specific attributes,
combine measurements, and hidden flags. Uses the same attribute generation
as active players to ensure clean transfer upon drafting.
"""

import random
import sqlite3
from typing import Optional

from ..generation.players import (
    generate_player_attributes, generate_rating, weighted_random_choice,
)
from ..generation.names import generate_player_name, generate_college
from ..utils.constants import (
    RATING_MIN, RATING_MAX,
    DEVELOPMENT_TRAIT_WEIGHTS,
    DRAFT_CLASS_SIZE_RANGE,
    DRAFT_CLASS_STRENGTH_WEIGHTS,
    DRAFT_CLASS_POSITION_COUNTS,
    DRAFT_CLASS_OVERALL_BY_STRENGTH,
    DRAFT_CLASS_NOTES,
    PROSPECT_INJURY_HISTORY_RATE,
    PROSPECT_CHARACTER_FLAG_RATE,
    PROSPECT_AGE_RANGE,
    PROSPECT_FA_POOL_MIN_OVR,
    PROSPECT_INJURY_DESCRIPTIONS,
    PROSPECT_CHARACTER_DESCRIPTIONS,
    COLLEGE_TO_CONFERENCE,
    COMBINE_FORTY_RANGES,
    COMBINE_BENCH_RANGES,
    COMBINE_VERTICAL_RANGES,
    COMBINE_WONDERLIC_RANGE,
    COMBINE_ATTENDANCE_RATE,
)
from ..db.queries import (
    insert_draft_class, get_draft_class_by_year,
    insert_prospect, get_all_prospects,
    get_prospect_by_id, get_undrafted_prospects,
)


def _generate_prospect(
    draft_class_id: int, position: str, class_strength: str,
    conn: sqlite3.Connection,
) -> dict:
    """
    Generate a single prospect and insert into the database.

    Args:
        draft_class_id: FK to draft_class table
        position: Player position
        class_strength: Draft class strength tier
        conn: Database connection

    Returns:
        Dict with all prospect fields including 'id' from DB insert
    """
    # Name and college
    first_name, last_name = generate_player_name()
    college = generate_college()
    college_conference = COLLEGE_TO_CONFERENCE.get(college, "Independent")

    # Age
    age = random.randint(*PROSPECT_AGE_RANGE)

    # Overall rating based on class strength
    mean, std = DRAFT_CLASS_OVERALL_BY_STRENGTH[class_strength]
    true_overall = generate_rating(mean, std)

    # Development trait and ceiling (same formula as players.py)
    development_trait = weighted_random_choice(DEVELOPMENT_TRAIT_WEIGHTS)
    if development_trait == 'superstar':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(15, 25))
    elif development_trait == 'star':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(8, 15))
    elif development_trait == 'normal':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(3, 8))
    else:  # slow
        true_ceiling = min(RATING_MAX, true_overall + random.randint(0, 3))

    # Position-specific attributes (reused directly from player generation)
    attrs = generate_player_attributes(position, true_overall)

    # Flags
    has_injury_history = 1 if random.random() < PROSPECT_INJURY_HISTORY_RATE else 0
    injury_history_desc = (
        random.choice(PROSPECT_INJURY_DESCRIPTIONS) if has_injury_history else None
    )
    has_character_flag = 1 if random.random() < PROSPECT_CHARACTER_FLAG_RATE else 0
    character_flag_desc = (
        random.choice(PROSPECT_CHARACTER_DESCRIPTIONS) if has_character_flag else None
    )

    # Combine
    combine_attended = 1 if random.random() < COMBINE_ATTENDANCE_RATE else 0
    if combine_attended:
        forty_lo, forty_hi = COMBINE_FORTY_RANGES[position]
        combine_forty = round(random.uniform(forty_lo, forty_hi), 2)
        bench_lo, bench_hi = COMBINE_BENCH_RANGES[position]
        combine_bench = random.randint(bench_lo, bench_hi)
        vert_lo, vert_hi = COMBINE_VERTICAL_RANGES[position]
        combine_vertical = round(random.uniform(vert_lo, vert_hi), 1)
        wond_lo, wond_hi = COMBINE_WONDERLIC_RANGE
        combine_wonderlic = random.randint(wond_lo, wond_hi)
    else:
        combine_forty = None
        combine_bench = None
        combine_vertical = None
        combine_wonderlic = None

    # Build prospect dict for insert
    prospect = {
        'draft_class_id': draft_class_id,
        'first_name': first_name,
        'last_name': last_name,
        'position': position,
        'age': age,
        'college': college,
        'college_conference': college_conference,
        'true_overall': true_overall,
        'true_ceiling': true_ceiling,
        'development_trait': development_trait,
        # Attributes
        'true_speed': attrs['true_speed'],
        'true_strength': attrs['true_strength'],
        'true_football_iq': attrs['true_football_iq'],
        'true_durability': attrs['true_durability'],
        'true_clutch': attrs['true_clutch'],
        'true_catch': attrs['true_catch'],
        'true_route_running': attrs['true_route_running'],
        'true_blocking': attrs['true_blocking'],
        'true_pass_rush': attrs['true_pass_rush'],
        'true_coverage_man': attrs['true_coverage_man'],
        'true_coverage_zone': attrs['true_coverage_zone'],
        'true_tackling': attrs['true_tackling'],
        'true_accuracy_short': attrs['true_accuracy_short'],
        'true_accuracy_mid': attrs['true_accuracy_mid'],
        'true_accuracy_deep': attrs['true_accuracy_deep'],
        'true_pocket_presence': attrs['true_pocket_presence'],
        'true_arm_strength': attrs['true_arm_strength'],
        'true_elusiveness': attrs['true_elusiveness'],
        'true_vision': attrs['true_vision'],
        'true_kick_accuracy': attrs['true_kick_accuracy'],
        'true_kick_power': attrs['true_kick_power'],
        'true_yac': attrs['true_yac'],
        # Flags
        'has_injury_history': has_injury_history,
        'injury_history_desc': injury_history_desc,
        'has_character_flag': has_character_flag,
        'character_flag_desc': character_flag_desc,
        # Combine
        'combine_forty': combine_forty,
        'combine_bench': combine_bench,
        'combine_vertical': combine_vertical,
        'combine_wonderlic': combine_wonderlic,
        'combine_attended': combine_attended,
    }

    prospect_id = insert_prospect(conn, prospect)
    prospect['id'] = prospect_id
    return prospect


def generate_draft_class(
    season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Generate a complete draft class for a season year.

    Idempotent guard: raises ValueError if a draft class already exists
    for this season year.

    Args:
        season_year: The season year for the draft class
        conn: Database connection

    Returns:
        List of prospect dicts with DB IDs

    Raises:
        ValueError: If a draft class already exists for this year
    """
    existing = get_draft_class_by_year(conn, season_year)
    if existing:
        raise ValueError(
            f"Draft class already exists for season {season_year}"
        )

    # Determine class strength
    class_strength = weighted_random_choice(DRAFT_CLASS_STRENGTH_WEIGHTS)

    # Class notes
    notes = random.choice(DRAFT_CLASS_NOTES[class_strength])

    # Insert draft_class record
    draft_class_id = insert_draft_class(conn, season_year, class_strength, notes)

    # Determine position counts
    position_counts = {}
    for pos, (lo, hi) in DRAFT_CLASS_POSITION_COUNTS.items():
        position_counts[pos] = random.randint(lo, hi)

    # Adjust total to fit within DRAFT_CLASS_SIZE_RANGE
    total = sum(position_counts.values())
    min_size, max_size = DRAFT_CLASS_SIZE_RANGE
    if total < min_size:
        # Add to largest position groups
        deficit = min_size - total
        positions = sorted(
            position_counts.keys(),
            key=lambda p: position_counts[p],
            reverse=True,
        )
        for i in range(deficit):
            pos = positions[i % len(positions)]
            hi_limit = DRAFT_CLASS_POSITION_COUNTS[pos][1]
            if position_counts[pos] < hi_limit + 5:  # allow slight overflow
                position_counts[pos] += 1
    elif total > max_size:
        # Trim from largest position groups
        excess = total - max_size
        positions = sorted(
            position_counts.keys(),
            key=lambda p: position_counts[p],
            reverse=True,
        )
        for i in range(excess):
            pos = positions[i % len(positions)]
            lo_limit = DRAFT_CLASS_POSITION_COUNTS[pos][0]
            if position_counts[pos] > lo_limit:
                position_counts[pos] -= 1

    # Generate prospects
    prospects = []
    for pos, count in position_counts.items():
        for _ in range(count):
            prospect = _generate_prospect(
                draft_class_id, pos, class_strength, conn,
            )
            prospects.append(prospect)

    conn.commit()
    return prospects


def get_draft_class_prospects(
    season_year: int, conn: sqlite3.Connection,
) -> list[dict]:
    """
    Get all prospects for a season year as dicts.

    Args:
        season_year: The season year
        conn: Database connection

    Returns:
        List of prospect dicts
    """
    rows = get_all_prospects(conn, season_year)
    return [dict(row) for row in rows]


def get_prospect(
    prospect_id: int, conn: sqlite3.Connection,
) -> Optional[dict]:
    """
    Get a single prospect by ID. Engine-layer only.

    Args:
        prospect_id: Prospect ID
        conn: Database connection

    Returns:
        Prospect dict or None if not found
    """
    row = get_prospect_by_id(conn, prospect_id)
    return dict(row) if row else None


def retire_undrafted_prospects(
    season_year: int, conn: sqlite3.Connection,
) -> int:
    """
    Count undrafted prospects below the FA pool minimum overall.
    These prospects won't enter the free agent pool.

    Args:
        season_year: The season year
        conn: Database connection

    Returns:
        Count of prospects below PROSPECT_FA_POOL_MIN_OVR
    """
    undrafted = get_undrafted_prospects(conn, season_year)
    count = sum(
        1 for p in undrafted if p['true_overall'] < PROSPECT_FA_POOL_MIN_OVR
    )
    return count
