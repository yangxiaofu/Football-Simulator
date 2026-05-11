"""
Phase 5 Prompt #8 Verification — Sentiment Transparency

Exit criteria:
1-4:   Mandatory guards (scope, Phase 4 regression, layer boundaries, P1-P7 regression)
5-7:   Schema / migration / backfill checks
8-9:   Reason catalog constants
10-11: Explainer function shapes
12-13: CLI smoke tests
14:    Lineup controversy reason visible (soft pass if no rows)
15:    Weekly summary embed no crash

Usage:
    python tests/verify/verify_phase5_p8.py saves/phase5_p8_test.db
"""

import sys
import os
import shutil
import subprocess
import tempfile

sys.path.insert(0, '.')

from src.db.connection import (
    get_connection,
    ensure_owner_sentiment_tables,
    ensure_satisfaction_tables,
)
from src.db.queries import get_league_state
from src.utils.constants import (
    OWNER_SENTIMENT_REASONS,
    PLAYER_SATISFACTION_REASONS,
)
from src.league.sentiment_explainer import (
    explain_owner_sentiment,
    explain_player_satisfaction,
)

PASS = "✅"
FAIL = "❌"
results = []


def _record(name, ok, detail=""):
    marker = PASS if ok else FAIL
    msg = f"  {marker} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append(ok)


def _get_temp_copy(save_path):
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    shutil.copy2(save_path, tmp.name)
    return tmp.name, lambda: os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Guard 1 — Scope discipline
# ---------------------------------------------------------------------------

def check_scope_discipline():
    print("\nGuard 1 — Scope discipline")
    ok = True

    # P8 files must exist
    required_files = [
        os.path.join('src', 'league', 'sentiment_explainer.py'),
        'view_sentiment.py',
        os.path.join('src', 'ui', 'sentiment_view.py'),
    ]
    for fpath in required_files:
        exists = os.path.isfile(fpath)
        _record(f"{fpath} exists", exists)
        if not exists:
            ok = False

    # P9 scope NOT shipped: no template_id column on press_event
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        tmp.close()
        shutil.copy2(sys.argv[1], tmp.name)
        try:
            from src.db.connection import get_connection as _gc
            conn_tmp = _gc(tmp.name)
            ensure_owner_sentiment_tables(conn_tmp)
            cols = {r['name'] for r in conn_tmp.execute("PRAGMA table_info(press_event)").fetchall()}
            conn_tmp.close()
            no_template_id = 'template_id' not in cols
            _record("press_event has no template_id column (P9 territory)", no_template_id,
                    "" if no_template_id else "template_id found — P9 shipped early")
            if not no_template_id:
                ok = False
        finally:
            os.unlink(tmp.name)
    except Exception as e:
        _record("press_event column check succeeded", False, str(e))
        ok = False

    # P7/P6/P5/P3 CLI surfaces intact
    rs_path = 'run_season.py'
    with open(rs_path) as f:
        rs_text = f.read()
    required_flags = [
        '--depth-chart', '--set-starter', '--player-value',
        '--estimate-trade', '--shop-player',
    ]
    for flag in required_flags:
        present = flag in rs_text
        _record(f"run_season.py has {flag}", present)
        if not present:
            ok = False

    # pitch_meeting_templates.py still exists (P7)
    tmpl_ok = os.path.isfile(os.path.join('src', 'utils', 'pitch_meeting_templates.py'))
    _record("pitch_meeting_templates.py exists (P7 intact)", tmpl_ok)
    if not tmpl_ok:
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Guard 2 — Phase 4 stress test regression
# ---------------------------------------------------------------------------

def check_phase4_regression(save_path):
    print("\nGuard 2 — Phase 4 stress-test regression")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        result = subprocess.run(
            [sys.executable, 'run_stress_test.py', tmp, '--seasons', '1', '--invariants'],
            capture_output=True, text=True, timeout=300,
        )
        out = result.stdout + result.stderr
        passed = '12 passed' in out and '0 failed' in out
        _record("Stress test: 12 passed, 0 failed", passed,
                "" if passed else out[-400:])
        return passed
    except subprocess.TimeoutExpired:
        _record("Stress test completed within timeout", False, "timed out after 300s")
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Guard 3 — Layer boundaries (no inline SQL in new P8 files)
# ---------------------------------------------------------------------------

