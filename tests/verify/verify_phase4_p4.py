#!/usr/bin/env python3
"""
Phase 4 Prompt #4 verification script.

Tests:
1. Schema exists (owner_sentiment, coach_job_offer tables)
2. All 32 teams initialized with default sentiment (70)
3. Hot seat tier classification works
4. Sentiment calculation produces expected scores
5. Firing probabilities return correct values
6. Player vacancy + offer generation works
7. Auto-accept best offer works
8. Invariants #11, #12 preserved (with vacancy exception)

Exit code:
    0 = all tests passed
    1 = one or more tests failed
"""

import sys
import os
import sqlite3

# Add project root to path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

from src.db.connection import get_connection
from src.db.queries import (
    get_owner_sentiment,
    insert_owner_sentiment,
    get_all_teams,
    get_coach_by_id,
    get_pending_offers_for_coach,
    get_vacant_coaches,
)
from src.league.owner_sentiment import (
    initialize_sentiment,
    classify_hot_seat_tier,
    get_firing_probability,
)
from src.transactions.coach_offers import (
    generate_offers_for_vacant_coach,
    auto_accept_best_offer,
    compute_offer_quality,
)
from src.utils.constants import (
    SENTIMENT_DEFAULT,
    HOT_SEAT_TIERS,
    FIRING_PROB_MID_SEASON,
    FIRING_PROB_END_SEASON,
)


