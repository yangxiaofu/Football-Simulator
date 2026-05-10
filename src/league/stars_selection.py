"""Stars of the Week selection algorithm (Phase 5 Prompt #4).

Runs after weekly stats aggregation each week. Selects up to 4 Stars:
  OFFENSE       — best offensive player league-wide (QB/RB/WR/TE)
  DEFENSE       — best defensive player league-wide (DL/LB/CB/S)
  SPECIAL_TEAMS — best ST player (K/P or any returner), skippable if threshold not met
  USER_TEAM_MVP — best player on the user's team (any position)

Idempotent: re-running for the same (season_year, week_number, is_playoff) overwrites
existing rows via INSERT OR REPLACE on the UNIQUE constraint.

No inline SQL — all DB access via src.db.queries.
"""

import sqlite3
from typing import Optional

from ..db.queries import (
    get_stars_candidates,
    get_league_state,
    get_team,
    upsert_weekly_award,
)
from ..utils.constants import (
    STARS_OFFENSE_POSITIONS,
    STARS_DEFENSE_POSITIONS,
    STARS_SPECIAL_TEAMS_POSITIONS,
    STARS_AWARD_OFFENSE,
    STARS_AWARD_DEFENSE,
    STARS_AWARD_SPECIAL_TEAMS,
    STARS_AWARD_USER_TEAM_MVP,
    STARS_WIN_BONUS,
    STARS_OPPONENT_STRENGTH_BONUS,
    STARS_CLUTCH_BONUS,
    STARS_KEY_PLAY_TIEBREAKER,
    STARS_BSV_QB_PASS_YARDS,
    STARS_BSV_QB_PASS_TD,
    STARS_BSV_QB_PASS_INT,
    STARS_BSV_QB_RUSH_YARDS,
    STARS_BSV_RB_RUSH_YARDS,
    STARS_BSV_RB_RUSH_TD,
    STARS_BSV_RB_REC_YARDS,
    STARS_BSV_RECEIVER_REC_YARDS,
    STARS_BSV_RECEIVER_REC_TD,
    STARS_BSV_RECEIVER_RECEPTIONS,
    STARS_BSV_DLLB_SACKS,
    STARS_BSV_DLLB_TACKLES,
    STARS_BSV_DLLB_FF,
    STARS_BSV_DB_TACKLES,
    STARS_BSV_DB_INT,
    STARS_BSV_DB_FF,
    STARS_BSV_K_FG_MADE,
    STARS_BSV_K_FG_50PLUS,
    STARS_BSV_K_XP_MADE,
    STARS_BSV_P_PUNT_YARDS,
    STARS_BSV_RET_RETURN_YARDS,
    STARS_BSV_RET_RETURN_TDS,
    STARS_ST_FG_LONG_THRESHOLD,
)
from ..utils.star_templates import (
    STAR_TEMPLATES_OFFENSE,
    STAR_TEMPLATES_DEFENSE,
    STAR_TEMPLATES_SPECIAL_TEAMS,
    STAR_TEMPLATES_USER_TEAM_MVP,
)


