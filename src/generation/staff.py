"""
Staff generation for Phase 0.

Generates coaching staff and scouts for all 32 teams.
"""

import sqlite3
import random
import json

from ..utils.constants import (
    COORDINATOR_ROLES, POSITION_COACH_ROLES, SCOUT_ROLES,
    RATING_MIN, RATING_MAX
)
from .names import generate_staff_name


def generate_rating(mean: int = 70, std_dev: int = 10) -> int:
    """
    Generate a rating with normal distribution.

    Args:
        mean: Target average rating
        std_dev: Standard deviation

    Returns:
        Rating between RATING_MIN and RATING_MAX
    """
    rating = int(random.gauss(mean, std_dev))
    return max(RATING_MIN, min(RATING_MAX, rating))


def generate_scheme_expertise(role: str) -> str:
    """
    Generate scheme expertise JSON for coordinators.

    Args:
        role: Staff role ('OC' or 'DC')

    Returns:
        JSON string of scheme expertise ratings
    """
    if role == 'OC':
        schemes = ['spread', 'west_coast', 'air_raid', 'pro_style', 'run_heavy', 'option']
    elif role == 'DC':
        schemes = ['4_3', '3_4', 'cover_2', 'cover_3', 'man', 'zone', 'blitz']
    else:
        return None

    # Generate ratings for each scheme (one will be elite, others varied)
    expertise = {}
    elite_scheme = random.choice(schemes)

    for scheme in schemes:
        if scheme == elite_scheme:
            expertise[scheme] = generate_rating(85, 5)
        else:
            expertise[scheme] = generate_rating(70, 12)

    return json.dumps(expertise)


def generate_staff_member(team_id: int, role: str) -> dict:
    """
    Generate a single staff member with all attributes.

    Args:
        team_id: Team ID to assign staff to
        role: Staff role (coordinator, position coach, or scout)

    Returns:
        Dict of all staff fields ready for INSERT
    """
    first_name, last_name = generate_staff_name()

    # Base ratings for all staff
    teaching_ability = generate_rating(70, 10)
    motivation = generate_rating(70, 10)
    loyalty = generate_rating(70, 12)
    years_experience = random.randint(2, 25)
    reputation = generate_rating(65, 15)

    staff = {
        'team_id': team_id,
        'first_name': first_name,
        'last_name': last_name,
        'role': role,
        'teaching_ability': teaching_ability,
        'motivation': motivation,
        'loyalty': loyalty,
        'years_experience': years_experience,
        'reputation': reputation,
        # Initialize all role-specific attributes to None
        'scheme_expertise': None,
        'play_calling_iq': None,
        'disguise_rating': None,
        'talent_evaluation': None,
        'regional_coverage': None,
        'medical_eye': None,
        'character_read': None,
        'region': None,
    }

    # Role-specific attributes
    if role in COORDINATOR_ROLES:
        staff['scheme_expertise'] = generate_scheme_expertise(role)
        staff['play_calling_iq'] = generate_rating(72, 10)
        if role == 'DC':
            staff['disguise_rating'] = generate_rating(70, 12)

    elif role in POSITION_COACH_ROLES:
        # Position coaches have slightly lower reputation on average
        staff['reputation'] = generate_rating(60, 12)

    elif role in SCOUT_ROLES:
        staff['talent_evaluation'] = generate_rating(70, 12)
        staff['medical_eye'] = generate_rating(68, 12)
        staff['character_read'] = generate_rating(68, 12)

        if role == 'regional_scout':
            staff['regional_coverage'] = random.randint(40, 80)  # Max prospects trackable
            # Assign a region
            regions = ['northeast', 'southeast', 'midwest', 'southwest', 'west']
            staff['region'] = random.choice(regions)
        elif role == 'head_scout':
            staff['regional_coverage'] = random.randint(80, 120)
            staff['region'] = None

    return staff


def insert_staff(conn: sqlite3.Connection, staff: dict) -> int:
    """
    Insert a staff member into the database.

    Args:
        conn: Database connection
        staff: Staff dict from generate_staff_member()

    Returns:
        Staff ID
    """
    cursor = conn.execute("""
        INSERT INTO staff (
            team_id, first_name, last_name, role,
            teaching_ability, motivation, loyalty,
            scheme_expertise, play_calling_iq, disguise_rating,
            talent_evaluation, regional_coverage, medical_eye, character_read, region,
            years_experience, reputation
        ) VALUES (
            :team_id, :first_name, :last_name, :role,
            :teaching_ability, :motivation, :loyalty,
            :scheme_expertise, :play_calling_iq, :disguise_rating,
            :talent_evaluation, :regional_coverage, :medical_eye, :character_read, :region,
            :years_experience, :reputation
        )
    """, staff)

    return cursor.lastrowid


def generate_team_staff(conn: sqlite3.Connection, team_id: int) -> list[int]:
    """
    Generate complete coaching staff and scouts for a team.

    Creates:
    - 1 Offensive Coordinator
    - 1 Defensive Coordinator
    - 1 Special Teams Coordinator
    - 4 Position coaches (random positions)
    - 1 Head scout
    - 3 Regional scouts

    Args:
        conn: Database connection
        team_id: Team ID

    Returns:
        List of staff IDs
    """
    staff_ids = []

    # Coordinators
    for role in ['OC', 'DC', 'ST_coord']:
        staff = generate_staff_member(team_id, role)
        staff_id = insert_staff(conn, staff)
        staff_ids.append(staff_id)

    # Position coaches (pick 4 random)
    coach_roles = random.sample(POSITION_COACH_ROLES, 4)
    for role in coach_roles:
        staff = generate_staff_member(team_id, role)
        staff_id = insert_staff(conn, staff)
        staff_ids.append(staff_id)

    # Head scout
    staff = generate_staff_member(team_id, 'head_scout')
    staff_id = insert_staff(conn, staff)
    staff_ids.append(staff_id)

    # Regional scouts (3)
    for _ in range(3):
        staff = generate_staff_member(team_id, 'regional_scout')
        staff_id = insert_staff(conn, staff)
        staff_ids.append(staff_id)

    return staff_ids


def generate_all_staff(conn: sqlite3.Connection, team_ids: list[int]) -> int:
    """
    Generate staff for all teams.

    Args:
        conn: Database connection (must be in transaction)
        team_ids: List of all team IDs

    Returns:
        Total number of staff generated

    Usage:
        with conn:
            total = generate_all_staff(conn, team_ids)
            print(f"Generated {total} staff members across {len(team_ids)} teams")
    """
    total_staff = 0

    for team_id in team_ids:
        staff_ids = generate_team_staff(conn, team_id)
        total_staff += len(staff_ids)
        print(f"Generated {len(staff_ids)} staff for team {team_id}")

    return total_staff