def check_layer_boundaries():
    print("\nGuard 3 — Layer boundaries")
    ok = True

    SQL_PATTERNS = ['conn.execute(', '.fetchone(', '.fetchall(', 'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ']

    files_to_scan = [
        os.path.join('src', 'league', 'sentiment_explainer.py'),
        'view_sentiment.py',
        os.path.join('src', 'ui', 'sentiment_view.py'),
    ]

    for fpath in files_to_scan:
        if not os.path.isfile(fpath):
            _record(f"{fpath} scannable", False, "file missing")
            ok = False
            continue
        with open(fpath) as f:
            text = f.read()
        file_ok = True
        for pat in SQL_PATTERNS:
            if pat in text:
                _record(f"{fpath} contains no inline SQL (found {pat!r})", False)
                file_ok = False
                ok = False
                break
        if file_ok:
            _record(f"{fpath} contains no inline SQL", True)

    return ok


# ---------------------------------------------------------------------------
# Guard 4 — P1-P7 regression (per-subprocess timeout=180)
# ---------------------------------------------------------------------------

def check_p1_through_p7_regression(save_path):
    print("\nGuard 4 — P1-P7 regression (per-subprocess timeout; 180s for fast, scaled for slow)")
    ok = True
    # Per-script timeouts account for each script's own stress test + its own Guard 4 chain.
    # Measured runtimes: P1≈10s, P2≈15s, P3≈60s, P4≈180s, P5≈452s, P6≈745s, P7≈960s.
    # Each timeout adds ~30% buffer. If a script times out, it's a real hang, not normal runtime.
    timeouts = {1: 120, 2: 120, 3: 180, 4: 300, 5: 600, 6: 1000, 7: 1300}
    for n in range(1, 8):
        script = os.path.join('tests', 'verify', f'verify_phase5_p{n}.py')
        if not os.path.isfile(script):
            _record(f"verify_phase5_p{n}.py found", False, "script missing")
            ok = False
            continue
        t = timeouts.get(n, 300)
        try:
            result = subprocess.run(
                [sys.executable, script, save_path],
                capture_output=True, text=True, timeout=t,
            )
            passed = result.returncode == 0
            _record(f"verify_phase5_p{n}.py exits 0", passed,
                    "" if passed else result.stdout[-200:] + result.stderr[-200:])
            if not passed:
                ok = False
        except subprocess.TimeoutExpired:
            _record(f"verify_phase5_p{n}.py exits 0", False,
                    f"timed out after {t}s — possible hang in this script's own guards")
            ok = False
    return ok


# ---------------------------------------------------------------------------
# Check 5 — Schema columns present
# ---------------------------------------------------------------------------

def check_schema_columns_present(save_path):
    print("\nCheck 5 — Schema columns present")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_owner_sentiment_tables(conn)
        ensure_satisfaction_tables(conn)

        os_cols = {r['name'] for r in conn.execute("PRAGMA table_info(owner_sentiment)").fetchall()}
        se_cols = {r['name'] for r in conn.execute("PRAGMA table_info(satisfaction_event)").fetchall()}

        checks = [
            ('owner_sentiment.reason_code', 'reason_code' in os_cols),
            ('owner_sentiment.reason_detail', 'reason_detail' in os_cols),
            ('satisfaction_event.reason_code', 'reason_code' in se_cols),
        ]
        ok = True
        for name, present in checks:
            _record(f"{name} column exists", present)
            if not present:
                ok = False
        conn.close()
        return ok
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 6 — Migration is idempotent
# ---------------------------------------------------------------------------

def check_migration_idempotent(save_path):
    print("\nCheck 6 — ensure_*_tables() migrations are idempotent")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        try:
            ensure_owner_sentiment_tables(conn)
            ensure_owner_sentiment_tables(conn)
            ensure_satisfaction_tables(conn)
            ensure_satisfaction_tables(conn)
            _record("Both migrations called twice without error", True)
            return True
        except Exception as e:
            _record("Both migrations called twice without error", False, str(e))
            return False
        finally:
            conn.close()
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 7 — Legacy backfill
# ---------------------------------------------------------------------------

