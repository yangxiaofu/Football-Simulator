"""
Player development and aging logic.

Updates player ratings between seasons based on age, development trait,
and position. Young players grow, veterans decline.
"""

import random
import sqlite3

from ..db.queries import (
    get_all_active_players,
    get_player,
    update_player_attribute,
    insert_attribute_history,
)
from ..utils.constants import (
    RATING_MIN,
    RATING_MAX,
    DEVELOPMENT_GAIN_SUPERSTAR,
    DEVELOPMENT_GAIN_STAR,
    DEVELOPMENT_GAIN_NORMAL,
    DEVELOPMENT_GAIN_SLOW,
    DEVELOPMENT_AGE_PEAK,
    DEVELOPMENT_AGE_PLATEAU,
    DEVELOPMENT_AGE_DECLINE,
    AGING_DECLINE_BY_POSITION,
    AGING_SPEED_MULTIPLIER,
    AGING_STRENGTH_MULTIPLIER,
    AGING_IQ_MULTIPLIER,
    IQ_DEVELOPMENT_MULTIPLIER,
    SPEED_ATTRIBUTES,
    STRENGTH_ATTRIBUTES,
    IQ_ATTRIBUTES,
    ALL_TRUE_ATTRIBUTES,
    POSITION_ATTRIBUTES,
)


# Map development trait to gain range
_TRAIT_GAIN_MAP = {
    'superstar': DEVELOPMENT_GAIN_SUPERSTAR,
    'star': DEVELOPMENT_GAIN_STAR,
    'normal': DEVELOPMENT_GAIN_NORMAL,
    'slow': DEVELOPMENT_GAIN_SLOW,
}


