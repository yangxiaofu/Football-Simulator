"""
Coach identity and assignment system (Phase 4).

Provides the single mutation helper that keeps coach, team, and league state
in sync when a coach is assigned to or removed from a team.

Key invariants maintained:
- Invariant #11: league.user_team_id == player coach's current_team_id (when not NULL)
- Invariant #12: For every team with an active coach, team.gm_personality == coach_career.personality_archetype
"""

import sqlite3

from ..utils.constants import COACH_TENURE_END_REASONS


def assign_coach_to_team(
    conn: sqlite3.Connection,
    coach_id: int,
    team_id: int | None,
    season_year: int,
    end_reason_for_previous: str = 'current',
) -> None:
    """
    Assign a coach to a team (or remove from current team if team_id is None).

    This is the sole writer of team.gm_personality for coached teams. It maintains
    all coach/team/league invariants in a single transaction.

    Step 0: If team_id is not None and another active coach is currently
    assigned to that team, displace them — close their open tenure with
    end_reason='replaced', set their current_team_id=NULL, leave is_active=1.

    Steps 1-4: Close incoming coach's prior tenure, assign to new team, sync
    team.gm_personality, update league.user_team_id if player coach.

    Args:
        conn: Database connection
        coach_id: ID of the coach in coach_career
        team_id: Team to assign to, or None to remove from current team
        season_year: Current season year
        end_reason_for_previous: Reason for ending previous tenure
            Must be one of COACH_TENURE_END_REASONS

    Raises:
        ValueError: If end_reason_for_previous is not valid
    """
    if end_reason_for_previous not in COACH_TENURE_END_REASONS:
        raise ValueError(
            f"Invalid end_reason: {end_reason_for_previous!r}. "
            f"Must be one of {COACH_TENURE_END_REASONS}"
        )

    with conn:
        # Step 0: Displace existing coach on destination team
        if team_id is not None:
            existing = conn.execute(
                """SELECT id FROM coach_career
                   WHERE current_team_id = ? AND is_active = 1 AND id != ?""",
                (team_id, coach_id)
            ).fetchone()
            if existing:
                displaced_coach_id = existing['id']
                # Close their open tenure
                conn.execute(
                    """UPDATE coach_tenure
                       SET end_year = ?, end_reason = 'replaced'
                       WHERE coach_id = ? AND end_year IS NULL""",
                    (season_year, displaced_coach_id)
                )
                # Mark them as between jobs (still active, no team)
                conn.execute(
                    "UPDATE coach_career SET current_team_id = NULL WHERE id = ?",
                    (displaced_coach_id,)
                )

        # Step 1: Read coach row
        coach = conn.execute(
            "SELECT is_player, personality_archetype FROM coach_career WHERE id = ?",
            (coach_id,)
        ).fetchone()
        if coach is None:
            raise ValueError(f"Coach {coach_id} not found")

        is_player = coach['is_player']
        archetype = coach['personality_archetype']

        # Step 2: Close any open tenure for incoming coach (end_year IS NULL means current)
        conn.execute(
            """UPDATE coach_tenure
               SET end_year = ?, end_reason = ?
               WHERE coach_id = ? AND end_year IS NULL""",
            (season_year, end_reason_for_previous, coach_id)
        )

        # Step 3: Update coach's current team
        conn.execute(
            "UPDATE coach_career SET current_team_id = ? WHERE id = ?",
            (team_id, coach_id)
        )

        if team_id is not None:
            # Insert new open tenure
            conn.execute(
                """INSERT INTO coach_tenure (coach_id, team_id, start_year, end_reason)
                   VALUES (?, ?, ?, 'current')""",
                (coach_id, team_id, season_year)
            )

            # Phase 4 Prompt #7: Set starting condition multiplier
            from ..league.legacy import lookup_starting_condition_multiplier
            starting_mult = lookup_starting_condition_multiplier(
                conn, coach_id, team_id, season_year
            )
            conn.execute(
                """UPDATE coach_tenure
                   SET starting_condition_multiplier = ?
                   WHERE coach_id = ? AND end_year IS NULL""",
                (starting_mult, coach_id)
            )

            # Step 4: Sync team.gm_personality with coach archetype (Invariant #12)
            conn.execute(
                "UPDATE team SET gm_personality = ? WHERE id = ?",
                (archetype, team_id)
            )

            # If player coach, update league.user_team_id (Invariant #11)
            if is_player:
                conn.execute(
                    "UPDATE league SET user_team_id = ? WHERE id = 1",
                    (team_id,)
                )
