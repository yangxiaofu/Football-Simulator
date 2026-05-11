"""
Phase 5 Prompt #9 verification script — Press Conference Variety Expansion.

Run: python tests/verify/verify_phase5_p9.py <save_path>
Expected exit: 0 with "ALL CHECKS PASSED (15/15)"
"""

import os
import sys
import sqlite3
import subprocess
import tempfile
import shutil

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


# ---------------------------------------------------------------------------
# Guard 1 — Scope discipline
# ---------------------------------------------------------------------------

def check_scope_discipline():
    """MANDATORY GUARD #1: No P10+ work shipped early; P3-P8 artifacts intact."""
    with open('run_season.py') as f:
        run_src = f.read()
    for flag in ['--depth-chart', '--set-starter', '--swap-depth', '--reset-depth',
                 '--player-value', '--estimate-trade', '--shop-player']:
        assert flag in run_src, f"Prior prompt flag missing in run_season.py: {flag}"

    for entry in ['view_stats.py', 'view_sentiment.py']:
        assert os.path.exists(entry), f"Prior entry point missing: {entry}"

    # No P10 work
    assert not os.path.exists('src/league/season_recap.py'), \
        "P10 season_recap.py shipped early"
    assert 'year_over_year_recap' not in run_src, \
        "P10 year-over-year recap auto-print found in run_season.py"


# ---------------------------------------------------------------------------
# Guard 2 — Phase 4 regression (stress harness 12/12)
# ---------------------------------------------------------------------------

def check_phase4_regression(save_path):
    """MANDATORY GUARD #2: Phase 4 stress harness passes 12/12 invariants."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        result = subprocess.run(
            ['python', 'run_stress_test.py', tmp_path, '--seasons', '1', '--invariants'],
            capture_output=True, text=True, timeout=300,
        )
        assert result.returncode == 0, (
            f"Stress harness exited {result.returncode}\n"
            f"stderr tail: {result.stderr[-500:]}"
        )
        assert '12 passed' in result.stdout and '0 failed' in result.stdout, (
            f"Expected '12 passed' AND '0 failed'.\n"
            f"Stdout tail: {result.stdout[-500:]}"
        )
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Guard 3 — Layer boundaries
# ---------------------------------------------------------------------------

def check_layer_boundaries():
    """MANDATORY GUARD #3: press_templates.py is SQL-free; new P9 code in
    press_conference.py doesn't introduce inline SQL in select_template_for_context."""
    with open('src/utils/press_templates.py') as f:
        tmpl_src = f.read()
    assert 'conn.execute' not in tmpl_src, \
        "press_templates.py must be pure data — no SQL allowed"
    assert 'SELECT' not in tmpl_src and 'INSERT' not in tmpl_src, \
        "press_templates.py contains SQL keywords"

    with open('src/transactions/press_conference.py') as f:
        pc_src = f.read()
    # Find select_template_for_context body and assert no inline SQL there
    start = pc_src.find('def select_template_for_context(')
    end = pc_src.find('\ndef ', start + 1)
    fn_body = pc_src[start:end] if end != -1 else pc_src[start:]
    assert 'conn.execute' not in fn_body, \
        "select_template_for_context must not contain inline SQL — use queries.py"


# ---------------------------------------------------------------------------
# Guard 4 — Prior Phase 5 artifacts intact (flat check, no subprocess nesting)
# ---------------------------------------------------------------------------