def run_development_pass(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Run development updates for all players in peak/plateau age range.

    Players aged 22-26 get full development gains.
    Players aged 27-29 get reduced development gains.

    Returns dict with counts.
    """
    players = get_all_active_players(conn)
    developed_count = 0
    total_changes = 0

    for player in players:
        p = dict(player)
        age = p['age']
        pos = p['position']
        trait = p.get('development_trait', 'normal')
        ceiling = p.get('true_ceiling', RATING_MAX)

        # Only develop players in the growth age range
        if age < DEVELOPMENT_AGE_PEAK[0] or age > DEVELOPMENT_AGE_PLATEAU[1]:
            continue

        # Determine gain range based on trait
        gain_range = _TRAIT_GAIN_MAP.get(trait, DEVELOPMENT_GAIN_NORMAL)

        # Plateau age bracket gets half the gain
        if age >= DEVELOPMENT_AGE_PLATEAU[0]:
            max_gain = max(0, gain_range[1] // 2)
            gain_range = (0, max_gain)

        if gain_range[1] <= 0:
            continue

        # Get all applicable attributes for this position
        attrs = list(ALL_TRUE_ATTRIBUTES)
        pos_attrs = POSITION_ATTRIBUTES.get(pos, [])
        attrs.extend(pos_attrs)
        # Remove duplicates while preserving order
        seen = set()
        unique_attrs = []
        for a in attrs:
            if a not in seen:
                seen.add(a)
                unique_attrs.append(a)

        player_changed = False
        for attr in unique_attrs:
            current_val = p.get(attr)
            if current_val is None:
                continue

            # Roll development gain
            gain = random.randint(gain_range[0], gain_range[1])
            if gain <= 0:
                continue

            # Apply attribute-specific multipliers
            if attr in SPEED_ATTRIBUTES:
                # Speed develops normally during youth
                pass
            elif attr in IQ_ATTRIBUTES:
                # IQ develops a bit faster (experience-based)
                gain = int(gain * IQ_DEVELOPMENT_MULTIPLIER)

            new_val = min(ceiling, min(RATING_MAX, current_val + gain))

            if new_val != current_val:
                update_player_attribute(conn, p['id'], attr, new_val)
                insert_attribute_history(
                    conn, p['id'], season_year, attr,
                    current_val, new_val, 'development',
                )
                total_changes += 1
                player_changed = True

        # Update true_overall to reflect changes
        if player_changed:
            _recalculate_overall(conn, p['id'], season_year)
            developed_count += 1

    return {
        'players_developed': developed_count,
        'total_attribute_changes': total_changes,
    }


def run_aging_pass(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Apply age-based decline for players 30+.

    Returns dict with counts.
    """
    players = get_all_active_players(conn)
    aged_count = 0
    total_changes = 0

    for player in players:
        p = dict(player)
        age = p['age']
        pos = p['position']

        if age < DEVELOPMENT_AGE_DECLINE:
            continue

        raw_decline = AGING_DECLINE_BY_POSITION.get(pos, (-1, -3))
        # Ensure range is ordered (most negative first for randint)
        decline_range = (min(raw_decline), max(raw_decline))
        # Older players decline faster
        age_factor = 1.0 + (age - DEVELOPMENT_AGE_DECLINE) * 0.1

        attrs = list(ALL_TRUE_ATTRIBUTES)
        pos_attrs = POSITION_ATTRIBUTES.get(pos, [])
        attrs.extend(pos_attrs)
        seen = set()
        unique_attrs = []
        for a in attrs:
            if a not in seen:
                seen.add(a)
                unique_attrs.append(a)

        player_changed = False
        for attr in unique_attrs:
            current_val = p.get(attr)
            if current_val is None:
                continue

            # Base decline
            decline = random.randint(decline_range[0], decline_range[1])

            # Apply attribute-specific multipliers
            if attr in SPEED_ATTRIBUTES:
                decline = int(decline * AGING_SPEED_MULTIPLIER)
            elif attr in STRENGTH_ATTRIBUTES:
                decline = int(decline * AGING_STRENGTH_MULTIPLIER)
            elif attr in IQ_ATTRIBUTES:
                decline = int(decline * AGING_IQ_MULTIPLIER)

            # Apply age factor (older = more decline)
            decline = int(decline * age_factor)

            # Decline is negative, so we add it
            new_val = max(RATING_MIN, current_val + decline)

            if new_val != current_val:
                update_player_attribute(conn, p['id'], attr, new_val)
                insert_attribute_history(
                    conn, p['id'], season_year, attr,
                    current_val, new_val, 'aging',
                )
                total_changes += 1
                player_changed = True

        if player_changed:
            _recalculate_overall(conn, p['id'], season_year)
            aged_count += 1

    return {
        'players_aged': aged_count,
        'total_attribute_changes': total_changes,
    }


def _recalculate_overall(
    conn: sqlite3.Connection, player_id: int, season_year: int,
) -> None:
    """Recalculate a player's true_overall from their individual attributes.

    Overall = weighted average of all non-null position-relevant attributes.
    """
    player = get_player(conn, player_id)
    if not player:
        return

    p = dict(player)
    pos = p['position']

    # Core attributes everyone has
    core_attrs = ['true_speed', 'true_strength', 'true_football_iq',
                  'true_durability', 'true_clutch']
    pos_attrs = POSITION_ATTRIBUTES.get(pos, [])

    all_attrs = core_attrs + pos_attrs
    values = []
    for attr in all_attrs:
        val = p.get(attr)
        if val is not None:
            values.append(val)

    if not values:
        return

    new_overall = int(round(sum(values) / len(values)))
    new_overall = max(RATING_MIN, min(RATING_MAX, new_overall))

    # Enforce ceiling
    ceiling = p.get('true_ceiling', RATING_MAX)
    new_overall = min(new_overall, ceiling)

    old_overall = p['true_overall']
    if new_overall != old_overall:
        update_player_attribute(conn, player_id, 'true_overall', new_overall)
        insert_attribute_history(
            conn, player_id, season_year, 'true_overall',
            old_overall, new_overall,
            'development' if new_overall > old_overall else 'aging',
        )


def run_full_development(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Run both development and aging passes.

    Returns combined results.
    """
    dev_result = run_development_pass(conn, season_year)
    age_result = run_aging_pass(conn, season_year)

    return {
        'players_developed': dev_result['players_developed'],
        'players_aged': age_result['players_aged'],
        'total_attribute_changes': (
            dev_result['total_attribute_changes'] +
            age_result['total_attribute_changes']
        ),
    }
