"""
Standings calculator with NFL tiebreaker logic.

Computes win/loss records from completed games and applies tiebreakers
for division rankings, wildcard seeding, and draft order.
"""

import sqlite3

from ..db.queries import (
    get_completed_games_for_team,
    get_division_teams,
    get_conference_divisions,
    get_conferences,
    get_head_to_head_record,
    get_division_record,
    get_conference_record,
    upsert_team_season_record,
)


def calculate_team_record(
    conn: sqlite3.Connection, team_id: int, season_year: int,
) -> dict:
    """Calculate a team's record from completed games.

    Returns dict with:
        team_id, wins, losses, ties, points_for, points_against, point_diff
    """
    games = get_completed_games_for_team(conn, team_id, season_year)

    wins = losses = ties = points_for = points_against = 0
    for g in games:
        if g['home_team_id'] == team_id:
            my_score = g['home_score']
            opp_score = g['away_score']
        else:
            my_score = g['away_score']
            opp_score = g['home_score']

        points_for += my_score
        points_against += opp_score

        if my_score > opp_score:
            wins += 1
        elif my_score < opp_score:
            losses += 1
        else:
            ties += 1

    return {
        'team_id': team_id,
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'points_for': points_for,
        'points_against': points_against,
        'point_diff': points_for - points_against,
        'games_played': wins + losses + ties,
    }


def _win_pct(record: dict) -> float:
    """Calculate win percentage (ties count as half a win)."""
    games = record['wins'] + record['losses'] + record['ties']
    if games == 0:
        return 0.0
    return (record['wins'] + record['ties'] * 0.5) / games


def update_all_standings(
    conn: sqlite3.Connection, season_year: int,
) -> list[dict]:
    """Recalculate and persist standings for all 32 teams.

    Returns list of all team records (sorted by win%).
    """
    from ..db.queries import get_all_teams
    teams = get_all_teams(conn)
    records = []

    for team in teams:
        rec = calculate_team_record(conn, team['id'], season_year)
        upsert_team_season_record(
            conn, team['id'], season_year,
            rec['wins'], rec['losses'], rec['ties'],
            rec['points_for'], rec['points_against'],
        )
        records.append(rec)

    records.sort(key=lambda r: _win_pct(r), reverse=True)
    return records


def _tiebreak_sort_key(
    team_record: dict,
    conn: sqlite3.Connection,
    season_year: int,
    opponent_ids: list[int],
) -> tuple:
    """Generate a sort key tuple for tiebreaking.

    NFL tiebreaker order:
    1. Head-to-head record (among tied teams)
    2. Division record
    3. Conference record
    4. Point differential
    5. Points scored
    """
    tid = team_record['team_id']

    # Head-to-head against the other tied teams
    h2h_wins = 0
    h2h_losses = 0
    for opp_id in opponent_ids:
        if opp_id == tid:
            continue
        h2h = get_head_to_head_record(conn, tid, opp_id, season_year)
        h2h_wins += h2h['wins']
        h2h_losses += h2h['losses']
    h2h_pct = h2h_wins / max(1, h2h_wins + h2h_losses)

    # Division record
    div_rec = get_division_record(conn, tid, season_year)
    div_pct = div_rec['wins'] / max(1, div_rec['wins'] + div_rec['losses'] + div_rec['ties'])

    # Conference record
    conf_rec = get_conference_record(conn, tid, season_year)
    conf_pct = conf_rec['wins'] / max(1, conf_rec['wins'] + conf_rec['losses'] + conf_rec['ties'])

    return (
        _win_pct(team_record),
        h2h_pct,
        div_pct,
        conf_pct,
        team_record['point_diff'],
        team_record['points_for'],
    )


def rank_teams(
    conn: sqlite3.Connection,
    team_ids: list[int],
    season_year: int,
) -> list[dict]:
    """Rank a list of teams using tiebreakers. Returns sorted list of records."""
    records = []
    for tid in team_ids:
        rec = calculate_team_record(conn, tid, season_year)
        records.append(rec)

    all_ids = [r['team_id'] for r in records]

    records.sort(
        key=lambda r: _tiebreak_sort_key(r, conn, season_year, all_ids),
        reverse=True,
    )
    return records


