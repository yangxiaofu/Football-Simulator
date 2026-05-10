"""
Player generation for Phase 0.

Generates 53-man rosters for all 32 teams with position-specific attributes.
"""

import sqlite3
import random
from typing import Optional

from ..utils.constants import (
    ROSTER_COMPOSITION, ALL_POSITIONS,
    RATING_MIN, RATING_MAX,
    DEVELOPMENT_TRAIT_WEIGHTS, AGE_DISTRIBUTION, AGE_RANGES,
    OFFENSE_POSITIONS, DEFENSE_POSITIONS,
    STAMINA_MAX
)
from .names import generate_player_name, generate_college


def weighted_random_choice(weights_dict: dict) -> str:
    """
    Select a random key from a dict based on probability weights.

    Args:
        weights_dict: Dict of {key: probability}

    Returns:
        Selected key
    """
    choices = list(weights_dict.keys())
    probabilities = list(weights_dict.values())
    return random.choices(choices, weights=probabilities, k=1)[0]


def generate_rating(mean: int, std_dev: int = 8) -> int:
    """
    Generate a rating with normal distribution.

    Args:
        mean: Target average rating
        std_dev: Standard deviation (default 8)

    Returns:
        Rating between RATING_MIN and RATING_MAX
    """
    rating = int(random.gauss(mean, std_dev))
    return max(RATING_MIN, min(RATING_MAX, rating))


def generate_age(age_category: str) -> int:
    """
    Generate an age from a category.

    Args:
        age_category: One of: 'rookie', 'young', 'prime', 'veteran', 'old'

    Returns:
        Age in years
    """
    min_age, max_age = AGE_RANGES[age_category]
    return random.randint(min_age, max_age)


def generate_player_attributes(position: str, overall: int) -> dict:
    """
    Generate position-specific attributes based on overall rating.

    Each position has different important attributes.

    Args:
        position: Player position
        overall: Target overall rating (determines attribute levels)

    Returns:
        Dict of attribute_name -> value (None for non-relevant attributes)
    """
    # Base attributes for all positions
    attrs = {
        'true_speed': generate_rating(overall, 10),
        'true_strength': generate_rating(overall, 10),
        'true_football_iq': generate_rating(overall, 8),
        'true_durability': generate_rating(overall, 12),
        'true_clutch': generate_rating(overall, 15),
        # Initialize all position-specific attributes to None
        'true_catch': None,
        'true_route_running': None,
        'true_blocking': None,
        'true_pass_rush': None,
        'true_coverage_man': None,
        'true_coverage_zone': None,
        'true_tackling': None,
        'true_accuracy_short': None,
        'true_accuracy_mid': None,
        'true_accuracy_deep': None,
        'true_pocket_presence': None,
        'true_arm_strength': None,
        'true_elusiveness': None,
        'true_vision': None,
        'true_kick_accuracy': None,
        'true_kick_power': None,
        'true_yac': None,
    }

    # Position-specific attributes
    if position == 'QB':
        attrs.update({
            'true_accuracy_short': generate_rating(overall, 8),
            'true_accuracy_mid': generate_rating(overall, 10),
            'true_accuracy_deep': generate_rating(overall, 12),
            'true_pocket_presence': generate_rating(overall, 10),
            'true_arm_strength': generate_rating(overall, 10),
        })

    elif position == 'RB':
        attrs.update({
            'true_elusiveness': generate_rating(overall, 10),
            'true_vision': generate_rating(overall, 10),
            'true_catch': generate_rating(overall - 5, 12),  # RBs generally worse at catching
            'true_blocking': generate_rating(overall - 10, 12),
        })

    elif position == 'WR':
        attrs.update({
            'true_catch': generate_rating(overall, 8),
            'true_route_running': generate_rating(overall, 10),
            'true_yac': generate_rating(overall, 12),
        })

    elif position == 'TE':
        attrs.update({
            'true_catch': generate_rating(overall, 10),
            'true_route_running': generate_rating(overall - 5, 12),
            'true_blocking': generate_rating(overall, 10),
            'true_yac': generate_rating(overall, 12),
        })

    elif position == 'OL':
        attrs.update({
            'true_blocking': generate_rating(overall, 8),
        })
        # OL generally slower, stronger
        attrs['true_speed'] = generate_rating(overall - 20, 8)
        attrs['true_strength'] = generate_rating(overall + 5, 8)

    elif position == 'DL':
        attrs.update({
            'true_pass_rush': generate_rating(overall, 10),
            'true_tackling': generate_rating(overall, 10),
        })
        # DL generally strong
        attrs['true_strength'] = generate_rating(overall + 5, 10)

    elif position == 'LB':
        attrs.update({
            'true_tackling': generate_rating(overall, 8),
            'true_coverage_man': generate_rating(overall - 5, 12),
            'true_coverage_zone': generate_rating(overall, 10),
            'true_pass_rush': generate_rating(overall - 5, 12),
        })

    elif position == 'CB':
        attrs.update({
            'true_coverage_man': generate_rating(overall, 8),
            'true_coverage_zone': generate_rating(overall, 10),
            'true_catch': generate_rating(overall - 10, 15),  # INTs
            'true_tackling': generate_rating(overall - 5, 10),
        })
        # CBs generally fast
        attrs['true_speed'] = generate_rating(overall + 5, 8)

    elif position == 'S':
        attrs.update({
            'true_coverage_man': generate_rating(overall - 5, 10),
            'true_coverage_zone': generate_rating(overall, 8),
            'true_tackling': generate_rating(overall, 10),
            'true_catch': generate_rating(overall - 8, 12),
        })

    elif position in ['K', 'P']:
        attrs.update({
            'true_kick_accuracy': generate_rating(overall, 8),
            'true_kick_power': generate_rating(overall, 10),
        })
        # Kickers don't need most physical attributes
        attrs['true_speed'] = generate_rating(50, 10)
        attrs['true_strength'] = generate_rating(50, 10)

    return attrs


