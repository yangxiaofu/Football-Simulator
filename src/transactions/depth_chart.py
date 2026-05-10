"""
Depth chart CRUD operations and auto-fallback logic (Phase 5 Prompt #3).

CRITICAL: This module contains ZERO SQL. All database access via src/db/queries.py.
Layer boundary: transactions/ → db/ → database.
"""

import sqlite3
from typing import Optional

from src.db.queries import (
    get_depth_chart, get_starter_for_position, get_backup_for_position,
    upsert_depth_chart_entry, delete_depth_chart_entry, clear_depth_chart_for_team,
    get_positions_for_player, get_injured_starters, get_depth_chart_restore_candidates,
    get_player, get_team, insert_player_event, get_team_roster,
    get_league_state, get_player_active_injury, log_lineup_controversy,
    update_sentiment_drivers,
)
from src.utils.constants import (
    DEPTH_CHART_POSITIONS, DEPTH_CHART_TO_PLAYER_POSITION,
    FLEXIBLE_POSITION_EQUIVALENTS, OUT_OF_POSITION_SAR_PENALTY,
    MAX_DEPTH_PER_POSITION, AUTO_PROMOTE_INJURY_STATUSES,
    LINEUP_CONTROVERSY_A_GRADE_THRESHOLD, LINEUP_CONTROVERSY_C_GRADE_THRESHOLD,
    LINEUP_CONTROVERSY_SENTIMENT_DELTA,
)


def validate_position_slot(position_slot: str) -> bool:
    """Check if position_slot is valid."""
    return position_slot in DEPTH_CHART_POSITIONS


def get_position_mismatch_penalty(player_position: str, depth_chart_slot: str) -> int:
    """
    Calculate SAR penalty when player's position doesn't match depth chart slot.

    Returns:
        0 if perfect match or flexible equivalent
        OUT_OF_POSITION_SAR_PENALTY if mismatch
    """
    expected_position = DEPTH_CHART_TO_PLAYER_POSITION.get(depth_chart_slot)

    if player_position == expected_position:
        return 0

    # Check flexible equivalents (e.g., OL can play any O-line slot)
    for generic_pos, allowed_slots in FLEXIBLE_POSITION_EQUIVALENTS.items():
        if player_position == generic_pos and depth_chart_slot in allowed_slots:
            return 0

    return OUT_OF_POSITION_SAR_PENALTY


def validate_player_eligibility(conn: sqlite3.Connection, player_id: int,
                                 team_id: int) -> tuple[bool, str]:
    """
    Check if player can be assigned to depth chart.

    Returns:
        (True, "") if eligible
        (False, error_message) if ineligible
    """
    player = get_player(conn, player_id)
    if not player:
        return False, f"Player {player_id} not found"

    if player['team_id'] != team_id:
        return False, f"Player {player['first_name']} {player['last_name']} not on team"

    if not player['is_active']:
        return False, f"Player {player['first_name']} {player['last_name']} is not active"

    return True, ""