def select_stars_for_week(
    conn: sqlite3.Connection,
    season_year: int,
    week_number: int,
    is_playoff: bool,
) -> dict:
    """Select Stars of the Week and write to weekly_award.

    Returns a summary dict keyed by award type (lower-cased):
        {
            'offense':        candidate_dict or None,
            'defense':        candidate_dict or None,
            'special_teams':  candidate_dict or None,  # None if threshold not met
            'user_team_mvp':  candidate_dict or None,
        }

    Each candidate_dict contains all player_week_stats fields plus computed
    fields (player_name, position, team_abbr, won, score_diff, opponent_w_pct,
    key_play_count, return_yards, return_tds, score, narrative_blurb).
    """
    is_playoff_int = 1 if is_playoff else 0

    candidates = get_stars_candidates(conn, season_year, week_number, is_playoff_int)
    if not candidates:
        return {'offense': None, 'defense': None, 'special_teams': None, 'user_team_mvp': None}

    # Compute scores
    for c in candidates:
        c['score'] = _compute_score(c)

    # League stars
    offense = _pick_top(candidates, STARS_OFFENSE_POSITIONS)
    defense = _pick_top(candidates, STARS_DEFENSE_POSITIONS)

    # Special teams: K/P by their formula; any position with returns by return formula
    st_candidates = _build_st_candidates(candidates)
    if st_candidates and any(_st_meets_threshold(c) for c in st_candidates):
        # Re-score ST candidates by ST-specific formula so a WR with a return TD
        # beats a K who had a routine game
        for c in st_candidates:
            c['st_score'] = _st_score(c)
        special_teams = max(st_candidates, key=lambda c: c['st_score'])
    else:
        special_teams = None

    # User team MVP
    league = get_league_state(conn)
    user_team_id = league['user_team_id'] if league else None
    user_team_row = get_team(conn, user_team_id) if user_team_id else None
    user_team_name = (f"{user_team_row['city']} {user_team_row['nickname']}"
                      if user_team_row else 'your team')
    user_candidates = [c for c in candidates if c['team_id'] == user_team_id] if user_team_id else []
    user_team_mvp = max(user_candidates, key=lambda c: c['score']) if user_candidates else None
    if user_team_mvp is not None:
        user_team_mvp['user_team_name'] = user_team_name

    # Generate narratives and write to DB
    summary = {'offense': None, 'defense': None, 'special_teams': None, 'user_team_mvp': None}

    pairs = [
        (offense,       STARS_AWARD_OFFENSE,       STAR_TEMPLATES_OFFENSE,       'offense'),
        (defense,       STARS_AWARD_DEFENSE,        STAR_TEMPLATES_DEFENSE,       'defense'),
        (special_teams, STARS_AWARD_SPECIAL_TEAMS,  STAR_TEMPLATES_SPECIAL_TEAMS, 'special_teams'),
        (user_team_mvp, STARS_AWARD_USER_TEAM_MVP,  STAR_TEMPLATES_USER_TEAM_MVP, 'user_team_mvp'),
    ]

    for star, award_type, template_list, key in pairs:
        if star is None:
            continue
        blurb = _render_narrative(star, template_list)
        upsert_weekly_award(
            conn,
            season_year=season_year,
            week_number=week_number,
            is_playoff=is_playoff_int,
            award_type=award_type,
            player_id=star['player_id'],
            team_id=star['team_id'],
            score=star['score'],
            narrative_blurb=blurb,
        )
        # Snapshot the star dict with this award's blurb — avoids mutation when the
        # same player wins multiple categories (e.g., user-team WR wins league OFFENSE
        # and USER_TEAM_MVP; both categories need separate narrative blurbs).
        summary[key] = {**star, 'narrative_blurb': blurb}

    return summary


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _compute_score(c: dict) -> float:
    """Weighted score per design doc §4.2."""
    score = _base_stat_value(c)
    if c.get('won'):
        score += STARS_WIN_BONUS
    score += STARS_OPPONENT_STRENGTH_BONUS * c.get('opponent_w_pct', 0.0)
    # STARS_CLUTCH_BONUS × 0: deferred — quarter splits not tracked by engine
    score += STARS_KEY_PLAY_TIEBREAKER * c.get('key_play_count', 0)
    return score


def _base_stat_value(c: dict) -> float:
    """Position-aware base stat value from design doc §4.2.

    Uses actual player_week_stats column names (not build-prompt assumed names).
    Dropped terms:
      - TFL (not tracked in player_week_stats)
      - fumble_recoveries (not tracked)
      - def_tds (not tracked)
      - punts_inside_20 (not tracked)
    These are documented simplifications scoped for a future prompt.
    """
    pos = c.get('position', '')

    if pos == 'QB':
        return (STARS_BSV_QB_PASS_YARDS * c.get('pass_yards', 0)
                + STARS_BSV_QB_PASS_TD * c.get('pass_tds', 0)
                + STARS_BSV_QB_PASS_INT * c.get('interceptions_thrown', 0)
                + STARS_BSV_QB_RUSH_YARDS * c.get('rush_yards', 0))

    if pos == 'RB':
        return (STARS_BSV_RB_RUSH_YARDS * c.get('rush_yards', 0)
                + STARS_BSV_RB_RUSH_TD * c.get('rush_tds', 0)
                + STARS_BSV_RB_REC_YARDS * c.get('rec_yards', 0))

    if pos in ('WR', 'TE'):
        return (STARS_BSV_RECEIVER_REC_YARDS * c.get('rec_yards', 0)
                + STARS_BSV_RECEIVER_REC_TD * c.get('rec_tds', 0)
                + STARS_BSV_RECEIVER_RECEPTIONS * c.get('receptions', 0))

    if pos in ('DL', 'LB'):
        return (STARS_BSV_DLLB_SACKS * c.get('sacks', 0)
                + STARS_BSV_DLLB_TACKLES * c.get('tackles', 0)
                + STARS_BSV_DLLB_FF * c.get('forced_fumbles', 0))

    if pos in ('CB', 'S'):
        return (STARS_BSV_DB_TACKLES * c.get('tackles', 0)
                + STARS_BSV_DB_INT * c.get('interceptions', 0)
                + STARS_BSV_DB_FF * c.get('forced_fumbles', 0))

    if pos == 'K':
        return _k_score(c)

    if pos == 'P':
        return _p_score(c)

    # OL and any unrecognized position → 0 (no stats tracked)
    return 0.0


