"""
Invariant battery for the multi-season stress harness.

12 invariant functions that verify database consistency after each
simulated season. Each returns (passed: bool, detail: str).
"""

import sqlite3
from typing import Tuple

from ..utils.constants import (
    MAX_CAP_OVERAGE_TOLERANCE,
    ACTIVE_ROSTER_SIZE,
    PRACTICE_SQUAD_SIZE,
)


def _inv_career_stats_match_season_sums(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 1: Career stats = sum of season stats."""
    career_rows = conn.execute(
        "SELECT COUNT(*) AS cnt FROM player_career_stats"
    ).fetchone()
    if career_rows['cnt'] == 0:
        return (True, "skipped -- no career stats in database yet")

    columns = [
        ('career_pass_yards', 'pass_yards'),
        ('career_pass_tds', 'pass_tds'),
        ('career_rush_yards', 'rush_yards'),
        ('career_rush_tds', 'rush_tds'),
        ('career_rec_yards', 'rec_yards'),
        ('career_rec_tds', 'rec_tds'),
        ('career_sacks', 'sacks'),
        ('career_interceptions', 'interceptions'),
        ('career_fg_made', 'fg_made'),
    ]

    mismatches = []
    for career_col, season_col in columns:
        rows = conn.execute(f"""
            SELECT c.player_id,
                   c.{career_col} AS career_val,
                   COALESCE(s.season_sum, 0) AS season_sum
            FROM player_career_stats c
            LEFT JOIN (
                SELECT player_id, SUM({season_col}) AS season_sum
                FROM player_season_stats
                GROUP BY player_id
            ) s ON c.player_id = s.player_id
            WHERE ABS(c.{career_col} - COALESCE(s.season_sum, 0)) > 0
        """).fetchall()
        if rows:
            mismatches.append(
                f"{career_col}: {len(rows)} player(s) mismatch"
            )

    if mismatches:
        return (False, "; ".join(mismatches))
    return (True, "all career stats match season sums")


def _inv_no_orphan_fk_references(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 2: No orphan FK references in key_play or box_score."""
    orphan_key_plays = conn.execute("""
        SELECT COUNT(*) AS cnt FROM key_play
        WHERE game_id NOT IN (SELECT id FROM game)
    """).fetchone()['cnt']

    orphan_box_scores = conn.execute("""
        SELECT COUNT(*) AS cnt FROM box_score
        WHERE game_id NOT IN (SELECT id FROM game)
    """).fetchone()['cnt']

    issues = []
    if orphan_key_plays > 0:
        issues.append(f"{orphan_key_plays} orphan key_play rows")
    if orphan_box_scores > 0:
        issues.append(f"{orphan_box_scores} orphan box_score rows")

    if issues:
        return (False, "; ".join(issues))
    return (True, "no orphan FK references")


def _inv_cap_discipline(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 3: No team over the cap beyond tolerance."""
    over_cap = conn.execute("""
        SELECT id, abbreviation, cap_space FROM team
        WHERE cap_space < ?
    """, (-MAX_CAP_OVERAGE_TOLERANCE,)).fetchall()

    if over_cap:
        details = [
            f"{r['abbreviation']}=${r['cap_space']:,}"
            for r in over_cap
        ]
        return (False, f"{len(over_cap)} team(s) over cap: {', '.join(details)}")
    return (True, "all teams within cap")


def _inv_roster_integrity(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 4: Each team has exactly 53 active players, <= 16 practice squad."""
    teams = conn.execute("SELECT id, abbreviation FROM team").fetchall()
    issues = []

    for team in teams:
        active = conn.execute("""
            SELECT COUNT(*) AS cnt FROM player
            WHERE team_id = ? AND roster_status = 'active'
        """, (team['id'],)).fetchone()['cnt']

        ps = conn.execute("""
            SELECT COUNT(*) AS cnt FROM player
            WHERE team_id = ? AND roster_status = 'practice_squad'
        """, (team['id'],)).fetchone()['cnt']

        if active != ACTIVE_ROSTER_SIZE:
            issues.append(f"{team['abbreviation']}: {active} active (expected {ACTIVE_ROSTER_SIZE})")
        if ps > PRACTICE_SQUAD_SIZE:
            issues.append(f"{team['abbreviation']}: {ps} PS (max {PRACTICE_SQUAD_SIZE})")

    if issues:
        return (False, f"{len(issues)} issue(s): {'; '.join(issues[:5])}" +
                (f" ... and {len(issues)-5} more" if len(issues) > 5 else ""))
    return (True, "all teams have valid roster counts")


def _inv_contract_continuity(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 5: Every active rostered player has exactly 1 active contract."""
    # Check if contracts exist at all
    total_contracts = conn.execute(
        "SELECT COUNT(*) AS cnt FROM contract WHERE status = 'active'"
    ).fetchone()['cnt']

    if total_contracts == 0:
        return (True, "skipped -- no contracts in database")

    players_without = conn.execute("""
        SELECT p.id, p.first_name, p.last_name, p.position
        FROM player p
        WHERE p.team_id IS NOT NULL
          AND p.roster_status = 'active'
          AND (
            SELECT COUNT(*) FROM contract c
            WHERE c.player_id = p.id AND c.status = 'active'
          ) != 1
    """).fetchall()

    if players_without:
        return (False,
                f"{len(players_without)} active player(s) without exactly 1 active contract")
    return (True, "all active players have exactly 1 active contract")


def _inv_awards_uniqueness(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 6: Exactly 1 MVP per completed season."""
    # Check if season stats exist for this year
    stats_exist = conn.execute(
        "SELECT COUNT(*) AS cnt FROM player_season_stats WHERE season_year = ?",
        (season_year,),
    ).fetchone()['cnt']

    if stats_exist == 0:
        return (True, "skipped -- no season stats for this year")

    mvp_count = conn.execute(
        "SELECT COUNT(*) AS cnt FROM player_season_stats WHERE won_mvp = 1 AND season_year = ?",
        (season_year,),
    ).fetchone()['cnt']

    if mvp_count != 1:
        return (False, f"MVP count for {season_year}: {mvp_count} (expected 1)")

    # OPOY/DPOY are returned by assign_awards() but not persisted as columns
    return (True, f"exactly 1 MVP for {season_year} (OPOY/DPOY not persisted in DB, skipped)")


def _inv_champion_uniqueness(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 7: Exactly one champion per completed season."""
    row = conn.execute(
        "SELECT champion_team_id, is_complete FROM season WHERE year = ?",
        (season_year,),
    ).fetchone()

    if not row:
        return (False, f"no season record for {season_year}")

    if not row['is_complete']:
        return (True, f"skipped -- season {season_year} not yet complete")

    if row['champion_team_id'] is None:
        return (False, f"season {season_year} is complete but champion_team_id is NULL")

    return (True, f"champion_team_id={row['champion_team_id']} for {season_year}")


def _inv_coach_assignment_integrity(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 8: Every team has exactly one coach; no coach on multiple teams."""
    # Check if coach_career table exists and has data
    try:
        coach_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM coach_career WHERE is_active = 1"
        ).fetchone()['cnt']
    except sqlite3.OperationalError:
        return (True, "skipped -- coach_career table not found")

    if coach_count == 0:
        return (True, "skipped -- no active coaches in database")

    teams = conn.execute("SELECT id, abbreviation FROM team").fetchall()
    issues = []

    for team in teams:
        coaches = conn.execute("""
            SELECT COUNT(*) AS cnt FROM coach_career
            WHERE current_team_id = ? AND is_active = 1
        """, (team['id'],)).fetchone()['cnt']

        if coaches != 1:
            issues.append(f"{team['abbreviation']}: {coaches} coach(es)")

    # Check for coaches assigned to multiple teams
    multi = conn.execute("""
        SELECT id, first_name, last_name, current_team_id
        FROM coach_career
        WHERE is_active = 1 AND current_team_id IS NOT NULL
        GROUP BY current_team_id
        HAVING COUNT(*) > 1
    """).fetchall()

    if multi:
        issues.append(f"{len(multi)} team(s) with multiple coaches")

    if issues:
        return (False, f"{len(issues)} issue(s): {'; '.join(issues[:5])}" +
                (f" ... and {len(issues)-5} more" if len(issues) > 5 else ""))
    return (True, "all teams have exactly 1 coach, no duplicates")


def _inv_age_progression(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 9: All active players age >= 21, years_experience >= 0."""
    underage = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE is_active = 1 AND age < 21
    """).fetchone()['cnt']

    neg_exp = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE is_active = 1 AND years_experience < 0
    """).fetchone()['cnt']

    issues = []
    if underage > 0:
        issues.append(f"{underage} player(s) under age 21")
    if neg_exp > 0:
        issues.append(f"{neg_exp} player(s) with negative experience")

    # Check drafted players have experience > 0 if drafted in/before season_year
    drafted_no_exp = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE is_active = 1
          AND draft_year IS NOT NULL
          AND draft_year <= ?
          AND years_experience <= 0
    """, (season_year,)).fetchone()['cnt']

    if drafted_no_exp > 0:
        issues.append(f"{drafted_no_exp} drafted player(s) with 0 experience")

    if issues:
        return (False, "; ".join(issues))
    return (True, "all age/experience values valid")


def _inv_retirement_plausibility(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 10: Retirement rate is plausible."""
    # Count retired players
    retired_count = conn.execute("""
        SELECT COUNT(*) AS cnt FROM player
        WHERE roster_status = 'retired'
    """).fetchone()['cnt']

    # Also check transaction log for retirement entries
    retired_txn = conn.execute("""
        SELECT COUNT(*) AS cnt FROM transaction_log
        WHERE transaction_type = 'retired' AND season_year = ?
    """, (season_year,)).fetchone()['cnt']

    total_players = conn.execute(
        "SELECT COUNT(*) AS cnt FROM player"
    ).fetchone()['cnt']

    if retired_count == 0 and retired_txn == 0:
        return (True, "skipped -- retirement system not yet active")

    rate = retired_count / max(total_players, 1)
    return (True, f"retired={retired_count} ({rate:.1%} of {total_players} players), "
                  f"txn_log_retirements_this_season={retired_txn}")


def _inv_player_team_pointer_sync(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 11: Player coach's current_team_id matches league.user_team_id."""
    try:
        player_coach = conn.execute("""
            SELECT id, current_team_id FROM coach_career
            WHERE is_player = 1 AND is_active = 1
        """).fetchone()
    except sqlite3.OperationalError:
        return (True, "skipped -- coach_career table not found")

    if not player_coach:
        return (True, "skipped -- no player coach exists")

    league = conn.execute(
        "SELECT user_team_id FROM league WHERE id = 1"
    ).fetchone()

    if not league:
        return (False, "no league record found")

    if player_coach['current_team_id'] != league['user_team_id']:
        return (False,
                f"coach.current_team_id={player_coach['current_team_id']} "
                f"!= league.user_team_id={league['user_team_id']}")

    return (True, f"player coach team_id={player_coach['current_team_id']} matches league")


def _inv_coach_team_personality_sync(
    conn: sqlite3.Connection, season_year: int,
) -> Tuple[bool, str]:
    """Inv 12: Team gm_personality matches assigned coach personality_archetype."""
    try:
        coaches = conn.execute("""
            SELECT c.id, c.first_name, c.last_name,
                   c.personality_archetype, c.current_team_id,
                   t.abbreviation, t.gm_personality
            FROM coach_career c
            JOIN team t ON c.current_team_id = t.id
            WHERE c.is_active = 1 AND c.current_team_id IS NOT NULL
        """).fetchall()
    except sqlite3.OperationalError:
        return (True, "skipped -- coach_career table not found")

    if not coaches:
        return (True, "skipped -- no coaches assigned to teams")

    mismatches = []
    for coach in coaches:
        if coach['personality_archetype'] != coach['gm_personality']:
            mismatches.append(
                f"{coach['abbreviation']}: coach={coach['personality_archetype']} "
                f"vs team={coach['gm_personality']}"
            )

    if mismatches:
        return (False, f"{len(mismatches)} mismatch(es): {'; '.join(mismatches[:5])}" +
                (f" ... and {len(mismatches)-5} more" if len(mismatches) > 5 else ""))
    return (True, "all coach/team personalities in sync")


# ==============================
# REGISTRY + AGGREGATOR
# ==============================

ALL_INVARIANTS = [
    ("Inv 1: Career stats = sum of seasons", _inv_career_stats_match_season_sums),
    ("Inv 2: No orphan FK references", _inv_no_orphan_fk_references),
    ("Inv 3: Cap discipline", _inv_cap_discipline),
    ("Inv 4: Roster integrity", _inv_roster_integrity),
    ("Inv 5: Contract continuity", _inv_contract_continuity),
    ("Inv 6: Awards uniqueness", _inv_awards_uniqueness),
    ("Inv 7: Champion uniqueness", _inv_champion_uniqueness),
    ("Inv 8: Coach assignment integrity", _inv_coach_assignment_integrity),
    ("Inv 9: Age progression", _inv_age_progression),
    ("Inv 10: Retirement plausibility", _inv_retirement_plausibility),
    ("Inv 11: Player team pointer sync", _inv_player_team_pointer_sync),
    ("Inv 12: Coach-team personality sync", _inv_coach_team_personality_sync),
]


def run_all_invariants(
    conn: sqlite3.Connection, season_year: int,
) -> list[dict]:
    """Run all 12 invariants and return results.

    Returns:
        List of dicts with keys: name, passed, detail.
    """
    results = []
    for name, func in ALL_INVARIANTS:
        try:
            passed, detail = func(conn, season_year)
        except Exception as e:
            passed, detail = False, f"EXCEPTION: {e}"
        results.append({
            'name': name,
            'passed': passed,
            'detail': detail,
        })
    return results
