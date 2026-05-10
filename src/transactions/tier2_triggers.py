"""
Tier 2 dramatic press conference trigger detection (Phase 4 Prompt #6).

8 trigger detectors, guard-based deduplication, and an orchestrator that
runs detectors in priority order. Each detector returns (fired, context_dict).

Triggers fire at most once per guard_key per team per season.
"""

import sqlite3
from typing import Tuple, Optional

from ..utils.constants import (
    TIER2_MAX_PER_SEASON,
    TIER2_STAR_RATING_THRESHOLD,
    TIER2_LOSING_STREAK_GAMES,
    TIER2_TRIGGER_PRIORITY,
    PLAYOFF_WEEK_TO_ROUND_MAP,
    REGULAR_SEASON_WEEKS,
    TIER2_EVENT_RISING_STAR_STREAK,
    STREAK_LENGTH_WEEKS,
    STREAK_AWARD_TYPES,
)


# ============================================================
# GUARD HELPERS
# ============================================================

def is_trigger_guarded(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    trigger_type: str,
    guard_key: str,
) -> bool:
    """Check if this trigger has already fired for the given guard key."""
    row = conn.execute("""
        SELECT 1 FROM tier2_trigger_guard
        WHERE team_id = ? AND season_year = ? AND trigger_type = ? AND guard_key = ?
    """, (team_id, season_year, trigger_type, guard_key)).fetchone()
    return row is not None


def insert_trigger_guard(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    trigger_type: str,
    guard_key: str,
    fired_week: int,
) -> None:
    """Insert a trigger guard to prevent re-firing."""
    conn.execute("""
        INSERT OR IGNORE INTO tier2_trigger_guard
        (team_id, season_year, trigger_type, guard_key, fired_week)
        VALUES (?, ?, ?, ?, ?)
    """, (team_id, season_year, trigger_type, guard_key, fired_week))


def count_tier2_events_this_season(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
) -> int:
    """Count how many Tier 2 events have already fired this season."""
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM tier2_press_event
        WHERE team_id = ? AND season_year = ?
    """, (team_id, season_year)).fetchone()
    return row['cnt'] if row else 0


# ============================================================
# TRIGGER DETECTORS
# ============================================================

def detect_championship_won(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect if team won the championship this season."""
    guard_key = f"champ_{season_year}"
    if is_trigger_guarded(conn, team_id, season_year, 'championship_won', guard_key):
        return (False, {})

    # Check season table for champion
    row = conn.execute("""
        SELECT champion_team_id FROM season WHERE year = ?
    """, (season_year,)).fetchone()

    if row and row['champion_team_id'] == team_id:
        return (True, {'guard_key': guard_key, 'year': season_year})

    return (False, {})


