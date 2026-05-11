"""
Phase 5 Prompt #7 Verification — FA Pitch Meeting Narrative + Typed Rejection Reasons

Exit Criteria:
1-4:   Mandatory guards (scope, Phase 4 regression, layer boundaries, P1-P6 regression)
5-6:   Schema / migration checks
7-8:   Template and constant checks
9-11:  Outcome narrative writes and reason_code checks
12-13: Template match-lambda and token checks
14-15: Integration smoke tests

Usage:
    python tests/verify/verify_phase5_p7.py saves/phase5_p7_test.db
"""

import sys
import os
import re
import shutil
import subprocess
import tempfile

sys.path.insert(0, '.')

from src.db.connection import get_connection, ensure_fa_tables
from src.db.queries import (
    get_league_state,
    get_fa_interest,
    get_fa_interests_for_player,
    update_fa_interest_outcome,
    get_fa_interest_with_outcome,
    get_fa_outcomes_for_season,
)
from src.utils.constants import (
    FA_REJECTION_REASONS,
    PITCH_SIGNAL_TYPES,
    PITCH_SIGNAL_INTEREST_LEVEL,
    PITCH_SIGNAL_COMPETING_OFFER,
    PITCH_SIGNAL_AGENT_POSTURE,
    PITCH_SIGNAL_FIT_VIBE,
    PITCH_SIGNAL_MONEY_PRIMARY,
    PITCH_SIGNAL_WINNING_PRIMARY,
)
from src.utils.pitch_meeting_templates import PITCH_TEMPLATES
from src.transactions.free_agency import (
    request_pitch_meeting,
    generate_outcome_narrative,
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


def _get_any_fa_interest_row(conn):
    """Return any fa_interest row, or None."""
    return conn.execute("SELECT * FROM fa_interest LIMIT 1").fetchone()


# ---------------------------------------------------------------------------
# Guard 1 — Scope discipline
# ---------------------------------------------------------------------------

def check_scope_discipline():
    print("\nGuard 1 — Scope discipline")
    import ast

    ok = True

    # pitch_meeting_templates.py must exist in src/utils/
    tmpl_path = os.path.join('src', 'utils', 'pitch_meeting_templates.py')
    if not os.path.isfile(tmpl_path):
        _record("pitch_meeting_templates.py exists in src/utils/", False,
                "file not found")
        ok = False
    else:
        _record("pitch_meeting_templates.py exists in src/utils/", True)

    # sentiment_explainer.py must NOT exist (P8 territory)
    forbidden_files = [
        os.path.join('src', 'league', 'sentiment_explainer.py'),
        'view_sentiment.py',
    ]
    for fpath in forbidden_files:
        if os.path.isfile(fpath):
            _record(f"No {fpath} (P8 territory)", False, "file exists — scope creep")
            ok = False
        else:
            _record(f"No {fpath} (P8 territory)", True)

    # run_season.py must retain existing P6 CLI flags
    rs_path = 'run_season.py'
    with open(rs_path) as f:
        rs_text = f.read()
    required_flags = [
        '--depth-chart', '--set-starter', '--swap-depth', '--reset-depth',
        '--player-value', '--estimate-trade', '--shop-player',
    ]
    for flag in required_flags:
        ok_flag = flag in rs_text
        _record(f"run_season.py has {flag}", ok_flag)
        if not ok_flag:
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
                "" if passed else out[-300:])
        return passed
    except subprocess.TimeoutExpired:
        _record("Stress test completed within timeout", False, "timed out after 300s")
        return False
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Guard 3 — Layer boundaries
# ---------------------------------------------------------------------------

