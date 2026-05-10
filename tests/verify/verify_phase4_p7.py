#!/usr/bin/env python3
"""
Verification script for Phase 4 Prompt #7 (Legacy Score Expansion).

Tests:
1. Schema check (3 new tables exist)
2. Coach legacy populated for every active coach for every completed season
3. Era difficulty in valid range (0.85-1.15)
4. Starting condition multipliers stored on tenures
5. Tenure stability bonus = 0 for fresh tenures (Year 1-5)
6. Peer ranking returns sensible structure
7. Narrative beats generated for player every season
8. Career total = sum of season scores + stability bonus

Exit code:
    0 = all checks pass
    1 = one or more checks failed
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.connection import get_connection
from src.league.era_context import compute_era_difficulty_multiplier
from src.league.legacy import compute_career_legacy_total, compute_tenure_stability_bonus
from src.league.peer_ranking import get_player_peer_rank
from src.utils.constants import (
    ERA_DIFFICULTY_MIN,
    ERA_DIFFICULTY_MAX,
    TENURE_STABILITY_THRESHOLD_YEARS,
)


def main():
    db_path = "saves/phase4_p7.db"

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Run: python generate.py saves/phase4_p7.db --season 2024")
        print("Then: python run_stress_test.py saves/phase4_p7.db --seasons 3")
        return 1

    conn = get_connection(db_path)
    failures = 0

    print("=" * 60)
    print("PHASE 4 PROMPT #7 VERIFICATION")
    print("=" * 60)

    # Check 1: Schema check
    print("\n[1/8] Schema check (3 new tables exist)...")
    tables_to_check = [
        'coach_legacy_score',
        'coach_narrative_beat',
        'peer_ranking_snapshot',
    ]

    existing_tables = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table'
    """).fetchall()
    existing_table_names = [row['name'] for row in existing_tables]

    for table in tables_to_check:
        if table in existing_table_names:
            print(f"  ✓ {table} exists")
        else:
            print(f"  ❌ {table} MISSING")
            failures += 1

    # Check starting_condition_multiplier column on coach_tenure
    try:
        conn.execute("SELECT starting_condition_multiplier FROM coach_tenure LIMIT 1")
        print("  ✓ coach_tenure.starting_condition_multiplier exists")
    except sqlite3.OperationalError:
        print("  ❌ coach_tenure.starting_condition_multiplier MISSING")
        failures += 1

    # Check 2: Coach legacy populated for every active coach for every completed season
    print("\n[2/8] Coach legacy populated for all active coaches...")
    completed_seasons = conn.execute("""
        SELECT year FROM season WHERE is_complete = 1
    """).fetchall()

    if not completed_seasons:
        print("  ⚠️  No completed seasons found (run stress test first)")
    else:
        for season_row in completed_seasons:
            year = season_row['year']
            active_coaches = conn.execute("""
                SELECT id FROM coach_career WHERE is_active = 1
            """).fetchall()

            legacy_rows = conn.execute("""
                SELECT COUNT(*) as cnt FROM coach_legacy_score
                WHERE season_year = ?
            """, (year,)).fetchone()

            expected_count = len(active_coaches)
            actual_count = legacy_rows['cnt']

            if actual_count == expected_count:
                print(f"  ✓ Season {year}: {actual_count}/{expected_count} coaches")
            else:
                print(f"  ❌ Season {year}: {actual_count}/{expected_count} coaches (MISMATCH)")
                failures += 1

    # Check 3: Era difficulty in valid range
    print("\n[3/8] Era difficulty in valid range (0.85-1.15)...")
    if completed_seasons:
        for season_row in completed_seasons:
            year = season_row['year']
            era_mult = compute_era_difficulty_multiplier(conn, year)

            if ERA_DIFFICULTY_MIN <= era_mult <= ERA_DIFFICULTY_MAX:
                print(f"  ✓ Season {year}: {era_mult:.3f}")
            else:
                print(f"  ❌ Season {year}: {era_mult:.3f} OUT OF RANGE")
                failures += 1
    else:
        print("  ⚠️  No completed seasons to check")

    # Check 4: Starting condition multipliers stored on tenures
    print("\n[4/8] Starting condition multipliers stored on tenures...")
    tenures = conn.execute("""
        SELECT id, starting_condition_multiplier FROM coach_tenure
        WHERE end_year IS NULL
    """).fetchall()

    if not tenures:
        print("  ⚠️  No active tenures found")
    else:
        valid_count = 0
        for tenure in tenures:
            mult = tenure['starting_condition_multiplier']
            if 0.90 <= mult <= 1.20:
                valid_count += 1

        print(f"  ✓ {valid_count}/{len(tenures)} tenures have valid multipliers (0.90-1.20)")
        if valid_count != len(tenures):
            print(f"  ❌ {len(tenures) - valid_count} tenures have invalid multipliers")
            failures += 1

    # Check 5: Tenure stability bonus = 0 for Year 1-5
    print("\n[5/8] Tenure stability bonus = 0 for Year 1-5...")
    league = conn.execute("SELECT current_season FROM league WHERE id = 1").fetchone()
    current_season = league['current_season']

    recent_tenures = conn.execute("""
        SELECT coach_id, start_year FROM coach_tenure
        WHERE end_year IS NULL
    """).fetchall()

    if not recent_tenures:
        print("  ⚠️  No active tenures to check")
    else:
        for tenure in recent_tenures:
            years_at_team = current_season - tenure['start_year'] + 1
            bonus = compute_tenure_stability_bonus(conn, tenure['coach_id'], current_season)

            if years_at_team <= TENURE_STABILITY_THRESHOLD_YEARS:
                if bonus == 0:
                    print(f"  ✓ Coach {tenure['coach_id']} Year {years_at_team}: bonus = 0")
                else:
                    print(f"  ❌ Coach {tenure['coach_id']} Year {years_at_team}: bonus = {bonus} (should be 0)")
                    failures += 1
            else:
                expected_bonus = min((years_at_team - TENURE_STABILITY_THRESHOLD_YEARS) * 5, 25)
                if bonus == expected_bonus:
                    print(f"  ✓ Coach {tenure['coach_id']} Year {years_at_team}: bonus = {bonus}")
                else:
                    print(f"  ❌ Coach {tenure['coach_id']} Year {years_at_team}: bonus = {bonus} (expected {expected_bonus})")
                    failures += 1

    # Check 6: Peer ranking returns sensible structure
    print("\n[6/8] Peer ranking returns sensible structure...")
    if completed_seasons:
        latest_season = max(row['year'] for row in completed_seasons)
        peer_rank = get_player_peer_rank(conn, latest_season)

        if peer_rank is None:
            print("  ⚠️  No player coach found")
        else:
            required_keys = ['active_rank', 'n_active', 'all_time_rank', 'n_all_time', 'career_legacy_total']
            missing_keys = [k for k in required_keys if k not in peer_rank]

            if not missing_keys:
                print(f"  ✓ Peer rank structure valid")
                print(f"    Active: {peer_rank['active_rank']}/{peer_rank['n_active']}")
                print(f"    All-time: {peer_rank['all_time_rank']}/{peer_rank['n_all_time']}")
                print(f"    Career total: {peer_rank['career_legacy_total']}")

                # Sanity check ranks
                if not (1 <= peer_rank['active_rank'] <= peer_rank['n_active']):
                    print(f"  ❌ Active rank out of bounds")
                    failures += 1
                if not (1 <= peer_rank['all_time_rank'] <= peer_rank['n_all_time']):
                    print(f"  ❌ All-time rank out of bounds")
                    failures += 1
            else:
                print(f"  ❌ Missing keys: {missing_keys}")
                failures += 1
    else:
        print("  ⚠️  No completed seasons to check")

    # Check 7: Narrative beats generated for player every season
    print("\n[7/8] Narrative beats generated for player every season...")
    player_coach = conn.execute("""
        SELECT id FROM coach_career WHERE is_player = 1 LIMIT 1
    """).fetchone()

    if not player_coach:
        print("  ⚠️  No player coach found")
    elif not completed_seasons:
        print("  ⚠️  No completed seasons to check")
    else:
        coach_id = player_coach['id']
        for season_row in completed_seasons:
            year = season_row['year']
            beat = conn.execute("""
                SELECT beat_type, text FROM coach_narrative_beat
                WHERE coach_id = ? AND season_year = ?
            """, (coach_id, year)).fetchone()

            if beat:
                beat_type = beat['beat_type']
                text_preview = beat['text'][:60] + "..." if len(beat['text']) > 60 else beat['text']
                print(f"  ✓ Season {year} ({beat_type}): {text_preview}")
            else:
                print(f"  ❌ Season {year}: NO NARRATIVE BEAT")
                failures += 1

    # Check 8: Career total = sum of season scores + stability bonus
    print("\n[8/8] Career total arithmetic...")
    if player_coach and completed_seasons:
        coach_id = player_coach['id']
        latest_season = max(row['year'] for row in completed_seasons)

        # Manual sum
        season_scores = conn.execute("""
            SELECT season_legacy_score FROM coach_legacy_score
            WHERE coach_id = ?
        """, (coach_id,)).fetchall()

        manual_sum = sum(row['season_legacy_score'] for row in season_scores)
        stability_bonus = compute_tenure_stability_bonus(conn, coach_id, latest_season)
        manual_total = manual_sum + stability_bonus

        # Computed total
        computed_total = compute_career_legacy_total(conn, coach_id, latest_season)

        if manual_total == computed_total:
            print(f"  ✓ Career total: {computed_total}")
            print(f"    (Season sum: {manual_sum} + Stability: {stability_bonus})")
        else:
            print(f"  ❌ Career total mismatch:")
            print(f"    Manual: {manual_total}")
            print(f"    Computed: {computed_total}")
            failures += 1
    else:
        print("  ⚠️  Cannot verify (no player coach or completed seasons)")

    # Summary
    print("\n" + "=" * 60)
    if failures == 0:
        print("✅ ALL CHECKS PASSED")
        print("=" * 60)
        return 0
    else:
        print(f"❌ {failures} CHECK(S) FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