def detect_dynasty_milestone(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect dynasty milestone — fires week 1 of the following season."""
    if week_number != 1:
        return (False, {})

    prev_year = season_year - 1
    guard_key = f"dynasty_{prev_year}"
    if is_trigger_guarded(conn, team_id, season_year, 'dynasty_milestone', guard_key):
        return (False, {})

    # Get player coach for this team
    coach = conn.execute("""
        SELECT id FROM coach_career
        WHERE current_team_id = ? AND is_player = 1 AND is_active = 1
    """, (team_id,)).fetchone()

    if not coach:
        return (False, {})

    # Check legacy_score for previous season dynasty flag (coach-centric table)
    row = conn.execute("""
        SELECT is_dynasty FROM legacy_score
        WHERE season_year = ? AND coach_id = ?
    """, (prev_year, coach['id'])).fetchone()

    if row and row['is_dynasty']:
        return (True, {'guard_key': guard_key, 'prev_year': prev_year})

    return (False, {})


def detect_playoff_loss(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect a playoff loss (wildcard, divisional, or conference round)."""
    # Only check during playoff weeks (REGULAR_SEASON_WEEKS + 1 and beyond)
    if week_number <= REGULAR_SEASON_WEEKS:
        return (False, {})

    # Determine round name from week
    round_name = PLAYOFF_WEEK_TO_ROUND_MAP.get(week_number, f'week_{week_number}')

    guard_key = f"round_{round_name}"
    if is_trigger_guarded(conn, team_id, season_year, 'playoff_loss', guard_key):
        return (False, {})

    # Check if team lost a game this playoff week
    row = conn.execute("""
        SELECT g.id, g.home_team_id, g.away_team_id, g.home_score, g.away_score
        FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ?
          AND w.week_number = ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 1
    """, (season_year, week_number, team_id, team_id)).fetchone()

    if not row:
        return (False, {})

    is_home = row['home_team_id'] == team_id
    team_score = row['home_score'] if is_home else row['away_score']
    opp_score = row['away_score'] if is_home else row['home_score']

    if team_score < opp_score:
        # Get opponent name
        opp_id = row['away_team_id'] if is_home else row['home_team_id']
        opp = conn.execute("""
            SELECT city, nickname FROM team WHERE id = ?
        """, (opp_id,)).fetchone()
        opponent = f"{opp['city']} {opp['nickname']}" if opp else "Unknown"

        return (True, {
            'guard_key': guard_key,
            'round_name': round_name.replace('_', ' ').title(),
            'opponent': opponent,
            'score': f"{team_score}-{opp_score}",
        })

    return (False, {})


def detect_star_injury(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect a star player (OVR >= 88) placed on IR this week."""
    # Check transaction_log for IR placements this week
    rows = conn.execute("""
        SELECT tl.player_id, p.first_name, p.last_name, p.position, p.true_overall
        FROM transaction_log tl
        JOIN player p ON tl.player_id = p.id
        WHERE tl.team_id = ?
          AND tl.season_year = ?
          AND tl.week_number = ?
          AND tl.transaction_type = 'ir_placed'
          AND p.true_overall >= ?
    """, (team_id, season_year, week_number, TIER2_STAR_RATING_THRESHOLD)).fetchall()

    for row in rows:
        guard_key = f"player_{row['player_id']}"
        if is_trigger_guarded(conn, team_id, season_year, 'star_injury', guard_key):
            continue
        star_name = f"{row['first_name']} {row['last_name']}"
        return (True, {
            'guard_key': guard_key,
            'star_name': star_name,
            'position': row['position'],
            'player_id': row['player_id'],
        })

    return (False, {})


def detect_blockbuster_trade(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect a blockbuster trade involving a star or 1st-round pick."""
    # Check for completed trades this week involving this team
    trades = conn.execute("""
        SELECT t.id, t.team_a_id, t.team_b_id
        FROM trade t
        WHERE t.season_year = ?
          AND t.week_number = ?
          AND t.status = 'completed'
          AND (t.team_a_id = ? OR t.team_b_id = ?)
    """, (season_year, week_number, team_id, team_id)).fetchall()

    for trade in trades:
        guard_key = f"trade_{trade['id']}"
        if is_trigger_guarded(conn, team_id, season_year, 'blockbuster_trade', guard_key):
            continue

        # Check if trade involves a star player (OVR >= 88) or 1st-round pick
        star_asset = conn.execute("""
            SELECT p.first_name, p.last_name, p.position, p.true_overall
            FROM trade_asset ta
            JOIN player p ON ta.player_id = p.id
            WHERE ta.trade_id = ? AND ta.asset_type = 'player'
              AND p.true_overall >= ?
        """, (trade['id'], TIER2_STAR_RATING_THRESHOLD)).fetchone()

        pick_asset = conn.execute("""
            SELECT ta.id FROM trade_asset ta
            JOIN draft_pick dp ON ta.draft_pick_id = dp.id
            WHERE ta.trade_id = ? AND ta.asset_type = 'pick'
              AND dp.round = 1
        """, (trade['id'],)).fetchone()

        if star_asset:
            star_name = f"{star_asset['first_name']} {star_asset['last_name']}"
            return (True, {
                'guard_key': guard_key,
                'star_name': star_name,
                'position': star_asset['position'],
                'trade_id': trade['id'],
            })
        elif pick_asset:
            # Determine trade partner
            partner_id = trade['team_b_id'] if trade['team_a_id'] == team_id else trade['team_a_id']
            partner = conn.execute("""
                SELECT city, nickname FROM team WHERE id = ?
            """, (partner_id,)).fetchone()
            partner_name = f"{partner['city']} {partner['nickname']}" if partner else "Unknown"
            return (True, {
                'guard_key': guard_key,
                'star_name': partner_name,
                'trade_id': trade['id'],
            })

    return (False, {})


def detect_blown_lead(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """STUB: Halftime scores are not stored. Always returns (False, {})."""
    return (False, {})


def detect_holdout_public(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect a public holdout by a star player."""
    rows = conn.execute("""
        SELECT pe.player_id, p.first_name, p.last_name, p.position, p.true_overall
        FROM player_event pe
        JOIN player p ON pe.player_id = p.id
        WHERE pe.team_id = ?
          AND pe.season_year = ?
          AND pe.event_type = 'holdout'
          AND pe.resolved = 0
          AND p.true_overall >= ?
    """, (team_id, season_year, TIER2_STAR_RATING_THRESHOLD)).fetchall()

    for row in rows:
        guard_key = f"player_{row['player_id']}"
        if is_trigger_guarded(conn, team_id, season_year, 'holdout_public', guard_key):
            continue
        star_name = f"{row['first_name']} {row['last_name']}"
        return (True, {
            'guard_key': guard_key,
            'star_name': star_name,
            'position': row['position'],
            'player_id': row['player_id'],
        })

    return (False, {})


def detect_losing_streak_3(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Detect a 3-game losing streak. Fires on the 3rd loss only."""
    # Get last 4 game results (need 4 to confirm streak starts at game 3)
    last_4 = conn.execute("""
        SELECT
            w.week_number,
            CASE
                WHEN g.home_team_id = ? THEN
                    CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END
                ELSE
                    CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END
            END as won
        FROM game g
        JOIN week w ON g.week_id = w.id
        JOIN season s ON w.season_id = s.id
        WHERE s.year = ?
          AND w.week_number <= ?
          AND (g.home_team_id = ? OR g.away_team_id = ?)
          AND g.is_complete = 1
        ORDER BY w.week_number DESC
        LIMIT 4
    """, (team_id, season_year, week_number, team_id, team_id)).fetchall()

    if len(last_4) < TIER2_LOSING_STREAK_GAMES:
        return (False, {})

    # Check that last 3 are all losses
    last_3_results = [g['won'] for g in last_4[:3]]
    if not all(r == 0 for r in last_3_results):
        return (False, {})

    # The 4th-most-recent must NOT be a loss (or fewer than 4 games played)
    # This ensures we fire only on the 3rd consecutive loss, not 4th/5th
    if len(last_4) >= 4 and last_4[3]['won'] == 0:
        return (False, {})

    # Guard key uses the week of the first loss in the streak
    first_loss_week = last_4[2]['week_number']  # 3rd from end = first loss in streak
    guard_key = f"streak_from_{first_loss_week}"
    if is_trigger_guarded(conn, team_id, season_year, 'losing_streak_3', guard_key):
        return (False, {})

    return (True, {
        'guard_key': guard_key,
        'streak_length': TIER2_LOSING_STREAK_GAMES,
        'first_loss_week': first_loss_week,
    })


def detect_rising_star_streak(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[bool, dict]:
    """Fire on the EXACT week a user-team player hits STREAK_LENGTH_WEEKS consecutive league stars.

    Fires only on the 3rd consecutive week (not on week 4, 5, 6 of the same streak).
    Uses a W-3 award check to prevent re-fire on streak extensions.
    Guard key provides idempotency if dispatcher is called twice for the same week.
    """
    from ..db.queries import get_user_team_weekly_awards, get_player, get_league_state

    league = get_league_state(conn)
    if not league or league['user_team_id'] != team_id:
        return (False, {})

    if week_number < STREAK_LENGTH_WEEKS:
        return (False, {})

    streak_weeks = list(range(week_number - STREAK_LENGTH_WEEKS + 1, week_number + 1))
    awards = get_user_team_weekly_awards(
        conn, team_id, season_year, streak_weeks, list(STREAK_AWARD_TYPES)
    )

    # Group by player_id: which weeks did each player win?
    by_player: dict = {}
    for row in awards:
        by_player.setdefault(row['player_id'], set()).add(row['week_number'])

    for player_id, weeks_won in by_player.items():
        if not set(streak_weeks).issubset(weeks_won):
            continue  # player didn't win all 3 streak weeks

        # Check week W-3: if also won then, this is ≥ week 4 of an older streak — skip
        pre_week = week_number - STREAK_LENGTH_WEEKS
        if pre_week >= 1:
            pre_awards = get_user_team_weekly_awards(
                conn, team_id, season_year, [pre_week], list(STREAK_AWARD_TYPES)
            )
            if any(r['player_id'] == player_id for r in pre_awards):
                continue  # continuation of older streak; only fire on week 3

        streak_start = streak_weeks[0]
        guard_key = f"rss_{player_id}_{streak_start}"
        if is_trigger_guarded(conn, team_id, season_year, TIER2_EVENT_RISING_STAR_STREAK, guard_key):
            continue

        player = get_player(conn, player_id)
        player_name = (
            f"{player['first_name']} {player['last_name']}" if player else "Unknown"
        )

        # Find award type for the current week (determines category label)
        current_week_awards = [r for r in awards
                                if r['player_id'] == player_id
                                and r['week_number'] == week_number]
        current_award_type = current_week_awards[0]['award_type'] if current_week_awards else 'OFFENSE'
        category = _award_type_to_label(current_award_type)

        return (True, {
            'guard_key': guard_key,
            'player_id': player_id,
            'star_name': player_name,
            'player_name': player_name,
            'position': player['position'] if player else '',
            'streak_length': str(STREAK_LENGTH_WEEKS),
            'category': category,
        })

    return (False, {})


def _award_type_to_label(award_type: str) -> str:
    return {
        'OFFENSE': 'Offensive Player of the Week',
        'DEFENSE': 'Defensive Player of the Week',
        'SPECIAL_TEAMS': 'Special Teams Player of the Week',
    }.get(award_type, 'Player of the Week')


# ============================================================
# ORCHESTRATOR
# ============================================================

_DETECTOR_MAP = {
    'championship_won': detect_championship_won,
    'dynasty_milestone': detect_dynasty_milestone,
    'playoff_loss': detect_playoff_loss,
    'star_injury': detect_star_injury,
    'blockbuster_trade': detect_blockbuster_trade,
    'blown_lead': detect_blown_lead,
    'holdout_public': detect_holdout_public,
    'losing_streak_3': detect_losing_streak_3,
    TIER2_EVENT_RISING_STAR_STREAK: detect_rising_star_streak,
}


def detect_tier2_trigger(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week_number: int,
) -> Tuple[Optional[str], dict]:
    """
    Run detectors in TIER2_TRIGGER_PRIORITY order.

    Checks season cap first. Returns first trigger that fires, or (None, {}).

    Args:
        conn: Database connection
        team_id: Team to check triggers for
        season_year: Current season year
        week_number: Current week number

    Returns:
        Tuple of (trigger_type, context_dict) or (None, {})
    """
    # Check season cap
    if count_tier2_events_this_season(conn, team_id, season_year) >= TIER2_MAX_PER_SEASON:
        return (None, {})

    for trigger_type in TIER2_TRIGGER_PRIORITY:
        detector = _DETECTOR_MAP.get(trigger_type)
        if detector is None:
            continue
        fired, context = detector(conn, team_id, season_year, week_number)
        if fired:
            return (trigger_type, context)

    return (None, {})
