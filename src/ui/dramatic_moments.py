"""Dramatic moment displays for dynasty activation and HOF eligibility (Phase 4 Prompt #9)."""

import sqlite3
from typing import Optional
from src.utils.constants import DISPLAY_WIDTH, DISPLAY_BORDER_HEAVY
from src.ui.colors import bold, cyan, yellow
from src.db.queries import get_narrative_beats_for_coach, get_coach_legacy_scores


def maybe_render_dynasty_moment(
    conn: sqlite3.Connection,
    season_year: int,
    coach_id: int,
    use_color: bool = True,
) -> Optional[str]:
    """Check if dynasty flag newly activated this season AND not shown before.

    Returns dramatic screen if triggered, else None.
    Inserts into narrative_moment_shown to prevent re-render.

    Layout:
      ============================================================
                          DYNASTY ACHIEVED
      ============================================================

      Three championships in seven years.
      Chicago belongs to you now.

      2024  •  2025  •  2026
           Super Bowl LIX, LX, LXI

      Press Enter to continue ...
      ============================================================
    """
    # 1. Check if already shown
    already_shown = conn.execute("""
        SELECT 1 FROM narrative_moment_shown
        WHERE coach_id = ? AND moment_type = 'dynasty'
    """, (coach_id,)).fetchone()

    if already_shown:
        return None

    # 2. Check legacy_score.is_dynasty for this season AND previous season was 0
    current_legacy = conn.execute("""
        SELECT is_dynasty FROM legacy_score
        WHERE season_year = ? AND coach_id = ?
    """, (season_year, coach_id)).fetchone()

    if not current_legacy or not current_legacy['is_dynasty']:
        return None

    # Check if this is the FIRST time (previous season was not dynasty)
    previous_legacy = conn.execute("""
        SELECT is_dynasty FROM legacy_score
        WHERE season_year = ? AND coach_id = ?
    """, (season_year - 1, coach_id)).fetchone()

    if previous_legacy and previous_legacy['is_dynasty']:
        return None

    # 3. Pull narrative text from coach_narrative_beat
    beats = get_narrative_beats_for_coach(conn, coach_id)
    dynasty_beat = None

    for beat in beats:
        if beat['beat_type'] == 'dynasty_milestone' and beat['season_year'] == season_year:
            dynasty_beat = beat
            break

    narrative_text = dynasty_beat['text'] if dynasty_beat else "Three championships in seven years."

    # 4. Get championship years
    coach_row = conn.execute("""
        SELECT current_team_id FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach_row or not coach_row['current_team_id']:
        team_id = None
    else:
        team_id = coach_row['current_team_id']

    championship_years = []
    if team_id:
        champ_rows = conn.execute("""
            SELECT year FROM season
            WHERE champion_team_id = ?
            ORDER BY year
        """, (team_id,)).fetchall()
        championship_years = [r['year'] for r in champ_rows]

    # Build the display
    lines = [
        DISPLAY_BORDER_HEAVY,
        bold("                      DYNASTY ACHIEVED", use_color).center(DISPLAY_WIDTH),
        DISPLAY_BORDER_HEAVY,
        "",
        narrative_text.center(DISPLAY_WIDTH),
        "",
    ]

    # Championship years
    if championship_years:
        years_str = "  •  ".join(str(y) for y in championship_years)
        lines.append(yellow(years_str, use_color).center(DISPLAY_WIDTH + (11 if use_color else 0)))
        lines.append("")

    lines.append(bold("Press Enter to continue ...", use_color).center(DISPLAY_WIDTH + (8 if use_color else 0)))
    lines.append(DISPLAY_BORDER_HEAVY)

    # 5. INSERT into narrative_moment_shown
    with conn:
        conn.execute("""
            INSERT INTO narrative_moment_shown (coach_id, moment_type, shown_season)
            VALUES (?, 'dynasty', ?)
        """, (coach_id, season_year))

    return '\n'.join(lines)


def maybe_render_hof_moment(
    conn: sqlite3.Connection,
    season_year: int,
    coach_id: int,
    use_color: bool = True,
) -> Optional[str]:
    """Same pattern for HOF eligibility first crossing threshold.

    Layout:
      ============================================================
                       HALL OF FAME ELIGIBLE
      ============================================================

      [Coach name] crossed the threshold this year.
      Whatever comes next, the bust is waiting.

      Career legacy: [N]
      Championships: [N]  Conference titles: [M]

      Press Enter to continue ...
      ============================================================
    """
    # 1. Check if already shown
    already_shown = conn.execute("""
        SELECT 1 FROM narrative_moment_shown
        WHERE coach_id = ? AND moment_type = 'hof_eligible'
    """, (coach_id,)).fetchone()

    if already_shown:
        return None

    # 2. Check legacy_score.hof_eligible for this season AND previous season was 0
    current_legacy = conn.execute("""
        SELECT hof_eligible, total_legacy_score FROM legacy_score
        WHERE season_year = ? AND coach_id = ?
    """, (season_year, coach_id)).fetchone()

    if not current_legacy or not current_legacy['hof_eligible']:
        return None

    # Check if this is the FIRST time (previous season was not HOF eligible)
    previous_legacy = conn.execute("""
        SELECT hof_eligible FROM legacy_score
        WHERE season_year = ? AND coach_id = ?
    """, (season_year - 1, coach_id)).fetchone()

    if previous_legacy and previous_legacy['hof_eligible']:
        return None

    # 3. Pull narrative text from coach_narrative_beat
    beats = get_narrative_beats_for_coach(conn, coach_id)
    hof_beat = None

    for beat in beats:
        if beat['beat_type'] == 'hof_eligible_first_time' and beat['season_year'] == season_year:
            hof_beat = beat
            break

    narrative_text = hof_beat['text'] if hof_beat else "Whatever comes next, the bust is waiting."

    # 4. Get coach name and career stats
    coach = conn.execute("""
        SELECT first_name, last_name, current_team_id
        FROM coach_career
        WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach:
        return None

    coach_name = f"{coach['first_name']} {coach['last_name']}"
    career_legacy = current_legacy['total_legacy_score']

    # Count championships and conference titles
    team_id = coach['current_team_id']

    if team_id:
        championships = conn.execute("""
            SELECT COUNT(*) as n FROM season
            WHERE champion_team_id = ?
        """, (team_id,)).fetchone()

        conf_titles = conn.execute("""
            SELECT COUNT(*) as n FROM season
            WHERE conference_champ_afc = ? OR conference_champ_nfc = ?
        """, (team_id, team_id)).fetchone()

        n_championships = championships['n'] if championships else 0
        n_conf_titles = conf_titles['n'] if conf_titles else 0
    else:
        n_championships = 0
        n_conf_titles = 0

    # Build the display
    lines = [
        DISPLAY_BORDER_HEAVY,
        bold("                   HALL OF FAME ELIGIBLE", use_color).center(DISPLAY_WIDTH),
        DISPLAY_BORDER_HEAVY,
        "",
        f"{coach_name} crossed the threshold this year.".center(DISPLAY_WIDTH),
        narrative_text.center(DISPLAY_WIDTH),
        "",
        cyan(f"Career legacy: {career_legacy:.1f}", use_color).center(DISPLAY_WIDTH + (11 if use_color else 0)),
        f"Championships: {n_championships}  •  Conference titles: {n_conf_titles}".center(DISPLAY_WIDTH),
        "",
        bold("Press Enter to continue ...", use_color).center(DISPLAY_WIDTH + (8 if use_color else 0)),
        DISPLAY_BORDER_HEAVY,
    ]

    # 5. INSERT into narrative_moment_shown
    with conn:
        conn.execute("""
            INSERT INTO narrative_moment_shown (coach_id, moment_type, shown_season)
            VALUES (?, 'hof_eligible', ?)
        """, (coach_id, season_year))

    return '\n'.join(lines)
