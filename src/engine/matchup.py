"""
Matchup resolution: logistic probability function and 1v1 battle resolution.

Pure math module with no engine dependencies.
"""

import math
import random

from ..utils.constants import MATCHUP_K, VARIANCE_CAP


def matchup_probability(sar_attacker: int, sar_defender: int, k: float = MATCHUP_K) -> float:
    """
    Calculate the probability that the attacker wins a 1v1 matchup.

    Uses logistic function: P(win) = 1 / (1 + e^(-k * (SAR_att - SAR_def)))

    At equal ratings: 50%
    At +30 differential: ~88%
    At -30 differential: ~12%

    Args:
        sar_attacker: Scheme-adjusted rating of the attacker
        sar_defender: Scheme-adjusted rating of the defender
        k: Curve steepness (default from constants)

    Returns:
        Probability (0.0 to 1.0) that attacker wins
    """
    diff = sar_attacker - sar_defender
    return 1.0 / (1.0 + math.exp(-k * diff))


def resolve_matchup(sar_attacker: int, sar_defender: int, k: float = MATCHUP_K) -> bool:
    """
    Resolve a single 1v1 matchup: does the attacker win?

    Args:
        sar_attacker: Scheme-adjusted rating of the attacker
        sar_defender: Scheme-adjusted rating of the defender
        k: Curve steepness

    Returns:
        True if attacker wins, False if defender wins
    """
    prob = matchup_probability(sar_attacker, sar_defender, k)
    return random.random() < prob


def resolve_matchup_with_variance(
    sar_attacker: int,
    sar_defender: int,
    k: float = MATCHUP_K,
    variance_cap: int = VARIANCE_CAP,
) -> dict:
    """
    Resolve a matchup and generate a quality score indicating how decisively
    the winner won. Used to scale outcome magnitude (yards gained, etc.).

    Args:
        sar_attacker: Scheme-adjusted rating of the attacker
        sar_defender: Scheme-adjusted rating of the defender
        k: Curve steepness
        variance_cap: Maximum random modifier

    Returns:
        dict with:
            'attacker_wins': bool
            'margin': float (-1.0 to 1.0, positive = attacker advantage)
            'variance': int (random modifier applied)
    """
    variance = random.randint(-variance_cap, variance_cap)
    effective_att = sar_attacker + variance
    prob = matchup_probability(effective_att, sar_defender, k)
    attacker_wins = random.random() < prob

    # Margin represents how decisive the outcome was
    # Scale the probability to -1.0 (defender dominant) to +1.0 (attacker dominant)
    margin = (prob - 0.5) * 2.0

    return {
        'attacker_wins': attacker_wins,
        'margin': margin,
        'variance': variance,
    }


def resolve_group_matchup(
    attackers: list[int],
    defenders: list[int],
    k: float = MATCHUP_K,
) -> dict:
    """
    Resolve a group battle (e.g., 5 OL vs pass rushers).
    Each attacker is paired with a defender; excess on either side
    are uncontested wins.

    Args:
        attackers: List of SAR values for attackers
        defenders: List of SAR values for defenders

    Returns:
        dict with:
            'attacker_wins': int (number of individual wins)
            'defender_wins': int
            'total': int (total matchups resolved)
    """
    att_wins = 0
    def_wins = 0
    pairs = min(len(attackers), len(defenders))

    # Sort both to pair strongest vs strongest
    sorted_att = sorted(attackers, reverse=True)
    sorted_def = sorted(defenders, reverse=True)

    for i in range(pairs):
        if resolve_matchup(sorted_att[i], sorted_def[i], k):
            att_wins += 1
        else:
            def_wins += 1

    # Uncontested matchups
    if len(attackers) > pairs:
        att_wins += len(attackers) - pairs
    if len(defenders) > pairs:
        def_wins += len(defenders) - pairs

    return {
        'attacker_wins': att_wins,
        'defender_wins': def_wins,
        'total': att_wins + def_wins,
    }