def check_legacy_backfill(save_path):
    print("\nCheck 7 — Legacy backfill (no NULL reason_code after migration)")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_owner_sentiment_tables(conn)
        ensure_satisfaction_tables(conn)

        os_nulls = conn.execute(
            "SELECT COUNT(*) as c FROM owner_sentiment WHERE reason_code IS NULL"
        ).fetchone()['c']
        se_nulls = conn.execute(
            "SELECT COUNT(*) as c FROM satisfaction_event WHERE reason_code IS NULL"
        ).fetchone()['c']

        ok_os = os_nulls == 0
        ok_se = se_nulls == 0
        _record(f"owner_sentiment has 0 NULL reason_code rows (got {os_nulls})", ok_os)
        _record(f"satisfaction_event has 0 NULL reason_code rows (got {se_nulls})", ok_se)
        conn.close()
        return ok_os and ok_se
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 8 — OWNER_SENTIMENT_REASONS catalog
# ---------------------------------------------------------------------------

def check_owner_sentiment_reasons_catalog():
    print("\nCheck 8 — OWNER_SENTIMENT_REASONS catalog")
    ok = True

    count_ok = len(OWNER_SENTIMENT_REASONS) >= 10
    _record(f"OWNER_SENTIMENT_REASONS has >= 10 keys (got {len(OWNER_SENTIMENT_REASONS)})", count_ok)
    if not count_ok:
        ok = False

    for required_key in ('lineup_controversy', 'legacy_unknown'):
        present = required_key in OWNER_SENTIMENT_REASONS
        _record(f"'{required_key}' in OWNER_SENTIMENT_REASONS", present)
        if not present:
            ok = False

    all_strings = all(isinstance(v, str) and v for v in OWNER_SENTIMENT_REASONS.values())
    _record("All OWNER_SENTIMENT_REASONS values are non-empty strings", all_strings)
    if not all_strings:
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Check 9 — PLAYER_SATISFACTION_REASONS catalog
# ---------------------------------------------------------------------------

def check_player_satisfaction_reasons_catalog():
    print("\nCheck 9 — PLAYER_SATISFACTION_REASONS catalog")
    ok = True

    count_ok = len(PLAYER_SATISFACTION_REASONS) >= 8
    _record(f"PLAYER_SATISFACTION_REASONS has >= 8 keys (got {len(PLAYER_SATISFACTION_REASONS)})", count_ok)
    if not count_ok:
        ok = False

    present = 'legacy_unknown' in PLAYER_SATISFACTION_REASONS
    _record("'legacy_unknown' in PLAYER_SATISFACTION_REASONS", present)
    if not present:
        ok = False

    all_strings = all(isinstance(v, str) and v for v in PLAYER_SATISFACTION_REASONS.values())
    _record("All PLAYER_SATISFACTION_REASONS values are non-empty strings", all_strings)
    if not all_strings:
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Check 10 — explain_owner_sentiment shape
# ---------------------------------------------------------------------------

def check_explain_owner_sentiment_shape(save_path):
    print("\nCheck 10 — explain_owner_sentiment return shape")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_owner_sentiment_tables(conn)

        league = get_league_state(conn)
        season_year = league['current_season'] if league else 2024
        user_team_id = league['user_team_id'] if league else None

        if user_team_id is None:
            _record("user_team_id available for sentiment check", False, "no user team in save")
            conn.close()
            return False

        result = explain_owner_sentiment(conn, user_team_id, season_year)

        ok = True
        has_tier = 'current_tier' in result and isinstance(result['current_tier'], str)
        _record("result has 'current_tier' (str)", has_tier)
        if not has_tier:
            ok = False

        has_net = 'net_change' in result and isinstance(result['net_change'], int)
        _record("result has 'net_change' (int)", has_net)
        if not has_net:
            ok = False

        has_contribs = 'contributors' in result and isinstance(result['contributors'], list)
        _record("result has 'contributors' (list)", has_contribs)
        if not has_contribs:
            ok = False

        # Each contributor must have required keys
        if has_contribs and result['contributors']:
            contrib = result['contributors'][0]
            for key in ('reason_code', 'reason_label', 'delta'):
                present = key in contrib
                _record(f"contributor has '{key}' key", present)
                if not present:
                    ok = False
        else:
            _record("contributors structure valid (empty list is acceptable)", True)

        conn.close()
        return ok
    except Exception as e:
        _record("explain_owner_sentiment runs without error", False, str(e))
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 11 — explain_player_satisfaction shape
# ---------------------------------------------------------------------------

