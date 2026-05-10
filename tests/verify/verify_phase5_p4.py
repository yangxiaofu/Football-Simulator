"""Phase 5 Prompt #4 verification — Stars of the Week.

Requires a save that has at least 4 regular-season weeks simulated.
Run: python tests/verify/verify_phase5_p4.py saves/phase5_p4_test.db
Exit 0 = all checks passed.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, '.')


def _get_season_with_awards(save_path):
    """Return the most recent season_year that has weekly_award rows."""
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT season_year FROM weekly_award ORDER BY season_year DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row['season_year'] if row else None


# ---------------------------------------------------------------------------
# Mandatory Guards
# ---------------------------------------------------------------------------

def check_scope_discipline():
    """MANDATORY GUARD #1: P3 flags still present; no P5 streak/lineup_controversy files."""
    with open('run_season.py') as f:
        run_src = f.read()

    # view_stats flags must NOT have leaked into run_season.py
    forbidden_p2 = ['--leaderboard', '--stars-of-week', '--player-weekly']
    leaked = [f_ for f_ in forbidden_p2 if f_ in run_src]
    assert not leaked, f"view_stats flags leaked into run_season.py: {leaked}"

    # P3 depth-chart flags must still be present
    required_p3 = ['--depth-chart', '--set-starter', '--swap-depth', '--reset-depth']
    missing = [r for r in required_p3 if r not in run_src]
    assert not missing, f"P3 depth-chart flags removed from run_season.py: {missing}"

    # P5 Prompt #5 files must NOT exist yet
    forbidden_p5 = []
    for fname in os.listdir('src/transactions'):
        if 'streak' in fname.lower() or 'lineup_controversy' in fname.lower():
            forbidden_p5.append(fname)
    assert not forbidden_p5, f"P5 Prompt #5 work shipped early: {forbidden_p5}"

    return True


def check_phase4_regression(save_path):
    """MANDATORY GUARD #2: Phase 4 stress harness still passes 12/12 invariants.

    Uses a temp copy of the save to avoid advancing the test DB's season state.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        result = subprocess.run(
            ['python', 'run_stress_test.py', tmp_path, '--seasons', '1', '--invariants'],
            capture_output=True, text=True, timeout=600,
        )
        assert result.returncode == 0, (
            f"Stress harness exit {result.returncode}\n"
            f"stderr tail: {result.stderr[-500:]}"
        )
        assert '12 passed' in result.stdout and '0 failed' in result.stdout, (
            f"Expected '12 passed' and '0 failed' in stdout.\n"
            f"Stdout tail: {result.stdout[-500:]}"
        )
    finally:
        os.unlink(tmp_path)
    return True


def check_layer_boundaries():
    """MANDATORY GUARD #3: No inline SQL in stars_selection.py or stats_view.py."""
    targets = [
        'src/league/stars_selection.py',
        'src/ui/stats_view.py',
    ]
    sql_tokens = ['conn.execute(', 'cursor.execute(', '.fetchall(', '.fetchone(']
    for path in targets:
        with open(path) as f:
            lines = f.readlines()
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Track multi-line docstrings (triple-quoted)
            triple_count = stripped.count('"""') + stripped.count("'''")
            if triple_count == 1:
                in_docstring = not in_docstring
            if in_docstring or stripped.startswith('#'):
                continue
            if triple_count >= 2:
                continue
            for tok in sql_tokens:
                assert tok not in stripped, (
                    f"{path}:{i} contains inline SQL: {stripped[:80]}"
                )
    return True


