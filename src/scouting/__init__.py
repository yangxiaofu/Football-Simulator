"""
Scouting and draft module (Phase 3).

This module contains:
- Draft class generation (prospects.py)
- Scout assignment and evaluation (scouts.py)
- Scouting report cycle and combine events (reports.py)
- Draft board management (board.py)
- Draft day logic (to be implemented)
"""

from .prospects import (
    generate_draft_class,
    get_draft_class_prospects,
    get_prospect,
    retire_undrafted_prospects,
)

from .scouts import (
    get_scouting_department,
    assign_scout,
    get_assignments,
    generate_scouted_grade,
    generate_scouting_flags,
    get_scouted_prospect,
)

from .reports import (
    run_scouting_phase,
    generate_combine_event,
    generate_competitor_intelligence,
    generate_mock_draft,
)

from .board import (
    build_draft_board,
    get_board_entry,
    update_board_rank,
    run_postdraft_review,
)

__all__ = [
    # prospects
    'generate_draft_class',
    'get_draft_class_prospects',
    'get_prospect',
    'retire_undrafted_prospects',
    # scouts
    'get_scouting_department',
    'assign_scout',
    'get_assignments',
    'generate_scouted_grade',
    'generate_scouting_flags',
    'get_scouted_prospect',
    # reports
    'run_scouting_phase',
    'generate_combine_event',
    'generate_competitor_intelligence',
    'generate_mock_draft',
    # board
    'build_draft_board',
    'get_board_entry',
    'update_board_rank',
    'run_postdraft_review',
]