def check_prior_phase5_artifacts_intact(save_path):
    """MANDATORY GUARD #4: Flat artifact check for P1–P8. No subprocess calls."""
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row

    # P1: 5 stats tables
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    for t in ('player_week_stats', 'player_season_running', 'team_week_stats',
              'team_season_running', 'weekly_award'):
        assert t in tables, f"P1 table missing: {t}"

    # P2: view_stats.py + flags
    assert os.path.exists('view_stats.py'), 'P2 view_stats.py missing'
    with open('view_stats.py') as f:
        vs_src = f.read()
    for flag in ('--leaderboard', '--player', '--team', '--week', '--stars'):
        assert flag in vs_src, f"P2 flag missing: {flag}"

    # P3: depth_chart table + CLI flags
    assert 'depth_chart' in tables, 'P3 depth_chart table missing'
    with open('run_season.py') as f:
        run_src = f.read()
    for flag in ('--depth-chart', '--set-starter'):
        assert flag in run_src, f"P3 flag missing: {flag}"

    # P4: stars_selection.py + star_templates.py with enough templates
    for p in ('src/league/stars_selection.py', 'src/utils/star_templates.py'):
        assert os.path.exists(p), f"P4 file missing: {p}"
    with open('src/utils/star_templates.py') as f:
        star_src = f.read()
    id_count = star_src.count("'id':") + star_src.count('"id":')
    assert id_count >= 15, f"P4 star_templates has only {id_count} id entries"

    # P5: lineup controversy hook + streak detector
    assert os.path.exists('src/transactions/depth_chart.py'), 'P5 depth_chart.py missing'
    with open('src/transactions/depth_chart.py') as f:
        dc_src = f.read()
    assert '_maybe_queue_lineup_controversy' in dc_src, \
        'P5 lineup controversy hook missing'
    assert os.path.exists('src/transactions/tier2_triggers.py')
    with open('src/transactions/tier2_triggers.py') as f:
        t2_src = f.read()
    assert 'detect_rising_star_streak' in t2_src, 'P5 streak detector missing'

    # P6: trade functions
    with open('src/transactions/trades.py') as f:
        tr_src = f.read()
    for fn in ('def estimate_trade', 'def get_player_value', 'def shop_player', 'def propose_counter'):
        assert fn in tr_src, f"P6 function missing: {fn}"

    # P7: pitch_meeting_templates.py + fa_interest columns
    assert os.path.exists('src/utils/pitch_meeting_templates.py'), 'P7 templates file missing'
    with open('src/utils/pitch_meeting_templates.py') as f:
        pmt_src = f.read()
    pmt_count = pmt_src.count("'signal_type':") + pmt_src.count('"signal_type":')
    assert pmt_count >= 20, f"P7 has only {pmt_count} pitch templates"
    fa_cols = [c[1] for c in conn.execute("PRAGMA table_info(fa_interest)").fetchall()]
    assert 'outcome_narrative' in fa_cols, 'P7 outcome_narrative column missing'
    assert 'reason_code' in fa_cols, 'P7 fa_interest.reason_code column missing'

    # P8: sentiment_explainer.py + view_sentiment.py + owner_sentiment.reason_code
    for p in ('src/league/sentiment_explainer.py', 'view_sentiment.py'):
        assert os.path.exists(p), f"P8 file missing: {p}"
    os_cols = [c[1] for c in conn.execute("PRAGMA table_info(owner_sentiment)").fetchall()]
    assert 'reason_code' in os_cols, 'P8 owner_sentiment.reason_code column missing'

    conn.close()


# ---------------------------------------------------------------------------
# Check 5 — Schema: template_id column present
# ---------------------------------------------------------------------------

def check_schema_template_id_present(save_path):
    """Check 5: ensure_press_tables migration adds template_id column."""
    from src.db.connection import ensure_press_tables
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    ensure_press_tables(conn)  # run migration to add column
    cols = [c[1] for c in conn.execute("PRAGMA table_info(press_event)").fetchall()]
    conn.close()
    assert 'template_id' in cols, \
        f"press_event.template_id missing after migration. Columns: {cols}"


# ---------------------------------------------------------------------------
# Check 6 — Migration idempotent
# ---------------------------------------------------------------------------

def check_migration_idempotent(save_path):
    """Check 6: calling ensure_press_tables(conn) twice does not error."""
    from src.db.connection import ensure_press_tables
    conn = sqlite3.connect(save_path)
    conn.row_factory = sqlite3.Row
    ensure_press_tables(conn)
    ensure_press_tables(conn)  # second call must be silent
    conn.close()


