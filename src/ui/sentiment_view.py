"""Sentiment display module (Phase 5 P8).

Pure rendering — no SQL, no business logic.
All data arrives pre-computed from sentiment_explainer.py.
"""
from __future__ import annotations

_TIER_LABELS = {
    'untouchable': 'Untouchable',
    'stable':      'Stable',
    'warm':        'Warm',
    'hot':         'Hot Seat',
    'termination': 'Termination',
}


def _tier_label(raw: str) -> str:
    return _TIER_LABELS.get(raw, raw.capitalize())


def print_owner_sentiment(result: dict, coach_name: str, season_year: int) -> None:
    """Print owner sentiment contributor summary."""
    tier = _tier_label(result.get('current_tier', 'unknown'))
    net = result.get('net_change', 0)
    contributors = result.get('contributors', [])

    print(f"\n=== Owner Sentiment: Coach {coach_name} ({season_year} season) ===")
    print(f"Current tier: {tier}")
    sign = '+' if net >= 0 else ''
    print(f"Net change season-to-date: {sign}{net}")

    if contributors:
        print("\nTop contributors:")
        for c in contributors:
            s = '+' if c['delta'] >= 0 else ''
            detail = f" — {c['detail']}" if c.get('detail') else ''
            week_str = f" (Week {c['week_number']})" if c.get('week_number') else ''
            print(f"  {s}{c['delta']:3d}  {c['reason_label']}{week_str}{detail}")
    else:
        print("\n  No sentiment contributors recorded yet.")


def print_player_satisfaction(result: dict, player_name: str, season_year: int) -> None:
    """Print player satisfaction event summary."""
    state = result.get('current_state', 'Unknown')
    events = result.get('events', [])

    print(f"\n=== Player Satisfaction: {player_name} ({season_year} season) ===")
    print(f"Current state: {state}")

    if events:
        print("\nTop events:")
        for e in events:
            s = '+' if e['delta'] >= 0 else ''
            week_str = f" (Week {e['week_number']})" if e.get('week_number') else ''
            print(f"  {s}{e['delta']:3d}  {e['reason_label']}{week_str}")
    else:
        print("\n  No satisfaction events recorded this season.")


def print_all_players_concerns(
    concerns: list[dict], season_year: int, threshold: int,
) -> None:
    """Print a list of players with satisfaction below threshold."""
    print(f"\n=== Player Satisfaction Concerns ({season_year} season) ===")
    print(f"Players with satisfaction < {threshold}:")

    if not concerns:
        print("  (none)")
        return

    print(f"  {'Name':<24} {'Pos':<5} {'Sat':>4}  Top reason")
    print("  " + "-" * 60)
    for c in concerns:
        reason = c.get('top_reason') or '—'
        print(f"  {c['name']:<24} {c['position']:<5} {c['satisfaction']:>4}  {reason}")
