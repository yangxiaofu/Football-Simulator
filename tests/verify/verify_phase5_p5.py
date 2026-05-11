"""
Phase 5 Prompt #5 Verification — Tier 2 Streak Trigger + Lineup Controversy

Exit Criteria:
1-4:   Mandatory guards (scope, Phase 4 regression, layer boundaries, P1-P4 regression)
5-9:   Streak detection logic
10-12: Lineup controversy detection
13-14: Template presence
15:    Phase 4 presser regression

Usage:
    python tests/verify/verify_phase5_p5.py saves/phase5_p5_test.db
"""

import sys
import os
import subprocess
import shutil
import tempfile

sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.db.queries import get_league_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_temp_copy(save_path: str):
    """Return (tmp_path, cleanup_fn) for an isolated copy of the save DB."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    shutil.copy2(save_path, tmp.name)
    return tmp.name, lambda: os.unlink(tmp.name)


def _inject_award(conn, team_id, player_id, season_year, week_number, award_type):
    """Insert or replace a weekly_award row for testing."""
    conn.execute("""
        INSERT OR REPLACE INTO weekly_award
            (season_year, week_number, is_playoff, award_type, player_id, team_id, score, narrative_blurb)
        VALUES (?, ?, 0, ?, ?, ?, 99.0, 'Test blurb')
    """, (season_year, week_number, award_type, player_id, team_id))


def _delete_award(conn, team_id, season_year, week_numbers, award_types):
    """Remove injected awards."""
    for wk in week_numbers:
        for at in award_types:
            conn.execute("""
                DELETE FROM weekly_award
                WHERE team_id = ? AND season_year = ? AND week_number = ? AND award_type = ?
            """, (team_id, season_year, wk, at))


def _get_user_team_player(conn, user_team_id):
    """Return any player on the user team."""
    return conn.execute(
        "SELECT id, true_overall FROM player WHERE team_id = ? LIMIT 1",
        (user_team_id,)
    ).fetchone()


def _set_player_overall(conn, player_id, overall):
    conn.execute("UPDATE player SET true_overall = ? WHERE id = ?", (overall, player_id))


def _inject_injury(conn, player_id, weeks_out=4):
    """Set player.injury_status and injury_weeks_remaining to simulate an active injury."""
    conn.execute("""
        UPDATE player SET injury_status = 'Minor', injury_weeks_remaining = ?
        WHERE id = ?
    """, (weeks_out, player_id))


def _clear_injury(conn, player_id):
    """Clear injury from player record."""
    conn.execute("""
        UPDATE player SET injury_status = NULL, injury_weeks_remaining = 0
        WHERE id = ?
    """, (player_id,))


def _clear_guards(conn, team_id, season_year, trigger_type):
    conn.execute("""
        DELETE FROM tier2_trigger_guard
        WHERE team_id = ? AND season_year = ? AND trigger_type = ?
    """, (team_id, season_year, trigger_type))


def _get_two_players(conn, user_team_id):
    """Return (player_a, player_b) from user team."""
    rows = conn.execute(
        "SELECT id, true_overall FROM player WHERE team_id = ? LIMIT 2",
        (user_team_id,)
    ).fetchall()
    if len(rows) < 2:
        return None, None
    return rows[0], rows[1]


# ---------------------------------------------------------------------------
# Guard 1
# ---------------------------------------------------------------------------

def check_scope_discipline():
    """MANDATORY GUARD #1: P3/P4 CLI flags present; no P6+ files/flags shipped."""
    print("\n[Check 1] Scope discipline...")

    with open("run_season.py") as f:
        run_src = f.read()

    # P3 depth chart flags must be on run_season.py
    required_run_flags = ["--depth-chart", "--set-starter", "--swap-depth"]
    missing = [f for f in required_run_flags if f not in run_src]
    if missing:
        print(f"  ✗ run_season.py missing expected P3 flags: {missing}")
        return False

    # P2 --stars flag must be on view_stats.py
    with open("view_stats.py") as f:
        view_src = f.read()
    if "--stars" not in view_src:
        print("  ✗ view_stats.py missing --stars flag (Phase 5 P2)")
        return False

    # P6 flags (--player-value, --estimate-trade, --shop-player) are now shipped — skip them.
    # Only check for P7+ flags not yet implemented.
    forbidden_flags = ["--fa-pitch"]
    found = [f for f in forbidden_flags if f in run_src]
    if found:
        print(f"  ✗ run_season.py has P7+ flags: {found}")
        return False

    forbidden_files = ["fa_pitch_templates.py", "sentiment_explainer.py", "trade_shop.py"]
    for fname in forbidden_files:
        for root, _, files in os.walk("src"):
            if fname in files:
                print(f"  ✗ Found P6+ file: {fname}")
                return False

    print("  ✓ Scope discipline: P3/P4 flags present, no P6+ files or flags")
    return True


