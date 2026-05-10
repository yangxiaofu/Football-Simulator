"""
League Health Report generator.

Produces a plain-text report summarizing league health across
a multi-season stress test run.
"""

import sqlite3
import math

from ..utils.constants import (
    HEALTH_STAR_RATING_THRESHOLD,
    HEALTH_AGE_BUCKETS,
    HEALTH_CAP_BUCKETS,
)


def generate_health_report(
    conn: sqlite3.Connection, year_one: int, year_final: int,
) -> str:
    """Generate a League Health Report spanning multiple seasons.

    Args:
        conn: Database connection.
        year_one: First season year simulated.
        year_final: Last season year simulated.

    Returns:
        Plain-text report string (~80 char width).
    """
    lines = []
    w = 78  # line width

    lines.append("=" * w)
    lines.append("LEAGUE HEALTH REPORT".center(w))
    lines.append("=" * w)

    # Section 1: Run Summary
    lines.append("")
    lines.append("1. RUN SUMMARY")
    lines.append("-" * w)
    seasons_covered = year_final - year_one + 1
    completed = conn.execute(
        "SELECT COUNT(*) AS cnt FROM season WHERE is_complete = 1 AND year >= ? AND year <= ?",
        (year_one, year_final),
    ).fetchone()['cnt']
    lines.append(f"  Years covered:      {year_one} - {year_final} ({seasons_covered} season(s))")
    lines.append(f"  Seasons completed:  {completed}")

    # Section 2: Roster Turnover
    lines.append("")
    lines.append("2. ROSTER TURNOVER")
    lines.append("-" * w)
    first_year_players = conn.execute("""
        SELECT COUNT(DISTINCT player_id) AS cnt
        FROM player_season_stats WHERE season_year = ?
    """, (year_one,)).fetchone()['cnt']
    final_year_players = conn.execute("""
        SELECT COUNT(DISTINCT player_id) AS cnt
        FROM player_season_stats WHERE season_year = ?
    """, (year_final,)).fetchone()['cnt']

    if first_year_players > 0 and final_year_players > 0:
        # Players who appeared in both
        overlap = conn.execute("""
            SELECT COUNT(DISTINCT a.player_id) AS cnt
            FROM player_season_stats a
            JOIN player_season_stats b ON a.player_id = b.player_id
            WHERE a.season_year = ? AND b.season_year = ?
        """, (year_one, year_final)).fetchone()['cnt']
        turnover_pct = (1.0 - overlap / max(first_year_players, 1)) * 100
        lines.append(f"  Players in {year_one}:     {first_year_players}")
        lines.append(f"  Players in {year_final}:     {final_year_players}")
        lines.append(f"  Overlap (both):       {overlap}")
        lines.append(f"  Turnover rate:        {turnover_pct:.1f}%")
    else:
        lines.append("  Insufficient season stats data for turnover analysis")

    # Section 3: Age Distribution
    lines.append("")
    lines.append("3. AGE DISTRIBUTION (current roster)")
    lines.append("-" * w)
    positions = conn.execute("""
        SELECT DISTINCT position FROM player
        WHERE is_active = 1 AND team_id IS NOT NULL
        ORDER BY position
    """).fetchall()

    header = f"  {'Position':<6}"
    for lo, hi in HEALTH_AGE_BUCKETS:
        label = f"{lo}-{hi}" if hi < 99 else f"{lo}+"
        header += f"  {label:>6}"
    header += f"  {'Total':>6}"
    lines.append(header)

    for pos_row in positions:
        pos = pos_row['position']
        row_str = f"  {pos:<6}"
        total = 0
        for lo, hi in HEALTH_AGE_BUCKETS:
            cnt = conn.execute("""
                SELECT COUNT(*) AS cnt FROM player
                WHERE is_active = 1 AND team_id IS NOT NULL
                  AND position = ? AND age >= ? AND age <= ?
            """, (pos, lo, hi)).fetchone()['cnt']
            row_str += f"  {cnt:>6}"
            total += cnt
        row_str += f"  {total:>6}"
        lines.append(row_str)

    # Section 4: Cap Distribution
    lines.append("")
    lines.append("4. CAP DISTRIBUTION")
    lines.append("-" * w)
    for label, lo, hi in HEALTH_CAP_BUCKETS:
        if hi == float('inf'):
            cnt = conn.execute(
                "SELECT COUNT(*) AS cnt FROM team WHERE cap_space >= ?",
                (lo,),
            ).fetchone()['cnt']
        elif lo == float('-inf'):
            cnt = conn.execute(
                "SELECT COUNT(*) AS cnt FROM team WHERE cap_space < ?",
                (hi,),
            ).fetchone()['cnt']
        else:
            cnt = conn.execute(
                "SELECT COUNT(*) AS cnt FROM team WHERE cap_space >= ? AND cap_space < ?",
                (lo, hi),
            ).fetchone()['cnt']
        lines.append(f"  {label:<12} {cnt:>3} team(s)")

    # Section 5: Talent Distribution
    lines.append("")
    lines.append("5. TALENT DISTRIBUTION (avg true_overall by position)")
    lines.append("-" * w)
    talent = conn.execute("""
        SELECT position,
               AVG(true_overall) AS avg_ovr,
               MIN(true_overall) AS min_ovr,
               MAX(true_overall) AS max_ovr,
               COUNT(*) AS cnt
        FROM player
        WHERE is_active = 1 AND team_id IS NOT NULL
        GROUP BY position
        ORDER BY AVG(true_overall) DESC
    """).fetchall()

    lines.append(f"  {'Position':<6}  {'Avg':>5}  {'Min':>5}  {'Max':>5}  {'Count':>6}")
    for row in talent:
        lines.append(
            f"  {row['position']:<6}  {row['avg_ovr']:>5.1f}  "
            f"{row['min_ovr']:>5}  {row['max_ovr']:>5}  {row['cnt']:>6}"
        )

    # Section 6: Star Count
    lines.append("")
    lines.append("6. STAR COUNT")
    lines.append("-" * w)
    stars = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE is_active = 1 AND team_id IS NOT NULL
          AND true_overall >= ?
    """, (HEALTH_STAR_RATING_THRESHOLD,)).fetchone()['cnt']
    lines.append(f"  Players with true_overall >= {HEALTH_STAR_RATING_THRESHOLD}: {stars}")

    # Section 7: Champions
    lines.append("")
    lines.append("7. CHAMPIONS")
    lines.append("-" * w)
    champions = conn.execute("""
        SELECT s.year, t.city, t.nickname, t.abbreviation
        FROM season s
        LEFT JOIN team t ON s.champion_team_id = t.id
        WHERE s.year >= ? AND s.year <= ? AND s.is_complete = 1
        ORDER BY s.year
    """, (year_one, year_final)).fetchall()

    if champions:
        for champ in champions:
            if champ['city']:
                lines.append(f"  {champ['year']}: {champ['city']} {champ['nickname']} ({champ['abbreviation']})")
            else:
                lines.append(f"  {champ['year']}: (no champion recorded)")
    else:
        lines.append("  No completed seasons with champions")

    # Section 8: Competitive Balance
    lines.append("")
    lines.append("8. COMPETITIVE BALANCE")
    lines.append("-" * w)
    records = conn.execute("""
        SELECT wins FROM team_season_record
        WHERE season_year = ?
    """, (year_final,)).fetchall()

    if records:
        wins_list = [r['wins'] for r in records]
        avg_wins = sum(wins_list) / len(wins_list)
        variance = sum((w - avg_wins) ** 2 for w in wins_list) / len(wins_list)
        std_dev = math.sqrt(variance)
        lines.append(f"  Season {year_final} win distribution:")
        lines.append(f"    Teams:     {len(wins_list)}")
        lines.append(f"    Avg wins:  {avg_wins:.1f}")
        lines.append(f"    Std dev:   {std_dev:.2f}")
        lines.append(f"    Min wins:  {min(wins_list)}")
        lines.append(f"    Max wins:  {max(wins_list)}")
    else:
        lines.append("  No team_season_record data for final season")

    # Section 9: AI Rebuild Cycles
    lines.append("")
    lines.append("9. AI REBUILD CYCLES")
    lines.append("-" * w)
    try:
        ended_tenures = conn.execute("""
            SELECT COUNT(*) AS cnt FROM coach_tenure
            WHERE end_year IS NOT NULL
        """).fetchone()['cnt']
        lines.append(f"  Coach tenures ended: {ended_tenures}")
    except sqlite3.OperationalError:
        lines.append("  N/A (coach_tenure table not found)")

    lines.append("")
    lines.append("=" * w)
    lines.append("END OF REPORT".center(w))
    lines.append("=" * w)

    return "\n".join(lines)
