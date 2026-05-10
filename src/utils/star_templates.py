"""Narrative templates for Stars of the Week (Phase 5 Prompt #4).

Each template is a dict with:
  id       — unique identifier
  context  — short description for debugging/logging
  match    — lambda(row: dict) -> bool; first True match wins
  template — string with {TOKEN} placeholders

Tokens available (all pre-computed in the candidate row dict):
  {NAME}, {OPP}, {SCORE_DIFF}, {PASS_YARDS}, {PASS_TDS}, {CARRIES},
  {RUSH_YARDS}, {RUSH_TDS}, {REC_YARDS}, {REC_TDS}, {RECEPTIONS},
  {TACKLES}, {SACKS}, {INTS}, {FG_MADE}, {FG_LONG}, {PUNT_YARDS},
  {RETURN_YARDS}, {RETURN_TDS}, {USER_TEAM_NAME}

Selection: iterate list top-to-bottom, use first matching template.
The last entry in each list is a catch-all fallback (match always True).
"""

STAR_TEMPLATES_OFFENSE = [
    {
        'id': 'off_qb_dominant_passer',
        'context': 'QB with 3+ TDs in a win',
        'match': lambda r: r['position'] == 'QB' and r.get('pass_tds', 0) >= 3 and r.get('won'),
        'template': "{NAME} took command against {OPP}, throwing for {PASS_YARDS} yards and {PASS_TDS} touchdowns to power a {SCORE_DIFF}-point victory.",
    },
    {
        'id': 'off_qb_300_yards',
        'context': 'QB with 300+ pass yards',
        'match': lambda r: r['position'] == 'QB' and r.get('pass_yards', 0) >= 300,
        'template': "{NAME} shredded the {OPP} secondary for {PASS_YARDS} passing yards and {PASS_TDS} scores in a performance that kept the scoreboard busy all afternoon.",
    },
    {
        'id': 'off_qb_comeback',
        'context': 'QB who won a close game (diff <= 7)',
        'match': lambda r: r['position'] == 'QB' and r.get('won') and r.get('score_diff', 99) <= 7,
        'template': "{NAME} delivered when it mattered most, engineering a {SCORE_DIFF}-point win over {OPP} with {PASS_YARDS} passing yards and {PASS_TDS} touchdowns.",
    },
    {
        'id': 'off_rb_100_rush',
        'context': 'RB with 100+ rushing yards',
        'match': lambda r: r['position'] == 'RB' and r.get('rush_yards', 0) >= 100,
        'template': "{NAME} put the ground game on his back, grinding out {RUSH_YARDS} rushing yards and {RUSH_TDS} touchdowns on {CARRIES} carries against {OPP}.",
    },
    {
        'id': 'off_rb_multi_td',
        'context': 'RB with 2+ TDs',
        'match': lambda r: r['position'] == 'RB' and (r.get('rush_tds', 0) + r.get('rec_tds', 0)) >= 2,
        'template': "{NAME} found the end zone {RUSH_TDS} times rushing and added {REC_YARDS} receiving yards as {OPP} had no answer for the workhorse back.",
    },
    {
        'id': 'off_wr_100_rec',
        'context': 'WR/TE with 100+ receiving yards',
        'match': lambda r: r['position'] in ('WR', 'TE') and r.get('rec_yards', 0) >= 100,
        'template': "{NAME} was the top target all game, hauling in {RECEPTIONS} receptions for {REC_YARDS} yards and {REC_TDS} touchdowns to torch the {OPP} secondary.",
    },
    {
        'id': 'off_wr_td_win',
        'context': 'WR/TE with TD in a win',
        'match': lambda r: r['position'] in ('WR', 'TE') and r.get('rec_tds', 0) >= 1 and r.get('won'),
        'template': "{NAME} came up huge in the win over {OPP} with {REC_YARDS} receiving yards and {REC_TDS} touchdowns on {RECEPTIONS} catches.",
    },
    {
        'id': 'off_rb_receiving',
        'context': 'RB with receiving contribution',
        'match': lambda r: r['position'] == 'RB' and r.get('rec_yards', 0) >= 40,
        'template': "{NAME} was a weapon both on the ground and through the air against {OPP}, totaling {RUSH_YARDS} rushing and {REC_YARDS} receiving yards.",
    },
    {
        'id': 'off_blowout',
        'context': 'Any offensive player in a blowout win (diff >= 21)',
        'match': lambda r: r['position'] in ('QB', 'RB', 'WR', 'TE') and r.get('won') and r.get('score_diff', 0) >= 21,
        'template': "{NAME} was a driving force in the {SCORE_DIFF}-point rout of {OPP}, setting the tone with a performance the scoreboard reflected from start to finish.",
    },
    {
        'id': 'off_generic',
        'context': 'fallback',
        'match': lambda r: True,
        'template': "{NAME} led the offensive attack against {OPP}, standing out in a week of strong performances across the league.",
    },
]

