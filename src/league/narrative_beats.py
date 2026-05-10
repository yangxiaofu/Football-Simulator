"""
Narrative beat generation for coach seasons.

Generates 2-3 line season summaries with routine vs dramatic voice.
"""

import sqlite3
import random
from typing import Optional

from ..db.queries import (
    get_team_season_record,
    insert_narrative_beat,
    get_all_active_coaches,
    count_team_championships,
)
from ..utils.constants import NARRATIVE_DRAMATIC_TRIGGERS
from .legacy import evaluate_dynasty_and_hof


# ==============================
# ROUTINE TEMPLATES
# ==============================

ROUTINE_TEMPLATES = [
    "{coach_name}'s {team_abbr} finished {record} in {year}. {biggest_event}. The franchise continues building toward contention.",

    "Another season in the books for {coach_name}. The {team_abbr} went {record}, {biggest_event}. Steady progress in {year}.",

    "{year}: {team_abbr} closes {record} under {coach_name}. {biggest_event}. The front office remains patient with the rebuild.",

    "{coach_name} navigated {team_abbr} to a {record} finish in {year}. {biggest_event}. Work continues in the offseason.",

    "The {team_abbr} posted {record} in {year} as {coach_name} enters Year {tenure_year}. {biggest_event}. Foundation-building continues.",

    "{team_abbr} wraps {year} at {record}. {coach_name}'s {biggest_event}. The organization points toward next season.",

    "{record} for {coach_name}'s {team_abbr} in {year}. {biggest_event}. Incremental progress, with eyes on the draft.",

    "{coach_name} completes Year {tenure_year} with {team_abbr} at {record}. {biggest_event}. The grind continues.",

    "Season {year}: {team_abbr} finishes {record}. {biggest_event} under {coach_name}. A workmanlike campaign.",

    "{year} saw {coach_name}'s {team_abbr} go {record}. {biggest_event}. Decent fundamentals, but no signature moment.",

    "{team_abbr} closes {year} with {record} record. {biggest_event} in {coach_name}'s tenure. Solid, if unspectacular.",

    "{coach_name} steered {team_abbr} to {record} in {year}. {biggest_event}. The arrows point up, but slowly.",
]


# ==============================
# DRAMATIC TEMPLATES
# ==============================

