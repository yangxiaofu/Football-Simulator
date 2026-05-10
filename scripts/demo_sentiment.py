#!/usr/bin/env python3
"""
Demo script showing owner sentiment system in action.

Creates a test scenario where we can see sentiment change based on performance.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.db.connection import get_connection
from src.db.queries import (
    get_owner_sentiment,
    get_all_teams,
    insert_owner_sentiment,
)
from src.league.owner_sentiment import (
    initialize_sentiment,
    set_preseason_expectation,
    update_wins_delta_after_game,
    finalize_season_sentiment,
    classify_hot_seat_tier,
    get_firing_probability,
)


def demo_sentiment_system():
    """Demo the owner sentiment system with a sample team."""
    print("\n" + "="*70)
    print("OWNER SENTIMENT SYSTEM DEMONSTRATION")
    print("="*70)

    # Create test database
    db_path = "saves/sentiment_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    print("\nGenerating test database...")
    os.system(f"python generate.py {db_path} --season 2024 > /dev/null 2>&1")

    conn = get_connection(db_path)
    teams = get_all_teams(conn)
    demo_team = teams[0]  # Use first team
    season_year = 2024

    print(f"\n{'='*70}")
    print(f"TEAM: {demo_team['city']} {demo_team['nickname']} (ID: {demo_team['id']})")
    print(f"SEASON: {season_year}")
    print(f"{'='*70}")

    # Initialize sentiment
    initialize_sentiment(conn, demo_team['id'], season_year)
    conn.commit()

    # Set preseason expectation
    conn.execute(
        "UPDATE team SET team_phase = 'win_now' WHERE id = ?",
        (demo_team['id'],)
    )
    conn.commit()

    set_preseason_expectation(conn, demo_team['id'], season_year)
    conn.commit()

    sentiment = get_owner_sentiment(conn, demo_team['id'], season_year)

    print(f"\n1. PRESEASON EXPECTATION")
    print(f"   Team Phase: win_now")
    print(f"   Expectation Tier: {sentiment['preseason_expectation']}")
    print(f"   Target Wins: 12 (championship expectation)")
    print(f"   Initial Sentiment: {sentiment['sentiment_score']}/100")
    print(f"   Hot Seat Tier: {sentiment['hot_seat_tier']}")

    # Simulate a poor season (3 wins)
    print(f"\n2. SIMULATING SEASON (3-14 record)...")
    print(f"   Expected: 12 wins")
    print(f"   Actual: 3 wins")
    print(f"   Delta: -9 wins")

    # Add team_season_record
    conn.execute("""
        INSERT INTO team_season_record
        (team_id, season_year, wins, losses, points_for, points_against, made_playoffs)
        VALUES (?, ?, 3, 14, 200, 400, 0)
    """, (demo_team['id'], season_year))
    conn.commit()

    # Simulate wins updates (3 wins total)
    for i in range(3):
        update_wins_delta_after_game(conn, demo_team['id'], season_year, won=True)
        conn.commit()

    # Finalize sentiment
    finalize_season_sentiment(conn, demo_team['id'], season_year)
    conn.commit()

    sentiment = get_owner_sentiment(conn, demo_team['id'], season_year)

    print(f"\n3. END-OF-SEASON SENTIMENT")
    print(f"   Sentiment Drivers:")
    print(f"     Wins vs Expectation: {sentiment['wins_vs_expectation']} (-9 wins × -5 weight)")
    print(f"     Cap Management: {sentiment['cap_management_score']}")
    print(f"     Star Holdouts: {sentiment['star_holdout_penalty']}")
    print(f"     Playoff Bonus: {sentiment['playoff_bonus']} (missed playoffs)")
    print(f"     Championship Bonus: {sentiment['championship_bonus']}")
    print(f"   Final Score: {sentiment['sentiment_score']}/100")
    print(f"   Hot Seat Tier: {sentiment['hot_seat_tier']}")

    # Show firing probability
    fire_prob = get_firing_probability(sentiment['hot_seat_tier'], is_mid_season=False)
    print(f"\n4. FIRING PROBABILITY")
    print(f"   Tier: {sentiment['hot_seat_tier']}")
    print(f"   End-of-Season Fire Probability: {fire_prob*100:.0f}%")

    # Show what different records would produce
    print(f"\n5. HYPOTHETICAL SCENARIOS")
    print(f"   What if team had won different amounts?")
    print(f"   {'Wins':<6} {'Delta':<8} {'Sentiment':<12} {'Tier':<14} {'Fire %'}")
    print(f"   {'-'*60}")

    for wins in [0, 3, 6, 9, 12, 15]:
        delta = wins - 12
        sentiment_score = 70 + (delta * 5)  # Simplified (just wins driver)
        tier = classify_hot_seat_tier(sentiment_score)
        prob = get_firing_probability(tier, is_mid_season=False)
        print(f"   {wins:<6} {delta:<8} {sentiment_score:<12} {tier:<14} {prob*100:.0f}%")

    print(f"\n{'='*70}")
    print("DEMONSTRATION COMPLETE")
    print("="*70)

    conn.close()

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    demo_sentiment_system()