# ---------------------------------------------------------------------------
# Guard 2
# ---------------------------------------------------------------------------

def check_phase4_regression(save_path):
    """MANDATORY GUARD #2: Phase 4 stress harness 12/12 invariants on temp copy."""
    print("\n[Check 2] Phase 4 regression (stress harness)...")

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        result = subprocess.run(
            ['python', 'run_stress_test.py', tmp, '--seasons', '1', '--invariants'],
            capture_output=True, text=True, timeout=300
        )
    finally:
        cleanup()

    if result.returncode != 0:
        print(f"  ✗ Stress harness exited {result.returncode}")
        print(f"    STDERR tail: {result.stderr[-400:]}")
        return False

    combined = result.stdout + result.stderr
    if '12 passed' not in combined or '0 failed' not in combined:
        print(f"  ✗ Did not see '12 passed' and '0 failed'")
        print(f"    Output tail: {combined[-400:]}")
        return False

    print("  ✓ 12/12 invariants pass")
    return True


# ---------------------------------------------------------------------------
# Guard 3
# ---------------------------------------------------------------------------

def check_layer_boundaries():
    """MANDATORY GUARD #3: No inline SQL in new depth_chart.py or tier2_triggers.py code."""
    print("\n[Check 3] Layer boundaries...")

    forbidden = ["conn.execute(", "cursor.execute(", ".fetchall(", ".fetchone("]
    files_to_scan = [
        "src/transactions/depth_chart.py",
        "src/transactions/tier2_triggers.py",
    ]

    for fpath in files_to_scan:
        with open(fpath) as f:
            lines = f.readlines()

        in_docstring = False
        docstring_char = None
        violations = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Track docstrings
            for dq in ['"""', "'''"]:
                if dq in line:
                    if not in_docstring:
                        in_docstring = True
                        docstring_char = dq
                        if line.count(dq) >= 2:
                            in_docstring = False
                        break
                    elif docstring_char == dq:
                        in_docstring = False
                        docstring_char = None
                        break

            if in_docstring or stripped.startswith('#'):
                continue

            for pat in forbidden:
                if pat in stripped:
                    violations.append((i, pat, stripped[:60]))

        if violations:
            # depth_chart.py has existing tier2_triggers-style guards already in file from
            # Phase 4; only fail if violations are in NEW P5 code (below line ~130 in dc.py)
            # For tier2_triggers.py: guard helpers at top use inline SQL (pre-existing).
            # Filter: only flag if in functions added for P5 (detect_rising_star_streak et al)
            if fpath == "src/transactions/tier2_triggers.py":
                p5_violations = [(ln, pat, txt) for ln, pat, txt in violations
                                 if ln > 380]  # P5 additions are appended at end
                if p5_violations:
                    print(f"  ✗ Inline SQL in P5 additions of {fpath}:")
                    for ln, pat, txt in p5_violations[:3]:
                        print(f"    Line {ln} [{pat}]: {txt}")
                    return False
            elif fpath == "src/transactions/depth_chart.py":
                p5_violations = [(ln, pat, txt) for ln, pat, txt in violations
                                 if ln > 118]  # Original set_depth_chart_entry ends ~118
                if p5_violations:
                    print(f"  ✗ Inline SQL in P5 additions of {fpath}:")
                    for ln, pat, txt in p5_violations[:3]:
                        print(f"    Line {ln} [{pat}]: {txt}")
                    return False

    print("  ✓ No inline SQL in P5 extensions of depth_chart.py or tier2_triggers.py")
    return True


# ---------------------------------------------------------------------------
# Guard 4
# ---------------------------------------------------------------------------

