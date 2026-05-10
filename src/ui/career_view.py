"""Full coach career view (Phase 4 Prompt #9).

Used by view_career.py CLI tool.

Sections:
- Identity (name, age, archetype)
- Career totals (seasons, record, championships)
- Tenure history (per-team breakdown)
- Legacy trajectory (season-by-season graph)
- Records held (player + coach records)
"""

import sqlite3
from src.utils.constants import DISPLAY_WIDTH, DISPLAY_BORDER_HEAVY, DISPLAY_BORDER_LIGHT, REGULAR_SEASON_WEEKS
from src.ui.colors import bold, dim, cyan, yellow
from src.db.queries import get_coach_legacy_scores, get_peer_ranking


def render_career_view(
    conn: sqlite3.Connection,
    coach_id: int,
    use_color: bool = True,
) -> str:
    """Compose full career view as printable string."""
    sections = [
        render_career_header(conn, coach_id, use_color),
        render_career_totals(conn, coach_id, use_color),
        render_tenure_history(conn, coach_id, use_color),
        render_legacy_trajectory(conn, coach_id, use_color),
        render_records_held(conn, coach_id, use_color),
    ]
    return '\n\n'.join(s for s in sections if s)


def render_career_header(conn, coach_id, use_color):
    """COACH BILL WALSH  •  AGE 52  •  ANALYTICS"""
    coach = conn.execute("""
        SELECT first_name, last_name, age, personality_archetype
        FROM coach_career
        WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach:
        return ""

    name = f"{coach['first_name']} {coach['last_name']}".upper()
    age = coach['age']
    archetype = coach['personality_archetype'].replace('_', ' ').title()

    header = f"COACH {name}  •  AGE {age}  •  {archetype}"
    return bold(header, use_color)


def render_career_totals(conn, coach_id, use_color):
    """N seasons coaching  •  Career W-L: X-Y (.zzz)
    N championships  •  M conference titles  •  K playoff appearances"""
    # Get all tenures
    tenures = conn.execute("""
        SELECT team_id, start_year, end_year
        FROM coach_tenure
        WHERE coach_id = ?
        ORDER BY start_year
    """, (coach_id,)).fetchall()

    if not tenures:
        return ""

    # Count seasons
    total_seasons = 0
    for tenure in tenures:
        end_year = tenure['end_year']
        if end_year is None:
            # Active tenure - get current season
            league = conn.execute("SELECT current_season FROM league").fetchone()
            if league:
                end_year = league['current_season']
            else:
                end_year = tenure['start_year']

        total_seasons += (end_year - tenure['start_year'] + 1)

    # Calculate career W-L
    total_wins = 0
    total_losses = 0

    for tenure in tenures:
        team_id = tenure['team_id']
        start_year = tenure['start_year']
        end_year = tenure['end_year']

        if end_year is None:
            league = conn.execute("SELECT current_season FROM league").fetchone()
            if league:
                end_year = league['current_season']
            else:
                end_year = start_year

        # Sum wins/losses for this tenure
        standings = conn.execute("""
            SELECT SUM(wins) as w, SUM(losses) as l
            FROM team_season_record
            WHERE team_id = ? AND season_year BETWEEN ? AND ?
        """, (team_id, start_year, end_year)).fetchone()

        if standings:
            total_wins += standings['w'] or 0
            total_losses += standings['l'] or 0

    win_pct = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.0

    # Count championships
    championships = []
    conf_titles = []
    playoff_appearances = []

    for tenure in tenures:
        team_id = tenure['team_id']
        start_year = tenure['start_year']
        end_year = tenure['end_year']

        if end_year is None:
            league = conn.execute("SELECT current_season FROM league").fetchone()
            if league:
                end_year = league['current_season']
            else:
                end_year = start_year

        # Championships
        champs = conn.execute("""
            SELECT year FROM season
            WHERE champion_team_id = ? AND year BETWEEN ? AND ?
        """, (team_id, start_year, end_year)).fetchall()
        championships.extend([c['year'] for c in champs])

        # Conference titles (Super Bowl participant = conference champ)
        conf = conn.execute("""
            SELECT year FROM season
            WHERE (champion_team_id = ? OR runner_up_team_id = ?)
              AND year BETWEEN ? AND ?
        """, (team_id, team_id, start_year, end_year)).fetchall()
        conf_titles.extend([c['year'] for c in conf])

        # Playoff appearances (any game after week 17)
        playoffs = conn.execute("""
            SELECT DISTINCT s.year as season_year
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE (g.home_team_id = ? OR g.away_team_id = ?)
              AND w.week_number > ?
              AND s.year BETWEEN ? AND ?
        """, (team_id, team_id, REGULAR_SEASON_WEEKS, start_year, end_year)).fetchall()
        playoff_appearances.extend([p['season_year'] for p in playoffs])

    n_championships = len(championships)
    n_conf_titles = len(conf_titles)
    n_playoffs = len(set(playoff_appearances))

    lines = [
        DISPLAY_BORDER_LIGHT,
        f"{total_seasons} seasons coaching  •  Career W-L: {total_wins}-{total_losses} ({win_pct:.3f})",
        f"{n_championships} championships  •  {n_conf_titles} conference titles  •  {n_playoffs} playoff appearances",
    ]

    return '\n'.join(lines)


def render_tenure_history(conn, coach_id, use_color):
    """Section: TENURE HISTORY
    For each tenure row:
      [start-end]  TEAM   W-L  •  championships
      Inherited [N-M] team. [Brief note on starting_condition_multiplier]
      Ended: [end_reason]
    """
    tenures = conn.execute("""
        SELECT t.team_id, t.start_year, t.end_year, t.end_reason, t.starting_condition_multiplier,
               tm.city, tm.nickname
        FROM coach_tenure t
        JOIN team tm ON t.team_id = tm.id
        WHERE t.coach_id = ?
        ORDER BY t.start_year
    """, (coach_id,)).fetchall()

    if not tenures:
        return ""

    lines = [bold("TENURE HISTORY", use_color), DISPLAY_BORDER_LIGHT]

    for tenure in tenures:
        team_id = tenure['team_id']
        start_year = tenure['start_year']
        end_year = tenure['end_year']
        end_reason = tenure['end_reason']
        start_cond_mult = tenure['starting_condition_multiplier']
        team_name = f"{tenure['city']} {tenure['nickname']}"

        # Determine year range display
        if end_year is None:
            league = conn.execute("SELECT current_season FROM league").fetchone()
            if league:
                end_year = league['current_season']
            else:
                end_year = start_year
            year_range = f"{start_year}-present"
        else:
            year_range = f"{start_year}-{end_year}"

        # Calculate W-L for this tenure
        standings = conn.execute("""
            SELECT SUM(wins) as w, SUM(losses) as l
            FROM team_season_record
            WHERE team_id = ? AND season_year BETWEEN ? AND ?
        """, (team_id, start_year, end_year)).fetchone()

        wins = standings['w'] or 0
        losses = standings['l'] or 0

        # Count championships
        champs = conn.execute("""
            SELECT COUNT(*) as n FROM season
            WHERE champion_team_id = ? AND year BETWEEN ? AND ?
        """, (team_id, start_year, end_year)).fetchone()

        n_champs = champs['n'] if champs else 0

        # Build tenure line
        lines.append(f"  [{year_range}]  {team_name}  {wins}-{losses}")

        if n_champs > 0:
            lines.append(f"    {n_champs} championship{'s' if n_champs > 1 else ''}")

        # Starting condition note
        if start_cond_mult != 1.0:
            if start_cond_mult > 1.0:
                cond_note = yellow(f"    Inherited struggling team ({start_cond_mult:.2f}x difficulty)", use_color)
            else:
                cond_note = cyan(f"    Inherited strong team ({start_cond_mult:.2f}x difficulty)", use_color)
            lines.append(cond_note)

        # End reason
        if end_reason:
            reason_display = end_reason.replace('_', ' ').title()
            lines.append(dim(f"    Ended: {reason_display}", use_color))

        lines.append("")  # Spacing between tenures

    return '\n'.join(lines)


def render_legacy_trajectory(conn, coach_id, use_color):
    """Section: LEGACY TRAJECTORY
    Career legacy total: N (active rank #X of M, all-time #Y of Z)
    By tenure breakdown"""
    # Get latest aggregate legacy score
    latest = conn.execute("""
        SELECT season_year, total_legacy_score, is_dynasty, hof_eligible
        FROM legacy_score
        WHERE coach_id = ?
        ORDER BY season_year DESC
        LIMIT 1
    """, (coach_id,)).fetchone()

    if not latest:
        return ""

    lines = [bold("LEGACY TRAJECTORY", use_color), DISPLAY_BORDER_LIGHT]

    # Latest total
    career_total = latest['total_legacy_score']
    latest_season = latest['season_year']

    # Get latest peer ranking
    ranking = get_peer_ranking(conn, coach_id, latest_season)

    if ranking:
        active_rank = ranking['active_rank']
        n_active = ranking['n_active']
        all_time_rank = ranking['all_time_rank']
        n_all_time = ranking['n_all_time']
        lines.append(f"  Career legacy total: {career_total}")
        lines.append(f"  Active rank: #{active_rank} of {n_active}")
        lines.append(f"  All-time rank: #{all_time_rank} of {n_all_time}")
    else:
        lines.append(f"  Career legacy total: {career_total}")

    lines.append("")

    # Season-by-season breakdown (last 10 seasons)
    lines.append(dim("  Recent seasons:", use_color))

    # Get per-season detail
    season_details = conn.execute("""
        SELECT cls.season_year, cls.season_legacy_score,
               ls.total_legacy_score, ls.is_dynasty, ls.hof_eligible
        FROM coach_legacy_score cls
        LEFT JOIN legacy_score ls ON cls.season_year = ls.season_year AND cls.coach_id = ls.coach_id
        WHERE cls.coach_id = ?
        ORDER BY cls.season_year DESC
        LIMIT 10
    """, (coach_id,)).fetchall()

    for row in reversed(season_details):  # Show oldest to newest
        year = row['season_year']
        contribution = row['season_legacy_score']
        cumulative = row['total_legacy_score'] or 0

        # Dynasty/HOF markers
        markers = []
        if row['is_dynasty']:
            markers.append(yellow("★", use_color))
        if row['hof_eligible']:
            markers.append(cyan("♦", use_color))

        marker_str = ''.join(markers) if markers else ' '

        lines.append(f"  {year}  {contribution:+6d}  →  {cumulative:6d}  {marker_str}")

    return '\n'.join(lines)


def render_records_held(conn, coach_id, use_color):
    """Section: RECORDS HELD
    Read league_record rows where holder_coach_id = coach OR holder_player_id
    is on this coach's roster during record season. List up to 10. Empty returns ''."""
    # Get records held by this coach
    coach_records = conn.execute("""
        SELECT category, scope, record_value, season_year
        FROM league_record
        WHERE holder_coach_id = ?
        ORDER BY set_at DESC
        LIMIT 10
    """, (coach_id,)).fetchall()

    # Get records held by players on coach's teams
    # (This is complex - need to check all tenures and find matching records)
    tenures = conn.execute("""
        SELECT team_id, start_year, end_year
        FROM coach_tenure
        WHERE coach_id = ?
    """, (coach_id,)).fetchall()

    player_records = []

    for tenure in tenures:
        team_id = tenure['team_id']
        start_year = tenure['start_year']
        end_year = tenure['end_year']

        if end_year is None:
            league = conn.execute("SELECT current_season FROM league").fetchone()
            if league:
                end_year = league['current_season']
            else:
                end_year = start_year

        records = conn.execute("""
            SELECT category, scope, record_value, holder_name, season_year
            FROM league_record
            WHERE holder_team_id = ? AND season_year BETWEEN ? AND ?
            ORDER BY set_at DESC
            LIMIT 10
        """, (team_id, start_year, end_year)).fetchall()

        player_records.extend(records)

    all_records = list(coach_records) + player_records

    if not all_records:
        return ""

    lines = [bold("RECORDS HELD", use_color), DISPLAY_BORDER_LIGHT]

    # Limit to 10 most recent
    for record in all_records[:10]:
        category = record['category'].replace('_', ' ').title()
        scope = record['scope'].replace('_', ' ').title()
        value = record['record_value']
        year = record['season_year']

        # Format value
        if isinstance(value, float) and value % 1 != 0:
            value_str = f"{value:.1f}"
        else:
            value_str = f"{int(value)}"

        # Check if coach or player record
        holder_name = record['holder_name'] if 'holder_name' in record.keys() else 'You'

        lines.append(f"  {category} ({scope}): {value_str} — {holder_name} ({year})")

    return '\n'.join(lines)
