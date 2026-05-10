"""Verification for Phase 4 Prompt #8 — Historical Records."""
import sys
sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.league.historical_records import (
    get_record_book, get_all_time_leaders, get_champion_history,
)

DB = "saves/phase4_p8.db"

def main():
    conn = get_connection(DB)

    print("Phase 4 Prompt #8 — Historical Records Verification")
    print("=" * 70)

    # 1. Schema check
    print("\n1. Schema check...")
    tables = {r['name'] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert 'league_record' in tables, "league_record table missing"
    print("   ✓ league_record table exists")

    cols = {r['name'] for r in conn.execute("PRAGMA table_info(season)").fetchall()}
    required_cols = [
        'runner_up_team_id', 'championship_home_score', 'championship_away_score',
        'championship_mvp_player_id', 'championship_coach_id'
    ]
    for c in required_cols:
        assert c in cols, f"season.{c} column missing"
    print(f"   ✓ All {len(required_cols)} season columns added")

    # 2. Records populated
    print("\n2. Records populated...")
    n_records = conn.execute("SELECT COUNT(*) as cnt FROM league_record").fetchone()['cnt']
    print(f"   Records tracked: {n_records}")
    assert n_records >= 10, f"expected at least 10 records, got {n_records}"
    print(f"   ✓ At least 10 records exist")

    # 3. Each record has a holder
    print("\n3. Holder validation...")
    unholdered = conn.execute("""
        SELECT category, scope FROM league_record
        WHERE holder_player_id IS NULL AND holder_team_id IS NULL
          AND holder_coach_id IS NULL
    """).fetchall()
    assert len(unholdered) == 0, f"records with no holder: {unholdered}"
    print(f"   ✓ All records have holders")

    # 4. Read API smoke tests
    print("\n4. Read API tests...")
    records = get_record_book(conn)
    assert len(records) > 0, "get_record_book returned empty"
    print(f"   ✓ get_record_book returned {len(records)} records")

    leaders = get_all_time_leaders(conn, 'passing_yards', scope='career', top_n=5)
    assert len(leaders) > 0, "no career passing yards leaders"
    values = [l['value'] for l in leaders]
    assert values == sorted(values, reverse=True), "leaders not sorted descending"
    print(f"   ✓ get_all_time_leaders sorted correctly ({len(leaders)} leaders)")

    # 5. Champion history populated
    print("\n5. Champion history...")
    champs = get_champion_history(conn, n=10)
    n_completed = conn.execute(
        "SELECT COUNT(*) as cnt FROM season WHERE is_complete=1"
    ).fetchone()['cnt']
    assert len(champs) >= min(n_completed, 1), \
        f"expected at least {min(n_completed, 1)} champions, got {len(champs)}"
    print(f"   ✓ Champion history has {len(champs)} seasons")

    # 6. Each champion has team abbr
    print("\n6. Champion data integrity...")
    for c in champs:
        assert c.get('champion_team_abbr'), f"champion missing team abbr: {c}"
    print(f"   ✓ All champions have team abbreviations")

    # 7. Check that at least some championships have full details
    detailed_count = sum(1 for c in champs if c.get('mvp_player_name') is not None)
    print(f"   ℹ {detailed_count}/{len(champs)} championships have MVP data")

    print("\n" + "=" * 70)
    print("✅ Phase 4 prompt #8 verification passed.")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