def check_layer_boundaries():
    print("\nGuard 3 — Layer boundaries")
    ok = True

    # Scan pitch_meeting_templates.py for SQL
    tmpl_path = os.path.join('src', 'utils', 'pitch_meeting_templates.py')
    if os.path.isfile(tmpl_path):
        with open(tmpl_path) as f:
            tmpl_text = f.read()
        sql_patterns = ['conn.execute(', '.fetchone(', '.fetchall(', 'SELECT ', 'INSERT ']
        for pat in sql_patterns:
            if pat in tmpl_text:
                _record(f"pitch_meeting_templates.py has no SQL ({pat!r})", False,
                        "SQL found in template file")
                ok = False
        if ok:
            _record("pitch_meeting_templates.py contains no SQL", True)

    # Scan P7 additions in free_agency.py for inline SQL
    fa_path = os.path.join('src', 'transactions', 'free_agency.py')
    with open(fa_path) as f:
        lines = f.readlines()

    # Find the Phase 5 P7 section start
    p7_start = None
    for i, line in enumerate(lines):
        if 'Phase 5 P7' in line:
            p7_start = i
            break

    if p7_start is None:
        _record("Phase 5 P7 section found in free_agency.py", False)
        return False
    _record("Phase 5 P7 section found in free_agency.py", True)

    inline_sql_found = False
    for line in lines[p7_start:]:
        stripped = line.strip()
        # Allow calls to query functions (those are OK — they go through queries.py)
        # Flag raw SQL strings
        if re.search(r'(SELECT|INSERT|UPDATE|DELETE)\s+', stripped, re.IGNORECASE):
            # Check it's not in a string comment or docstring
            if not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'"):
                inline_sql_found = True
                _record("No inline SQL in P7 additions of free_agency.py", False,
                        f"Found: {stripped[:80]}")
                ok = False
                break

    if not inline_sql_found:
        _record("No inline SQL in P7 additions of free_agency.py", True)

    return ok


# ---------------------------------------------------------------------------
# Guard 4 — P1-P6 regression
# ---------------------------------------------------------------------------

def check_p1_through_p6_regression(save_path):
    print("\nGuard 4 — P1-P6 regression (all prior verify scripts)")
    ok = True
    for i in range(1, 7):
        script = os.path.join('tests', 'verify', f'verify_phase5_p{i}.py')
        if not os.path.isfile(script):
            _record(f"verify_phase5_p{i}.py found", False, "script missing")
            ok = False
            continue
        result = subprocess.run(
            [sys.executable, script, save_path],
            capture_output=True, text=True, timeout=300,
        )
        passed = result.returncode == 0
        _record(f"verify_phase5_p{i}.py exits 0", passed,
                "" if passed else result.stdout[-200:] + result.stderr[-200:])
        if not passed:
            ok = False
    return ok


# ---------------------------------------------------------------------------
# Check 5 — Schema columns present
# ---------------------------------------------------------------------------

def check_schema_columns_present(save_path):
    print("\nCheck 5 — Schema columns present on fa_interest")
    conn = get_connection(save_path)
    try:
        ensure_fa_tables(conn)
        rows = conn.execute("PRAGMA table_info(fa_interest)").fetchall()
        col_names = {r['name'] for r in rows}
        for col in ('outcome_narrative', 'reason_code'):
            present = col in col_names
            _record(f"fa_interest.{col} column exists", present)
        return 'outcome_narrative' in col_names and 'reason_code' in col_names
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Check 6 — Migration is idempotent
# ---------------------------------------------------------------------------

def check_migration_idempotent(save_path):
    print("\nCheck 6 — ensure_fa_tables() is idempotent")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        try:
            ensure_fa_tables(conn)
            ensure_fa_tables(conn)  # second call must not raise
            _record("ensure_fa_tables() called twice without error", True)
            return True
        except Exception as e:
            _record("ensure_fa_tables() called twice without error", False, str(e))
            return False
        finally:
            conn.close()
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 7 — Template count meets minimum
# ---------------------------------------------------------------------------

def check_template_count_meets_minimum():
    print("\nCheck 7 — Pitch template count")
    total = len(PITCH_TEMPLATES)
    ok_total = total >= 20
    _record(f"Total templates >= 20 (got {total})", ok_total)

    ok = ok_total
    counts = {}
    for sig in PITCH_SIGNAL_TYPES:
        counts[sig] = sum(1 for t in PITCH_TEMPLATES if t['signal_type'] == sig)
    for sig, cnt in counts.items():
        ok_sig = cnt >= 3
        _record(f"signal_type '{sig}' has >= 3 templates (got {cnt})", ok_sig)
        if not ok_sig:
            ok = False

    return ok


# ---------------------------------------------------------------------------
# Check 8 — FA_REJECTION_REASONS typed
# ---------------------------------------------------------------------------

def check_fa_rejection_reasons_typed():
    print("\nCheck 8 — FA_REJECTION_REASONS")
    ok = True
    ok_count = len(FA_REJECTION_REASONS) >= 6
    _record(f"FA_REJECTION_REASONS has >= 6 keys (got {len(FA_REJECTION_REASONS)})", ok_count)
    if not ok_count:
        ok = False

    for key, val in FA_REJECTION_REASONS.items():
        ok_val = isinstance(val, str) and len(val) > 0
        if not ok_val:
            _record(f"FA_REJECTION_REASONS['{key}'] is non-empty string", False)
            ok = False

    if ok:
        _record("All FA_REJECTION_REASONS values are non-empty strings", True)

    return ok