def set_depth_chart_entry(conn: sqlite3.Connection, team_id: int, season_year: int,
                          position_slot: str, slot_order: int, player_id: int,
                          is_user_set: bool = True, notes: Optional[str] = None) -> tuple[bool, str]:
    """
    Set a depth chart entry (user command or auto-fill).

    Validates:
        - Position slot is valid
        - Slot order is 1-3
        - Player exists and is on team
        - Player not already assigned to another slot

    Returns:
        (True, success_message) if successful
        (False, error_message) if validation fails
    """
    # Validate position
    if not validate_position_slot(position_slot):
        return False, f"Invalid position slot '{position_slot}'"

    # Validate slot order
    if slot_order < 1 or slot_order > MAX_DEPTH_PER_POSITION:
        return False, f"Invalid slot order {slot_order} (must be 1-{MAX_DEPTH_PER_POSITION})"

    # Validate player eligibility
    eligible, error = validate_player_eligibility(conn, player_id, team_id)
    if not eligible:
        return False, error

    # Check for duplicate assignment (player already on depth chart)
    existing_assignments = get_positions_for_player(conn, player_id, season_year)
    for assignment in existing_assignments:
        if assignment['position_slot'] == position_slot and assignment['slot_order'] == slot_order:
            # Same slot - this is an update, not a duplicate
            continue
        return False, f"Player already assigned to {assignment['position_slot']} slot {assignment['slot_order']}"

    # Capture outgoing starter BEFORE the upsert (after upsert it's overwritten)
    outgoing_entry = None
    if slot_order == 1 and is_user_set:
        outgoing_entry = get_starter_for_position(conn, team_id, season_year, position_slot)

    # Insert or update
    with conn:
        upsert_depth_chart_entry(
            conn, team_id, season_year, position_slot, slot_order, player_id,
            is_user_set=1 if is_user_set else 0, replaced_player_id=None, notes=notes
        )

    # Phase 5 P5: lineup controversy detection (user-set starters only)
    if slot_order == 1 and is_user_set:
        _maybe_queue_lineup_controversy(
            conn, team_id, position_slot, player_id, season_year, outgoing_entry
        )

    player = get_player(conn, player_id)
    return True, f"Set {player['first_name']} {player['last_name']} as {position_slot} #{slot_order}"


def _maybe_queue_lineup_controversy(
    conn: sqlite3.Connection,
    team_id: int,
    position_slot: str,
    incoming_player_id: int,
    season_year: int,
    outgoing_entry,  # depth_chart row captured before the upsert, or None
) -> None:
    """Log a lineup controversy event if an extreme A→C demotion is detected.

    Fires when ALL conditions are true:
    - team is the user's team
    - outgoing starter has true_overall >= LINEUP_CONTROVERSY_A_GRADE_THRESHOLD
    - outgoing starter has no active injury
    - incoming player has true_overall <= LINEUP_CONTROVERSY_C_GRADE_THRESHOLD
    """
    if not outgoing_entry:
        return  # no existing starter to demote

    league = get_league_state(conn)
    if not league or league['user_team_id'] != team_id:
        return

    # Get full player record for outgoing (depth_chart row has player_id, not true_overall)
    outgoing = get_player(conn, outgoing_entry['player_id'])
    if not outgoing:
        return

    if outgoing['true_overall'] < LINEUP_CONTROVERSY_A_GRADE_THRESHOLD:
        return

    if get_player_active_injury(conn, outgoing['id']):
        return  # outgoing is injured — not a controversy

    incoming = get_player(conn, incoming_player_id)
    if not incoming:
        return

    if incoming['true_overall'] > LINEUP_CONTROVERSY_C_GRADE_THRESHOLD:
        return

    # All conditions met — log controversy and apply sentiment delta
    week_number = league['current_week']
    description = (
        f"Lineup controversy: benched {outgoing['first_name']} {outgoing['last_name']} "
        f"(OVR {outgoing['true_overall']}) for "
        f"{incoming['first_name']} {incoming['last_name']} "
        f"(OVR {incoming['true_overall']}) at {position_slot}"
    )
    with conn:
        log_lineup_controversy(conn, team_id, outgoing['id'], season_year, week_number, description)
        update_sentiment_drivers(conn, team_id, season_year, presser_delta=LINEUP_CONTROVERSY_SENTIMENT_DELTA)


