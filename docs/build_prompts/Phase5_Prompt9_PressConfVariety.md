# Phase 5 Build Prompt #9 — Press Conference Variety Expansion

**Model**: Sonnet 4.6
**Planning mode**: Yes — multi-file, schema-touching, large content-writing component (~70-84 templates).

**Verification minimum**: ≥13 named checks including the 4 mandatory guards. **No failures may be declared optional, future enhancement, or skipped.**

**Mandatory exit criterion**: `python tests/verify/verify_phase5_p9.py <save>` MUST print `✅ ALL CHECKS PASSED (N/N)` (N ≥ 13) and exit 0. **You must paste the verbatim final pass line in your completion report.** Without that line, the prompt is not complete.

**Verification-script reliability requirements** (NEW — addresses three bugs surfaced in P7/P8):
1. **Guard 4 is a flat artifact check, NOT a chained subprocess run.** Do NOT spawn `verify_phase5_pN.py` as subprocesses. Instead, spot-check that the artifacts each prior prompt was supposed to ship are still present. See Task 7 Section A for the exact pattern.
2. **Every subprocess call in the verify script must specify `timeout=` explicitly** — default 60s for fast commands, 180s for stress harness. If a subprocess hangs, the check fails fast.
3. **Column existence checks must use safe iteration**, not index access. Pattern: `cols = [c[1] for c in conn.execute('PRAGMA table_info(table_name)').fetchall()]; assert 'col_name' in cols`. Never `result[0]` on a query that might return empty.

---

## Context

Phase 5 Prompts #1–#8 are complete. This prompt addresses the playthrough finding that **press conferences feel repetitive after 10+ weeks**. Phase 4 shipped 30 Tier 1 templates across 8 contexts; by week 10 the user has cycled through every template 2-3 times in the most common contexts (post-win, post-loss, mid-season-grind). The problem is structural: small pool + no anti-repetition + coarse contexts.

This prompt adds three things:

1. **Anti-repetition guard** — track last 3 templates used per coach per context; exclude them from the next selection (N=3 LRU). State persisted in `press_event.template_id` column.
2. **Context refinement** — 8 contexts → 14 contexts. Split `post_win` into 3 sub-contexts (blowout, narrow, vs_rival); split `post_loss` into 3 (blowout, close, upset); add `post_starter_injury`.
3. **Template pool expansion** — ~70-84 Tier 1 templates total (up from 30), with 5-7 templates per context floor.

Tier 2 templates stay at 24 (fire rarely; no current staleness signal).

**Read first**:
1. `CLAUDE.md` — project conventions.
2. `docs/Phase5_DesignDecisions.md` §8 (entire section — Press Conference Variety Expansion). This is the contract.
3. `src/transactions/press_conference.py` (Phase 4) — locate `detect_context()` and the template selection function. These are the extension points.
4. `src/utils/press_templates.py` (Phase 4) — existing 30 templates across 8 contexts. New templates merge into the same module.
5. `src/db/schema.sql` — find `press_event` table. Confirm column shape before adding `template_id`.
6. `src/db/connection.py` — locate `ensure_press_tables()` for migration extension.
7. `src/utils/constants.py` — existing press constants. New constants extend this namespace.

## Goal

After this prompt:
- Within any context, the user does not see the same template twice in three consecutive press conferences.
- Post-win and post-loss contexts are split into 3 sub-contexts each (blowout/narrow/vs_rival, blowout/close/upset) so the dramatic register matches the moment.
- A new `post_starter_injury` context fires when a key starter went down that week.
- The template pool is large enough that variety holds across a full season.

## Tasks

### Task 1 — Schema additions

Add `template_id` to `press_event`:

```sql
ALTER TABLE press_event ADD COLUMN template_id TEXT;
```