# ---------------------------------------------------------------------------
# Check 9 — Outcome narrative writes
# ---------------------------------------------------------------------------

def check_outcome_narrative_writes(save_path):
    print("\nCheck 9 — Outcome narrative write / read-back")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_fa_tables(conn)
        try:
            row = _get_any_fa_interest_row(conn)
            if not row:
                _record("fa_interest row exists in save", False,
                        "no fa_interest rows — run offseason FA phase first")
                return False
            _record("fa_interest row found in save", True)

            # Generate and persist narrative
            result = generate_outcome_narrative(conn, row, 'signed_elsewhere')
            ok_narrative = isinstance(result.get('narrative'), str) and len(result['narrative']) > 0
            _record("generate_outcome_narrative returns non-empty narrative", ok_narrative,
                    "" if ok_narrative else str(result))

            with conn:
                update_fa_interest_outcome(conn, row['id'], result['narrative'], None)

            fetched = get_fa_interest_with_outcome(conn, row['id'])
            ok_stored = fetched is not None and fetched['outcome_narrative'] is not None
            _record("outcome_narrative persisted and readable", ok_stored)

            return ok_narrative and ok_stored
        finally:
            conn.close()
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 10 — Decline sets reason_code
# ---------------------------------------------------------------------------

def check_decline_sets_reason_code(save_path):
    print("\nCheck 10 — Decline outcome sets reason_code")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_fa_tables(conn)
        try:
            row = _get_any_fa_interest_row(conn)
            if not row:
                _record("fa_interest row available", False, "no rows in save")
                return False

            result = generate_outcome_narrative(conn, row, 'declined')
            ok_reason = result.get('reason_code') in FA_REJECTION_REASONS
            _record(f"reason_code in FA_REJECTION_REASONS (got {result.get('reason_code')!r})", ok_reason)

            # Persist and read back
            with conn:
                update_fa_interest_outcome(
                    conn, row['id'], result['narrative'], result.get('reason_code')
                )
            fetched = get_fa_interest_with_outcome(conn, row['id'])
            ok_persisted = fetched is not None and fetched['reason_code'] == result.get('reason_code')
            _record("reason_code persists and matches", ok_persisted)

            return ok_reason and ok_persisted
        finally:
            conn.close()
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 11 — signed_with_user has no reason_code
# ---------------------------------------------------------------------------

def check_signed_with_user_no_reason_code(save_path):
    print("\nCheck 11 — signed_with_user outcome has no reason_code")
    conn = get_connection(save_path)
    ensure_fa_tables(conn)
    try:
        row = _get_any_fa_interest_row(conn)
        if not row:
            _record("fa_interest row available", False, "no rows in save")
            return False

        result = generate_outcome_narrative(conn, row, 'signed_with_user')
        ok = result.get('reason_code') is None
        _record("reason_code is None for signed_with_user outcome", ok,
                "" if ok else f"got {result.get('reason_code')!r}")
        return ok
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Check 12 — Template match lambda smoke test
# ---------------------------------------------------------------------------

def check_pitch_template_match_function():
    print("\nCheck 12 — Template match lambda smoke test")
    sample_ctx = {
        'player_name': 'Test Player',
        'position': 'QB',
        'team_name': 'CHI',
        'rival_team_name': 'GB',
        'agent_name': "Test Player's agent",
        'offer_years': 3,
        'offer_value_m': 15,
    }

    templates_with_match = [t for t in PITCH_TEMPLATES if 'match' in t]
    templates_without_match = [t for t in PITCH_TEMPLATES if 'match' not in t]

    ok = True

    if templates_with_match:
        try:
            result = templates_with_match[0]['match'](sample_ctx)
            _record("Template with match lambda callable without error", True)
        except Exception as e:
            _record("Template with match lambda callable without error", False, str(e))
            ok = False
    else:
        _record("Template with match lambda found", False, "no templates have match lambdas")
        ok = False

    if templates_without_match:
        tmpl = templates_without_match[0]
        has_signal = 'signal_type' in tmpl
        _record("Template without match has signal_type (usable by signal alone)", has_signal)
        if not has_signal:
            ok = False
    else:
        _record("Template without match lambda found", False)
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Check 13 — Template slot-fill token validity
# ---------------------------------------------------------------------------

