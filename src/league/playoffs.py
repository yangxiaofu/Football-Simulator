"""
Playoff bracket generation, seeding, and simulation.

Generates playoff games (weeks 18-21), simulates rounds,
advances winners, and crowns a champion.
"""

import sqlite3

from ..db.queries import (
    get_league_state,
    update_league_state,
    get_season,
    get_week,
    insert_week,
    insert_game,
    mark_week_complete,
    get_all_games_for_week,
    set_season_champion,
    set_team_playoff_result,
    get_conferences,
    get_team,
    reset_weekly_stamina,
    heal_injured_players,
    get_team_conference_id,
)
from ..utils.constants import (
    PLAYOFF_WEEK_NUMBERS,
    WILDCARD_MATCHUP_PAIRS,
    PLAYOFF_SEED_FALLBACK,
)
from .standings import get_playoff_seeds


def generate_playoff_bracket(
    conn: sqlite3.Connection, season_year: int,
) -> dict:
    """Generate the wildcard round of playoff games.

    Creates week 18 (wildcard) with 6 games (3 per conference).
    The #1 seed in each conference gets a bye.

    Returns dict with seeding info and game IDs created.
    """
    season = get_season(conn, season_year)
    if not season:
        raise RuntimeError(f"Season {season_year} not found")

    conferences = get_conferences(conn)
    all_seeds = {}

    for conf in conferences:
        seeds = get_playoff_seeds(conn, conf['id'], season_year)
        all_seeds[conf['name']] = seeds

        # Mark all playoff teams
        for s in seeds:
            set_team_playoff_result(
                conn, s['team_id'], season_year, 'wildcard', made_playoffs=1,
            )

    # Create wildcard week (18)
    wc_week_id = insert_week(
        conn, season['id'], PLAYOFF_WEEK_NUMBERS['wildcard'], 'wildcard',
    )

    # Generate wildcard matchups: #2 vs #7, #3 vs #6, #4 vs #5
    # Higher seed is home team
    game_ids = []
    matchup_pairs = WILDCARD_MATCHUP_PAIRS

    for conf_name, seeds in all_seeds.items():
        seed_map = {s['seed']: s['team_id'] for s in seeds}
        for high_seed, low_seed in matchup_pairs:
            home_id = seed_map[high_seed]
            away_id = seed_map[low_seed]
            gid = insert_game(conn, wc_week_id, home_id, away_id)
            game_ids.append(gid)

    return {
        'seeds': all_seeds,
        'wildcard_week_id': wc_week_id,
        'wildcard_game_ids': game_ids,
    }


def simulate_playoff_round(
    conn: sqlite3.Connection,
    save_path: str,
    round_name: str,
    season_year: int,
) -> list[dict]:
    """Simulate all games in a playoff round.

    Args:
        conn: Database connection
        save_path: Path to .db file
        round_name: One of 'wildcard', 'divisional', 'conference', 'superbowl'
        season_year: Season year

    Returns:
        List of game results
    """
    from ..engine.game_sim import simulate_game

    week_number = PLAYOFF_WEEK_NUMBERS[round_name]
    games = get_all_games_for_week(conn, season_year, week_number)

    results = []
    for game in games:
        if game['is_complete']:
            continue
        result = simulate_game(save_path, game['id'], verbose=False)
        results.append(result)

    with conn:
        mark_week_complete(
            conn,
            get_week(conn, season_year, week_number)['id'],
        )

        # Aggregate weekly stats (Phase 5) - playoffs use is_playoff=True
        from ..league.weekly_stats import aggregate_week_stats
        aggregate_week_stats(conn, season_year, week_number, is_playoff=True)

        # Select Stars of the Week (Phase 5 Prompt #4)
        from ..league.stars_selection import select_stars_for_week
        stars_summary = select_stars_for_week(conn, season_year, week_number, is_playoff=True)
        print()
        print(f"Stars of the Week — {round_name} (Week {week_number}):")
        for cat in ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'USER_TEAM_MVP'):
            star = stars_summary.get(cat.lower())
            if star is None:
                if cat == 'SPECIAL_TEAMS':
                    print(f"  {cat}: (no qualifier — threshold not met)")
            else:
                print(f"  {cat}: {star['player_name']} ({star['team_abbr']}, {star['position']})")
                blurb = star.get('narrative_blurb', '')
                if blurb:
                    print(f"    {blurb}")

        heal_injured_players(conn)
        reset_weekly_stamina(conn)

    return results


def _get_round_winners(
    conn: sqlite3.Connection, season_year: int, round_name: str,
) -> list[int]:
    """Get winning team IDs from a completed playoff round."""
    week_number = PLAYOFF_WEEK_NUMBERS[round_name]
    games = get_all_games_for_week(conn, season_year, week_number)

    winners = []
    for g in games:
        if not g['is_complete']:
            continue
        if g['home_score'] > g['away_score']:
            winners.append(g['home_team_id'])
        elif g['away_score'] > g['home_score']:
            winners.append(g['away_team_id'])
        else:
            # Playoff games can't tie; home team wins in OT edge case
            winners.append(g['home_team_id'])

    return winners