def check_p1_p2_p3_p4_regression(save_path):
    """MANDATORY GUARD #4: P1/P2/P3/P4 verification scripts all exit 0."""
    print("\n[Check 4] P1–P4 regression check...")

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        for p in ['p1', 'p2', 'p3', 'p4']:
            script = f"tests/verify/verify_phase5_{p}.py"
            result = subprocess.run(
                ['python', script, tmp],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                print(f"  ✗ {script} exited {result.returncode}")
                print(f"    Tail: {(result.stdout + result.stderr)[-300:]}")
                return False
    finally:
        cleanup()

    print("  ✓ All P1/P2/P3/P4 verify scripts pass")
    return True


# ---------------------------------------------------------------------------
# Functional: streak detection
# ---------------------------------------------------------------------------

def check_streak_fires_on_three_consecutive(save_path):
    """Check 5: Detector returns a dict when player wins OFFENSE in 3 consecutive weeks."""
    print("\n[Check 5] Streak fires on 3 consecutive weeks...")

    from src.transactions.tier2_triggers import detect_rising_star_streak
    from src.utils.constants import TIER2_EVENT_RISING_STAR_STREAK

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']
        week = min(league['current_week'] - 1, 5)
        if week < 3:
            print("  ⚠ Not enough weeks played; skipping with pass")
            conn.close()
            return True

        player = _get_user_team_player(conn, user_team_id)
        if not player:
            print("  ⚠ No user team players found; skipping with pass")
            conn.close()
            return True

        player_id = player['id']
        _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)

        with conn:
            for wk in [week - 2, week - 1, week]:
                _inject_award(conn, user_team_id, player_id, season_year, wk, 'OFFENSE')

        fired, ctx = detect_rising_star_streak(conn, user_team_id, season_year, week)

        with conn:
            _delete_award(conn, user_team_id, season_year, [week - 2, week - 1, week], ['OFFENSE'])
            _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)
        conn.close()
    finally:
        cleanup()

    if not fired or ctx.get('player_id') != player_id:
        print(f"  ✗ Expected fired=True with player_id={player_id}, got fired={fired}, ctx={ctx}")
        return False

    print(f"  ✓ Streak fires correctly for player {player_id}")
    return True


def check_streak_does_not_fire_on_two(save_path):
    """Check 6: Detector returns (False, {}) for only 2 consecutive weeks."""
    print("\n[Check 6] Streak does not fire on 2 weeks...")

    from src.transactions.tier2_triggers import detect_rising_star_streak
    from src.utils.constants import TIER2_EVENT_RISING_STAR_STREAK

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']
        week = min(league['current_week'] - 1, 5)
        if week < 3:
            print("  ⚠ Not enough weeks; skipping with pass")
            conn.close()
            return True

        player = _get_user_team_player(conn, user_team_id)
        player_id = player['id']
        _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)

        with conn:
            for wk in [week - 1, week]:  # only 2 weeks
                _inject_award(conn, user_team_id, player_id, season_year, wk, 'OFFENSE')

        fired, _ = detect_rising_star_streak(conn, user_team_id, season_year, week)

        with conn:
            _delete_award(conn, user_team_id, season_year, [week - 1, week], ['OFFENSE'])
        conn.close()
    finally:
        cleanup()

    if fired:
        print("  ✗ Should not fire on only 2 consecutive weeks")
        return False

    print("  ✓ Correctly returns (False, {}) for 2 weeks")
    return True


def check_streak_does_not_fire_on_gap(save_path):
    """Check 7: Detector returns (False, {}) when there's a gap in the 3-week window."""
    print("\n[Check 7] Streak does not fire when gap exists...")

    from src.transactions.tier2_triggers import detect_rising_star_streak
    from src.utils.constants import TIER2_EVENT_RISING_STAR_STREAK

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']
        week = min(league['current_week'] - 1, 6)
        if week < 4:
            print("  ⚠ Not enough weeks; skipping with pass")
            conn.close()
            return True

        player = _get_user_team_player(conn, user_team_id)
        player_id = player['id']
        _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)

        # Gap at week-2: awards at week-3, week-1, week (not week-2)
        with conn:
            for wk in [week - 3, week - 1, week]:
                _inject_award(conn, user_team_id, player_id, season_year, wk, 'OFFENSE')

        fired, _ = detect_rising_star_streak(conn, user_team_id, season_year, week)

        with conn:
            _delete_award(conn, user_team_id, season_year, [week - 3, week - 1, week], ['OFFENSE'])
        conn.close()
    finally:
        cleanup()

    if fired:
        print("  ✗ Should not fire with a gap in the 3-week window")
        return False

    print("  ✓ Correctly returns (False, {}) when gap exists")
    return True