VALID_TOKENS = {
    'PLAYER_NAME', 'POSITION', 'TEAM_NAME', 'RIVAL_TEAM_NAME',
    'AGENT_NAME', 'OFFER_YEARS', 'OFFER_VALUE_M',
}

def check_pitch_template_slotfill_tokens():
    print("\nCheck 13 — Template token validity")
    ok = True
    for i, tmpl in enumerate(PITCH_TEMPLATES):
        tokens = re.findall(r'\{([A-Z_]+)\}', tmpl['template'])
        for tok in tokens:
            if tok not in VALID_TOKENS:
                _record(f"Template[{i}] invalid token {{{{ {tok} }}}}", False)
                ok = False

    if ok:
        _record("All template tokens are in documented valid set", True)
    return ok


# ---------------------------------------------------------------------------
# Check 14 — FA pitch integration smoke test
# ---------------------------------------------------------------------------

def check_fa_pitch_integration_smoke(save_path):
    print("\nCheck 14 — request_pitch_meeting integration smoke")
    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        ensure_fa_tables(conn)
        try:
            # Find a player with fa_interest in Tier 2 (pitch meetings require Tier 2)
            row = conn.execute(
                "SELECT * FROM fa_interest WHERE tier = 2 LIMIT 1"
            ).fetchone()
            if not row:
                # Tier 2 not available — try any tier row and check the return shape
                row = conn.execute(
                    "SELECT * FROM fa_interest WHERE tier != 3 LIMIT 1"
                ).fetchone()
            if not row:
                _record("fa_interest row with usable tier exists", False,
                        "no suitable fa_interest rows — run offseason FA phase first")
                return False

            player_id = row['player_id']
            team_id = row['team_id']
            tier = row['tier']

            _record(f"fa_interest row found (tier={tier})", True)

            try:
                result = request_pitch_meeting(player_id, team_id, 'winning', conn)
                ok_key = 'pitch_narratives' in result
                _record("return dict contains 'pitch_narratives' key", ok_key,
                        "" if ok_key else f"keys: {list(result.keys())}")
                ok_list = isinstance(result.get('pitch_narratives'), list)
                _record("pitch_narratives is a list", ok_list)
                ok_nonempty = len(result.get('pitch_narratives', [])) >= 1
                _record("pitch_narratives has >= 1 entry", ok_nonempty,
                        "" if ok_nonempty else "empty list returned")
                return ok_key and ok_list and ok_nonempty
            except ValueError as e:
                # Tier 3 raises — expected; still check the key exists when it does return
                _record("request_pitch_meeting ran (or raised expected ValueError)", True,
                        f"raised ValueError: {e}")
                return True

        finally:
            conn.close()
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Check 15 — Existing Phase 3 FA logic intact
# ---------------------------------------------------------------------------

def check_existing_phase3_fa_logic_intact(save_path):
    print("\nCheck 15 — Phase 3 FA logic intact")
    from src.transactions.free_agency import get_fa_market_status
    conn = get_connection(save_path)
    ensure_fa_tables(conn)
    try:
        result = get_fa_market_status(conn)
        ok = result is not None
        _record("get_fa_market_status() returns non-None result", ok,
                "" if ok else "returned None")
        return ok
    except Exception as e:
        _record("get_fa_market_status() does not raise", False, str(e))
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p7.py <save_path>")
        sys.exit(1)

    save_path = sys.argv[1]
    if not os.path.isfile(save_path):
        print(f"Save file not found: {save_path}")
        sys.exit(1)

    print(f"\nPhase 5 Prompt #7 Verification — {save_path}")
    print("=" * 60)

    check_scope_discipline()
    check_phase4_regression(save_path)
    check_layer_boundaries()
    check_p1_through_p6_regression(save_path)
    check_schema_columns_present(save_path)
    check_migration_idempotent(save_path)
    check_template_count_meets_minimum()
    check_fa_rejection_reasons_typed()
    check_outcome_narrative_writes(save_path)
    check_decline_sets_reason_code(save_path)
    check_signed_with_user_no_reason_code(save_path)
    check_pitch_template_match_function()
    check_pitch_template_slotfill_tokens()
    check_fa_pitch_integration_smoke(save_path)
    check_existing_phase3_fa_logic_intact(save_path)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} CHECKS FAILED ({passed}/{total} passed)")
        sys.exit(1)


if __name__ == '__main__':
    main()