Nullable. Existing rows backfill with NULL (those are pre-P9 events; the LRU guard treats NULL as "no record" which is correct for legacy data — they don't constrain future selections).

### Task 2 — Migration helper

Extend `ensure_press_tables(conn)` (or whichever existing helper covers press_event) to add the column idempotently. Do NOT create a new migration helper.

### Task 3 — Constants

Add to `src/utils/constants.py` in a new "Phase 5 — Press Conference Variety" section:

```python
# Phase 5 P9 — Anti-repetition LRU guard
PRESS_LRU_EXCLUDE_COUNT = 3   # exclude last N templates used per coach per context
PRESS_MIN_POOL_FALLBACK = 4   # if pool drops below this after LRU exclusion,
                               # fall back to least-recently-used (not random)

# Phase 5 P9 — Context refinement (14 contexts replace 8)
# Existing 6 are kept; 8 new ones added (6 replace post_win/post_loss splits,
# 1 new post_starter_injury, plus post_starter_injury is genuinely new).
PRESS_CONTEXT_POST_WIN_BLOWOUT = 'post_win_blowout'      # margin ≥ 17
PRESS_CONTEXT_POST_WIN_NARROW = 'post_win_narrow'        # margin ≤ 7
PRESS_CONTEXT_POST_WIN_VS_RIVAL = 'post_win_vs_rival'    # division opponent

PRESS_CONTEXT_POST_LOSS_BLOWOUT = 'post_loss_blowout'    # margin ≥ 17
PRESS_CONTEXT_POST_LOSS_CLOSE = 'post_loss_close'        # margin ≤ 7
PRESS_CONTEXT_POST_LOSS_UPSET = 'post_loss_upset'        # underdog won against you

PRESS_CONTEXT_POST_STARTER_INJURY = 'post_starter_injury'  # key starter went down

# Existing contexts (kept verbatim from Phase 4 — confirm against existing code):
# - mid_season_grind, pre_division_game, post_injury_critical,
#   pre_playoff_game, post_clinching, post_eliminated
# (post_win and post_loss DEPRECATED — replaced by the 6 sub-contexts above;
#  remove these context strings from any active code paths)

PRESS_BLOWOUT_MARGIN_THRESHOLD = 17  # design doc convention
PRESS_NARROW_MARGIN_THRESHOLD = 7
```

### Task 4 — Context detection refinement

In `src/transactions/press_conference.py`, find `detect_context()` (or equivalent). Modify the post-game branch:

```python
def detect_context(game_result, team_state, season_state):
    # ... existing pre-game / mid-season logic stays ...

    if game_result.is_post_game:
        margin = abs(game_result.user_score - game_result.opponent_score)
        is_rival = game_result.opponent_division == team_state.division
        is_user_win = game_result.user_score > game_result.opponent_score

        # Check for new starter-injury context first (highest priority)
        # — only if a key starter actually went down THIS week
        if team_state.had_critical_starter_injury_this_week:
            return PRESS_CONTEXT_POST_STARTER_INJURY

        if is_user_win:
            if margin >= PRESS_BLOWOUT_MARGIN_THRESHOLD:
                return PRESS_CONTEXT_POST_WIN_BLOWOUT
            if is_rival:
                return PRESS_CONTEXT_POST_WIN_VS_RIVAL
            if margin <= PRESS_NARROW_MARGIN_THRESHOLD:
                return PRESS_CONTEXT_POST_WIN_NARROW
            # Default fallback for non-blowout / non-rival / non-narrow wins
            return PRESS_CONTEXT_POST_WIN_NARROW  # treat all non-blowout, non-rival as narrow
        else:
            if margin >= PRESS_BLOWOUT_MARGIN_THRESHOLD:
                return PRESS_CONTEXT_POST_LOSS_BLOWOUT
            if game_result.user_team_was_favorite_by_2plus:
                return PRESS_CONTEXT_POST_LOSS_UPSET
            return PRESS_CONTEXT_POST_LOSS_CLOSE

    # ... rest of contexts ...
```

The exact predicates (`had_critical_starter_injury_this_week`, `user_team_was_favorite_by_2plus`) may not exist in the current data model. Read the existing context detection code and adapt — use whatever signals are already available. If a needed signal isn't present, add a minimal helper that derives it from existing tables.

**Important**: do not remove the OLD `post_win` and `post_loss` context strings if they appear elsewhere in the codebase yet — search for them. If they're only used in `detect_context()` and the template selector, then deprecating in place is safe. If they appear elsewhere, leave a shim that maps the old strings to the closest new sub-context.

### Task 5 — Template library expansion

Extend `src/utils/press_templates.py`. **Target: ≥70 Tier 1 templates total, with ≥5 per context across 14 contexts. Design goal is ~84 templates (6 per context).**

Templates follow the existing Phase 4 shape. Distribution:

| Context | Min count | Notes |
|---|---|---|
| post_win_blowout | 6 | celebratory, magnanimous, "still got better to do" |
| post_win_narrow | 6 | grinding-it-out narrative, defensive stop heroes |
| post_win_vs_rival | 6 | division rivalry tone |
| post_loss_blowout | 6 | accountability, "we got our asses kicked" |
| post_loss_close | 6 | bitter, "inches away" |
| post_loss_upset | 6 | shock, accountability for being favored and losing |
| post_starter_injury | 5 | next-man-up + worry for player |
| mid_season_grind | 6 | bye week, dog days, week 10-12 fatigue |
| pre_division_game | 5 | rivalry preview |
| post_injury_critical | 5 | season-altering injury |
| pre_playoff_game | 5 | playoff intensity |
| post_clinching | 5 | clinched playoff spot |
| post_eliminated | 5 | eliminated from playoffs |
| (1 more context if needed) | | (the 14th — confirm by counting above) |

Counts may flex ±1, but **total ≥ 70 and each context floor of 5 is non-negotiable**.

Tone variation within each context: at least one template should be flat/quiet (one-liner), at least one dramatic (multi-sentence with emotion), and at least one neutral. Variety across templates within a context is what the anti-repetition guard relies on.

Template shape (mirror existing Phase 4 entries):

```python
{
    'id': 'post_win_blowout_dominant_phase',  # unique within press_templates.py
    'context': PRESS_CONTEXT_POST_WIN_BLOWOUT,
    'template': "[Beat reporter]: Coach, that was your most complete game of the year. "
                "What does this tell us about where the {USER_TEAM_NAME} are headed?",
    'response_options': [
        {'id': 'modest', 'text': "...modest response...", 'effect': {'sentiment': +1}},
        {'id': 'confident', 'text': "...confident response...", 'effect': {'sentiment': +2}},
        {'id': 'deflect', 'text': "...deflect response...", 'effect': {'sentiment': 0}},
    ],
}
```

Read 3-5 existing Phase 4 templates to confirm exact field names and `response_options` shape before writing new ones.

### Task 6 — Anti-repetition guard in template selection

In `src/transactions/press_conference.py`, find the template selection function (likely `select_template_for_context()` or similar). Add LRU exclusion:

```python
def select_template_for_context(conn, context, coach_id):
    """Phase 5 P9: LRU-anti-repetition guard.

    1. Get all templates for this context.
    2. Query press_event for the last PRESS_LRU_EXCLUDE_COUNT template_ids
       used by this coach in this context (ordered by id DESC).
    3. Exclude those template_ids from the candidate pool.
    4. If pool drops below PRESS_MIN_POOL_FALLBACK, fall back to
       least-recently-used (pick the template_id with the OLDEST press_event
       timestamp/id from the originally-excluded set).
    5. Random pick from the final pool.
    6. Caller must write the chosen template_id back to press_event when the
       press conference resolves.
    """
    all_templates = [t for t in PRESS_TEMPLATES if t['context'] == context]
    if not all_templates:
        return None

    # Last N template_ids used by this coach in this context
    recent_ids = queries.get_recent_template_ids_for_coach_context(
        conn, coach_id, context, limit=PRESS_LRU_EXCLUDE_COUNT
    )

    candidate_pool = [t for t in all_templates if t['id'] not in recent_ids]

    if len(candidate_pool) >= PRESS_MIN_POOL_FALLBACK:
        return random.choice(candidate_pool)

    # Pool too thin — LRU fallback: among the excluded, pick the one used
    # LONGEST ago. recent_ids is ordered most-recent-first, so the LAST item
    # is the LRU candidate.
    if recent_ids:
        lru_id = recent_ids[-1]
        for t in all_templates:
            if t['id'] == lru_id:
                return t

    # Truly degenerate case (only 1-2 templates total in this context)
    return random.choice(all_templates)
```

After the user resolves the press conference, the caller writes `template_id` to the `press_event` row:

```python
queries.write_press_event_template_id(conn, press_event_id, chosen_template['id'])
```

### Task 7 — Verification script

Create `tests/verify/verify_phase5_p9.py` with **at least 13 named checks**.

**Section A — Mandatory guards (4 checks; FIRST in main()):**

```python
def check_scope_discipline():
    """MANDATORY GUARD #1: No P10+ work shipped early.
    - No HOF offseason phase logic added (Prompt #10)
    - No coaching carousel summary added beyond Phase 4's existing carousel
    - No season_recap.py module
    - No year-over-year recap auto-print in run_season.py
    P3-P8 surfaces all intact (CLI flags + key files present).

    IMPLEMENTATION NOTE: Use safe iteration for column / file existence checks.
    DO NOT use result[0] on PRAGMA or directory listings — use list comprehension
    over the full result set.
    """
    # P3-P8 CLI flags present in run_season.py
    with open('run_season.py') as f:
        run_src = f.read()
    for flag in ['--depth-chart', '--set-starter', '--swap-depth', '--reset-depth',
                  '--player-value', '--estimate-trade', '--shop-player']:
        assert flag in run_src, f"prior prompt flag missing: {flag}"
    # P2/P7/P8 CLI entry points exist
    for entry in ['view_stats.py', 'view_sentiment.py']:
        assert os.path.exists(entry), f"prior entry point missing: {entry}"
    # No P10 work
    assert not os.path.exists('src/league/season_recap.py'), "P10 season_recap.py shipped early"


def check_phase4_regression(save_path):
    """MANDATORY GUARD #2: Phase 4 stress harness 12/12.
    Substring: '12 passed' AND '0 failed'. Use tempfile copy. timeout=300."""
    import tempfile, shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(save_path, tmp_path)
        result = subprocess.run(
            ['python', 'run_stress_test.py', tmp_path, '--seasons', '1', '--invariants'],
            capture_output=True, text=True, timeout=300,
        )
        assert result.returncode == 0, (
            f"Stress harness exit {result.returncode}\n"
            f"stderr tail: {result.stderr[-500:]}"
        )
        assert '12 passed' in result.stdout and '0 failed' in result.stdout, (
            f"Expected '12 passed' AND '0 failed'.\n"
            f"Stdout tail: {result.stdout[-500:]}"
        )
    finally:
        os.unlink(tmp_path)


def check_layer_boundaries():
    """MANDATORY GUARD #3: New code in press_conference.py + press_templates.py
    contains no inline SQL (where applicable).
    - press_templates.py is pure data: zero SQL allowed.
    - press_conference.py extensions: line-number-scoped — find the P9 section
      and only flag SQL there. Pre-existing Phase 4 SQL is grandfathered.
    """


def check_prior_phase5_artifacts_intact(save_path):
    """MANDATORY GUARD #4 (RESTRUCTURED — DO NOT NEST SUBPROCESSES).

    Replaces the chain-of-subprocess pattern from P3-P8. That pattern caused
    exponential nesting and 1h+ hangs. This flat check spot-verifies each
    prior prompt's key artifacts directly:

    - P1: 5 stats tables exist (player_week_stats, player_season_running,
      team_week_stats, team_season_running, weekly_award)
    - P2: view_stats.py exists, has --leaderboard / --player / --team / --week / --stars flags
    - P3: depth_chart table exists; run_season.py has --depth-chart / --set-starter
    - P4: stars_selection.py exists; star_templates.py exists with ≥40 templates
    - P5: depth_chart.py has _maybe_queue_lineup_controversy; tier2_triggers.py
      has detect_rising_star_streak
    - P6: trades.py has estimate_trade / get_player_value / shop_player / propose_counter
    - P7: pitch_meeting_templates.py exists with ≥20 templates;
      fa_interest table has outcome_narrative + reason_code columns
    - P8: sentiment_explainer.py exists; view_sentiment.py exists;
      owner_sentiment has reason_code column

    All checks are filesystem reads or table-info queries. None spawn
    verify_phase5_pN.py as a subprocess. Total runtime should be <1 second.

    Implementation:

        import sqlite3
        conn = sqlite3.connect(save_path)

        # P1
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        for t in ('player_week_stats', 'player_season_running', 'team_week_stats',
                  'team_season_running', 'weekly_award'):
            assert t in tables, f"P1 table missing: {t}"

        # P2
        assert os.path.exists('view_stats.py'), 'P2 view_stats.py missing'
        with open('view_stats.py') as f:
            src = f.read()
        for flag in ('--leaderboard', '--player', '--team', '--week', '--stars'):
            assert flag in src, f"P2 flag missing: {flag}"

        # P3
        assert 'depth_chart' in tables, 'P3 depth_chart table missing'
        with open('run_season.py') as f:
            run_src = f.read()
        for flag in ('--depth-chart', '--set-starter'):
            assert flag in run_src, f"P3 flag missing: {flag}"

        # P4
        for p in ('src/league/stars_selection.py', 'src/utils/star_templates.py'):
            assert os.path.exists(p), f"P4 file missing: {p}"
        # Template count signal — count 'id': occurrences (single or double quote)
        with open('src/utils/star_templates.py') as f:
            star_src = f.read()
        id_count = star_src.count("'id':") + star_src.count('"id":')
        assert id_count >= 15, f"P4 star_templates has only {id_count} templates"

        # P5
        assert os.path.exists('src/transactions/depth_chart.py'), 'P5 depth_chart.py missing'
        with open('src/transactions/depth_chart.py') as f:
            dc_src = f.read()
        assert '_maybe_queue_lineup_controversy' in dc_src, \
            'P5 lineup controversy hook missing'
        assert os.path.exists('src/transactions/tier2_triggers.py')
        with open('src/transactions/tier2_triggers.py') as f:
            t2_src = f.read()
        assert 'detect_rising_star_streak' in t2_src, 'P5 streak detector missing'

        # P6
        with open('src/transactions/trades.py') as f:
            tr_src = f.read()
        for fn in ('def estimate_trade', 'def get_player_value', 'def shop_player', 'def propose_counter'):
            assert fn in tr_src, f"P6 function missing: {fn}"

        # P7
        assert os.path.exists('src/utils/pitch_meeting_templates.py'), 'P7 templates file missing'
        with open('src/utils/pitch_meeting_templates.py') as f:
            pmt_src = f.read()
        pmt_count = pmt_src.count("'signal_type':") + pmt_src.count('"signal_type":')
        assert pmt_count >= 20, f"P7 has only {pmt_count} pitch templates"
        fa_cols = [c[1] for c in conn.execute("PRAGMA table_info(fa_interest)").fetchall()]
        assert 'outcome_narrative' in fa_cols, 'P7 outcome_narrative column missing'
        assert 'reason_code' in fa_cols, 'P7 fa_interest.reason_code column missing'

        # P8
        for p in ('src/league/sentiment_explainer.py', 'view_sentiment.py'):
            assert os.path.exists(p), f"P8 file missing: {p}"
        os_cols = [c[1] for c in conn.execute("PRAGMA table_info(owner_sentiment)").fetchall()]
        assert 'reason_code' in os_cols, 'P8 owner_sentiment.reason_code column missing'

        conn.close()
        return True
    """
```

**Section B — Functional checks (≥9 more; total ≥13):**

5. **`check_schema_template_id_present`** — `press_event` table has `template_id TEXT` column. Use safe iteration: `cols = [c[1] for c in conn.execute("PRAGMA table_info(press_event)").fetchall()]; assert 'template_id' in cols`.

6. **`check_migration_idempotent`** — calling `ensure_press_tables(conn)` twice does not error.

7. **`check_template_count_meets_minimum`** — `PRESS_TEMPLATES` has ≥70 entries; each of the 14 named contexts has ≥5 templates. Group by context, assert per-context floor.

8. **`check_all_14_contexts_present`** — verify the 14 context strings (`PRESS_CONTEXT_POST_WIN_BLOWOUT`, etc.) each have at least 1 template. Catches typos in context references.

9. **`check_anti_repetition_lru_no_repeat_in_3`** — simulate selecting 4 templates from the same context for the same coach (writing each chosen template_id to press_event). Assert no template appears twice in the first 3 selections. Tests the LRU exclusion logic directly.

10. **`check_anti_repetition_pool_fallback`** — construct a context that has exactly 3 templates. Run 5 selections. Assert the LRU fallback fires (the 4th selection returns the LRU template, not random).

11. **`check_context_detection_split_works`** — synthesize a post-game state with margin=20 (blowout) and assert `detect_context()` returns `post_win_blowout` (not the old generic `post_win`).

12. **`check_context_detection_rival_works`** — synthesize a post-game state with margin=10 and is_rival=True. Assert returns `post_win_vs_rival`.

13. **`check_starter_injury_context_works`** — synthesize a post-game state with `had_critical_starter_injury_this_week=True`. Assert returns `post_starter_injury` even if margin would otherwise trigger blowout/narrow.

14. **`check_template_id_persists_to_press_event`** — call the press conference resolution flow with a fixture. Assert the resulting press_event row has a non-null `template_id` field.

15. **`check_phase4_tier2_templates_untouched`** — confirm Tier 2 templates (`src/utils/tier2_templates.py`) have NOT been expanded by this prompt. Count templates pre/post — count should match Phase 4 + P5 baseline. Per design doc §8.4, Tier 2 stays as-is.

main():
```python
def main():
    save_path = sys.argv[1]
    checks = [
        ('Guard 1', lambda: check_scope_discipline()),
        ('Guard 2', lambda: check_phase4_regression(save_path)),
        ('Guard 3', lambda: check_layer_boundaries()),
        ('Guard 4', lambda: check_prior_phase5_artifacts_intact(save_path)),
        ('Check 5', lambda: check_schema_template_id_present(save_path)),
        # ... etc
    ]
    assert len(checks) >= 13
    passed = sum(1 for name, fn in checks if _safely_run(fn))
    total = len(checks)
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"❌ {total - passed}/{total} CHECKS FAILED")
        sys.exit(1)
```

Use `print(..., flush=True)` after every check to avoid the Python stdout-buffering issue that hid output in P8's run.

### Task 8 — Update CLAUDE.md

After verification passes:

```markdown
- [x] Press conference variety expansion: 14 contexts (8 → 14 via post_win/post_loss splits + post_starter_injury); ~84 Tier 1 templates (5-7 per context floor); LRU anti-repetition guard (N=3) via `press_event.template_id`; context detection refined in `press_conference.py`; verify_phase5_p9.py with N checks
```

## Constraints — what NOT to change

- Do NOT expand Tier 2 templates. Out of scope per design doc §8.4. Guard 15 enforces this.
- Do NOT modify the old `post_win` / `post_loss` context strings if they appear elsewhere; deprecate in place with shim if needed.
- Do NOT modify Phase 4 press infrastructure structure (template loading, response resolution). Only ADD anti-repetition logic and new templates/contexts.
- Do NOT add the season transition / HOF / coaching carousel work that's Prompt #10.
- Do NOT add inline SQL in `press_templates.py` (pure data file). All SQL in `queries.py` or pre-existing press_conference.py code paths.
- **No verification check may be declared optional, future enhancement, or skipped.**
- **Verbatim-paste exit criterion**: completion report must include the actual final pass line.

## Test plan

```bash
# Use a save with multiple weeks of press_event history if possible
cp saves/phase5_p8_test.db saves/phase5_p9_test.db

# Run a few weeks to exercise press conferences with new variety
python run_season.py saves/phase5_p9_test.db --advance-week
python run_season.py saves/phase5_p9_test.db --advance-week

# Run verification
python tests/verify/verify_phase5_p9.py saves/phase5_p9_test.db
```

Expected: prints `✅ ALL CHECKS PASSED (15/15)` (or N/N where N ≥ 13), exits 0. **Paste that verbatim line in your completion report.**

## Reference

Design doc: `docs/Phase5_DesignDecisions.md` §8 (entire section).
Phase 4 press infrastructure: `src/transactions/press_conference.py`, `src/utils/press_templates.py`.
**Verbatim-paste exit criterion**: paste `✅ ALL CHECKS PASSED (N/N)` in completion report.
**Guard 4 is restructured as flat artifact check, NOT chained subprocess** — see Task 7 Section A. This is the most important structural change in this prompt vs. earlier patterns.
**Subprocess timeouts mandatory** — every `subprocess.run` call specifies `timeout=`.
**Safe column iteration** — never `result[0]` on PRAGMA results; use list comprehension.
