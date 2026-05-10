"""
Generation module for Football Simulator.

Contains scripts for generating teams, players, staff, and schedules.
"""

from .teams import generate_all_teams
from .players import generate_all_rosters
from .staff import generate_all_staff
from .schedule import generate_full_schedule

__all__ = [
    'generate_all_teams',
    'generate_all_rosters',
    'generate_all_staff',
    'generate_full_schedule',
]
