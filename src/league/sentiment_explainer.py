"""Sentiment transparency explainer (Phase 5 P8).

Reads owner_sentiment and satisfaction_event, derives top contributors,
and returns structured data for display. No inline SQL — all DB access
via src.db.queries.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from ..db.queries import (
    get_owner_sentiment,
    get_owner_sentiment_history,
    get_player_satisfaction,
    get_satisfaction_events_for_player,
    get_players_below_satisfaction_threshold,
)
from ..utils.constants import (
    OWNER_SENTIMENT_REASONS,
    PLAYER_SATISFACTION_REASONS,
    SENTIMENT_TOP_CONTRIBUTORS_COUNT,
    SENTIMENT_WEEKLY_SUMMARY_TOP_COUNT,
)

# Maps each owner_sentiment driver column to a reason code by sign.
# Only columns that are regularly non-zero are included.
_DRIVER_REASON_MAP = {
    'wins_vs_expectation': {'positive': 'win_signature',       'negative': 'loss_blowout'},
    'cap_management_score': {'positive': 'trade_received_value', 'negative': 'cap_pressure_high'},
    'star_holdout_penalty': {'negative': 'contract_dispute'},
    'playoff_bonus':        {'positive': 'season_outlook_improve'},
    'championship_bonus':   {'positive': 'win_signature'},
    'presser_delta':        {'positive': 'press_response_strong', 'negative': 'press_response_fumble'},
}


def _driver_contributors(row) -> list[dict]:
    """Derive contributor list from driver column values on an owner_sentiment row."""
    contributors = []
    for col, reasons in _DRIVER_REASON_MAP.items():
        try:
            val = row[col]
        except (IndexError, KeyError):
            continue
        if val == 0:
            continue
        key = 'positive' if val > 0 else 'negative'
        reason_code = reasons.get(key)
        if reason_code is None:
            continue
        contributors.append({
            'reason_code': reason_code,
            'reason_label': OWNER_SENTIMENT_REASONS.get(reason_code, reason_code),
            'delta': val,
            'detail': None,
            'week_number': None,
        })

    # If the row has a specific reason_code set (e.g. 'lineup_controversy'), prepend it
    try:
        rc = row['reason_code']
        rd = row['reason_detail'] if 'reason_detail' in row.keys() else None
    except (IndexError, KeyError, AttributeError):
        rc = rd = None

    if rc and rc != 'legacy_unknown':
        # Prepend as highest-priority contributor — use presser_delta as its delta if available
        try:
            rc_delta = row['presser_delta'] or -1
        except (IndexError, KeyError):
            rc_delta = -1
        contributors.insert(0, {
            'reason_code': rc,
            'reason_label': OWNER_SENTIMENT_REASONS.get(rc, rc),
            'delta': rc_delta,
            'detail': rd,
            'week_number': None,
        })

    return sorted(contributors, key=lambda c: abs(c['delta']), reverse=True)


def explain_owner_sentiment(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_filter: Optional[int] = None,
    top_n: Optional[int] = None,
) -> dict:
    """Return top sentiment contributors for a team's owner sentiment.

    Returns:
        {
            'current_tier': str,
            'net_change': int,
            'contributors': [{'reason_code', 'reason_label', 'delta', 'detail', 'week_number'}, ...]
        }
    """
    if top_n is None:
        top_n = SENTIMENT_TOP_CONTRIBUTORS_COUNT

    row = get_owner_sentiment(conn, team_id, season_year)
    if row is None:
        return {'current_tier': 'unknown', 'net_change': 0, 'contributors': []}

    tier = row['hot_seat_tier'] or 'stable'
    # Net change = sum of all driver columns
    driver_cols = [
        'wins_vs_expectation', 'cap_management_score', 'star_holdout_penalty',
        'playoff_bonus', 'championship_bonus', 'presser_delta',
    ]
    net = sum(row[c] for c in driver_cols if row[c] is not None)

    contributors = _driver_contributors(row)[:top_n]
    return {'current_tier': tier, 'net_change': net, 'contributors': contributors}


def explain_player_satisfaction(
    conn: sqlite3.Connection,
    player_id: int,
    season_year: int,
    top_n: Optional[int] = None,
) -> dict:
    """Return top satisfaction-changing events for a player.

    Returns:
        {
            'current_state': str,
            'events': [{'reason_code', 'reason_label', 'delta', 'detail', 'week_number'}, ...]
        }
    """
    if top_n is None:
        top_n = SENTIMENT_TOP_CONTRIBUTORS_COUNT

    events_raw = get_satisfaction_events_for_player(conn, player_id, season_year)
    current_sat = get_player_satisfaction(conn, player_id) or 50

    if current_sat >= 70:
        current_state = 'Content'
    elif current_sat >= 50:
        current_state = 'Neutral'
    elif current_sat >= 30:
        current_state = 'Frustrated'
    else:
        current_state = 'Disgruntled'

    events = []
    for ev in events_raw:
        try:
            rc = ev['reason_code']
        except (IndexError, KeyError):
            rc = None
        if not rc or rc == 'legacy_unknown':
            # Fall back to the free-form reason text
            label = ev['reason'] if ev['reason'] else '(legacy — reason not tracked)'
            rc = 'legacy_unknown'
        else:
            label = PLAYER_SATISFACTION_REASONS.get(rc, rc)
        events.append({
            'reason_code': rc,
            'reason_label': label,
            'delta': ev['delta'],
            'detail': None,
            'week_number': ev['week'],
        })

    # Sort by absolute delta descending, take top_n
    events.sort(key=lambda e: abs(e['delta']), reverse=True)
    return {'current_state': current_state, 'events': events[:top_n]}


def get_weekly_owner_sentiment_summary(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Optional[dict]:
    """Return top contributors for the weekly summary embed in season.py.

    Returns None if all sentiment drivers are zero (nothing to display).
    Returns a dict with 'current_tier', 'net_change', 'contributors' otherwise.
    """
    result = explain_owner_sentiment(conn, team_id, season_year,
                                     top_n=SENTIMENT_WEEKLY_SUMMARY_TOP_COUNT)
    if result['net_change'] == 0 and not result['contributors']:
        return None
    return result


def get_all_player_satisfaction_concerns(
    conn: sqlite3.Connection,
    season_year: int,
    threshold: Optional[int] = None,
) -> list[dict]:
    """Return players with satisfaction below threshold with their most recent event reason.

    Default threshold: 40.
    """
    if threshold is None:
        threshold = 40

    players = get_players_below_satisfaction_threshold(conn, season_year, threshold)
    result = []
    for p in players:
        events = get_satisfaction_events_for_player(conn, p['id'], season_year)
        top_reason = None
        if events:
            last = events[-1]
            try:
                rc = last['reason_code']
            except (IndexError, KeyError):
                rc = None
            if rc and rc != 'legacy_unknown':
                top_reason = PLAYER_SATISFACTION_REASONS.get(rc, rc)
            else:
                top_reason = last['reason']
        result.append({
            'player_id': p['id'],
            'name': p['name'],
            'position': p['position'],
            'satisfaction': p['satisfaction'],
            'top_reason': top_reason,
        })
    return result
