"""
Trade evaluation display module (Phase 5 Prompt #6).

Pure presentation — no SQL, no business logic.
All inputs are pre-computed dicts from src/transactions/trades.py.
"""

from ..utils.constants import (
    ANSI_BOLD as BOLD,
    ANSI_RESET as RESET,
    ANSI_GREEN as GREEN,
    ANSI_YELLOW as YELLOW,
    ANSI_RED as RED,
    ANSI_CYAN as CYAN,
    ANSI_DIM as DIM,
)


def render_player_value(value_dict: dict) -> None:
    """Print single-asset valuation."""
    if not value_dict:
        print("Player not found.")
        return

    name = value_dict['player_name']
    pos = value_dict['true_position']
    grade = value_dict['overall_letter']
    age = value_dict.get('age', '?')
    v_low = value_dict['value_low']
    v_high = value_dict['value_high']
    comparables = value_dict.get('comparable_assets', [])

    print()
    print(f"{BOLD}=== Player Value: {pos} {name} ({grade}, {age}) ==={RESET}")
    print(f"Estimated value range: {CYAN}{v_low:,}{RESET} – {CYAN}{v_high:,}{RESET} trade units")
    if comparables:
        print("Comparable assets:")
        for c in comparables:
            print(f"  - {c}")
    print()


def render_trade_estimate(
    estimate_dict: dict,
    giving_abbr: str,
    receiving_abbr: str,
) -> None:
    """Print dry-run trade evaluation."""
    if not estimate_dict:
        print("Could not evaluate trade.")
        return

    g_val = estimate_dict['giving_value']
    r_val = estimate_dict['receiving_value']
    gap_pct = estimate_dict['value_gap_pct'] * 100
    prob = estimate_dict['acceptance_probability']
    predicted = estimate_dict['predicted_response']
    reason = estimate_dict.get('reason_code')
    counter = estimate_dict.get('counter_offer')

    gap_sign = '+' if gap_pct >= 0 else ''
    gap_color = GREEN if gap_pct > 0 else (RED if gap_pct < -5 else YELLOW)

    print()
    print(f"{BOLD}=== Trade Estimate: {giving_abbr} ↔ {receiving_abbr} ==={RESET}")
    print(f"You give:  (value: {g_val:,})")
    print(f"You get:   (value: {r_val:,})")
    print(f"Value gap: {gap_color}{gap_sign}{gap_pct:.1f}%{RESET} "
          f"({'in your favor' if gap_pct > 0 else 'against you' if gap_pct < 0 else 'even'})")
    print()
    print(f"{receiving_abbr}'s assessment: {BOLD}{predicted}{RESET}")
    print(f"Acceptance probability: {prob:.0%}")
    if reason and predicted == 'likely_reject':
        from ..utils.constants import TRADE_REJECTION_REASONS
        reason_text = TRADE_REJECTION_REASONS.get(reason, reason)
        print(f"Likely reason: {DIM}{reason_text}{RESET}")
    if counter:
        print(f"\nPossible counter: {counter.get('message', 'See details')}")
    print()


def render_shop_results(shop_dict: dict) -> None:
    """Print trade shopping results across all AI teams."""
    if not shop_dict:
        print("Player not found.")
        return

    name = shop_dict['player_name']
    pos = shop_dict['true_position']
    grade = shop_dict['overall_letter']
    tiers = shop_dict.get('tiers', {})
    estimates = shop_dict.get('top_offer_estimates', {})

    high = tiers.get('HIGH', [])
    moderate = tiers.get('MODERATE', [])
    low = tiers.get('LOW', [])
    no = tiers.get('NO', [])

    print()
    print(f"{BOLD}=== Trade Interest in {pos} {name} ({grade}) ==={RESET}")

    if high:
        print(f"{GREEN}{BOLD}HIGH{RESET}  (would offer near full value): "
              f"  {', '.join(high)}")
    else:
        print(f"{DIM}HIGH  (would offer near full value):   — none{RESET}")

    if moderate:
        print(f"{YELLOW}MODERATE{RESET}  (50–80% of value): "
              f"           {', '.join(moderate)}")
    else:
        print(f"{DIM}MODERATE  (50–80% of value):           — none{RESET}")

    if low:
        label = f"{len(low)} other team{'s' if len(low) != 1 else ''}"
        print(f"{DIM}LOW  (20–50%):                         {label}{RESET}")
    else:
        print(f"{DIM}LOW  (20–50%):                         — none{RESET}")

    not_interested = len(no)
    if not_interested:
        print(f"Not interested:                        {not_interested} other team{'s' if not_interested != 1 else ''}")
    print()