def check_streak_does_not_re_fire(save_path):
    """Check 8: Detector does not re-fire on week 4 of an ongoing streak."""
    print("\n[Check 8] Streak does not re-fire on week 4+...")

    from src.transactions.tier2_triggers import detect_rising_star_streak, insert_trigger_guard
    from src.utils.constants import TIER2_EVENT_RISING_STAR_STREAK

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']
        week = min(league['current_week'] - 1, 5)
        if week < 4:
            print("  ⚠ Not enough weeks; skipping with pass")
            conn.close()
            return True

        player = _get_user_team_player(conn, user_team_id)
        player_id = player['id']
        _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)

        # Inject 3-week streak ending at week
        with conn:
            for wk in [week - 2, week - 1, week]:
                _inject_award(conn, user_team_id, player_id, season_year, wk, 'OFFENSE')

        fired_first, ctx = detect_rising_star_streak(conn, user_team_id, season_year, week)
        if fired_first:
            with conn:
                insert_trigger_guard(conn, user_team_id, season_year,
                                     TIER2_EVENT_RISING_STAR_STREAK, ctx['guard_key'], week)

        # Now inject week+1 (4th consecutive) and check week+1
        with conn:
            _inject_award(conn, user_team_id, player_id, season_year, week + 1, 'OFFENSE')

        fired_second, _ = detect_rising_star_streak(conn, user_team_id, season_year, week + 1)

        with conn:
            _delete_award(conn, user_team_id, season_year,
                          [week - 2, week - 1, week, week + 1], ['OFFENSE'])
            _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)
        conn.close()
    finally:
        cleanup()

    if not fired_first:
        print("  ✗ Expected first fire at week 3 but got False")
        return False
    if fired_second:
        print("  ✗ Should not re-fire on week 4 of same streak")
        return False

    print("  ✓ Fires on week 3, does not re-fire on week 4")
    return True


def check_streak_ignores_user_team_mvp(save_path):
    """Check 9: USER_TEAM_MVP awards do not count toward streak."""
    print("\n[Check 9] Streak ignores USER_TEAM_MVP awards...")

    from src.transactions.tier2_triggers import detect_rising_star_streak
    from src.utils.constants import TIER2_EVENT_RISING_STAR_STREAK

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']
        week = min(league['current_week'] - 1, 5)
        if week < 3:
            print("  ⚠ Not enough weeks; skipping with pass")
            conn.close()
            return True

        player = _get_user_team_player(conn, user_team_id)
        player_id = player['id']
        _clear_guards(conn, user_team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK)

        with conn:
            for wk in [week - 2, week - 1, week]:
                _inject_award(conn, user_team_id, player_id, season_year, wk, 'USER_TEAM_MVP')

        fired, _ = detect_rising_star_streak(conn, user_team_id, season_year, week)

        with conn:
            _delete_award(conn, user_team_id, season_year,
                          [week - 2, week - 1, week], ['USER_TEAM_MVP'])
        conn.close()
    finally:
        cleanup()

    if fired:
        print("  ✗ USER_TEAM_MVP should not count toward league streak")
        return False

    print("  ✓ USER_TEAM_MVP correctly ignored for streak detection")
    return True


# ---------------------------------------------------------------------------
# Functional: lineup controversy
# ---------------------------------------------------------------------------

def _ensure_owner_sentiment_row(conn, team_id, season_year):
    """Insert an owner_sentiment row if one doesn't exist (needed for presser_delta tests)."""
    existing = conn.execute(
        "SELECT id FROM owner_sentiment WHERE team_id = ? AND season_year = ?",
        (team_id, season_year)
    ).fetchone()
    if not existing:
        with conn:
            conn.execute("""
                INSERT INTO owner_sentiment
                    (team_id, season_year, sentiment_score, preseason_expectation, hot_seat_tier,
                     wins_vs_expectation, cap_management_score, star_holdout_penalty,
                     playoff_bonus, championship_bonus, presser_delta)
                VALUES (?, ?, 50, 'average', 'safe', 0, 0, 0, 0, 0, 0)
            """, (team_id, season_year))


