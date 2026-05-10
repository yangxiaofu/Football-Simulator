"""
Simulation engine module (Phase 1).

Public API:
    simulate_game(db_path, game_id, verbose=True) -> dict

Usage:
    from src.engine import simulate_game
    result = simulate_game('saves/my_franchise.db', game_id=1)
"""

from .game_sim import simulate_game

__all__ = ['simulate_game']