def check_explain_player_satisfaction_shape(save_path):
    print("\nCheck 11 — explain_player_satisfaction return shape")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_satisfaction_tables(conn)

        league = get_league_state(conn)
        season_year = league['current_season'] if league else 2024

        # Find a player who has satisfaction_event rows, and use their season
        row = conn.execute(
            "SELECT player_id, season_year FROM satisfaction_event LIMIT 1"
        ).fetchone()

        if row:
            player_id = row['player_id']
            player_season = row['season_year']
        else:
            # Fall back: just pick any player with current season
            fb = conn.execute("SELECT id AS player_id FROM player LIMIT 1").fetchone()
            if not fb:
                _record("player available for satisfaction check", False, "no players in save")
                conn.close()
                return False
            player_id = fb['player_id']
            player_season = season_year

        result = explain_player_satisfaction(conn, player_id, player_season)

        ok = True
        has_state = 'current_state' in result and isinstance(result['current_state'], str)
        _record("result has 'current_state' (str)", has_state)
        if not has_state:
            ok = False

        has_events = 'events' in result and isinstance(result['events'], list)
        _record("result has 'events' (list)", has_events)
        if not has_events:
            ok = False

        if has_events and result['events']:
            ev = result['events'][0]
            for key in ('reason_code', 'reason_label', 'delta'):
                present = key in ev
                _record(f"event has '{key}' key", present)
                if not present:
                    ok = False
        else:
            _record("events structure valid (empty list acceptable for no-event player)", True)

        conn.close()
        return ok
    except Exception as e:
        _record("explain_player_satisfaction runs without error", False, str(e))
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 12 — view_sentiment.py --owner CLI smoke test
# ---------------------------------------------------------------------------

def check_view_sentiment_owner_runs(save_path):
    print("\nCheck 12 — view_sentiment.py --owner CLI smoke test")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        result = subprocess.run(
            [sys.executable, 'view_sentiment.py', tmp, '--owner'],
            capture_output=True, text=True, timeout=60,
        )
        out = result.stdout + result.stderr
        passed = result.returncode == 0
        _record("view_sentiment.py --owner exits 0", passed,
                "" if passed else out[-300:])
        if not passed:
            return False

        tier_words = ('stable', 'untouchable', 'warm', 'hot', 'termination',
                      'Stable', 'Untouchable', 'Warm', 'Hot', 'Termination',
                      'sentiment', 'Sentiment')
        has_tier = any(w in out for w in tier_words)
        _record("--owner output contains sentiment tier word", has_tier,
                "" if has_tier else f"output: {out[:200]}")
        return passed and has_tier
    except subprocess.TimeoutExpired:
        _record("view_sentiment.py --owner exits 0", False, "timed out after 60s")
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 13 — view_sentiment.py --player CLI smoke test
# ---------------------------------------------------------------------------

def check_view_sentiment_player_runs(save_path):
    print("\nCheck 13 — view_sentiment.py --player <pid> CLI smoke test")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        row = conn.execute("SELECT id FROM player LIMIT 1").fetchone()
        conn.close()
        if not row:
            _record("player available for --player test", False, "no players in save")
            return False
        pid = row['id']

        result = subprocess.run(
            [sys.executable, 'view_sentiment.py', tmp, '--player', str(pid)],
            capture_output=True, text=True, timeout=60,
        )
        out = result.stdout + result.stderr
        passed = result.returncode == 0
        non_empty = len(result.stdout.strip()) > 0
        _record("view_sentiment.py --player exits 0", passed,
                "" if passed else out[-300:])
        _record("--player output is non-empty", non_empty,
                "" if non_empty else "stdout was empty")
        return passed and non_empty
    except subprocess.TimeoutExpired:
        _record("view_sentiment.py --player exits 0", False, "timed out after 60s")
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 14 — Lineup controversy visible in explainer (soft pass if no rows)
# ---------------------------------------------------------------------------