def generate_player(
    team_id: int,
    position: str,
    overall_mean: int = 68,
    age_category: Optional[str] = None
) -> dict:
    """
    Generate a single player with all attributes.

    Args:
        team_id: Team ID to assign player to
        position: Player position
        overall_mean: Target overall rating mean for this player
        age_category: Age category (None = random from distribution)

    Returns:
        Dict of all player fields ready for INSERT
    """
    # Generate name and basic info
    first_name, last_name = generate_player_name()
    college = generate_college()

    # Age
    if age_category is None:
        age_category = weighted_random_choice(AGE_DISTRIBUTION)
    age = generate_age(age_category)
    years_experience = max(0, age - 22)

    # Draft history (older players were drafted earlier)
    if years_experience > 0:
        draft_year = 2024 - years_experience
        draft_round = random.randint(1, 7)
        draft_pick = random.randint(1, 32)
    else:
        draft_year = None
        draft_round = None
        draft_pick = None

    # Overall rating
    true_overall = generate_rating(overall_mean, 8)

    # Development trait and ceiling
    development_trait = weighted_random_choice(DEVELOPMENT_TRAIT_WEIGHTS)

    if development_trait == 'superstar':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(15, 25))
    elif development_trait == 'star':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(8, 15))
    elif development_trait == 'normal':
        true_ceiling = min(RATING_MAX, true_overall + random.randint(3, 8))
    else:  # slow
        true_ceiling = min(RATING_MAX, true_overall + random.randint(0, 3))

    # Generate position-specific attributes
    attrs = generate_player_attributes(position, true_overall)

    # Build player dict
    player = {
        'team_id': team_id,
        'first_name': first_name,
        'last_name': last_name,
        'position': position,
        'age': age,
        'years_experience': years_experience,
        'college': college,
        'draft_year': draft_year,
        'draft_round': draft_round,
        'draft_pick': draft_pick,
        'true_overall': true_overall,
        'true_ceiling': true_ceiling,
        'development_trait': development_trait,
        'weekly_stamina': STAMINA_MAX,
        'season_wear': 0,
        'satisfaction': 75,
        'is_active': 1,
        'roster_status': 'active',
        'injury_status': None,
        'injury_weeks_remaining': 0,
    }

    # Add all attributes
    player.update(attrs)

    return player