def _k_score(c: dict) -> float:
    base = (STARS_BSV_K_FG_MADE * c.get('fg_made', 0)
            + STARS_BSV_K_XP_MADE * c.get('xp_made', 0))
    if c.get('fg_long', 0) >= STARS_ST_FG_LONG_THRESHOLD:
        base += STARS_BSV_K_FG_50PLUS
    return base


def _p_score(c: dict) -> float:
    # NOTE: punts_inside_20 not tracked → dropped. Future prompt.
    return STARS_BSV_P_PUNT_YARDS * c.get('punt_yards', 0)


def _return_score(c: dict) -> float:
    return (STARS_BSV_RET_RETURN_YARDS * c.get('return_yards', 0)
            + STARS_BSV_RET_RETURN_TDS * c.get('return_tds', 0))


# ---------------------------------------------------------------------------
# ST-specific scoring and candidate building
# ---------------------------------------------------------------------------

def _st_score(c: dict) -> float:
    """ST-specific score used only when comparing ST candidates."""
    pos = c.get('position', '')
    if pos == 'K':
        base = _k_score(c)
    elif pos == 'P':
        base = _p_score(c)
    else:
        base = _return_score(c)

    # Apply standard context bonuses
    bonus = 0.0
    if c.get('won'):
        bonus += STARS_WIN_BONUS
    bonus += STARS_OPPONENT_STRENGTH_BONUS * c.get('opponent_w_pct', 0.0)
    bonus += STARS_KEY_PLAY_TIEBREAKER * c.get('key_play_count', 0)
    return base + bonus


def _build_st_candidates(candidates: list[dict]) -> list[dict]:
    """K/P players + any player with return yards (returners can be any position)."""
    result = []
    for c in candidates:
        pos = c.get('position', '')
        if pos in STARS_SPECIAL_TEAMS_POSITIONS:
            result.append(c)
        elif c.get('return_yards', 0) > 0 or c.get('return_tds', 0) > 0:
            result.append(c)
    return result


def _st_meets_threshold(c: dict) -> bool:
    """ST threshold gate per design doc §4.5 (simplified to available data)."""
    return (c.get('return_tds', 0) > 0
            or c.get('fg_long', 0) >= STARS_ST_FG_LONG_THRESHOLD)


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def _pick_top(candidates: list[dict], allowed_positions: tuple) -> Optional[dict]:
    eligible = [c for c in candidates if c.get('position', '') in allowed_positions]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c['score'])


# ---------------------------------------------------------------------------
# Narrative rendering
# ---------------------------------------------------------------------------

def _render_narrative(star: dict, template_list: list[dict]) -> str:
    """Pick first matching template and slot-fill it."""
    for t in template_list:
        try:
            if t['match'](star):
                return _format_template(t['template'], star)
        except (KeyError, TypeError):
            continue
    return f"{star.get('player_name', 'Unknown')} stood out for the {star.get('team_abbr', '')} this week."


def _format_template(template_str: str, star: dict) -> str:
    """Slot-fill {TOKEN} placeholders from star data."""
    tokens = {
        'NAME': star.get('player_name', ''),
        'OPP': star.get('opp_abbr', star.get('team_abbr', '')),
        'SCORE_DIFF': str(star.get('score_diff', 0)),
        'PASS_YARDS': str(star.get('pass_yards', 0)),
        'PASS_TDS': str(star.get('pass_tds', 0)),
        'CARRIES': str(star.get('carries', 0)),
        'RUSH_YARDS': str(star.get('rush_yards', 0)),
        'RUSH_TDS': str(star.get('rush_tds', 0)),
        'REC_YARDS': str(star.get('rec_yards', 0)),
        'REC_TDS': str(star.get('rec_tds', 0)),
        'RECEPTIONS': str(star.get('receptions', 0)),
        'TACKLES': str(star.get('tackles', 0)),
        'SACKS': str(star.get('sacks', 0)),
        'INTS': str(star.get('interceptions', 0)),
        'FG_MADE': str(star.get('fg_made', 0)),
        'FG_LONG': str(star.get('fg_long', 0)),
        'PUNT_YARDS': str(star.get('punt_yards', 0)),
        'RETURN_YARDS': str(star.get('return_yards', 0)),
        'RETURN_TDS': str(star.get('return_tds', 0)),
        'USER_TEAM_NAME': star.get('user_team_name', 'your team'),
    }

    class _SafeDict(dict):
        def __missing__(self, key):
            return f'{{{key}}}'

    return template_str.format_map(_SafeDict(tokens))