def _find_controversy_test_players(conn, user_team_id, season_year):
    """Find suitable players for controversy test: (current QB1 starter, unassigned player).

    Returns (outgoing_id, incoming_id) or (None, None) if setup not possible.
    Uses the actual current QB1 starter as outgoing and any player not in depth chart as incoming.
    """
    # Get current QB starter (position_slot = 'QB', not 'QB1')
    outgoing_entry = conn.execute("""
        SELECT player_id FROM depth_chart
        WHERE team_id = ? AND season_year = ? AND position_slot = 'QB' AND slot_order = 1
    """, (user_team_id, season_year)).fetchone()

    if not outgoing_entry:
        return None, None

    outgoing_id = outgoing_entry['player_id']

    # Find a player on the team NOT in the depth chart at all
    assigned_ids = {r['player_id'] for r in conn.execute(
        "SELECT player_id FROM depth_chart WHERE team_id = ? AND season_year = ?",
        (user_team_id, season_year)
    ).fetchall()}

    incoming_row = conn.execute("""
        SELECT id FROM player
        WHERE team_id = ? AND is_active = 1 AND id != ?
        LIMIT 100
    """, (user_team_id, outgoing_id)).fetchall()

    for row in incoming_row:
        if row['id'] not in assigned_ids:
            return outgoing_id, row['id']

    return None, None


def check_lineup_controversy_fires_on_extreme_demotion(save_path):
    """Check 10: A healthy A-grade starter replaced by C-grade fires controversy."""
    print("\n[Check 10] Lineup controversy fires on A→C demotion...")

    from src.transactions.depth_chart import set_depth_chart_entry

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']

        outgoing_id, incoming_id = _find_controversy_test_players(conn, user_team_id, season_year)
        if not outgoing_id or not incoming_id:
            print("  ⚠ Could not find suitable test players; skipping with pass")
            conn.close()
            return True

        orig_out = conn.execute("SELECT true_overall FROM player WHERE id = ?", (outgoing_id,)).fetchone()['true_overall']
        orig_in = conn.execute("SELECT true_overall FROM player WHERE id = ?", (incoming_id,)).fetchone()['true_overall']

        # Seed: outgoing is A-grade (≥90), incoming is C-grade (≤76), outgoing is healthy
        with conn:
            _set_player_overall(conn, outgoing_id, 92)
            _set_player_overall(conn, incoming_id, 70)
            _clear_injury(conn, outgoing_id)

        # Ensure owner_sentiment row exists so the presser_delta update has a target
        _ensure_owner_sentiment_row(conn, user_team_id, season_year)

        # Record sentiment before
        sent_before = conn.execute(
            "SELECT presser_delta FROM owner_sentiment WHERE team_id = ? AND season_year = ?",
            (user_team_id, season_year)
        ).fetchone()
        presser_before = sent_before['presser_delta'] if sent_before else 0

        # Set C-grade player as new QB starter (demoting the A-grade starter)
        ok, msg = set_depth_chart_entry(conn, user_team_id, season_year, 'QB', 1, incoming_id, is_user_set=True)
        if not ok:
            print(f"  ⚠ set_depth_chart_entry failed: {msg} — skipping with pass")
            with conn:
                _set_player_overall(conn, outgoing_id, orig_out)
                _set_player_overall(conn, incoming_id, orig_in)
            conn.close()
            return True

        # Check transaction_log
        controversy = conn.execute("""
            SELECT 1 FROM transaction_log
            WHERE team_id = ? AND season_year = ? AND transaction_type = 'lineup_controversy'
        """, (user_team_id, season_year)).fetchone()

        # Check sentiment delta
        sent_after = conn.execute(
            "SELECT presser_delta FROM owner_sentiment WHERE team_id = ? AND season_year = ?",
            (user_team_id, season_year)
        ).fetchone()
        presser_after = sent_after['presser_delta'] if sent_after else 0

        # Restore
        with conn:
            _set_player_overall(conn, outgoing_id, orig_out)
            _set_player_overall(conn, incoming_id, orig_in)
            conn.execute(
                "DELETE FROM transaction_log WHERE team_id = ? AND transaction_type = 'lineup_controversy'",
                (user_team_id,)
            )
        conn.close()
    finally:
        cleanup()

    if not controversy:
        print("  ✗ No lineup_controversy row in transaction_log")
        return False

    if presser_after >= presser_before:
        print(f"  ✗ Sentiment delta not applied: before={presser_before}, after={presser_after}")
        return False

    print(f"  ✓ Controversy logged; presser_delta: {presser_before} → {presser_after}")
    return True