# ---------------------------------------------------------------------------
# Check 7 — Template count meets minimum
# ---------------------------------------------------------------------------

def check_template_count_meets_minimum():
    """Check 7: ≥70 total templates; each of the 14 named contexts has ≥5."""
    from src.utils.press_templates import TEMPLATES
    from src.utils.constants import (
        PRESS_CONTEXT_POST_WIN_BLOWOUT, PRESS_CONTEXT_POST_WIN_NARROW,
        PRESS_CONTEXT_POST_WIN_VS_RIVAL, PRESS_CONTEXT_POST_LOSS_BLOWOUT,
        PRESS_CONTEXT_POST_LOSS_CLOSE, PRESS_CONTEXT_POST_LOSS_UPSET,
        PRESS_CONTEXT_POST_STARTER_INJURY, PRESS_CONTEXT_MID_SEASON_GRIND,
        PRESS_CONTEXT_PRE_DIVISION_GAME, PRESS_CONTEXT_POST_INJURY_CRITICAL,
        PRESS_CONTEXT_PRE_PLAYOFF_GAME, PRESS_CONTEXT_POST_CLINCHING,
        PRESS_CONTEXT_POST_ELIMINATED, PRESS_CONTEXT_LINEUP_CONTROVERSY,
    )
    assert len(TEMPLATES) >= 70, f"Total templates {len(TEMPLATES)} < 70"

    NAMED_14 = [
        PRESS_CONTEXT_POST_WIN_BLOWOUT, PRESS_CONTEXT_POST_WIN_NARROW,
        PRESS_CONTEXT_POST_WIN_VS_RIVAL, PRESS_CONTEXT_POST_LOSS_BLOWOUT,
        PRESS_CONTEXT_POST_LOSS_CLOSE, PRESS_CONTEXT_POST_LOSS_UPSET,
        PRESS_CONTEXT_POST_STARTER_INJURY, PRESS_CONTEXT_MID_SEASON_GRIND,
        PRESS_CONTEXT_PRE_DIVISION_GAME, PRESS_CONTEXT_POST_INJURY_CRITICAL,
        PRESS_CONTEXT_PRE_PLAYOFF_GAME, PRESS_CONTEXT_POST_CLINCHING,
        PRESS_CONTEXT_POST_ELIMINATED, PRESS_CONTEXT_LINEUP_CONTROVERSY,
    ]
    from collections import Counter
    counts = Counter(t['context'] for t in TEMPLATES)
    for ctx in NAMED_14:
        n = counts.get(ctx, 0)
        assert n >= 5, f"Context '{ctx}' has only {n} templates (floor is 5)"


# ---------------------------------------------------------------------------
# Check 8 — All 14 contexts present in template pool
# ---------------------------------------------------------------------------

def check_all_14_contexts_present():
    """Check 8: each PRESS_CONTEXT_* constant has ≥1 template in TEMPLATES."""
    from src.utils.press_templates import TEMPLATES
    from src.utils.constants import (
        PRESS_CONTEXT_POST_WIN_BLOWOUT, PRESS_CONTEXT_POST_WIN_NARROW,
        PRESS_CONTEXT_POST_WIN_VS_RIVAL, PRESS_CONTEXT_POST_LOSS_BLOWOUT,
        PRESS_CONTEXT_POST_LOSS_CLOSE, PRESS_CONTEXT_POST_LOSS_UPSET,
        PRESS_CONTEXT_POST_STARTER_INJURY, PRESS_CONTEXT_MID_SEASON_GRIND,
        PRESS_CONTEXT_PRE_DIVISION_GAME, PRESS_CONTEXT_POST_INJURY_CRITICAL,
        PRESS_CONTEXT_PRE_PLAYOFF_GAME, PRESS_CONTEXT_POST_CLINCHING,
        PRESS_CONTEXT_POST_ELIMINATED, PRESS_CONTEXT_LINEUP_CONTROVERSY,
    )
    ctx_set = {t['context'] for t in TEMPLATES}
    for ctx in [
        PRESS_CONTEXT_POST_WIN_BLOWOUT, PRESS_CONTEXT_POST_WIN_NARROW,
        PRESS_CONTEXT_POST_WIN_VS_RIVAL, PRESS_CONTEXT_POST_LOSS_BLOWOUT,
        PRESS_CONTEXT_POST_LOSS_CLOSE, PRESS_CONTEXT_POST_LOSS_UPSET,
        PRESS_CONTEXT_POST_STARTER_INJURY, PRESS_CONTEXT_MID_SEASON_GRIND,
        PRESS_CONTEXT_PRE_DIVISION_GAME, PRESS_CONTEXT_POST_INJURY_CRITICAL,
        PRESS_CONTEXT_PRE_PLAYOFF_GAME, PRESS_CONTEXT_POST_CLINCHING,
        PRESS_CONTEXT_POST_ELIMINATED, PRESS_CONTEXT_LINEUP_CONTROVERSY,
    ]:
        assert ctx in ctx_set, f"Context '{ctx}' has no templates in TEMPLATES"


