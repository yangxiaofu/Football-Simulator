"""
Transactions and offseason module (Phase 3).

This module contains:
- Contract management (signing, restructuring, release, market valuation)
- Player satisfaction (weekly evaluation, warning signals, interventions, contagion)
- Free agency (market generation, interest tiers, pitch meetings, offers, AI signings)
- Trade system (player/pick exchanges, AI trade logic, GM personality)
- Franchise tags (exclusive/transition tags, salary calculation)
"""

from .contracts import (
    calculate_cap_hit,
    calculate_dead_cap,
    offer_contract,
    restructure_contract,
    release_player,
    get_market_value,
)

from .satisfaction import (
    get_satisfaction,
    adjust_satisfaction,
    evaluate_satisfaction_factors,
    get_warning_signal,
    process_weekly_satisfaction,
    apply_intervention,
    check_locker_room_influence,
)

from .free_agency import (
    generate_fa_market,
    get_interest_tier,
    request_pitch_meeting,
    submit_offer,
    resolve_offer,
    run_ai_fa_signings,
    get_fa_market_status,
)

from .trades import (
    calculate_player_trade_value,
    calculate_pick_value,
    evaluate_trade,
    propose_trade,
    execute_trade,
    receive_trade_offers,
    check_trade_deadline,
)

from .coaching import (
    assign_coach_to_team,
)

__all__ = [
    'calculate_cap_hit',
    'calculate_dead_cap',
    'offer_contract',
    'restructure_contract',
    'release_player',
    'get_market_value',
    'get_satisfaction',
    'adjust_satisfaction',
    'evaluate_satisfaction_factors',
    'get_warning_signal',
    'process_weekly_satisfaction',
    'apply_intervention',
    'check_locker_room_influence',
    'generate_fa_market',
    'get_interest_tier',
    'request_pitch_meeting',
    'submit_offer',
    'resolve_offer',
    'run_ai_fa_signings',
    'get_fa_market_status',
    'calculate_player_trade_value',
    'calculate_pick_value',
    'evaluate_trade',
    'propose_trade',
    'execute_trade',
    'receive_trade_offers',
    'check_trade_deadline',
    'assign_coach_to_team',
]