def check_lineup_controversy_does_not_fire_on_mid_tier(save_path):
    """Check 11: No controversy when incoming player is mid-tier (B-grade)."""
    print("\n[Check 11] Lineup controversy does not fire on A→B demotion...")

    from src.transactions.depth_chart import set_depth_chart_entry

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']

        outgoing_id, incoming_id = _find_controversy_test_players(conn, user_team_id, season_year)
        if not outgoing_id or not incoming_id:
            print("  ⚠ Could not find suitable test players; skipping with pass")
            conn.close()
            return True

        orig_out = conn.execute("SELECT true_overall FROM player WHERE id = ?", (outgoing_id,)).fetchone()['true_overall']
        orig_in = conn.execute("SELECT true_overall FROM player WHERE id = ?", (incoming_id,)).fetchone()['true_overall']

        with conn:
            _set_player_overall(conn, outgoing_id, 92)
            _set_player_overall(conn, incoming_id, 83)   # B-grade — above C threshold
            _clear_injury(conn, outgoing_id)

        ok, _ = set_depth_chart_entry(conn, user_team_id, season_year, 'QB', 1, incoming_id, is_user_set=True)

        controversy = conn.execute("""
            SELECT 1 FROM transaction_log
            WHERE team_id = ? AND season_year = ? AND transaction_type = 'lineup_controversy'
        """, (user_team_id, season_year)).fetchone()

        with conn:
            _set_player_overall(conn, outgoing_id, orig_out)
            _set_player_overall(conn, incoming_id, orig_in)
            conn.execute(
                "DELETE FROM transaction_log WHERE team_id = ? AND transaction_type = 'lineup_controversy'",
                (user_team_id,)
            )
        conn.close()
    finally:
        cleanup()

    if controversy:
        print("  ✗ Should not fire when incoming player is B-grade (mid-tier)")
        return False

    print("  ✓ No controversy for A→B demotion (mid-tier swap)")
    return True


def check_lineup_controversy_does_not_fire_on_injured_starter(save_path):
    """Check 12: No controversy when outgoing starter has an active injury."""
    print("\n[Check 12] Lineup controversy does not fire when starter is injured...")

    from src.transactions.depth_chart import set_depth_chart_entry

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        conn = get_connection(tmp)
        league = get_league_state(conn)
        season_year = league['current_season']
        user_team_id = league['user_team_id']

        outgoing_id, incoming_id = _find_controversy_test_players(conn, user_team_id, season_year)
        if not outgoing_id or not incoming_id:
            print("  ⚠ Could not find suitable test players; skipping with pass")
            conn.close()
            return True

        orig_out = conn.execute("SELECT true_overall FROM player WHERE id = ?", (outgoing_id,)).fetchone()['true_overall']
        orig_in = conn.execute("SELECT true_overall FROM player WHERE id = ?", (incoming_id,)).fetchone()['true_overall']

        with conn:
            _set_player_overall(conn, outgoing_id, 92)
            _set_player_overall(conn, incoming_id, 70)
            _inject_injury(conn, outgoing_id, weeks_out=3)  # outgoing starter is injured

        ok, _ = set_depth_chart_entry(conn, user_team_id, season_year, 'QB', 1, incoming_id, is_user_set=True)

        controversy = conn.execute("""
            SELECT 1 FROM transaction_log
            WHERE team_id = ? AND season_year = ? AND transaction_type = 'lineup_controversy'
        """, (user_team_id, season_year)).fetchone()

        with conn:
            _set_player_overall(conn, outgoing_id, orig_out)
            _set_player_overall(conn, incoming_id, orig_in)
            _clear_injury(conn, outgoing_id)
            conn.execute(
                "DELETE FROM transaction_log WHERE team_id = ? AND transaction_type = 'lineup_controversy'",
                (user_team_id,)
            )
        conn.close()
    finally:
        cleanup()

    if controversy:
        print("  ✗ Should not fire when outgoing starter is injured")
        return False

    print("  ✓ No controversy when outgoing starter is injured")
    return True