def get_division_standings(
    conn: sqlite3.Connection, division_id: int, season_year: int,
) -> list[dict]:
    """Get sorted standings for a division."""
    teams = get_division_teams(conn, division_id)
    team_ids = [t['id'] for t in teams]
    return rank_teams(conn, team_ids, season_year)


def get_conference_standings(
    conn: sqlite3.Connection, conference_id: int, season_year: int,
) -> list[dict]:
    """Get sorted standings for a conference (all divisions)."""
    divisions = get_conference_divisions(conn, conference_id)
    team_ids = []
    for d in divisions:
        teams = get_division_teams(conn, d['id'])
        team_ids.extend(t['id'] for t in teams)
    return rank_teams(conn, team_ids, season_year)


def get_division_winner(
    conn: sqlite3.Connection, division_id: int, season_year: int,
) -> int:
    """Return team_id of the division winner."""
    standings = get_division_standings(conn, division_id, season_year)
    return standings[0]['team_id'] if standings else None


def get_playoff_seeds(
    conn: sqlite3.Connection, conference_id: int, season_year: int,
) -> list[dict]:
    """Get 7 playoff teams for a conference, properly seeded.

    Seeds 1-4: Division winners (sorted by record + tiebreakers).
    Seeds 5-7: Best remaining teams (wildcards).

    Returns list of dicts: [{'seed': 1, 'team_id': ..., 'record': ...}, ...]
    """
    divisions = get_conference_divisions(conn, conference_id)

    # Get division winners
    div_winners = []
    for d in divisions:
        winner_id = get_division_winner(conn, d['id'], season_year)
        if winner_id:
            rec = calculate_team_record(conn, winner_id, season_year)
            div_winners.append(rec)

    # Rank division winners
    winner_ids = [r['team_id'] for r in div_winners]
    div_winners = rank_teams(conn, winner_ids, season_year)

    # Get all conference teams not among division winners
    all_conf_teams = []
    for d in divisions:
        teams = get_division_teams(conn, d['id'])
        for t in teams:
            if t['id'] not in winner_ids:
                all_conf_teams.append(t['id'])

    # Rank wildcards
    wildcards = rank_teams(conn, all_conf_teams, season_year)

    # Assemble seeds
    seeds = []
    for i, rec in enumerate(div_winners[:4]):
        seeds.append({'seed': i + 1, 'team_id': rec['team_id'], 'record': rec})

    for i, rec in enumerate(wildcards[:3]):
        seeds.append({'seed': 5 + i, 'team_id': rec['team_id'], 'record': rec})

    return seeds


def get_draft_order(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """Get draft order (reverse of final standings, non-playoff teams first).

    Returns list of team_ids from pick 1 (worst team) to pick 32 (champion).
    """
    conferences = get_conferences(conn)
    playoff_teams = set()

    for conf in conferences:
        seeds = get_playoff_seeds(conn, conf['id'], season_year)
        for s in seeds:
            playoff_teams.add(s['team_id'])

    from ..db.queries import get_all_teams
    teams = get_all_teams(conn)

    non_playoff = []
    playoff_list = []

    for t in teams:
        rec = calculate_team_record(conn, t['id'], season_year)
        if t['id'] in playoff_teams:
            playoff_list.append(rec)
        else:
            non_playoff.append(rec)

    # Sort non-playoff teams: worst record first
    non_playoff.sort(key=lambda r: (_win_pct(r), r['point_diff'], r['points_for']))

    # Sort playoff teams: worst record first (among playoff teams)
    playoff_list.sort(key=lambda r: (_win_pct(r), r['point_diff'], r['points_for']))

    draft_order = [r['team_id'] for r in non_playoff] + [r['team_id'] for r in playoff_list]
    return draft_order
