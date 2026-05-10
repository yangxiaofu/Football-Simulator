"""
AI GM Behavior Matrix (Phase 4 Prompt #3).

Pure constants module containing the 5x5 personality x phase behavior grid.
No imports from other src/ modules (utils layer is dependency-free).

Each cell defines multipliers applied on top of existing personality traits:
- fa_aggression_mult: Scales free agency aggressiveness
- trade_willingness_mult: Scales trade willingness
- overpay_mult: Added to FA overpay percentage
- draft_strategy: 'bpa' | 'need' | 'upside' — selects draft weight profile
- max_fa_offers_mult: Scales max FA offers per team
- trade_vets_for_picks: Whether to trade veterans for draft picks
"""

from .constants import TEAM_PHASE_DEFAULT


# 25-cell behavior matrix: (personality, phase) -> behavior profile
BEHAVIOR_MATRIX = {
    # =====================
    # DRAFT PURIST
    # =====================
    ('draft_purist', 'rebuild'): {
        'fa_aggression_mult': 0.3,
        'trade_willingness_mult': 1.5,
        'overpay_mult': -0.05,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.5,
        'trade_vets_for_picks': True,
    },
    ('draft_purist', 'bridge'): {
        'fa_aggression_mult': 0.5,
        'trade_willingness_mult': 1.0,
        'overpay_mult': 0.0,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.7,
        'trade_vets_for_picks': False,
    },
    ('draft_purist', 'contend'): {
        'fa_aggression_mult': 0.7,
        'trade_willingness_mult': 0.8,
        'overpay_mult': 0.0,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.8,
        'trade_vets_for_picks': False,
    },
    ('draft_purist', 'win_now'): {
        'fa_aggression_mult': 0.8,
        'trade_willingness_mult': 0.6,
        'overpay_mult': 0.05,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('draft_purist', 'decline'): {
        'fa_aggression_mult': 0.2,
        'trade_willingness_mult': 1.8,
        'overpay_mult': -0.10,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.4,
        'trade_vets_for_picks': True,
    },

    # =====================
    # WIN NOW
    # =====================
    ('win_now', 'rebuild'): {
        'fa_aggression_mult': 0.8,
        'trade_willingness_mult': 1.2,
        'overpay_mult': 0.05,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('win_now', 'bridge'): {
        'fa_aggression_mult': 1.0,
        'trade_willingness_mult': 1.0,
        'overpay_mult': 0.05,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('win_now', 'contend'): {
        'fa_aggression_mult': 1.3,
        'trade_willingness_mult': 1.3,
        'overpay_mult': 0.10,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.3,
        'trade_vets_for_picks': False,
    },
    ('win_now', 'win_now'): {
        'fa_aggression_mult': 1.5,
        'trade_willingness_mult': 1.5,
        'overpay_mult': 0.15,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.5,
        'trade_vets_for_picks': False,
    },
    ('win_now', 'decline'): {
        'fa_aggression_mult': 1.2,
        'trade_willingness_mult': 1.0,
        'overpay_mult': 0.10,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.2,
        'trade_vets_for_picks': False,
    },

    # =====================
    # ANALYTICS
    # =====================
    ('analytics', 'rebuild'): {
        'fa_aggression_mult': 0.4,
        'trade_willingness_mult': 1.3,
        'overpay_mult': -0.05,
        'draft_strategy': 'upside',
        'max_fa_offers_mult': 0.6,
        'trade_vets_for_picks': True,
    },
    ('analytics', 'bridge'): {
        'fa_aggression_mult': 0.7,
        'trade_willingness_mult': 1.0,
        'overpay_mult': 0.0,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.8,
        'trade_vets_for_picks': False,
    },
    ('analytics', 'contend'): {
        'fa_aggression_mult': 1.0,
        'trade_willingness_mult': 1.0,
        'overpay_mult': 0.05,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('analytics', 'win_now'): {
        'fa_aggression_mult': 1.2,
        'trade_willingness_mult': 1.2,
        'overpay_mult': 0.08,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.2,
        'trade_vets_for_picks': False,
    },
    ('analytics', 'decline'): {
        'fa_aggression_mult': 0.3,
        'trade_willingness_mult': 1.5,
        'overpay_mult': -0.08,
        'draft_strategy': 'upside',
        'max_fa_offers_mult': 0.5,
        'trade_vets_for_picks': True,
    },

    # =====================
    # LOYALTY
    # =====================
    ('loyalty', 'rebuild'): {
        'fa_aggression_mult': 0.6,
        'trade_willingness_mult': 0.5,
        'overpay_mult': 0.0,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.7,
        'trade_vets_for_picks': False,
    },
    ('loyalty', 'bridge'): {
        'fa_aggression_mult': 0.7,
        'trade_willingness_mult': 0.6,
        'overpay_mult': 0.05,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.8,
        'trade_vets_for_picks': False,
    },
    ('loyalty', 'contend'): {
        'fa_aggression_mult': 0.9,
        'trade_willingness_mult': 0.7,
        'overpay_mult': 0.08,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('loyalty', 'win_now'): {
        'fa_aggression_mult': 1.0,
        'trade_willingness_mult': 0.8,
        'overpay_mult': 0.10,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('loyalty', 'decline'): {
        'fa_aggression_mult': 0.5,
        'trade_willingness_mult': 0.4,
        'overpay_mult': 0.0,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 0.6,
        'trade_vets_for_picks': False,
    },

    # =====================
    # OPPORTUNIST
    # =====================
    ('opportunist', 'rebuild'): {
        'fa_aggression_mult': 0.6,
        'trade_willingness_mult': 1.4,
        'overpay_mult': 0.0,
        'draft_strategy': 'upside',
        'max_fa_offers_mult': 0.8,
        'trade_vets_for_picks': True,
    },
    ('opportunist', 'bridge'): {
        'fa_aggression_mult': 0.8,
        'trade_willingness_mult': 1.2,
        'overpay_mult': 0.05,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 1.0,
        'trade_vets_for_picks': False,
    },
    ('opportunist', 'contend'): {
        'fa_aggression_mult': 1.1,
        'trade_willingness_mult': 1.3,
        'overpay_mult': 0.08,
        'draft_strategy': 'bpa',
        'max_fa_offers_mult': 1.2,
        'trade_vets_for_picks': False,
    },
    ('opportunist', 'win_now'): {
        'fa_aggression_mult': 1.3,
        'trade_willingness_mult': 1.5,
        'overpay_mult': 0.12,
        'draft_strategy': 'need',
        'max_fa_offers_mult': 1.4,
        'trade_vets_for_picks': False,
    },
    ('opportunist', 'decline'): {
        'fa_aggression_mult': 0.5,
        'trade_willingness_mult': 1.6,
        'overpay_mult': -0.05,
        'draft_strategy': 'upside',
        'max_fa_offers_mult': 0.6,
        'trade_vets_for_picks': True,
    },
}


# Default fallback profile (bridge phase, analytics personality)
_DEFAULT_PROFILE = {
    'fa_aggression_mult': 1.0,
    'trade_willingness_mult': 1.0,
    'overpay_mult': 0.0,
    'draft_strategy': 'bpa',
    'max_fa_offers_mult': 1.0,
    'trade_vets_for_picks': False,
}


def get_behavior_signature(personality: str, phase: str) -> dict:
    """Look up the behavior profile for a personality + phase combination.

    Falls back to (personality, 'bridge') if the exact phase isn't found,
    then to the default profile if the personality is unknown.

    Args:
        personality: GM personality archetype.
        phase: Team phase ('rebuild', 'bridge', 'contend', 'win_now', 'decline').

    Returns:
        Dict with fa_aggression_mult, trade_willingness_mult, overpay_mult,
        draft_strategy, max_fa_offers_mult, trade_vets_for_picks.
    """
    key = (personality, phase)
    if key in BEHAVIOR_MATRIX:
        return BEHAVIOR_MATRIX[key]

    # Fallback: try bridge phase for this personality
    bridge_key = (personality, TEAM_PHASE_DEFAULT)
    if bridge_key in BEHAVIOR_MATRIX:
        return BEHAVIOR_MATRIX[bridge_key]

    return dict(_DEFAULT_PROFILE)