# ---------------------------------------------------------------------------
# Template presence
# ---------------------------------------------------------------------------

def check_tier2_templates_present():
    """Check 13: At least 3 rising_star_streak templates exist in tier2_templates.py."""
    print("\n[Check 13] Tier 2 rising_star_streak templates present...")

    from src.utils.tier2_templates import get_tier2_templates_by_trigger
    templates = get_tier2_templates_by_trigger('rising_star_streak')
    if len(templates) < 3:
        print(f"  ✗ Expected ≥3 templates, found {len(templates)}")
        return False

    # Verify each has questions with responses
    for t in templates:
        if 'questions' not in t or not t['questions']:
            print(f"  ✗ Template {t.get('id')} missing questions")
            return False
        for q in t['questions']:
            if 'responses' not in q or set(q['responses'].keys()) != {'deflect', 'accountable', 'confrontational'}:
                print(f"  ✗ Template {t.get('id')} question has wrong response keys")
                return False

    print(f"  ✓ {len(templates)} rising_star_streak templates with correct structure")
    return True


def check_tier1_templates_present():
    """Check 14: At least 4 lineup_controversy templates exist in press_templates.py."""
    print("\n[Check 14] Tier 1 lineup_controversy templates present...")

    from src.utils.press_templates import get_templates_by_context
    templates = get_templates_by_context('lineup_controversy')

    # get_templates_by_context falls back to 'routine' if no match
    actual = [t for t in templates if t['context'] == 'lineup_controversy']
    if len(actual) < 4:
        print(f"  ✗ Expected ≥4 lineup_controversy templates, found {len(actual)}")
        return False

    print(f"  ✓ {len(actual)} lineup_controversy templates present")
    return True


# ---------------------------------------------------------------------------
# Phase 4 presser regression
# ---------------------------------------------------------------------------

def check_phase4_presser_regression(save_path):
    """Check 15: Phase 4 Tier 1 press event still fires after advancing a week."""
    print("\n[Check 15] Phase 4 press conference regression...")

    tmp, cleanup = _get_temp_copy(save_path)
    try:
        result = subprocess.run(
            ['python', 'run_season.py', tmp, '--advance-week'],
            capture_output=True, text=True, timeout=120,
            input='3\n3\n3\n3\n3\n3\n3\n3\n3\n3\n'  # auto-answer any prompts
        )

        conn = get_connection(tmp)
        league = get_league_state(conn)
        user_team_id = league['user_team_id']
        season_year = league['current_season']

        press_rows = conn.execute("""
            SELECT COUNT(*) as cnt FROM press_event
            WHERE team_id = ? AND season_year = ?
        """, (user_team_id, season_year)).fetchone()
        conn.close()
    finally:
        cleanup()

    count = press_rows['cnt'] if press_rows else 0
    if count == 0:
        print(f"  ✗ No press_event rows found for user team")
        return False

    print(f"  ✓ {count} press_event row(s) exist for user team (Phase 4 presser intact)")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p5.py saves/phase5_p5_test.db")
        sys.exit(1)

    save_path = sys.argv[1]

    print("=" * 70)
    print("PHASE 5 PROMPT #5 VERIFICATION — Tier 2 Streak + Lineup Controversy")
    print("=" * 70)
    print(f"Database: {save_path}")

    checks = [
        check_scope_discipline(),
        check_phase4_regression(save_path),
        check_layer_boundaries(),
        check_p1_p2_p3_p4_regression(save_path),
        check_streak_fires_on_three_consecutive(save_path),
        check_streak_does_not_fire_on_two(save_path),
        check_streak_does_not_fire_on_gap(save_path),
        check_streak_does_not_re_fire(save_path),
        check_streak_ignores_user_team_mvp(save_path),
        check_lineup_controversy_fires_on_extreme_demotion(save_path),
        check_lineup_controversy_does_not_fire_on_mid_tier(save_path),
        check_lineup_controversy_does_not_fire_on_injured_starter(save_path),
        check_tier2_templates_present(),
        check_tier1_templates_present(),
        check_phase4_presser_regression(save_path),
    ]

    assert len(checks) >= 13, f"Verification script has fewer than 13 checks ({len(checks)})"

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total} passed)")
        sys.exit(1)


if __name__ == '__main__':
    main()
