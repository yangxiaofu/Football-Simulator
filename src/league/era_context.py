"""
Era difficulty context calculation.

Computes era difficulty multiplier based on league-wide parity.
Lower variance (dominance era) = easier to win = lower multiplier.
Higher variance (parity era) = harder to win = higher multiplier.
"""

import sqlite3
import statistics
from typing import Optional

from ..db.queries import get_all_team_season_records
from ..utils.constants import (
    ERA_DIFFICULTY_BASELINE_VARIANCE,
    ERA_DIFFICULTY_VARIANCE_RANGE,
    ERA_DIFFICULTY_MIN,
    ERA_DIFFICULTY_MAX,
    ERA_DIFFICULTY_SMOOTHING_WINDOW,
)


def compute_season_w_pct_variance(
    conn: sqlite3.Connection, season_year: int,
) -> Optional[float]:
    """Return stdev of W% across 32 teams for given season.

    Returns:
        Standard deviation of win percentages, or None if season incomplete
    """
    records = get_all_team_season_records(conn, season_year)

    if not records or len(records) < 32:
        return None

    win_pcts = []
    for rec in records:
        total_games = rec['wins'] + rec['losses'] + rec['ties']
        if total_games == 0:
            # Season not started/completed
            return None
        wpct = (rec['wins'] + rec['ties'] * 0.5) / total_games
        win_pcts.append(wpct)

    if len(win_pcts) < 2:
        return None

    return statistics.stdev(win_pcts)


def compute_era_difficulty_multiplier(
    conn: sqlite3.Connection, season_year: int,
) -> float:
    """Smoothed era difficulty (3-season window).

    Logic:
    - Low variance (dominance) → easier to win → lower multiplier (0.85)
    - High variance (parity) → harder to win → higher multiplier (1.15)
    - Baseline = 0.16 stdev → 1.0 multiplier

    Returns:
        Multiplier between ERA_DIFFICULTY_MIN and ERA_DIFFICULTY_MAX
    """
    # Collect variance for current season and up to 2 prior seasons
    variances = []
    for year_offset in range(ERA_DIFFICULTY_SMOOTHING_WINDOW):
        year = season_year - year_offset
        if year < 0:
            break
        variance = compute_season_w_pct_variance(conn, year)
        if variance is not None:
            variances.append(variance)

    if not variances:
        # No data available, return baseline
        return 1.0

    # Average variance across window
    avg_variance = sum(variances) / len(variances)

    # Map variance delta to multiplier range
    # variance delta = avg_variance - baseline
    # ±ERA_DIFFICULTY_VARIANCE_RANGE (0.05) maps to ±0.15 multiplier
    variance_delta = avg_variance - ERA_DIFFICULTY_BASELINE_VARIANCE

    # Linear interpolation
    # If variance_delta = +0.05 → multiplier = 1.15
    # If variance_delta = -0.05 → multiplier = 0.85
    # If variance_delta = 0 → multiplier = 1.0
    multiplier_delta = (variance_delta / ERA_DIFFICULTY_VARIANCE_RANGE) * (ERA_DIFFICULTY_MAX - 1.0)
    multiplier = 1.0 + multiplier_delta

    # Clamp to valid range
    multiplier = max(ERA_DIFFICULTY_MIN, min(ERA_DIFFICULTY_MAX, multiplier))

    return multiplier