def insert_player(conn: sqlite3.Connection, player: dict) -> int:
    """
    Insert a player into the database.

    Args:
        conn: Database connection
        player: Player dict from generate_player()

    Returns:
        Player ID
    """
    cursor = conn.execute("""
        INSERT INTO player (
            team_id, first_name, last_name, position, age, years_experience,
            college, draft_year, draft_round, draft_pick,
            true_overall, true_speed, true_strength, true_football_iq,
            true_durability, true_clutch, true_ceiling, development_trait,
            true_catch, true_route_running, true_blocking, true_pass_rush,
            true_coverage_man, true_coverage_zone, true_tackling,
            true_accuracy_short, true_accuracy_mid, true_accuracy_deep,
            true_pocket_presence, true_arm_strength, true_elusiveness,
            true_vision, true_kick_accuracy, true_kick_power, true_yac,
            weekly_stamina, season_wear, satisfaction, is_active,
            roster_status, injury_status, injury_weeks_remaining
        ) VALUES (
            :team_id, :first_name, :last_name, :position, :age, :years_experience,
            :college, :draft_year, :draft_round, :draft_pick,
            :true_overall, :true_speed, :true_strength, :true_football_iq,
            :true_durability, :true_clutch, :true_ceiling, :development_trait,
            :true_catch, :true_route_running, :true_blocking, :true_pass_rush,
            :true_coverage_man, :true_coverage_zone, :true_tackling,
            :true_accuracy_short, :true_accuracy_mid, :true_accuracy_deep,
            :true_pocket_presence, :true_arm_strength, :true_elusiveness,
            :true_vision, :true_kick_accuracy, :true_kick_power, :true_yac,
            :weekly_stamina, :season_wear, :satisfaction, :is_active,
            :roster_status, :injury_status, :injury_weeks_remaining
        )
    """, player)

    return cursor.lastrowid


def generate_team_roster(conn: sqlite3.Connection, team_id: int) -> list[int]:
    """
    Generate a 53-man roster for a team.

    Creates players based on ROSTER_COMPOSITION with varied overall ratings
    to simulate a realistic team roster (stars, starters, backups, depth).

    Args:
        conn: Database connection
        team_id: Team ID

    Returns:
        List of player IDs
    """
    player_ids = []

    for position, count in ROSTER_COMPOSITION.items():
        # Generate varying quality players for each position
        # First player = starter (higher overall)
        # Others = backups/depth (lower overall)

        for i in range(count):
            if i == 0:
                # Starter: 70-85 overall
                overall_mean = random.randint(70, 85)
                age_category = weighted_random_choice({
                    'rookie': 0.15,
                    'young': 0.30,
                    'prime': 0.40,
                    'veteran': 0.15,
                })
            elif i == 1:
                # Backup: 65-75 overall
                overall_mean = random.randint(65, 75)
                age_category = weighted_random_choice({
                    'rookie': 0.20,
                    'young': 0.35,
                    'prime': 0.30,
                    'veteran': 0.15,
                })
            else:
                # Depth: 55-68 overall
                overall_mean = random.randint(55, 68)
                age_category = weighted_random_choice({
                    'rookie': 0.30,
                    'young': 0.40,
                    'prime': 0.20,
                    'veteran': 0.08,
                    'old': 0.02,
                })

            player = generate_player(team_id, position, overall_mean, age_category)
            player_id = insert_player(conn, player)
            player_ids.append(player_id)

    return player_ids


def generate_all_rosters(conn: sqlite3.Connection, team_ids: list[int]) -> int:
    """
    Generate 53-man rosters for all teams.

    Args:
        conn: Database connection (must be in transaction)
        team_ids: List of all team IDs

    Returns:
        Total number of players generated

    Usage:
        with conn:
            total = generate_all_rosters(conn, team_ids)
            print(f"Generated {total} players across {len(team_ids)} teams")
    """
    total_players = 0

    for team_id in team_ids:
        player_ids = generate_team_roster(conn, team_id)
        total_players += len(player_ids)
        print(f"Generated {len(player_ids)} players for team {team_id}")

    return total_players