# ---------------------------------------------------------------------------
# Check 9 — LRU no-repeat in 3
# ---------------------------------------------------------------------------

def check_anti_repetition_lru_no_repeat_in_3(save_path):
    """Check 9: selecting 4 templates for same coach+context doesn't repeat in first 3."""
    from src.db.connection import ensure_press_tables
    from src.db import queries as q
    from src.transactions.press_conference import select_template_for_context

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        # Use post_loss_close (7 templates): after excluding 3, pool=4 >= PRESS_MIN_POOL_FALLBACK(4)
        # so random.choice fires and the result should NOT be in recent_ids.
        context = 'post_loss_close'
        coach_id = 32  # player coach from save

        # Simulate 3 resolved press events by writing template_ids directly
        # to press_event table
        inserted_ids = []
        for week in range(1, 4):
            tmpl = select_template_for_context(conn, context, coach_id)
            with conn:
                cursor = conn.execute("""
                    INSERT INTO press_event
                    (season_year, week_number, team_id, coach_id, context_type,
                     question_template_id, template_id, created_at)
                    VALUES (9999, ?, 17, ?, ?, ?, ?, datetime('now'))
                """, (week, coach_id, context, tmpl['id'], tmpl['id']))
            inserted_ids.append(tmpl['id'])

        # 4th selection should not be any of the last 3
        fourth = select_template_for_context(conn, context, coach_id)
        recent = q.get_recent_template_ids_for_coach_context(conn, coach_id, context, limit=3)
        assert fourth['id'] not in recent, (
            f"4th selection '{fourth['id']}' is in recent 3: {recent}"
        )
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 10 — LRU pool fallback
# ---------------------------------------------------------------------------