DRAMATIC_TEMPLATES = {
    'championship_won': [
        "{coach_name} hoists the Lombardi Trophy! {team_abbr} defeated {opponent} in the championship, capping a {record} season. {biggest_event}. Dynasty whispers begin.",

        "Champions. {coach_name}'s {team_abbr} are world champions after a {record} run. {biggest_event}. The city erupts. History made in {year}.",

        "{year} belongs to {coach_name}. {team_abbr} wins it all with {record} record, beating {opponent} in the final. {biggest_event}. Immortality.",

        "The Lombardi comes home to {team_abbr}. {coach_name} caps {record} season with championship victory over {opponent}. {biggest_event}. Pure jubilation.",
    ],

    'dynasty_flag_activated': [
        "Dynasty confirmed. {coach_name}'s {team_abbr} secured their third title in the past decade. {record} in {year}. {biggest_event}. Generational greatness.",

        "{coach_name} cements legacy with third championship in 10 years. {team_abbr} finishes {record}. {biggest_event}. This is what dynasty looks like.",

        "Three rings in a decade. {coach_name}'s {team_abbr} reached dynasty status in {year} with {record} campaign. {biggest_event}. Elite company.",

        "{year} marks dynasty era for {coach_name}. Third title in ten years, {record} season. {biggest_event}. Hall of Fame trajectory locked in.",
    ],

    'hof_eligible_first_time': [
        "{coach_name} crosses into Hall of Fame territory. {team_abbr} went {record} in {year}. {biggest_event}. The body of work speaks for itself.",

        "Hall of Fame credentials officially secured. {coach_name}'s {record} campaign in {year} pushed career legacy past the threshold. {biggest_event}. Canton awaits.",

    "{year}: {coach_name} achieves Hall eligibility with {team_abbr} at {record}. {biggest_event}. A career that will be studied for generations.",

        "{coach_name} enters rarified air as Hall metrics hit. {team_abbr} posted {record} in {year}. {biggest_event}. The resume is undeniable.",
    ],

    'narrow_firing_escape': [
        "{coach_name} survives the hot seat after {team_abbr}'s {record} season. {biggest_event}. The leash is short heading into {next_year}.",

        "Job saved, barely. {coach_name}'s {team_abbr} limped to {record} in {year}. {biggest_event}. One more misstep could be the last.",

        "{year} was a white-knuckle ride for {coach_name}. {team_abbr} scraped to {record}. {biggest_event}. Front office granted one more chance.",

        "{coach_name} dodges termination after {record} showing with {team_abbr}. {biggest_event}. {year} was a reprieve, not vindication.",
    ],

    'star_player_developed': [
        "{coach_name} developed a franchise cornerstone in {year}. {team_abbr} went {record}. {biggest_event}. A star is born under this coaching staff.",

        "{year}: {coach_name}'s {team_abbr} posted {record}, but the real story is {star_name}'s emergence. {biggest_event}. Player development clinic.",

        "{coach_name} strikes gold with {star_name}'s breakout season. {team_abbr} at {record}. {biggest_event}. Scouting and coaching synergy at its peak.",

        "{team_abbr} finishes {record} in {year}, highlighted by {star_name} ascending to elite status. {biggest_event}. {coach_name}'s coaching tree grows.",
    ],

    'first_playoff_appearance': [
        "Playoffs. Finally. {coach_name}'s {team_abbr} breaks through with {record} season in {year}. {biggest_event}. The drought ends.",

        "{coach_name} delivers postseason berth for {team_abbr} at {record}. {biggest_event}. {year} marks the turning point.",

        "{year}: {team_abbr} makes playoffs under {coach_name} for the first time. {record} regular season. {biggest_event}. Validation.",

        "{coach_name} ends playoff drought. {team_abbr} punches ticket with {record} campaign. {biggest_event}. {year} will be remembered.",
    ],

    'first_division_title': [
        "Division champions. {coach_name}'s {team_abbr} claims first divisional crown at {record}. {biggest_event}. Banner raised in {year}.",

        "{year}: {coach_name} wins division with {team_abbr} at {record}. {biggest_event}. The foundation was worth it.",

        "{team_abbr} are division champs for the first time under {coach_name}. {record} season. {biggest_event}. Momentum building.",

        "{coach_name} hoists division trophy in {year}. {team_abbr} finishes {record}. {biggest_event}. First of many?",
    ],
}


# ==============================
# DRAMATIC TRIGGER DETECTION
# ==============================

