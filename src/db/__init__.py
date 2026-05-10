"""
Database module for Football Simulator.

Exports commonly-used functions for cleaner imports.
"""

from .connection import (
    get_connection,
    init_database,
    execute_query,
    execute_one,
    execute_write,
    table_exists,
    get_league_state,
    get_team_by_id,
    get_team_by_abbreviation,
    get_roster,
    get_player_by_id,
)

from .cap import (
    recalculate_cap_space,
    recalculate_all_teams_cap_space,
    get_contract_cap_hit,
    get_player_cap_hit,
    get_dead_cap_value,
    get_team_contract_breakdown,
    validate_team_cap_space,
    validate_all_teams_cap_space,
)

from .transactions import (
    log_transaction,
    get_team_transactions,
    get_player_transaction_history,
    get_recent_league_transactions,
    get_week_transactions,
    get_transaction_stats_by_type,
    get_total_cap_impact_by_team,
)

__all__ = [
    # connection
    'get_connection',
    'init_database',
    'execute_query',
    'execute_one',
    'execute_write',
    'table_exists',
    'get_league_state',
    'get_team_by_id',
    'get_team_by_abbreviation',
    'get_roster',
    'get_player_by_id',
    # cap
    'recalculate_cap_space',
    'recalculate_all_teams_cap_space',
    'get_contract_cap_hit',
    'get_player_cap_hit',
    'get_dead_cap_value',
    'get_team_contract_breakdown',
    'validate_team_cap_space',
    'validate_all_teams_cap_space',
    # transactions
    'log_transaction',
    'get_team_transactions',
    'get_player_transaction_history',
    'get_recent_league_transactions',
    'get_week_transactions',
    'get_transaction_stats_by_type',
    'get_total_cap_impact_by_team',
]