def check_anti_repetition_pool_fallback(save_path):
    """Check 10: when pool has only 3 templates, 4th pick falls back to LRU."""
    from src.db.connection import ensure_press_tables
    from src.utils.press_templates import TEMPLATES
    from src.transactions.press_conference import select_template_for_context
    from src.db import queries as q

    # Use a context with exactly 3 templates in the actual pool
    # post_starter_injury has exactly 5 — use a filtered mock by checking which context
    # has the smallest pool >= 3
    from collections import Counter
    counts = Counter(t['context'] for t in TEMPLATES)
    # We'll use 'post_starter_injury' (5 templates) but only pre-seed 4 recent ones
    # (leaving 1 in pool), which should trigger LRU. Actually let's just test with
    # a context that has >=4 templates and pre-seed PRESS_LRU_EXCLUDE_COUNT=3 to show fallback.
    from src.utils.constants import PRESS_LRU_EXCLUDE_COUNT, PRESS_MIN_POOL_FALLBACK

    context = 'post_starter_injury'  # 5 templates
    all_tmpl_ids = [t['id'] for t in TEMPLATES if t['context'] == context]
    # Pool after 3 LRU exclusions = 5-3 = 2, which is < PRESS_MIN_POOL_FALLBACK (4)
    # So LRU fallback should fire

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        coach_id = 32
        # Pre-seed 3 recent resolved events with the FIRST 3 template IDs
        for i, tid in enumerate(all_tmpl_ids[:3]):
            with conn:
                conn.execute("""
                    INSERT INTO press_event
                    (season_year, week_number, team_id, coach_id, context_type,
                     question_template_id, template_id, created_at)
                    VALUES (8888, ?, 17, ?, ?, ?, ?, datetime('now'))
                """, (i + 1, coach_id, context, tid, tid))

        # With 5 total and 3 excluded, pool=2 < PRESS_MIN_POOL_FALLBACK=4 → LRU fallback
        # The LRU is the oldest: all_tmpl_ids[0] (seeded first, so it's last in DESC ORDER)
        recent = q.get_recent_template_ids_for_coach_context(conn, coach_id, context, limit=3)
        assert len(recent) == 3, f"Expected 3 recent IDs, got {len(recent)}"

        # The LRU should be all_tmpl_ids[0] (oldest inserted = last in recent_ids list)
        lru_expected = recent[-1]
        assert lru_expected == all_tmpl_ids[0], \
            f"LRU expected {all_tmpl_ids[0]}, got {lru_expected}"

        # Now call select — with pool=2 < fallback=4 it should return the LRU (recent[-1])
        result = select_template_for_context(conn, context, coach_id)
        assert result['id'] == lru_expected, (
            f"Expected LRU fallback template {lru_expected}, got {result['id']}"
        )
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 11 — Context detection: blowout win
# ---------------------------------------------------------------------------

def check_context_detection_split_works(save_path):
    """Check 11: detect_context returns post_win_blowout for margin>=20 win."""
    from src.transactions.press_conference import detect_context
    from src.db.connection import get_connection, ensure_press_tables

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        # Find any completed game where team 17 (CHI) won by 20+
        row = conn.execute("""
            SELECT s.year, w.week_number
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE g.home_team_id = 17 AND g.home_score - g.away_score >= 20
              AND g.is_complete = 1
            UNION ALL
            SELECT s.year, w.week_number
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE g.away_team_id = 17 AND g.away_score - g.home_score >= 20
              AND g.is_complete = 1
            LIMIT 1
        """).fetchone()

        if not row:
            # Synthetically create a game result by updating an existing game
            # Find any completed game involving CHI
            game = conn.execute("""
                SELECT g.id, g.home_team_id, g.away_team_id, s.year, w.week_number
                FROM game g
                JOIN week w ON g.week_id = w.id
                JOIN season s ON w.season_id = s.id
                WHERE (g.home_team_id = 17 OR g.away_team_id = 17) AND g.is_complete = 1
                LIMIT 1
            """).fetchone()
            assert game, "No completed game found for CHI in save"
            if game['home_team_id'] == 17:
                with conn:
                    conn.execute("UPDATE game SET home_score = 35, away_score = 10 WHERE id = ?",
                                 (game['id'],))
            else:
                with conn:
                    conn.execute("UPDATE game SET away_score = 35, home_score = 10 WHERE id = ?",
                                 (game['id'],))
            season_year, week_number = game['year'], game['week_number']
        else:
            season_year, week_number = row['year'], row['week_number']

        ctx = detect_context(conn, 17, season_year, week_number)
        assert ctx == 'post_win_blowout', \
            f"Expected 'post_win_blowout' for 25-point win, got '{ctx}'"
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 12 — Context detection: rival win
# ---------------------------------------------------------------------------