def _get_team_conference(conn: sqlite3.Connection, team_id: int) -> int:
    """Get the conference_id for a team."""
    return get_team_conference_id(conn, team_id)


def _get_team_seed(
    conn: sqlite3.Connection, team_id: int, season_year: int, conference_id: int,
) -> int:
    """Get the playoff seed for a team. Uses the stored seeding."""
    seeds = get_playoff_seeds(conn, conference_id, season_year)
    for s in seeds:
        if s['team_id'] == team_id:
            return s['seed']
    return PLAYOFF_SEED_FALLBACK


def advance_to_divisional(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """Create divisional round games from wildcard winners + bye teams.

    Returns list of game IDs created.
    """
    season = get_season(conn, season_year)
    conferences = get_conferences(conn)

    # Get wildcard winners
    wc_winners = _get_round_winners(conn, season_year, 'wildcard')

    # Update playoff results for losers
    wc_week = PLAYOFF_WEEK_NUMBERS['wildcard']
    wc_games = get_all_games_for_week(conn, season_year, wc_week)
    for g in wc_games:
        if not g['is_complete']:
            continue
        loser_id = g['away_team_id'] if g['home_score'] > g['away_score'] else g['home_team_id']
        set_team_playoff_result(conn, loser_id, season_year, 'wildcard')

    # Create divisional week (19)
    div_week_id = insert_week(
        conn, season['id'], PLAYOFF_WEEK_NUMBERS['divisional'], 'divisional',
    )

    game_ids = []

    for conf in conferences:
        seeds = get_playoff_seeds(conn, conf['id'], season_year)
        seed_map = {s['seed']: s['team_id'] for s in seeds}

        # #1 seed (bye team) plays lowest remaining seed
        # Remaining seeds from wildcard winners in this conference
        conf_winners = []
        for tid in wc_winners:
            if _get_team_conference(conn, tid) == conf['id']:
                seed_num = _get_team_seed(conn, tid, season_year, conf['id'])
                conf_winners.append((seed_num, tid))

        # Sort by seed (highest seed number = lowest seed)
        conf_winners.sort(key=lambda x: x[0], reverse=True)

        # #1 plays lowest remaining, #2-winner/other plays highest remaining
        bye_team = seed_map[1]

        if len(conf_winners) >= 3:
            # #1 vs lowest remaining seed (highest number)
            gid1 = insert_game(conn, div_week_id, bye_team, conf_winners[0][1])
            # Remaining two play each other (higher seed hosts)
            if conf_winners[1][0] < conf_winners[2][0]:
                gid2 = insert_game(conn, div_week_id, conf_winners[1][1], conf_winners[2][1])
            else:
                gid2 = insert_game(conn, div_week_id, conf_winners[2][1], conf_winners[1][1])
            game_ids.extend([gid1, gid2])
        elif len(conf_winners) == 2:
            gid1 = insert_game(conn, div_week_id, bye_team, conf_winners[0][1])
            gid2 = insert_game(conn, div_week_id, conf_winners[1][1], conf_winners[0][1])
            game_ids.extend([gid1, gid2])

    return game_ids


def advance_to_conference(
    conn: sqlite3.Connection, season_year: int,
) -> list[int]:
    """Create conference championship games from divisional winners."""
    season = get_season(conn, season_year)
    conferences = get_conferences(conn)

    div_winners = _get_round_winners(conn, season_year, 'divisional')

    # Mark divisional losers
    div_week = PLAYOFF_WEEK_NUMBERS['divisional']
    div_games = get_all_games_for_week(conn, season_year, div_week)
    for g in div_games:
        if not g['is_complete']:
            continue
        loser_id = g['away_team_id'] if g['home_score'] > g['away_score'] else g['home_team_id']
        set_team_playoff_result(conn, loser_id, season_year, 'divisional')

    # Create conference championship week (20)
    conf_week_id = insert_week(
        conn, season['id'], PLAYOFF_WEEK_NUMBERS['conference'], 'conference',
    )

    game_ids = []
    for conf in conferences:
        conf_winners = []
        for tid in div_winners:
            if _get_team_conference(conn, tid) == conf['id']:
                seed_num = _get_team_seed(conn, tid, season_year, conf['id'])
                conf_winners.append((seed_num, tid))

        conf_winners.sort(key=lambda x: x[0])  # Lower seed = higher rank

        if len(conf_winners) >= 2:
            # Higher seed (lower number) hosts
            gid = insert_game(conn, conf_week_id, conf_winners[0][1], conf_winners[1][1])
            game_ids.append(gid)

    return game_ids


def advance_to_superbowl(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Create the Super Bowl game from conference championship winners."""
    season = get_season(conn, season_year)

    conf_winners = _get_round_winners(conn, season_year, 'conference')

    # Mark conference losers
    conf_week = PLAYOFF_WEEK_NUMBERS['conference']
    conf_games = get_all_games_for_week(conn, season_year, conf_week)
    for g in conf_games:
        if not g['is_complete']:
            continue
        loser_id = g['away_team_id'] if g['home_score'] > g['away_score'] else g['home_team_id']
        set_team_playoff_result(conn, loser_id, season_year, 'conference')

    # Create Super Bowl week (21)
    sb_week_id = insert_week(
        conn, season['id'], PLAYOFF_WEEK_NUMBERS['superbowl'], 'superbowl',
    )

    if len(conf_winners) >= 2:
        # Alternate home team (simplified: first winner is home)
        gid = insert_game(conn, sb_week_id, conf_winners[0], conf_winners[1])
        return gid

    return None


def crown_champion(
    conn: sqlite3.Connection, season_year: int,
) -> int:
    """Determine and record the Super Bowl winner.

    Returns the champion team_id.
    """
    from .historical_records import update_champion_history, determine_championship_mvp

    sb_winners = _get_round_winners(conn, season_year, 'superbowl')
    if not sb_winners:
        raise RuntimeError("No Super Bowl winner found")

    champion_id = sb_winners[0]

    # Set champion
    set_season_champion(conn, season_year, champion_id)
    set_team_playoff_result(conn, champion_id, season_year, 'champion')

    # Set Super Bowl loser and capture championship details (Phase 4 Prompt #8)
    sb_week = PLAYOFF_WEEK_NUMBERS['superbowl']
    sb_games = get_all_games_for_week(conn, season_year, sb_week)
    for g in sb_games:
        if not g['is_complete']:
            continue
        loser_id = g['away_team_id'] if g['home_team_id'] == champion_id else g['home_team_id']
        set_team_playoff_result(conn, loser_id, season_year, 'superbowl_loss')

        # Capture championship details
        sb_game_id = g['id']
        home_score = g['home_score']
        away_score = g['away_score']
        mvp_player_id = determine_championship_mvp(conn, sb_game_id)

        # Get coach of champion team
        coach_row = conn.execute("""
            SELECT id FROM coach_career
            WHERE current_team_id = ? AND is_active = 1
        """, (champion_id,)).fetchone()
        coach_id = coach_row['id'] if coach_row else None

        # Update championship history
        update_champion_history(
            conn, season_year,
            champion_team_id=champion_id,
            runner_up_team_id=loser_id,
            home_score=home_score,
            away_score=away_score,
            mvp_player_id=mvp_player_id,
            coach_id=coach_id,
        )

    return champion_id


def run_full_playoffs(
    conn: sqlite3.Connection, save_path: str, season_year: int,
) -> int:
    """Run the complete playoff bracket from wildcard to Super Bowl.

    Returns the champion team_id.
    """
    league = get_league_state(conn)

    # Generate bracket
    with conn:
        bracket = generate_playoff_bracket(conn, season_year)

    # Wildcard round
    print("  Wildcard Round...")
    simulate_playoff_round(conn, save_path, 'wildcard', season_year)
    _print_round_results(conn, season_year, 'wildcard')

    # Advance to divisional
    with conn:
        advance_to_divisional(conn, season_year)
        update_league_state(conn, season_year, PLAYOFF_WEEK_NUMBERS['divisional'], 'playoffs')

    # Divisional round
    print("  Divisional Round...")
    simulate_playoff_round(conn, save_path, 'divisional', season_year)
    _print_round_results(conn, season_year, 'divisional')

    # Advance to conference
    with conn:
        advance_to_conference(conn, season_year)
        update_league_state(conn, season_year, PLAYOFF_WEEK_NUMBERS['conference'], 'playoffs')

    # Conference championships
    print("  Conference Championships...")
    simulate_playoff_round(conn, save_path, 'conference', season_year)
    _print_round_results(conn, season_year, 'conference')

    # Advance to Super Bowl
    with conn:
        advance_to_superbowl(conn, season_year)
        update_league_state(conn, season_year, PLAYOFF_WEEK_NUMBERS['superbowl'], 'playoffs')

    # Super Bowl
    print("  Super Bowl...")
    simulate_playoff_round(conn, save_path, 'superbowl', season_year)
    _print_round_results(conn, season_year, 'superbowl')

    # Crown champion
    with conn:
        champion_id = crown_champion(conn, season_year)

    champ = get_team(conn, champion_id)
    print(f"\n  Champion: {champ['city']} {champ['nickname']}!")

    return champion_id


def _print_round_results(
    conn: sqlite3.Connection, season_year: int, round_name: str,
) -> None:
    """Print results for a playoff round."""
    week_number = PLAYOFF_WEEK_NUMBERS[round_name]
    games = get_all_games_for_week(conn, season_year, week_number)

    for g in games:
        if not g['is_complete']:
            continue
        home = get_team(conn, g['home_team_id'])
        away = get_team(conn, g['away_team_id'])
        print(f"    {away['abbreviation']} {g['away_score']} "
              f"@ {home['abbreviation']} {g['home_score']}")