STAR_TEMPLATES_DEFENSE = [
    {
        'id': 'def_sack_monster',
        'context': 'DL/LB with 2+ sacks',
        'match': lambda r: r['position'] in ('DL', 'LB') and r.get('sacks', 0) >= 2,
        'template': "{NAME} was a one-man wrecking crew against {OPP}, recording {SACKS} sacks and wreaking havoc in the backfield all afternoon.",
    },
    {
        'id': 'def_int_return',
        'context': 'DB with interception(s)',
        'match': lambda r: r['position'] in ('CB', 'S') and r.get('interceptions', 0) >= 1,
        'template': "{NAME} turned the tide against {OPP} with {INTS} interception(s), giving the defense the ball — and the momentum — back.",
    },
    {
        'id': 'def_tackle_leader',
        'context': 'Any defender with 15+ tackles',
        'match': lambda r: r['position'] in ('DL', 'LB', 'CB', 'S') and r.get('tackles', 0) >= 15,
        'template': "{NAME} was everywhere on the field against {OPP}, racking up {TACKLES} tackles in a performance that made the stat sheet look like a solo effort.",
    },
    {
        'id': 'def_forced_fumble',
        'context': 'Defender with forced fumble',
        'match': lambda r: r['position'] in ('DL', 'LB', 'CB', 'S') and r.get('forced_fumbles', 0) >= 1,
        'template': "{NAME} changed the game with a forced fumble against {OPP}, disrupting the offense at a critical moment and swinging the momentum.",
    },
    {
        'id': 'def_lb_sack',
        'context': 'LB with a sack',
        'match': lambda r: r['position'] == 'LB' and r.get('sacks', 0) >= 1,
        'template': "{NAME} brought relentless pressure against {OPP}, finishing with {SACKS} sack(s) and {TACKLES} tackles in a dominant defensive showing.",
    },
    {
        'id': 'def_cb_shutdown',
        'context': 'CB in a win',
        'match': lambda r: r['position'] == 'CB' and r.get('won'),
        'template': "{NAME} locked down his side of the field against {OPP}, contributing {TACKLES} tackles as the defense held firm in a {SCORE_DIFF}-point victory.",
    },
    {
        'id': 'def_dl_pressure',
        'context': 'DL with a sack',
        'match': lambda r: r['position'] == 'DL' and r.get('sacks', 0) >= 1,
        'template': "{NAME} applied relentless pressure off the line against {OPP}, recording {SACKS} sack(s) and {TACKLES} tackles to anchor the defensive front.",
    },
    {
        'id': 'def_s_big_game',
        'context': 'Safety with high tackle total',
        'match': lambda r: r['position'] == 'S' and r.get('tackles', 0) >= 10,
        'template': "{NAME} roamed the secondary against {OPP} like he owned the field, posting {TACKLES} tackles and {INTS} interception(s) in a complete safety performance.",
    },
    {
        'id': 'def_shutout_contributor',
        'context': 'Defender in a shutout or near-shutout win (score_diff >= 17 win)',
        'match': lambda r: r['position'] in ('DL', 'LB', 'CB', 'S') and r.get('won') and r.get('score_diff', 0) >= 17,
        'template': "{NAME} was central to one of the defense's best games, helping smother {OPP} in a {SCORE_DIFF}-point victory with {TACKLES} tackles on the day.",
    },
    {
        'id': 'def_generic',
        'context': 'fallback',
        'match': lambda r: True,
        'template': "{NAME} stood out on the defensive side of the ball against {OPP}, delivering the kind of performance that changes the complexion of a game.",
    },
]

STAR_TEMPLATES_SPECIAL_TEAMS = [
    {
        'id': 'st_return_td',
        'context': 'Any player with a return TD',
        'match': lambda r: r.get('return_tds', 0) >= 1,
        'template': "{NAME} ignited the crowd and the scoreboard with a {RETURN_TDS} return touchdown(s) against {OPP}, turning special teams into a game-changing weapon.",
    },
    {
        'id': 'st_50plus_fg',
        'context': 'Kicker who made a 50+ yard FG',
        'match': lambda r: r['position'] == 'K' and r.get('fg_long', 0) >= 50,
        'template': "{NAME} was automatic against {OPP}, nailing a long of {FG_LONG} yards among {FG_MADE} field goals in a performance that had scouts and coaches nodding.",
    },
    {
        'id': 'st_perfect_kicker',
        'context': 'Kicker perfect on FGs (2+ made, none missed)',
        'match': lambda r: r['position'] == 'K' and r.get('fg_made', 0) >= 2 and r.get('fg_made', 0) == r.get('fg_attempts', 0),
        'template': "{NAME} kept pace with {OPP} in a tight game, going a perfect {FG_MADE}-for-{FG_MADE} on field goals with a long of {FG_LONG} yards.",
    },
    {
        'id': 'st_punter_big_game',
        'context': 'Punter with 400+ punt yards',
        'match': lambda r: r['position'] == 'P' and r.get('punt_yards', 0) >= 400,
        'template': "{NAME} flipped field position all afternoon against {OPP}, booting {PUNT_YARDS} total punt yards and forcing the opposition to start deep repeatedly.",
    },
    {
        'id': 'st_punter_solid',
        'context': 'Punter with a solid game',
        'match': lambda r: r['position'] == 'P' and r.get('punt_yards', 0) >= 250,
        'template': "{NAME} was the unsung hero against {OPP}, consistently pinning the offense deep with {PUNT_YARDS} punt yards and keeping field position in favor all game.",
    },
    {
        'id': 'st_generic',
        'context': 'fallback',
        'match': lambda r: True,
        'template': "{NAME} made the most of special teams opportunities against {OPP}, delivering a performance that reminded everyone how much the kicking game matters.",
    },
]