def swap_depth_chart_positions(conn: sqlite3.Connection, team_id: int, season_year: int,
                                position_slot: str, slot_order_a: int,
                                slot_order_b: int) -> tuple[bool, str]:
    """
    Swap two players at different depth slots within same position.

    Example: Swap starter (slot 1) with backup (slot 2) at WR1.
    """
    if not validate_position_slot(position_slot):
        return False, f"Invalid position slot '{position_slot}'"

    entry_a = get_backup_for_position(conn, team_id, season_year, position_slot, slot_order_a)
    entry_b = get_backup_for_position(conn, team_id, season_year, position_slot, slot_order_b)

    if not entry_a:
        return False, f"No player at {position_slot} slot {slot_order_a}"
    if not entry_b:
        return False, f"No player at {position_slot} slot {slot_order_b}"

    # Swap: mark both as user-set (permanent)
    with conn:
        upsert_depth_chart_entry(
            conn, team_id, season_year, position_slot, slot_order_a, entry_b['player_id'],
            is_user_set=1, replaced_player_id=None, notes=f"Swapped with slot {slot_order_b}"
        )
        upsert_depth_chart_entry(
            conn, team_id, season_year, position_slot, slot_order_b, entry_a['player_id'],
            is_user_set=1, replaced_player_id=None, notes=f"Swapped with slot {slot_order_a}"
        )

    player_a = get_player(conn, entry_a['player_id'])
    player_b = get_player(conn, entry_b['player_id'])
    return True, f"Swapped {player_a['last_name']} ↔ {player_b['last_name']} at {position_slot}"


def remove_depth_chart_entry(conn: sqlite3.Connection, team_id: int, season_year: int,
                              position_slot: str, slot_order: int) -> tuple[bool, str]:
    """Remove a depth chart entry (revert to auto-selection for that slot)."""
    if not validate_position_slot(position_slot):
        return False, f"Invalid position slot '{position_slot}'"

    entry = get_backup_for_position(conn, team_id, season_year, position_slot, slot_order)
    if not entry:
        return False, f"No entry at {position_slot} slot {slot_order}"

    with conn:
        delete_depth_chart_entry(conn, team_id, season_year, position_slot, slot_order)

    player = get_player(conn, entry['player_id'])
    return True, f"Removed {player['last_name']} from {position_slot} slot {slot_order}"


def reset_team_depth_chart(conn: sqlite3.Connection, team_id: int,
                            season_year: int) -> tuple[bool, str]:
    """Clear all depth chart entries for a team (revert to full auto-selection)."""
    with conn:
        clear_depth_chart_for_team(conn, team_id, season_year)

    team = get_team(conn, team_id)
    return True, f"Reset depth chart for {team['city']} {team['nickname']}"


def initialize_depth_chart_for_team(conn: sqlite3.Connection, team_id: int, season_year: int):
    """
    Auto-populate depth chart with rating-based defaults (is_user_set=0).
    Called during franchise generation or new season setup.

    For each depth chart position:
        - Get all players at that generic position (e.g., all OL for LT)
        - Sort by true_overall DESC
        - Assign top 3 to slots 1, 2, 3 with is_user_set=0
    """
    roster = get_team_roster(conn, team_id)

    for depth_slot in DEPTH_CHART_POSITIONS:
        generic_position = DEPTH_CHART_TO_PLAYER_POSITION[depth_slot]

        # Get all players at this generic position
        candidates = [p for p in roster if p['position'] == generic_position]

        # Sort by overall (best first)
        candidates.sort(key=lambda p: p['true_overall'] if p['true_overall'] else 0, reverse=True)

        # Assign top 3 (or fewer if not enough players)
        for slot_order in range(1, min(MAX_DEPTH_PER_POSITION + 1, len(candidates) + 1)):
            player = candidates[slot_order - 1]
            upsert_depth_chart_entry(
                conn, team_id, season_year, depth_slot, slot_order, player['id'],
                is_user_set=0, replaced_player_id=None,
                notes="Auto-initialized"
            )

    conn.commit()