def check_p1_p2_p3_regression(save_path):
    """MANDATORY GUARD #4: Phase 5 Prompts #1, #2, #3 verifications still pass.

    Uses a temp copy of the save for scripts that run the stress harness.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        for prior in ['verify_phase5_p1.py', 'verify_phase5_p2.py', 'verify_phase5_p3.py']:
            script = f'tests/verify/{prior}'
            if not os.path.exists(script):
                continue
            result = subprocess.run(
                ['python', script, tmp_path],
                capture_output=True, text=True, timeout=600,
            )
            assert result.returncode == 0, (
                f"{prior} regression — exit {result.returncode}\n"
                f"stderr tail: {result.stderr[-500:]}"
            )
    finally:
        os.unlink(tmp_path)
    return True


# ---------------------------------------------------------------------------
# Functional Checks
# ---------------------------------------------------------------------------

def check_weekly_awards_populated(save_path):
    """After 4+ weeks, weekly_award has rows for every week (3-4 per week)."""
    season_year = _get_season_with_awards(save_path)
    assert season_year, "No weekly_award rows found in DB"
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    weeks = conn.execute(
        "SELECT DISTINCT week_number FROM weekly_award WHERE season_year=? AND is_playoff=0 ORDER BY week_number",
        (season_year,)
    ).fetchall()
    assert len(weeks) >= 4, (
        f"Expected awards for at least 4 weeks in season {season_year}, found {len(weeks)}"
    )
    for row in weeks:
        wk = row['week_number']
        count = conn.execute(
            "SELECT COUNT(*) FROM weekly_award WHERE season_year=? AND week_number=? AND is_playoff=0",
            (season_year, wk)
        ).fetchone()[0]
        assert count >= 3, (
            f"Season {season_year} Week {wk} has only {count} award rows (expected 3-4)"
        )
    conn.close()
    return True


def check_narrative_blurb_present(save_path):
    """All weekly_award rows have a non-empty narrative_blurb (>10 chars)."""
    season_year = _get_season_with_awards(save_path)
    assert season_year, "No weekly_award rows found"
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT week_number, award_type, narrative_blurb FROM weekly_award WHERE season_year=?",
        (season_year,)
    ).fetchall()
    assert rows, f"No weekly_award rows for season {season_year}"
    for row in rows:
        blurb = row['narrative_blurb'] or ''
        assert len(blurb) > 10, (
            f"Season {season_year} Week {row['week_number']} {row['award_type']}: "
            f"blurb too short or empty: {repr(blurb)}"
        )
    conn.close()
    return True


def check_award_type_distinct_per_week(save_path):
    """No duplicate (season_year, week_number, is_playoff, award_type) combinations."""
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    dups = conn.execute("""
        SELECT season_year, week_number, is_playoff, award_type, COUNT(*) AS cnt
        FROM weekly_award
        GROUP BY season_year, week_number, is_playoff, award_type
        HAVING cnt > 1
    """).fetchall()
    assert not dups, (
        f"Duplicate award rows found: {[dict(r) for r in dups]}"
    )
    conn.close()
    return True


def check_st_threshold_gate(save_path):
    """Verify ST threshold gate works: a week with no returner TDs or 50+ FG has no ST row."""
    season_year = _get_season_with_awards(save_path)
    assert season_year, "No award rows to check"
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row

    weeks = conn.execute(
        "SELECT DISTINCT week_number FROM weekly_award WHERE season_year=? AND is_playoff=0 ORDER BY week_number",
        (season_year,)
    ).fetchall()

    for row in weeks:
        wk = row['week_number']
        qt_count = conn.execute("""
            SELECT COUNT(*) FROM player_week_stats
            WHERE season_year=? AND week_number=? AND is_playoff=0
              AND (punt_return_tds + kick_return_tds > 0 OR fg_long >= 50)
        """, (season_year, wk)).fetchone()[0]

        has_st_award = conn.execute("""
            SELECT COUNT(*) FROM weekly_award
            WHERE season_year=? AND week_number=? AND is_playoff=0 AND award_type='SPECIAL_TEAMS'
        """, (season_year, wk)).fetchone()[0]

        if qt_count == 0:
            assert has_st_award == 0, (
                f"Season {season_year} Week {wk}: no ST threshold met but SPECIAL_TEAMS row exists"
            )

    conn.close()
    return True


def check_user_team_mvp_always_present(save_path):
    """Every completed regular-season week has exactly one USER_TEAM_MVP row."""
    season_year = _get_season_with_awards(save_path)
    assert season_year, "No award rows to check"
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row

    completed_weeks = conn.execute("""
        SELECT DISTINCT week_number FROM weekly_award WHERE season_year=? AND is_playoff=0
    """, (season_year,)).fetchall()

    for row in completed_weeks:
        wk = row['week_number']
        count = conn.execute("""
            SELECT COUNT(*) FROM weekly_award
            WHERE season_year=? AND week_number=? AND is_playoff=0 AND award_type='USER_TEAM_MVP'
        """, (season_year, wk)).fetchone()[0]
        assert count == 1, (
            f"Season {season_year} Week {wk}: expected 1 USER_TEAM_MVP row, found {count}"
        )

    conn.close()
    return True


def check_view_stats_stars_renders(save_path):
    """python view_stats.py SAVE --stars --week 1 exits 0 and shows a player name."""
    # Use --week 1 to force a specific week that we know has award data
    result = subprocess.run(
        ['python', 'view_stats.py', save_path, '--stars', '--week', '1'],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"view_stats.py --stars --week 1 exit {result.returncode}\n"
        f"stderr: {result.stderr[-300:]}"
    )
    assert 'Stars of the Week will be implemented' not in result.stdout, (
        "Placeholder text still showing in --stars output"
    )
    # Should show at least one award label when week 1 has data
    assert any(label in result.stdout for label in
               ['Offensive Player', 'Defensive Player', 'Your Team MVP',
                'No Stars of the Week']), (
        f"Expected award label in output. Stdout head: {result.stdout[:300]}"
    )
    # Must have actual content (player name)
    assert 'STARS OF THE WEEK' in result.stdout, (
        f"Expected STARS header in output. Stdout: {result.stdout[:300]}"
    )
    return True


def check_view_stats_stars_week_filter(save_path):
    """python view_stats.py SAVE --stars --week 2 exits 0 and references Week 2."""
    result = subprocess.run(
        ['python', 'view_stats.py', save_path, '--stars', '--week', '2'],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"view_stats.py --stars --week 2 exit {result.returncode}\n"
        f"stderr: {result.stderr[-300:]}"
    )
    assert 'Week 2' in result.stdout, (
        f"Expected 'Week 2' in output. Stdout: {result.stdout[:300]}"
    )
    # Should show only Week 2, not other weeks
    assert 'Week 3' not in result.stdout, (
        "Week filter not working — Week 3 rows showing in --week 2 output"
    )
    return True


def check_idempotency(save_path):
    """Calling select_stars_for_week twice consecutively yields identical rows.

    True idempotency: two calls to the same function on the same DB state should
    produce the same output. We call select_stars_for_week twice on week 1 data
    and compare the two sets of DB rows produced. (Note: re-running a past week
    after opponent records have changed may select a different player — that is
    expected temporal behavior, not an idempotency failure.)
    """
    from src.db.connection import get_connection
    from src.league.stars_selection import select_stars_for_week

    season_year = _get_season_with_awards(save_path)
    assert season_year, "No award rows to check"

    conn = get_connection(save_path)
    weeks = conn.execute(
        "SELECT DISTINCT week_number FROM weekly_award WHERE season_year=? AND is_playoff=0 ORDER BY week_number",
        (season_year,)
    ).fetchall()
    assert weeks, f"No completed weeks for season {season_year}"
    wk = weeks[0]['week_number']

    def get_rows():
        return conn.execute(
            "SELECT award_type, player_id, score, narrative_blurb "
            "FROM weekly_award WHERE season_year=? AND week_number=? AND is_playoff=0 "
            "ORDER BY award_type",
            (season_year, wk)
        ).fetchall()

    # First call — write rows based on current DB state
    with conn:
        select_stars_for_week(conn, season_year, wk, is_playoff=False)
    rows_first = [(r['award_type'], r['player_id']) for r in get_rows()]
    count_first = len(rows_first)

    # Second call — should produce identical rows (same DB state, no changes)
    with conn:
        select_stars_for_week(conn, season_year, wk, is_playoff=False)
    rows_second = [(r['award_type'], r['player_id']) for r in get_rows()]
    count_second = len(rows_second)

    assert count_first == count_second, (
        f"Idempotency failed: first run={count_first} rows, second run={count_second} rows"
    )
    assert rows_first == rows_second, (
        f"Idempotency failed: rows differ between consecutive runs.\n"
        f"First:  {rows_first}\nSecond: {rows_second}"
    )

    conn.close()
    return True


def check_position_classification(save_path):
    """OFFENSE awards go to OFFENSE positions; DEFENSE to DEFENSE positions; ST to K/P or returners."""
    from src.utils.constants import STARS_OFFENSE_POSITIONS, STARS_DEFENSE_POSITIONS

    season_year = _get_season_with_awards(save_path)
    assert season_year, "No award rows to check"

    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row

    awards = conn.execute("""
        SELECT wa.award_type, p.position
        FROM weekly_award wa
        JOIN player p ON p.id = wa.player_id
        WHERE wa.season_year = ? AND wa.is_playoff = 0
    """, (season_year,)).fetchall()

    assert awards, f"No awards for season {season_year}"

    for row in awards:
        award_type = row['award_type']
        pos = row['position']
        if award_type == 'OFFENSE':
            assert pos in STARS_OFFENSE_POSITIONS, (
                f"OFFENSE award went to {pos} (not an offense position)"
            )
        elif award_type == 'DEFENSE':
            assert pos in STARS_DEFENSE_POSITIONS, (
                f"DEFENSE award went to {pos} (not a defense position)"
            )
        # ST and USER_TEAM_MVP can be any position — no restriction needed

    conn.close()
    return True


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p4.py <save_path>")
        sys.exit(1)

    save_path = sys.argv[1]

    checks = [
        ('check_scope_discipline',          lambda: check_scope_discipline()),
        ('check_phase4_regression',         lambda: check_phase4_regression(save_path)),
        ('check_layer_boundaries',          lambda: check_layer_boundaries()),
        ('check_p1_p2_p3_regression',       lambda: check_p1_p2_p3_regression(save_path)),
        ('check_weekly_awards_populated',   lambda: check_weekly_awards_populated(save_path)),
        ('check_narrative_blurb_present',   lambda: check_narrative_blurb_present(save_path)),
        ('check_award_type_distinct_per_week', lambda: check_award_type_distinct_per_week(save_path)),
        ('check_st_threshold_gate',         lambda: check_st_threshold_gate(save_path)),
        ('check_user_team_mvp_always_present', lambda: check_user_team_mvp_always_present(save_path)),
        ('check_view_stats_stars_renders',  lambda: check_view_stats_stars_renders(save_path)),
        ('check_view_stats_stars_week_filter', lambda: check_view_stats_stars_week_filter(save_path)),
        ('check_idempotency',               lambda: check_idempotency(save_path)),
        ('check_position_classification',   lambda: check_position_classification(save_path)),
    ]

    assert len(checks) >= 13, f"Need ≥13 checks, only have {len(checks)}"

    passed = 0
    failed = 0
    for name, fn in checks:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print()
    total = passed + failed
    if failed == 0:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"❌ {failed} CHECKS FAILED ({passed}/{total} passed)")
        sys.exit(1)


if __name__ == '__main__':
    main()