def check_context_detection_rival_works(save_path):
    """Check 12: detect_context returns post_win_vs_rival for division win with margin <=16."""
    from src.transactions.press_conference import detect_context
    from src.db.connection import ensure_press_tables

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        # Find any completed game where CHI played a NFC North opponent
        # CHI division: NFC North (id 17=CHI, 18=DET, 19=GB, 20=MIN)
        division_opp_ids = [18, 19, 20]
        game = conn.execute("""
            SELECT g.id, g.home_team_id, g.away_team_id, s.year, w.week_number
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE g.is_complete = 1 AND (
                (g.home_team_id = 17 AND g.away_team_id IN (18, 19, 20))
                OR
                (g.away_team_id = 17 AND g.home_team_id IN (18, 19, 20))
            )
            LIMIT 1
        """).fetchone()

        assert game, "No division game found for CHI in save"

        # Make CHI win by exactly 10 (non-blowout)
        if game['home_team_id'] == 17:
            with conn:
                conn.execute("UPDATE game SET home_score = 24, away_score = 14 WHERE id = ?",
                             (game['id'],))
        else:
            with conn:
                conn.execute("UPDATE game SET away_score = 24, home_score = 14 WHERE id = ?",
                             (game['id'],))

        ctx = detect_context(conn, 17, game['year'], game['week_number'])
        assert ctx == 'post_win_vs_rival', \
            f"Expected 'post_win_vs_rival' for division win, got '{ctx}'"
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 13 — Context detection: starter injury
# ---------------------------------------------------------------------------

def check_starter_injury_context_works(save_path):
    """Check 13: detect_context returns post_starter_injury when depth chart shows
    a promoted player with injured starter (injury_weeks_remaining >= 2)."""
    from src.transactions.press_conference import detect_context
    from src.db.connection import ensure_press_tables

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        # Find a completed non-division game for CHI (to avoid rival context taking priority)
        game = conn.execute("""
            SELECT s.year, w.week_number
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            JOIN team home ON g.home_team_id = home.id
            JOIN division home_div ON home.division_id = home_div.id
            JOIN team away ON g.away_team_id = away.id
            JOIN division away_div ON away.division_id = away_div.id
            WHERE g.is_complete = 1
              AND (g.home_team_id = 17 OR g.away_team_id = 17)
              AND home_div.name != away_div.name
            LIMIT 1
        """).fetchone()
        if not game:
            # Fall back to any completed game
            game = conn.execute("""
                SELECT s.year, w.week_number
                FROM game g
                JOIN week w ON g.week_id = w.id
                JOIN season s ON w.season_id = s.id
                WHERE (g.home_team_id = 17 OR g.away_team_id = 17) AND g.is_complete = 1
                LIMIT 1
            """).fetchone()
        assert game, "No completed game for CHI"
        season_year = game['year']

        # Find a CHI depth chart slot_order=1 player for the relevant season
        dc_row = conn.execute("""
            SELECT dc.id, dc.player_id, dc.season_year
            FROM depth_chart dc
            WHERE dc.team_id = 17 AND dc.slot_order = 1
            ORDER BY ABS(dc.season_year - ?) ASC
            LIMIT 1
        """, (season_year,)).fetchone()
        assert dc_row, "No slot_order=1 depth chart entry for CHI"

        # Get a backup player (different from current starter)
        backup = conn.execute("""
            SELECT id FROM player WHERE team_id = 17 AND id != ? LIMIT 1
        """, (dc_row['player_id'],)).fetchone()
        assert backup, "No backup player found for CHI"

        # Mark the original starter as injured (injury_weeks_remaining >= 2)
        original_starter_id = dc_row['player_id']
        with conn:
            conn.execute("""
                UPDATE player SET injury_status = 'Out', injury_weeks_remaining = 4
                WHERE id = ?
            """, (original_starter_id,))

        # Set depth chart: backup is now starter, replaced_player_id = original (injured)
        with conn:
            conn.execute("""
                UPDATE depth_chart
                SET player_id = ?, replaced_player_id = ?
                WHERE id = ?
            """, (backup['id'], original_starter_id, dc_row['id']))

        # Use the depth_chart's season_year for detect_context
        dc_season = dc_row['season_year']
        ctx = detect_context(conn, 17, dc_season, game['week_number'])
        assert ctx == 'post_starter_injury', \
            f"Expected 'post_starter_injury', got '{ctx}'"
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 14 — template_id persists to press_event row
# ---------------------------------------------------------------------------