STAR_TEMPLATES_USER_TEAM_MVP = [
    {
        'id': 'mvp_qb_win',
        'context': 'QB wins the game for user team',
        'match': lambda r: r['position'] == 'QB' and r.get('won'),
        'template': "Your {USER_TEAM_NAME} offense ran through {NAME} this week, and he delivered: {PASS_YARDS} yards, {PASS_TDS} touchdowns, and another W on the record.",
    },
    {
        'id': 'mvp_qb_loss',
        'context': 'QB in a loss',
        'match': lambda r: r['position'] == 'QB' and not r.get('won'),
        'template': "{NAME} fought hard for the {USER_TEAM_NAME} against {OPP}, putting up {PASS_YARDS} passing yards and {PASS_TDS} touchdowns in a tough loss that wasn't on him.",
    },
    {
        'id': 'mvp_rb_workhorse',
        'context': 'RB leads team',
        'match': lambda r: r['position'] == 'RB' and r.get('rush_yards', 0) >= 70,
        'template': "The {USER_TEAM_NAME} ran the ball with purpose this week behind {NAME}, who delivered {RUSH_YARDS} rushing yards and {RUSH_TDS} touchdowns against {OPP}.",
    },
    {
        'id': 'mvp_wr_te_big_game',
        'context': 'WR/TE with 80+ receiving yards',
        'match': lambda r: r['position'] in ('WR', 'TE') and r.get('rec_yards', 0) >= 80,
        'template': "{NAME} was the go-to weapon for {USER_TEAM_NAME} this week, hauling in {RECEPTIONS} catches for {REC_YARDS} yards and {REC_TDS} touchdowns against {OPP}.",
    },
    {
        'id': 'mvp_defender_win',
        'context': 'Defensive player leads user team in a win',
        'match': lambda r: r['position'] in ('DL', 'LB', 'CB', 'S') and r.get('won'),
        'template': "The {USER_TEAM_NAME} defense leaned on {NAME} this week, and he answered with {TACKLES} tackles in a {SCORE_DIFF}-point win over {OPP}.",
    },
    {
        'id': 'mvp_defender_loss',
        'context': 'Defensive player leads user team in a loss',
        'match': lambda r: r['position'] in ('DL', 'LB', 'CB', 'S') and not r.get('won'),
        'template': "{NAME} gave everything for {USER_TEAM_NAME} against {OPP}, posting {TACKLES} tackles in a tough loss. The effort was there — the result was not.",
    },
    {
        'id': 'mvp_kicker_clutch',
        'context': 'Kicker wins it for user team',
        'match': lambda r: r['position'] == 'K' and r.get('won') and r.get('score_diff', 99) <= 6,
        'template': "{NAME} came through when {USER_TEAM_NAME} needed it most, going {FG_MADE}-for-{FG_MADE} on field goals in a nail-biter over {OPP}.",
    },
    {
        'id': 'mvp_big_win',
        'context': 'User team win by 14+',
        'match': lambda r: r.get('won') and r.get('score_diff', 0) >= 14,
        'template': "In a dominant {SCORE_DIFF}-point showing against {OPP}, {NAME} led by example for {USER_TEAM_NAME} with a performance that set the tone from the opening drive.",
    },
    {
        'id': 'mvp_close_win',
        'context': 'User team squeaks out close win',
        'match': lambda r: r.get('won') and r.get('score_diff', 99) <= 7,
        'template': "It came down to the wire, but {NAME}'s performance gave {USER_TEAM_NAME} just enough to edge past {OPP} by {SCORE_DIFF} points.",
    },
    {
        'id': 'mvp_generic',
        'context': 'fallback',
        'match': lambda r: True,
        'template': "{NAME} was the standout performer for {USER_TEAM_NAME} this week, making a strong case to be the first name on the depth chart for the foreseeable future.",
    },
]