def detect_dramatic_triggers(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> list:
    """Inspect season outcome for dramatic triggers.

    Priority order: dynasty > championship > hof_eligible >
                    star_player > first_division > first_playoff > narrow_firing

    Returns:
        List of trigger names in priority order
    """
    triggers = []

    # Get coach's team
    coach_row = conn.execute("""
        SELECT current_team_id FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach_row or coach_row['current_team_id'] is None:
        return triggers

    team_id = coach_row['current_team_id']
    record = get_team_season_record(conn, team_id, season_year)

    if not record:
        return triggers

    # Dynasty and HOF (from legacy.py)
    legacy_triggers = evaluate_dynasty_and_hof(conn, coach_id, season_year)
    triggers.extend(legacy_triggers)

    # Championship won (check playoff_result)
    if record['playoff_result'] == 'champion':
        # Only add if not already flagged by dynasty
        if 'dynasty_flag_activated' not in triggers:
            triggers.append('championship_won')

    # Star player developed (check attribute_history for big jumps this season)
    star_jumps = conn.execute("""
        SELECT COUNT(*) as cnt FROM player_attribute_history
        WHERE season_year = ? AND change_reason = 'development'
          AND attribute_name = 'true_overall'
          AND (value_after - value_before) >= 15
          AND player_id IN (SELECT id FROM player WHERE team_id = ?)
    """, (season_year, team_id)).fetchone()

    if star_jumps and star_jumps['cnt'] > 0:
        triggers.append('star_player_developed')

    # First division title
    prior_division_wins = conn.execute("""
        SELECT COUNT(*) as cnt FROM team_season_record
        WHERE team_id = ? AND season_year < ?
          AND playoff_result IN ('wildcard', 'divisional', 'conference', 'superbowl_loss', 'champion')
          AND made_playoffs = 1
    """, (team_id, season_year)).fetchone()

    # Check if won division this year (made playoffs and not wildcard)
    if record['made_playoffs'] and record['playoff_result'] != 'wildcard':
        if prior_division_wins and prior_division_wins['cnt'] == 0:
            triggers.append('first_division_title')

    # First playoff appearance
    if record['made_playoffs']:
        prior_playoffs = conn.execute("""
            SELECT COUNT(*) as cnt FROM team_season_record
            WHERE team_id = ? AND season_year < ? AND made_playoffs = 1
        """, (team_id, season_year)).fetchone()

        if prior_playoffs and prior_playoffs['cnt'] == 0:
            triggers.append('first_playoff_appearance')

    # Narrow firing escape (check owner_sentiment)
    sentiment = conn.execute("""
        SELECT hot_seat_tier FROM owner_sentiment
        WHERE team_id = ? AND season_year = ?
    """, (team_id, season_year)).fetchone()

    if sentiment and sentiment['hot_seat_tier'] in ('hot', 'warm'):
        # Coach survived a hot seat
        triggers.append('narrow_firing_escape')

    return triggers


# ==============================
# BIGGEST EVENT IDENTIFICATION
# ==============================

def identify_biggest_event(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> str:
    """Pick most narratively significant event for slot-fill.

    Examples: "broke franchise scoring record at 487 points",
              "fell in divisional round to PIT",
              "extended playoff drought to 5 seasons"

    Returns:
        Event description string
    """
    # Get coach's team
    coach_row = conn.execute("""
        SELECT current_team_id FROM coach_career WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach_row or coach_row['current_team_id'] is None:
        return "wrapped up another offseason"

    team_id = coach_row['current_team_id']
    record = get_team_season_record(conn, team_id, season_year)

    if not record:
        return "managed the roster"

    # Check playoff result
    if record['playoff_result'] == 'champion':
        return f"won the championship"
    elif record['playoff_result'] in ('superbowl_loss', 'conference', 'divisional', 'wildcard'):
        playoff_round = record['playoff_result'].replace('_', ' ')
        return f"reached the {playoff_round}"
    elif record['made_playoffs']:
        return "made the playoffs"

    # Check win record milestones
    if record['wins'] >= 12:
        return f"dominated the regular season with {record['wins']} wins"
    elif record['wins'] <= 4:
        return f"struggled to {record['wins']}-{record['losses']} record"

    # Check points differential
    point_diff = record['points_for'] - record['points_against']
    if point_diff > 100:
        return f"outscored opponents by {point_diff} points"
    elif point_diff < -100:
        return f"was outscored by {abs(point_diff)} points"

    # Default
    return f"finished with {record['wins']}-{record['losses']} record"


# ==============================
# BEAT GENERATION
# ==============================

def generate_narrative_beat(
    conn: sqlite3.Connection,
    coach_id: int,
    season_year: int,
) -> dict:
    """Generate one beat for a coach's season.

    Process:
    1. Detect dramatic triggers
    2. If any fire, pick highest-priority dramatic template
    3. Else use routine template
    4. Slot-fill with season facts
    5. Write coach_narrative_beat row
    6. Return {'beat_type', 'text'}

    Returns:
        Dict with 'beat_type' and 'text'
    """
    # Get coach info
    coach = conn.execute("""
        SELECT first_name, last_name, current_team_id FROM coach_career
        WHERE id = ?
    """, (coach_id,)).fetchone()

    if not coach:
        return {'beat_type': 'routine', 'text': 'Season complete.'}

    coach_name = f"{coach['first_name']} {coach['last_name']}"
    team_id = coach['current_team_id']

    # Get team info
    if team_id is None:
        team_abbr = "UNEMPLOYED"
        record_str = "0-0"
    else:
        team = conn.execute("SELECT abbreviation FROM team WHERE id = ?", (team_id,)).fetchone()
        team_abbr = team['abbreviation'] if team else "???"

        record = get_team_season_record(conn, team_id, season_year)
        if record:
            record_str = f"{record['wins']}-{record['losses']}"
            if record['ties'] > 0:
                record_str += f"-{record['ties']}"
        else:
            record_str = "0-0"

    # Get tenure year
    tenure = conn.execute("""
        SELECT start_year FROM coach_tenure
        WHERE coach_id = ? AND end_year IS NULL
    """, (coach_id,)).fetchone()

    tenure_year = (season_year - tenure['start_year'] + 1) if tenure else 1

    # Detect triggers
    triggers = detect_dramatic_triggers(conn, coach_id, season_year)

    # Pick template
    if triggers:
        # Use highest-priority trigger
        # Priority order encoded in NARRATIVE_DRAMATIC_TRIGGERS
        for priority_trigger in NARRATIVE_DRAMATIC_TRIGGERS:
            if priority_trigger in triggers:
                beat_type = 'dramatic'
                template = random.choice(DRAMATIC_TEMPLATES[priority_trigger])
                break
        else:
            # Fallback if trigger not in template dict
            beat_type = 'routine'
            template = random.choice(ROUTINE_TEMPLATES)
    else:
        beat_type = 'routine'
        template = random.choice(ROUTINE_TEMPLATES)

    # Identify biggest event
    biggest_event = identify_biggest_event(conn, coach_id, season_year)

    # Slot-fill template
    # Get opponent for championship (if applicable)
    opponent = "the opposition"  # Default
    if 'championship_won' in triggers and team_id is not None:
        # Find Super Bowl game
        sb_game = conn.execute("""
            SELECT home_team_id, away_team_id, home_score, away_score
            FROM game g
            JOIN week w ON g.week_id = w.id
            JOIN season s ON w.season_id = s.id
            WHERE s.year = ? AND w.week_type = 'superbowl'
              AND (g.home_team_id = ? OR g.away_team_id = ?)
        """, (season_year, team_id, team_id)).fetchone()

        if sb_game:
            opp_id = sb_game['away_team_id'] if sb_game['home_team_id'] == team_id else sb_game['home_team_id']
            opp_team = conn.execute("SELECT abbreviation FROM team WHERE id = ?", (opp_id,)).fetchone()
            if opp_team:
                opponent = opp_team['abbreviation']

    # Get star name for star_player_developed
    star_name = "a key player"
    if 'star_player_developed' in triggers and team_id is not None:
        star_row = conn.execute("""
            SELECT p.first_name, p.last_name
            FROM player_attribute_history pah
            JOIN player p ON pah.player_id = p.id
            WHERE pah.season_year = ? AND pah.change_reason = 'development'
              AND pah.attribute_name = 'true_overall'
              AND (pah.value_after - pah.value_before) >= 15
              AND p.team_id = ?
            LIMIT 1
        """, (season_year, team_id)).fetchone()

        if star_row:
            star_name = f"{star_row['first_name']} {star_row['last_name']}"

    next_year = season_year + 1

    # Slot substitution
    text = template.format(
        coach_name=coach_name,
        team_abbr=team_abbr,
        record=record_str,
        year=season_year,
        biggest_event=biggest_event,
        tenure_year=tenure_year,
        opponent=opponent,
        star_name=star_name,
        next_year=next_year,
    )

    # Write to database
    insert_narrative_beat(conn, coach_id, season_year, beat_type, text)

    return {'beat_type': beat_type, 'text': text}


def generate_all_narrative_beats(
    conn: sqlite3.Connection,
    season_year: int,
) -> dict:
    """Run for every active coach.

    Returns:
        Dict mapping coach_id → beat dict
    """
    coaches = get_all_active_coaches(conn)
    results = {}

    for coach in coaches:
        beat = generate_narrative_beat(conn, coach['id'], season_year)
        results[coach['id']] = beat

    return results