def check_template_id_persists_to_press_event(save_path):
    """Check 14: headless press conference resolves and writes non-null template_id."""
    from src.transactions.press_conference import generate_weekly_press_event
    from src.db.connection import ensure_press_tables

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        ensure_press_tables(conn)

        # Find a season/week with a completed game for CHI
        game = conn.execute("""
            SELECT s.year, w.week_number
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE (g.home_team_id = 17 OR g.away_team_id = 17)
              AND g.is_complete = 1
              AND NOT EXISTS (
                SELECT 1 FROM press_event pe
                WHERE pe.season_year = s.year AND pe.week_number = w.week_number
                  AND pe.team_id = 17
              )
            ORDER BY s.year DESC, w.week_number DESC
            LIMIT 1
        """).fetchone()
        assert game, "No suitable game found (all weeks already have press events)"

        result = generate_weekly_press_event(
            conn, game['year'], game['week_number'], 17, 32, headless=True
        )
        assert result.get('resolved'), "Press event was not resolved"

        # Verify template_id was written
        pe_row = conn.execute(
            "SELECT template_id FROM press_event WHERE id = ?",
            (result['press_event_id'],)
        ).fetchone()
        assert pe_row and pe_row['template_id'] is not None, \
            f"template_id is NULL on press_event row {result['press_event_id']}"
        conn.close()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Check 15 — Tier 2 templates untouched
# ---------------------------------------------------------------------------

def check_phase4_tier2_templates_untouched():
    """Check 15: tier2_templates.py has not been expanded by P9 (still 27 entries)."""
    with open('src/utils/tier2_templates.py') as f:
        t2_src = f.read()
    count = t2_src.count("'id':") + t2_src.count('"id":')
    assert count == 27, (
        f"tier2_templates.py has {count} id entries; expected 27 (P4+P5 baseline). "
        "Tier 2 templates must not be expanded in P9."
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _safely_run(fn):
    try:
        fn()
        return True
    except Exception as e:
        print(f"    ERROR: {e}", flush=True)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/verify/verify_phase5_p9.py <save_path>", flush=True)
        sys.exit(1)
    save_path = sys.argv[1]

    checks = [
        ('Guard 1  scope_discipline',      lambda: check_scope_discipline()),
        ('Guard 2  phase4_regression',     lambda: check_phase4_regression(save_path)),
        ('Guard 3  layer_boundaries',      lambda: check_layer_boundaries()),
        ('Guard 4  prior_p5_artifacts',    lambda: check_prior_phase5_artifacts_intact(save_path)),
        ('Check 5  schema_template_id',    lambda: check_schema_template_id_present(save_path)),
        ('Check 6  migration_idempotent',  lambda: check_migration_idempotent(save_path)),
        ('Check 7  template_count_min',    lambda: check_template_count_meets_minimum()),
        ('Check 8  all_14_contexts',       lambda: check_all_14_contexts_present()),
        ('Check 9  lru_no_repeat_in_3',    lambda: check_anti_repetition_lru_no_repeat_in_3(save_path)),
        ('Check 10 lru_pool_fallback',     lambda: check_anti_repetition_pool_fallback(save_path)),
        ('Check 11 detection_blowout',     lambda: check_context_detection_split_works(save_path)),
        ('Check 12 detection_rival',       lambda: check_context_detection_rival_works(save_path)),
        ('Check 13 detection_injury',      lambda: check_starter_injury_context_works(save_path)),
        ('Check 14 template_id_write',     lambda: check_template_id_persists_to_press_event(save_path)),
        ('Check 15 tier2_untouched',       lambda: check_phase4_tier2_templates_untouched()),
    ]
    assert len(checks) == 15

    passed = 0
    for name, fn in checks:
        ok = _safely_run(fn)
        status = '✅' if ok else '❌'
        print(f"  {status} {name}", flush=True)
        if ok:
            passed += 1

    print(flush=True)
    total = len(checks)
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})", flush=True)
        sys.exit(0)
    else:
        print(f"❌ {total - passed}/{total} CHECKS FAILED", flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