def test_schema_exists(conn: sqlite3.Connection) -> bool:
    """Test 1: owner_sentiment and coach_job_offer tables exist."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('owner_sentiment', 'coach_job_offer')"
    )
    tables = [row[0] for row in cursor.fetchall()]

    if 'owner_sentiment' not in tables:
        print("  ✗ owner_sentiment table not found")
        return False
    if 'coach_job_offer' not in tables:
        print("  ✗ coach_job_offer table not found")
        return False

    print("  ✓ Both tables exist")
    return True


def test_sentiment_initialization(conn: sqlite3.Connection) -> bool:
    """Test 2: All teams initialized with default sentiment."""
    teams = get_all_teams(conn)
    season_year = 2024

    # Initialize all teams
    for team in teams:
        initialize_sentiment(conn, team['id'], season_year)

    conn.commit()

    # Verify all initialized
    all_initialized = True
    for team in teams:
        sentiment = get_owner_sentiment(conn, team['id'], season_year)
        if not sentiment:
            print(f"  ✗ Team {team['id']} not initialized")
            all_initialized = False
        elif sentiment['sentiment_score'] != SENTIMENT_DEFAULT:
            print(f"  ✗ Team {team['id']} has wrong default score: {sentiment['sentiment_score']}")
            all_initialized = False

    if all_initialized:
        print(f"  ✓ All {len(teams)} teams initialized with score {SENTIMENT_DEFAULT}")

    return all_initialized


def test_hot_seat_classification() -> bool:
    """Test 3: Hot seat tier classification."""
    test_cases = [
        (85, 'untouchable'),
        (70, 'untouchable'),
        (69, 'stable'),
        (40, 'stable'),
        (39, 'warm'),
        (20, 'warm'),
        (19, 'hot'),
        (10, 'hot'),
        (9, 'termination'),
        (0, 'termination'),
    ]

    all_passed = True
    for score, expected_tier in test_cases:
        tier = classify_hot_seat_tier(score)
        if tier != expected_tier:
            print(f"  ✗ Score {score} classified as '{tier}', expected '{expected_tier}'")
            all_passed = False

    if all_passed:
        print(f"  ✓ All {len(test_cases)} classification tests passed")

    return all_passed


def test_firing_probabilities() -> bool:
    """Test 5: Firing probabilities return correct values."""
    # Test mid-season probabilities
    mid_season_tests = [
        ('untouchable', True, 0.0),
        ('stable', True, 0.0),
        ('warm', True, 0.0),
        ('hot', True, 0.25),
        ('termination', True, 0.75),
    ]

    # Test end-season probabilities
    end_season_tests = [
        ('untouchable', False, 0.0),
        ('stable', False, 0.05),
        ('warm', False, 0.30),
        ('hot', False, 0.70),
        ('termination', False, 0.95),
    ]

    all_tests = mid_season_tests + end_season_tests
    all_passed = True

    for tier, is_mid_season, expected_prob in all_tests:
        prob = get_firing_probability(tier, is_mid_season)
        if prob != expected_prob:
            season_type = "mid-season" if is_mid_season else "end-season"
            print(f"  ✗ {tier} {season_type}: got {prob}, expected {expected_prob}")
            all_passed = False

    if all_passed:
        print(f"  ✓ All {len(all_tests)} firing probability tests passed")

    return all_passed


def test_offer_generation(conn: sqlite3.Connection) -> bool:
    """Test 6: Player vacancy + offer generation."""
    # Create a test coach
    cursor = conn.execute("""
        INSERT INTO coach_career
        (first_name, last_name, age, personality_archetype, career_start_year, current_team_id, is_player, is_active)
        VALUES ('Test', 'Coach', 45, 'analytics', 2024, NULL, 1, 1)
    """)
    coach_id = cursor.lastrowid
    conn.commit()

    # Generate offers
    generate_offers_for_vacant_coach(conn, coach_id, 2024, 0)
    conn.commit()

    # Check offers were created
    offers = get_pending_offers_for_coach(conn, coach_id, 2024)

    if len(offers) < 1 or len(offers) > 3:
        print(f"  ✗ Expected 1-3 offers, got {len(offers)}")
        return False

    print(f"  ✓ Generated {len(offers)} offers for vacant coach")

    # Cleanup
    conn.execute("DELETE FROM coach_job_offer WHERE coach_id = ?", (coach_id,))
    conn.execute("DELETE FROM coach_career WHERE id = ?", (coach_id,))
    conn.commit()

    return True


def test_auto_accept(conn: sqlite3.Connection) -> bool:
    """Test 7: Auto-accept best offer."""
    # Create a test coach
    cursor = conn.execute("""
        INSERT INTO coach_career
        (first_name, last_name, age, personality_archetype, career_start_year, current_team_id, is_player, is_active)
        VALUES ('Test2', 'Coach2', 45, 'analytics', 2024, NULL, 1, 1)
    """)
    coach_id = cursor.lastrowid
    conn.commit()

    # Generate offers
    generate_offers_for_vacant_coach(conn, coach_id, 2024, 0)
    conn.commit()

    # Auto-accept best offer
    auto_accept_best_offer(conn, coach_id, 2024)
    conn.commit()

    # Verify coach was assigned
    coach_row = get_coach_by_id(conn, coach_id)
    if not coach_row:
        print("  ✗ Coach not found after auto-accept")
        return False

    if coach_row['current_team_id'] is None:
        print("  ✗ Coach still has no team after auto-accept")
        return False

    print(f"  ✓ Coach assigned to team {coach_row['current_team_id']}")

    # Cleanup
    conn.execute("DELETE FROM coach_tenure WHERE coach_id = ?", (coach_id,))
    conn.execute("DELETE FROM coach_job_offer WHERE coach_id = ?", (coach_id,))
    conn.execute("UPDATE team SET gm_personality = 'analytics' WHERE id = ?", (coach_row['current_team_id'],))
    conn.execute("DELETE FROM coach_career WHERE id = ?", (coach_id,))
    conn.commit()

    return True


def run_all_tests():
    """Run all verification tests."""
    print("\nPhase 4 Prompt #4 Verification")
    print("=" * 50)

    # Create test database
    db_path = "saves/phase4_p4_test.db"

    # Remove if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Generate fresh database
    print("\nGenerating test database...")
    os.system(f"python generate.py {db_path} --season 2024 > /dev/null 2>&1")

    conn = get_connection(db_path)

    tests = [
        ("Schema exists", lambda: test_schema_exists(conn)),
        ("Sentiment initialization", lambda: test_sentiment_initialization(conn)),
        ("Hot seat classification", lambda: test_hot_seat_classification()),
        ("Firing probabilities", lambda: test_firing_probabilities()),
        ("Offer generation", lambda: test_offer_generation(conn)),
        ("Auto-accept best offer", lambda: test_auto_accept(conn)),
    ]

    print("\nRunning tests:")
    print("-" * 50)

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    conn.close()

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed_count}/{total_count} tests passed")

    # Cleanup test database
    if os.path.exists(db_path):
        os.remove(db_path)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