def process_injury_fallback(conn: sqlite3.Connection, team_id: int,
                             season_year: int, week_number: int) -> list[dict]:
    """
    Auto-promote backups when starters get injured.

    Called after each week's games (in season.py after heal_injured_players).

    Process:
        1. Find all starters (slot_order=1) with injury_status in AUTO_PROMOTE_INJURY_STATUSES
        2. For each injured starter:
            - Find backup at slot_order=2
            - If backup exists and is healthy:
                - Promote backup to slot_order=1 (is_user_set=0, replaced_player_id=original_starter)
                - Move injured starter to slot_order=2 temporarily
                - Insert player_event notification

    Returns:
        List of notification dicts for display to user
    """
    notifications = []
    injured_starters = get_injured_starters(conn, team_id, season_year)

    for entry in injured_starters:
        position_slot = entry['position_slot']
        injured_player_id = entry['player_id']

        # Find backup
        backup_entry = get_backup_for_position(conn, team_id, season_year, position_slot, 2)
        if not backup_entry:
            # No backup available - leave injured player as starter
            continue

        backup_player = get_player(conn, backup_entry['player_id'])
        if backup_player['injury_status'] in AUTO_PROMOTE_INJURY_STATUSES:
            # Backup also injured - skip
            continue

        # Promote backup to starter
        with conn:
            upsert_depth_chart_entry(
                conn, team_id, season_year, position_slot, 1, backup_entry['player_id'],
                is_user_set=0, replaced_player_id=injured_player_id,
                notes=f"Auto-promoted due to {entry['injury_status']}"
            )

            # Move injured starter to slot 2 (so they still appear on depth chart)
            upsert_depth_chart_entry(
                conn, team_id, season_year, position_slot, 2, injured_player_id,
                is_user_set=0, replaced_player_id=None,
                notes=f"Injured ({entry['injury_status']})"
            )

            # Insert notification
            insert_player_event(
                conn, backup_entry['player_id'], team_id, 'depth_chart_promotion',
                season_year, week_number,
                metadata_json=f'{{"position": "{position_slot}", "reason": "injury_fallback"}}'
            )

        injured_player = get_player(conn, injured_player_id)
        notifications.append({
            'position': position_slot,
            'injured': f"{injured_player['first_name']} {injured_player['last_name']}",
            'promoted': f"{backup_player['first_name']} {backup_player['last_name']}",
        })

    return notifications


def process_healing_restoration(conn: sqlite3.Connection, team_id: int,
                                 season_year: int, week_number: int) -> list[dict]:
    """
    Restore original starters when they heal (if auto-promoted backup is still there).

    Called after heal_injured_players() in season.py.

    Process:
        1. Find all entries where replaced_player_id is set and that player is now healthy
        2. For each:
            - Restore original starter to slot_order=1 (is_user_set=0, clear replaced_player_id)
            - Demote current starter back to slot_order=2
            - Insert player_event notification

    Returns:
        List of notification dicts for display
    """
    notifications = []
    restore_candidates = get_depth_chart_restore_candidates(conn, team_id, season_year)

    for entry in restore_candidates:
        position_slot = entry['position_slot']
        current_starter_id = entry['player_id']
        original_starter_id = entry['replaced_player_id']

        # Only restore if current entry is not user-set (ephemeral auto-promotion)
        if entry['is_user_set'] == 1:
            continue

        # Restore original starter
        with conn:
            upsert_depth_chart_entry(
                conn, team_id, season_year, position_slot, 1, original_starter_id,
                is_user_set=0, replaced_player_id=None,
                notes="Restored after healing"
            )

            # Demote auto-promoted backup back to slot 2
            upsert_depth_chart_entry(
                conn, team_id, season_year, position_slot, 2, current_starter_id,
                is_user_set=0, replaced_player_id=None,
                notes="Demoted after original starter healed"
            )

            # Insert notification
            insert_player_event(
                conn, original_starter_id, team_id, 'depth_chart_restoration',
                season_year, week_number,
                metadata_json=f'{{"position": "{position_slot}", "reason": "healing"}}'
            )

        original_player = get_player(conn, original_starter_id)
        demoted_player = get_player(conn, current_starter_id)
        notifications.append({
            'position': position_slot,
            'restored': f"{original_player['first_name']} {original_player['last_name']}",
            'demoted': f"{demoted_player['first_name']} {demoted_player['last_name']}",
        })

    return notifications