def check_p5_lineup_controversy_visible(save_path):
    print("\nCheck 14 — Lineup controversy reason visible in explainer")
    try:
        conn = get_connection(save_path)
        ensure_owner_sentiment_tables(conn)

        league = get_league_state(conn)
        season_year = league['current_season'] if league else 2024
        user_team_id = league['user_team_id'] if league else None

        if user_team_id is None:
            conn.close()
            _record("Lineup controversy check skipped — no user team", True,
                    "(soft pass: no user team in save)")
            return True

        # Check if any owner_sentiment row has reason_code='lineup_controversy'
        lc_row = conn.execute(
            "SELECT * FROM owner_sentiment WHERE reason_code = 'lineup_controversy' LIMIT 1"
        ).fetchone()

        if lc_row is None:
            conn.close()
            _record("Lineup controversy visible in explainer", True,
                    "(soft pass: no lineup_controversy rows in this save — check passes)")
            return True

        result = explain_owner_sentiment(conn, user_team_id, season_year)
        conn.close()

        lc_found = any(
            c.get('reason_code') == 'lineup_controversy'
            for c in result.get('contributors', [])
        )
        expected_label = OWNER_SENTIMENT_REASONS.get('lineup_controversy', '')
        lc_label_ok = any(
            c.get('reason_label') == expected_label
            for c in result.get('contributors', [])
        )

        _record("lineup_controversy contributor appears in explainer output", lc_found)
        _record("lineup_controversy has correct English label", lc_label_ok)
        return lc_found and lc_label_ok
    except Exception as e:
        _record("Lineup controversy check runs without error", False, str(e))
        return False


# ---------------------------------------------------------------------------
# Check 15 — Weekly summary embed no crash
# ---------------------------------------------------------------------------

def check_weekly_summary_embed_no_crash(save_path):
    print("\nCheck 15 — Weekly summary embed no crash on --advance-week")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        result = subprocess.run(
            [sys.executable, 'run_season.py', tmp, '--advance-week'],
            capture_output=True, text=True, timeout=120,
        )
        out = result.stdout + result.stderr

        # Exit 0 (or a known "season complete" message) is fine
        # We also accept non-zero if it's "week already complete" edge case
        ok_exit = result.returncode == 0 or 'already complete' in out.lower()

        has_crash = ('Traceback' in out or 'Error:' in out) and result.returncode != 0
        passed = ok_exit and not has_crash

        _record("run_season.py --advance-week exits 0 (or season-end state)", ok_exit,
                "" if ok_exit else f"exit {result.returncode}\n{out[-300:]}")
        _record("No Traceback / crash in output", not has_crash,
                "" if not has_crash else out[-300:])
        return passed
    except subprocess.TimeoutExpired:
        _record("--advance-week completed within 120s", False, "timed out")
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p8.py <save_path>")
        sys.exit(1)

    save_path = sys.argv[1]
    if not os.path.isfile(save_path):
        print(f"Save file not found: {save_path}")
        sys.exit(1)

    print(f"\nPhase 5 Prompt #8 Verification — {save_path}")
    print("=" * 60)

    check_scope_discipline()
    check_phase4_regression(save_path)
    check_layer_boundaries()
    check_p1_through_p7_regression(save_path)
    check_schema_columns_present(save_path)
    check_migration_idempotent(save_path)
    check_legacy_backfill(save_path)
    check_owner_sentiment_reasons_catalog()
    check_player_satisfaction_reasons_catalog()
    check_explain_owner_sentiment_shape(save_path)
    check_explain_player_satisfaction_shape(save_path)
    check_view_sentiment_owner_runs(save_path)
    check_view_sentiment_player_runs(save_path)
    check_p5_lineup_controversy_visible(save_path)
    check_weekly_summary_embed_no_crash(save_path)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    assert total >= 13, f"Verification script has only {total} checks — minimum is 13"

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} CHECKS FAILED ({passed}/{total} passed)")
        sys.exit(1)


if __name__ == '__main__':
    main()
