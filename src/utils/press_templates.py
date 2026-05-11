"""
Press conference template library for Tier 1 weekly pressers.

Provides dry, beat-reporter style questions and responses across 14 context types.
Voice: flat, no exclamation points, under 15 words per response.

Phase 5 P9: contexts refined from 8 to 14.
  - post_win split into: post_win_blowout, post_win_narrow, post_win_vs_rival
  - post_loss split into: post_loss_blowout, post_loss_close, post_loss_upset
  - New: post_starter_injury
  - Previously planned but unimplemented: mid_season_grind, pre_division_game,
    post_injury_critical, pre_playoff_game, post_clinching, post_eliminated
  - Kept: losing_streak, winning_streak, routine, lineup_controversy
"""

TEMPLATES = [
    # ========== POST_WIN_BLOWOUT (won by 17+ points) ==========
    {
        'id': 'post_blowout_win_1',
        'context': 'post_win_blowout',
        'question': "Dominant performance today. How does it feel to win convincingly?",
        'responses': {
            'deflect': "Just glad to get the win. On to next week.",
            'accountable': "Team showed up ready. We played a complete game.",
            'confrontational': "This is what happens when we play to our potential.",
        },
    },
    {
        'id': 'post_blowout_win_2',
        'context': 'post_win_blowout',
        'question': "Did you expect the margin to be this wide?",
        'responses': {
            'deflect': "Never know how these things go. Players executed.",
            'accountable': "We came out fast and never let up. That was the goal.",
            'confrontational': "Absolutely. We're better and everyone could see it today.",
        },
    },
    {
        'id': 'post_blowout_win_3',
        'context': 'post_win_blowout',
        'question': "Can this performance set the tone for the rest of the season?",
        'responses': {
            'deflect': "We'll see. One game at a time.",
            'accountable': "Shows what we're capable of when everything clicks.",
            'confrontational': "This is the baseline. Anything less is unacceptable.",
        },
    },
    {
        'id': 'post_win_blowout_4',
        'context': 'post_win_blowout',
        'question': "Your defense held them under 10 points. What was the key?",
        'responses': {
            'deflect': "Guys executed the game plan. Credit the players.",
            'accountable': "We identified their tendencies early and took them away.",
            'confrontational': "They never had an answer for us. Total dominance.",
        },
    },
    {
        'id': 'post_win_blowout_5',
        'context': 'post_win_blowout',
        'question': "This was your most complete game of the season. What changed?",
        'responses': {
            'deflect': "Good week of practice. Players were locked in.",
            'accountable': "We cleaned up some things on tape and it paid off.",
            'confrontational': "We were always capable of this. Took too long to show it.",
        },
    },
    {
        'id': 'post_win_blowout_6',
        'context': 'post_win_blowout',
        'question': "You scored on the opening drive and never looked back. Intentional?",
        'responses': {
            'deflect': "We just play our game. Results take care of themselves.",
            'accountable': "We wanted to set the tone early. Mission accomplished.",
            'confrontational': "We came here to impose our will. That's what good teams do.",
        },
    },

    # ========== POST_WIN_NARROW (won by 8 or fewer, non-rival) ==========
    {
        'id': 'post_win_1',
        'context': 'post_win_narrow',
        'question': "Coach, the team got the W today. What's your read on the performance?",
        'responses': {
            'deflect': "Just happy to come away with the win. Lots to clean up.",
            'accountable': "Pleased with the execution but we left plays on the field.",
            'confrontational': "Anyone who thought we wouldn't win this hasn't been watching.",
        },
    },
    {
        'id': 'post_win_2',
        'context': 'post_win_narrow',
        'question': "How do you feel about the way the game plan came together?",
        'responses': {
            'deflect': "Credit goes to the players. They made the plays.",
            'accountable': "We stuck to our identity and it paid off today.",
            'confrontational': "We imposed our will. That's what good teams do.",
        },
    },
    {
        'id': 'post_win_3',
        'context': 'post_win_narrow',
        'question': "What adjustments did you make at halftime to secure the win?",
        'responses': {
            'deflect': "Just tried to stay out of the way. Players won it.",
            'accountable': "We tightened up the coverage and got better pressure up front.",
            'confrontational': "They couldn't adjust to us. We dictated every series.",
        },
    },
    {
        'id': 'post_win_4',
        'context': 'post_win_narrow',
        'question': "Can you build momentum from this performance into next week?",
        'responses': {
            'deflect': "We'll see. One week at a time.",
            'accountable': "Win helps confidence but we know there's work to do.",
            'confrontational': "We should have been doing this all season. Finally clicked.",
        },
    },
    {
        'id': 'post_win_narrow_5',
        'context': 'post_win_narrow',
        'question': "It was tight at the end. How does it feel to grind out that win?",
        'responses': {
            'deflect': "A win's a win. Next week is all that matters.",
            'accountable': "Our defense made the stop when we needed it. Proud of the guys.",
            'confrontational': "We made it harder than it needed to be. That has to stop.",
        },
    },
    {
        'id': 'post_win_narrow_6',
        'context': 'post_win_narrow',
        'question': "The fourth quarter was yours today. What did you see that let you close?",
        'responses': {
            'deflect': "They kept playing and the game worked out. Simple as that.",
            'accountable': "We made the right adjustments. Guys stayed composed.",
            'confrontational': "We knew they'd fold. We just had to keep the pressure on.",
        },
    },

    # ========== POST_WIN_VS_RIVAL (beat a division opponent) ==========
    {
        'id': 'post_win_vs_rival_1',
        'context': 'post_win_vs_rival',
        'question': "Division win today. How much bigger does this feel in the standings?",
        'responses': {
            'deflect': "Every win counts the same. We're happy to get it.",
            'accountable': "Division games swing standings. We knew what was at stake.",
            'confrontational': "Now they have to beat us twice to win this division. Good luck.",
        },
    },
    {
        'id': 'post_win_vs_rival_2',
        'context': 'post_win_vs_rival',
        'question': "Your guys seemed locked in for this one. Was there extra motivation?",
        'responses': {
            'deflect': "We approach every game the same.",
            'accountable': "Division opponents know you well. You have to earn it.",
            'confrontational': "They've had our number before. Not today.",
        },
    },
    {
        'id': 'post_win_vs_rival_3',
        'context': 'post_win_vs_rival',
        'question': "These teams know each other well. What was the difference today?",
        'responses': {
            'deflect': "We executed a little better. That's about it.",
            'accountable': "We were more disciplined on third down. Kept the chains moving.",
            'confrontational': "We're just the better team right now. Simple.",
        },
    },
    {
        'id': 'post_win_vs_rival_4',
        'context': 'post_win_vs_rival',
        'question': "Is this a statement win for your division title chances?",
        'responses': {
            'deflect': "Long season ahead. Just taking it one game at a time.",
            'accountable': "It helps but we still need to keep winning. Nothing guaranteed.",
            'confrontational': "Division title runs through us now. That's where we want to be.",
        },
    },
    {
        'id': 'post_win_vs_rival_5',
        'context': 'post_win_vs_rival',
        'question': "You play this team again. Does today's film help you prepare?",
        'responses': {
            'deflect': "They'll make adjustments. We'll make adjustments. Even slate.",
            'accountable': "We'll study this one carefully. What worked and what didn't.",
            'confrontational': "We know how to beat them now. Bring on the rematch.",
        },
    },
    {
        'id': 'post_win_vs_rival_6',
        'context': 'post_win_vs_rival',
        'question': "The rivalry aspect. Does that add pressure or does the team embrace it?",
        'responses': {
            'deflect': "It's just another game on the schedule as far as we're concerned.",
            'accountable': "The guys love these moments. They prepare harder for these.",
            'confrontational': "We want the best version of them every time. That's how you measure yourself.",
        },
    },

    # ========== POST_LOSS_BLOWOUT (lost by 17+ points) ==========
    {
        'id': 'post_blowout_loss_1',
        'context': 'post_loss_blowout',
        'question': "That was a rough one. What happened out there?",
        'responses': {
            'deflect': "They played well. We didn't. That's the game.",
            'accountable': "We got outcoached and outplayed. I take full responsibility.",
            'confrontational': "Embarrassing effort. Nobody should feel good about this.",
        },
    },
    {
        'id': 'post_blowout_loss_2',
        'context': 'post_loss_blowout',
        'question': "How do you bounce back from a loss like this?",
        'responses': {
            'deflect': "Just have to move on. Season's not over.",
            'accountable': "We'll address it, correct it, and come back better.",
            'confrontational': "Someone's job should be on the line after that performance.",
        },
    },
    {
        'id': 'post_blowout_loss_3',
        'context': 'post_loss_blowout',
        'question': "Was there a turning point where the game got away from you?",
        'responses': {
            'deflect': "They just made more plays. Tip your cap and move on.",
            'accountable': "We never established rhythm. That's on the preparation.",
            'confrontational': "We were never in it. Complete breakdown from start to finish.",
        },
    },
    {
        'id': 'post_loss_blowout_4',
        'context': 'post_loss_blowout',
        'question': "Is there a concern about the team's ability to compete at this level?",
        'responses': {
            'deflect': "Every team has bad days. This was a bad day.",
            'accountable': "We have to be honest with ourselves. There are real gaps to fix.",
            'confrontational': "I won't accept excuses. This is on the coaching staff.",
        },
    },
    {
        'id': 'post_loss_blowout_5',
        'context': 'post_loss_blowout',
        'question': "The margin was 20-plus. How do you keep guys from losing confidence?",
        'responses': {
            'deflect': "They'll be fine. We've been here before.",
            'accountable': "I'll be direct with them. The film doesn't lie and we'll own it.",
            'confrontational': "If this damages confidence, they don't have the right mentality.",
        },
    },
    {
        'id': 'post_loss_blowout_6',
        'context': 'post_loss_blowout',
        'question': "You got outgained by 200 yards. Is this a scheme issue or an execution issue?",
        'responses': {
            'deflect': "I'll have to look at the tape before I make that call.",
            'accountable': "Honestly, probably both. We have a lot to address.",
            'confrontational': "We got dominated. I'm not going to sugarcoat it.",
        },
    },

    # ========== POST_LOSS_CLOSE (lost by 8 or fewer, not an upset) ==========
    {
        'id': 'post_loss_1',
        'context': 'post_loss_close',
        'question': "Tough loss today. Where did things break down?",
        'responses': {
            'deflect': "They made more plays than we did. Give them credit.",
            'accountable': "We didn't execute when it mattered. That falls on me.",
            'confrontational': "We beat ourselves with mistakes. Totally avoidable.",
        },
    },
    {
        'id': 'post_loss_2',
        'context': 'post_loss_close',
        'question': "How do you keep the locker room together after a game like this?",
        'responses': {
            'deflect': "Guys know what they need to do. They'll be fine.",
            'accountable': "We'll watch the tape, own our mistakes, and move forward.",
            'confrontational': "If they can't handle adversity, they shouldn't be here.",
        },
    },
    {
        'id': 'post_loss_3',
        'context': 'post_loss_close',
        'question': "What needs to change to avoid this result next week?",
        'responses': {
            'deflect': "Just need to keep grinding. Results will come.",
            'accountable': "Better discipline, better execution. We know the standard.",
            'confrontational': "Same mistakes every week. Someone has to be held accountable.",
        },
    },
    {
        'id': 'post_loss_4',
        'context': 'post_loss_close',
        'question': "Do you feel like the team is trending in the right direction?",
        'responses': {
            'deflect': "Win some, lose some. That's the league.",
            'accountable': "Process is good. Scoreboard didn't reflect that today.",
            'confrontational': "We're better than this. Today was unacceptable.",
        },
    },
    {
        'id': 'post_division_loss_1',
        'context': 'post_loss_close',
        'question': "Tough divisional loss. How much does this hurt the standings outlook?",
        'responses': {
            'deflect': "We'll see how it plays out. Still games to play.",
            'accountable': "Division games matter. We needed this one and didn't get it.",
            'confrontational': "This might cost us the division. Unacceptable to lose here.",
        },
    },
    {
        'id': 'post_division_loss_2',
        'context': 'post_loss_close',
        'question': "What adjustments do you need to make before you face them again?",
        'responses': {
            'deflect': "We'll watch the tape. Long season ahead.",
            'accountable': "We need to match their physicality. That was the difference.",
            'confrontational': "They wanted it more. That's a coaching failure.",
        },
    },
    {
        'id': 'post_division_loss_3',
        'context': 'post_loss_close',
        'question': "How do you keep playoff hopes alive after dropping this one?",
        'responses': {
            'deflect': "Just win the next game. That's all we can control.",
            'accountable': "Season's not over but margin for error is gone.",
            'confrontational': "If we keep playing like this, playoffs are a fantasy.",
        },
    },

    # ========== POST_LOSS_UPSET (user was favored and lost) ==========
    {
        'id': 'post_loss_upset_1',
        'context': 'post_loss_upset',
        'question': "You were the better team on paper. What went wrong?",
        'responses': {
            'deflect': "Paper doesn't matter. They played better today. That's football.",
            'accountable': "We came in thinking it would be easier than it was. Lesson learned.",
            'confrontational': "We played down to the competition. Completely unacceptable.",
        },
    },
    {
        'id': 'post_loss_upset_2',
        'context': 'post_loss_upset',
        'question': "This looks like a trap game loss in hindsight. Was the team focused?",
        'responses': {
            'deflect': "That's not fair to the other team. They earned this win.",
            'accountable': "Honestly, we may not have had the right mindset. That's on me.",
            'confrontational': "I won't accept 'trap game' as an excuse. We need to be better.",
        },
    },
    {
        'id': 'post_loss_upset_3',
        'context': 'post_loss_upset',
        'question': "How do you explain this result to the ownership and the fan base?",
        'responses': {
            'deflect': "I explain it the same way I do in the locker room: they played better.",
            'accountable': "I take responsibility. We prepared, we just didn't execute.",
            'confrontational': "I don't owe explanations to anyone except these players.",
        },
    },
    {
        'id': 'post_loss_upset_4',
        'context': 'post_loss_upset',
        'question': "Games like this can derail a season. How do you prevent that?",
        'responses': {
            'deflect': "One game. Move on. That's how it has to be.",
            'accountable': "We address the film, fix the habits, and do not repeat this.",
            'confrontational': "If this derails us, we weren't going anywhere anyway.",
        },
    },
    {
        'id': 'post_loss_upset_5',
        'context': 'post_loss_upset',
        'question': "You were favored by two scores. That's a statement loss in this league.",
        'responses': {
            'deflect': "Odds and records don't play. Sixty minutes decide it.",
            'accountable': "We have to be more consistent. A team like that cannot beat us.",
            'confrontational': "This won't happen again. I guarantee you that.",
        },
    },
    {
        'id': 'post_loss_upset_6',
        'context': 'post_loss_upset',
        'question': "Was there a moment where you felt the game slip away from you?",
        'responses': {
            'deflect': "I'll look at the tape. Wasn't one moment.",
            'accountable': "Second quarter, we stopped getting off the field. Changed everything.",
            'confrontational': "The moment we stopped competing at our level. Inexcusable.",
        },
    },

    # ========== POST_STARTER_INJURY (key starter went down this week) ==========
    {
        'id': 'post_starter_injury_1',
        'context': 'post_starter_injury',
        'question': "We saw your starter go down today. How serious is it and what's the timeline?",
        'responses': {
            'deflect': "We're still gathering information. Won't know more until the tests come back.",
            'accountable': "It's significant. We'll miss him and we have to be honest about that.",
            'confrontational': "Next man up. That's the only conversation we're having.",
        },
    },
    {
        'id': 'post_starter_injury_2',
        'context': 'post_starter_injury',
        'question': "How does the team respond when you lose someone of that caliber mid-season?",
        'responses': {
            'deflect': "These guys are professionals. They'll respond the right way.",
            'accountable': "We have to adjust the game plan and trust the guys stepping in.",
            'confrontational': "This is where you find out what your roster is really made of.",
        },
    },
    {
        'id': 'post_starter_injury_3',
        'context': 'post_starter_injury',
        'question': "Is the backup ready to step into a starting role this quickly?",
        'responses': {
            'deflect': "He'll get the reps this week and we'll see.",
            'accountable': "He's been preparing all year. Different player, same standard.",
            'confrontational': "He better be. There's no other option.",
        },
    },
    {
        'id': 'post_starter_injury_4',
        'context': 'post_starter_injury',
        'question': "How is the injured player holding up mentally? Did you talk to him?",
        'responses': {
            'deflect': "That stays in-house. He's a pro.",
            'accountable': "We talked. He's hurting but his mindset is right. Proud of him.",
            'confrontational': "He's a tough kid. More worried about the team than himself.",
        },
    },
    {
        'id': 'post_starter_injury_5',
        'context': 'post_starter_injury',
        'question': "Does this change your approach to the rest of the season?",
        'responses': {
            'deflect': "We'll figure it out. Season's long.",
            'accountable': "We have to be realistic. It changes some things, not everything.",
            'confrontational': "We adjust and keep competing. No other acceptable answer.",
        },
    },

    # ========== POST_INJURY_CRITICAL (season-altering injury, any player) ==========
    {
        'id': 'post_injury_critical_1',
        'context': 'post_injury_critical',
        'question': "Reports are calling this a season-ending injury. Can you confirm?",
        'responses': {
            'deflect': "We'll have an official update when we have the full evaluation.",
            'accountable': "It looks serious. We're preparing for the worst and hoping for better.",
            'confrontational': "It's bad. I won't sugarcoat it. We move forward without him.",
        },
    },
    {
        'id': 'post_injury_critical_2',
        'context': 'post_injury_critical',
        'question': "A loss like this can change the direction of a season. Does this change yours?",
        'responses': {
            'deflect': "Not going to make that call before we know all the facts.",
            'accountable': "Our goals don't change. The path to get there changes.",
            'confrontational': "Next man up. Roster was built for moments like this.",
        },
    },
    {
        'id': 'post_injury_critical_3',
        'context': 'post_injury_critical',
        'question': "Is there a transaction in play? Are you looking at the roster to fill the void?",
        'responses': {
            'deflect': "We'll evaluate all options. Nothing to announce right now.",
            'accountable': "We'll look at what's available and make the right decision for the team.",
            'confrontational': "We have options. We'll use them.",
        },
    },
    {
        'id': 'post_injury_critical_4',
        'context': 'post_injury_critical',
        'question': "This is the third significant injury this season. Is that a concern?",
        'responses': {
            'deflect': "Injuries happen in this league. We don't control that.",
            'accountable': "We need to look at our training and load management. Something's off.",
            'confrontational': "It's not ideal but the guys behind them are ready. Period.",
        },
    },
    {
        'id': 'post_injury_critical_5',
        'context': 'post_injury_critical',
        'question': "How do you keep this from becoming a distraction in the locker room?",
        'responses': {
            'deflect': "Focus is always on the next game. That's not going to change.",
            'accountable': "We acknowledge it, we support the player, and we move forward.",
            'confrontational': "Good teams don't get distracted. This is a test. We'll pass it.",
        },
    },

    # ========== LOSING_STREAK (3+ consecutive losses) ==========
    {
        'id': 'losing_streak_1',
        'context': 'losing_streak',
        'question': "Three losses in a row. What needs to change?",
        'responses': {
            'deflect': "Just need to catch a break. Losses happen.",
            'accountable': "We're not executing. I need to do a better job preparing them.",
            'confrontational': "This is on the players. Coaching can only do so much.",
        },
    },
    {
        'id': 'losing_streak_2',
        'context': 'losing_streak',
        'question': "Is your job security starting to weigh on you?",
        'responses': {
            'deflect': "I don't worry about that. Just focus on the work.",
            'accountable': "If we don't turn this around, everything's on the table.",
            'confrontational': "If they want to fire me, fine. I know what I'm doing.",
        },
    },
    {
        'id': 'losing_streak_3',
        'context': 'losing_streak',
        'question': "How do you stop the bleeding and get back in the win column?",
        'responses': {
            'deflect': "One play at a time. One game at a time.",
            'accountable': "We need to simplify and get back to fundamentals.",
            'confrontational': "Players need to look in the mirror and decide if they care.",
        },
    },

    # ========== WINNING_STREAK (3+ consecutive wins) ==========
    {
        'id': 'winning_streak_1',
        'context': 'winning_streak',
        'question': "Three straight wins. What's clicking right now?",
        'responses': {
            'deflect': "Guys are making plays. That's about it.",
            'accountable': "We're playing complementary football. Defense and offense both clicking.",
            'confrontational': "This is how we should have played all year. Finally woke up.",
        },
    },
    {
        'id': 'winning_streak_2',
        'context': 'winning_streak',
        'question': "Can you sustain this momentum through the rest of the season?",
        'responses': {
            'deflect': "We'll see. One week at a time.",
            'accountable': "Confidence is high but we know every week is a test.",
            'confrontational': "If we keep this up, nobody can stop us.",
        },
    },
    {
        'id': 'winning_streak_3',
        'context': 'winning_streak',
        'question': "What changed between the earlier struggles and this winning streak?",
        'responses': {
            'deflect': "Luck evens out. Bounces went our way lately.",
            'accountable': "We cleaned up penalties and turnovers. Made a big difference.",
            'confrontational': "We were always this good. Media just couldn't see it.",
        },
    },

    # ========== MID_SEASON_GRIND (weeks 10-14, no other notable trigger) ==========
    {
        'id': 'mid_season_grind_1',
        'context': 'mid_season_grind',
        'question': "You're past the halfway point. How do you keep energy levels up through this stretch?",
        'responses': {
            'deflect': "Short weeks, long weeks, doesn't matter. Work is the work.",
            'accountable': "We rotate guys, manage snaps, and keep the practice tempo right.",
            'confrontational': "If guys are tired now, they won't make it to January. That's reality.",
        },
    },
    {
        'id': 'mid_season_grind_2',
        'context': 'mid_season_grind',
        'question': "Week 11. Does the season start to feel different at this stage?",
        'responses': {
            'deflect': "Every week matters. We don't change that message.",
            'accountable': "Stakes get clearer. Every game has more weight behind it.",
            'confrontational': "We should be playing our best football right now. No excuses.",
        },
    },
    {
        'id': 'mid_season_grind_3',
        'context': 'mid_season_grind',
        'question': "How do you handle the wear and tear on your roster this deep into the season?",
        'responses': {
            'deflect': "Part of the game. Everyone deals with it.",
            'accountable': "We track everything. Smart load management through the week.",
            'confrontational': "Tough players play through it. That's not going to change.",
        },
    },
    {
        'id': 'mid_season_grind_4',
        'context': 'mid_season_grind',
        'question': "Looking at the second half of the schedule, what do you see?",
        'responses': {
            'deflect': "Can't look ahead. Just focus on the next opponent.",
            'accountable': "There are winnable games and tough games. We prepare the same for all.",
            'confrontational': "We should win out. That's the expectation I'm setting.",
        },
    },
    {
        'id': 'mid_season_grind_5',
        'context': 'mid_season_grind',
        'question': "Any players you're trying to protect a little coming out of the bye week stretch?",
        'responses': {
            'deflect': "No comment on individual players' health status.",
            'accountable': "We're monitoring a few guys closely. Being smart about it.",
            'confrontational': "If you can walk, you can practice. That's my standard.",
        },
    },
    {
        'id': 'mid_season_grind_6',
        'context': 'mid_season_grind',
        'question': "Have you made any schematic changes you've been saving for the second half?",
        'responses': {
            'deflect': "We do what works. Always been that way.",
            'accountable': "We've been building toward some things. You'll see it in the coming weeks.",
            'confrontational': "We've got things saved. Rest of the league hasn't seen our best yet.",
        },
    },

    # ========== PRE_DIVISION_GAME (upcoming game is a division matchup) ==========
    {
        'id': 'pre_division_game_1',
        'context': 'pre_division_game',
        'question': "Division matchup this week. How do you prepare for a team that knows you that well?",
        'responses': {
            'deflect': "Prepare the same way we always do. Film, reps, execution.",
            'accountable': "You have to take away their strengths and exploit your own advantages.",
            'confrontational': "Familiarity works both ways. We know them just as well.",
        },
    },
    {
        'id': 'pre_division_game_2',
        'context': 'pre_division_game',
        'question': "How much does a division win change the landscape of your season right now?",
        'responses': {
            'deflect': "We don't think about the standings. Think about the football.",
            'accountable': "Division games are the most important on the schedule. Always.",
            'confrontational': "Lose this game and we're in a hole we can't afford. Simple.",
        },
    },
    {
        'id': 'pre_division_game_3',
        'context': 'pre_division_game',
        'question': "What's the scouting report showing you heading into this one?",
        'responses': {
            'deflect': "We're not sharing that. It stays in the building.",
            'accountable': "They're well-coached and physical. We have to match their intensity.",
            'confrontational': "They've got weaknesses like everyone else. We'll find them.",
        },
    },
    {
        'id': 'pre_division_game_4',
        'context': 'pre_division_game',
        'question': "Have these rivalry games gotten into the players' heads in the past?",
        'responses': {
            'deflect': "That's for the players to answer. I focus on the Xs and Os.",
            'accountable': "We talk about channeling the energy the right way. Not letting it hurt us.",
            'confrontational': "If rivalry games rattle you, you're in the wrong business.",
        },
    },
    {
        'id': 'pre_division_game_5',
        'context': 'pre_division_game',
        'question': "Any injury or lineup concerns heading into this matchup?",
        'responses': {
            'deflect': "We'll be who we are. That's all I'll say.",
            'accountable': "A few guys are managing things. Day-to-day. Making smart calls.",
            'confrontational': "Healthy enough to beat them. That's all that matters.",
        },
    },

    # ========== PRE_PLAYOFF_GAME (week 15+, in playoff position, not yet clinched) ==========
    {
        'id': 'pre_playoff_game_1',
        'context': 'pre_playoff_game',
        'question': "This game has playoff implications written all over it. How do you prepare differently?",
        'responses': {
            'deflect': "You don't. You just prepare. The game is the game.",
            'accountable': "Stakes are higher but the process stays the same. Trust the routine.",
            'confrontational': "We've been preparing for this moment all year. We're ready.",
        },
    },
    {
        'id': 'pre_playoff_game_2',
        'context': 'pre_playoff_game',
        'question': "Every game from here on looks like a playoff game. How does the team respond to that?",
        'responses': {
            'deflect': "One game at a time. That's the only honest answer.",
            'accountable': "They've earned this position. Now they get to prove it under pressure.",
            'confrontational': "Good. I want them to feel the weight. Pressure is a privilege.",
        },
    },
    {
        'id': 'pre_playoff_game_3',
        'context': 'pre_playoff_game',
        'question': "You're in the hunt but not safe yet. How do you balance urgency without panic?",
        'responses': {
            'deflect': "We don't panic. We play our game.",
            'accountable': "Focus on execution, not the standings. What you control is what matters.",
            'confrontational': "No panic here. Just a team that knows what it needs to do.",
        },
    },
    {
        'id': 'pre_playoff_game_4',
        'context': 'pre_playoff_game',
        'question': "Does your team play better with their backs against the wall?",
        'responses': {
            'deflect': "I don't think about it that way. You just compete.",
            'accountable': "We've shown we can respond. But I'd rather not need to.",
            'confrontational': "Backs against the wall is when you see who the real players are.",
        },
    },
    {
        'id': 'pre_playoff_game_5',
        'context': 'pre_playoff_game',
        'question': "What's your message to the team going into this stretch run?",
        'responses': {
            'deflect': "Just keep working. Same as always.",
            'accountable': "We built something this year. Now we protect it.",
            'confrontational': "Anybody not locked in right now doesn't deserve to be here.",
        },
    },

    # ========== POST_CLINCHING (just clinched a playoff spot) ==========
    {
        'id': 'post_clinching_1',
        'context': 'post_clinching',
        'question': "You've punched your ticket to the playoffs. How does that feel?",
        'responses': {
            'deflect': "Good. Now we focus on where we're seeded.",
            'accountable': "Proud of how the guys responded all year. Earned this.",
            'confrontational': "This was always the expectation. Now the real work starts.",
        },
    },
    {
        'id': 'post_clinching_2',
        'context': 'post_clinching',
        'question': "Do you celebrate tonight or is it business as usual?",
        'responses': {
            'deflect': "That's up to the guys. They've earned whatever they want tonight.",
            'accountable': "Brief moment to recognize it. Then we get back to work tomorrow.",
            'confrontational': "We'll acknowledge it. Then we prepare to win in January.",
        },
    },
    {
        'id': 'post_clinching_3',
        'context': 'post_clinching',
        'question': "What's the priority for the rest of the regular season? Rest or seeding?",
        'responses': {
            'deflect': "We'll figure that out as we go. Nothing decided yet.",
            'accountable': "We want to keep momentum. Seeding matters. We'll stay sharp.",
            'confrontational': "We're competing until the clock hits zero. Every game, every week.",
        },
    },
    {
        'id': 'post_clinching_4',
        'context': 'post_clinching',
        'question': "Is this a validation of the direction you've taken the program?",
        'responses': {
            'deflect': "It's one step. We'll evaluate at the end of the run.",
            'accountable': "The players believed in what we were building. This confirms it.",
            'confrontational': "Anyone who doubted us can look at the standings now.",
        },
    },
    {
        'id': 'post_clinching_5',
        'context': 'post_clinching',
        'question': "What does this mean for the younger players on this roster?",
        'responses': {
            'deflect': "Hope it gives them confidence. That's about it.",
            'accountable': "Hopefully it shows them what's possible when you commit to the process.",
            'confrontational': "They better be ready. Playoffs aren't the time for on-the-job training.",
        },
    },

    # ========== POST_ELIMINATED (just been eliminated from playoff contention) ==========
    {
        'id': 'post_eliminated_1',
        'context': 'post_eliminated',
        'question': "The playoff door has officially closed. How do you process that?",
        'responses': {
            'deflect': "Still games to play. We owe it to the fans to finish strong.",
            'accountable': "It's disappointing. We'll own it in the offseason and come back better.",
            'confrontational': "It's unacceptable. This won't happen again.",
        },
    },
    {
        'id': 'post_eliminated_2',
        'context': 'post_eliminated',
        'question': "At what point in the season did this become the probable outcome?",
        'responses': {
            'deflect': "I'm not going to revisit that right now. It's in the past.",
            'accountable': "We had windows we didn't take advantage of. Several of them.",
            'confrontational': "The moment the players stopped competing at the level they should have.",
        },
    },
    {
        'id': 'post_eliminated_3',
        'context': 'post_eliminated',
        'question': "What do the remaining games mean to this team now?",
        'responses': {
            'deflect': "Everything. You play for pride and for next year.",
            'accountable': "Development, evaluation, and finishing with some dignity.",
            'confrontational': "Prove who wants to be here next year. Auditions start now.",
        },
    },
    {
        'id': 'post_eliminated_4',
        'context': 'post_eliminated',
        'question': "What's your honest assessment of this season?",
        'responses': {
            'deflect': "I'll save that for after the final game. Not doing it now.",
            'accountable': "We underperformed. There's no other way to characterize it.",
            'confrontational': "We wasted a season. That's the honest assessment.",
        },
    },
    {
        'id': 'post_eliminated_5',
        'context': 'post_eliminated',
        'question': "Is your job status something you're worried about heading into the offseason?",
        'responses': {
            'deflect': "Not my call to make. I focus on what I can control.",
            'accountable': "Results weren't good enough. I understand what that means.",
            'confrontational': "If they want to make a change, make it. But I stand by the work.",
        },
    },

    # ========== ROUTINE (fallback, bye week, generic) ==========
    {
        'id': 'routine_1',
        'context': 'routine',
        'question': "Coach, how is the team looking as you head into this week?",
        'responses': {
            'deflect': "Everyone's healthy and ready to work. That's all I ask.",
            'accountable': "We had a good week of practice. Focused on fundamentals.",
            'confrontational': "We're ready. Other team should be worried, not us.",
        },
    },
    {
        'id': 'routine_2',
        'context': 'routine',
        'question': "What's your message to the team this week?",
        'responses': {
            'deflect': "Same as always. Do your job.",
            'accountable': "Control what we can control. Stick to the process.",
            'confrontational': "Win or go home. There's no other option.",
        },
    },
    {
        'id': 'routine_3',
        'context': 'routine',
        'question': "Any injury updates or lineup changes heading into the game?",
        'responses': {
            'deflect': "Everyone who's supposed to play will play.",
            'accountable': "We'll evaluate day by day and make smart decisions.",
            'confrontational': "If you're healthy enough to practice, you're healthy enough to play.",
        },
    },

    # -------------------------------------------------------
    # lineup_controversy — Phase 5 Prompt #5
    # -------------------------------------------------------
    {
        'id': 'lineup_controversy_1',
        'context': 'lineup_controversy',
        'question': "Coach, a healthy starter was benched today in favor of a backup with a significantly lower grade. Can you walk us through that decision?",
        'responses': {
            'deflect':         "I make the decisions I think give us the best chance to win. That's it.",
            'accountable':     "I saw something in practice this week that gave me confidence in the change.",
            'confrontational': "I coach to win, not to manage reputations. Some calls are hard.",
        },
    },
    {
        'id': 'lineup_controversy_2',
        'context': 'lineup_controversy',
        'question': "There's a lot of surprise in the locker room about today's lineup. A healthy, high-rated starter is not starting. What's your message to the team?",
        'responses': {
            'deflect':         "The message is always the same: compete, and the best player plays.",
            'accountable':     "I understand the surprise. I owe the guys an honest explanation in the meeting room.",
            'confrontational': "If anyone has a problem with how I set the lineup, they can come see me directly.",
        },
    },
    {
        'id': 'lineup_controversy_3',
        'context': 'lineup_controversy',
        'question': "Fans are asking whether this lineup decision is about performance or something off the field. Can you clarify?",
        'responses': {
            'deflect':         "My lineup decisions are football decisions. Full stop.",
            'accountable':     "It's purely football. I should have communicated it better beforehand.",
            'confrontational': "I'm not going to justify my roster moves to social media.",
        },
    },
    {
        'id': 'lineup_controversy_4',
        'context': 'lineup_controversy',
        'question': "Has the benched player been told why he's not starting, and how did he respond?",
        'responses': {
            'deflect':         "Those conversations stay in-house.",
            'accountable':     "Yes, we talked. It wasn't easy, but he deserved honesty.",
            'confrontational': "Every player on this roster knows where they stand. No surprises.",
        },
    },
    {
        'id': 'lineup_controversy_5',
        'context': 'lineup_controversy',
        'question': "Is this a one-game decision, or a change in the depth chart going forward?",
        'responses': {
            'deflect':         "We evaluate everything week to week.",
            'accountable':     "Right now it's this week. We'll see what the player does with the reps.",
            'confrontational': "The depth chart reflects performance. It stays until performance changes.",
        },
    },
]


def get_templates_by_context(context_type: str) -> list:
    """
    Return all templates matching the given context type.
    Falls back to 'routine' if no matches found.

    Args:
        context_type: One of the 14 P9 context types (or legacy types)

    Returns:
        List of matching template dicts
    """
    matches = [t for t in TEMPLATES if t['context'] == context_type]
    if not matches:
        matches = [t for t in TEMPLATES if t['context'] == 'routine']
    return matches


def get_template_by_id(template_id: str) -> dict:
    """
    Lookup a specific template by ID.

    Args:
        template_id: Template ID string

    Returns:
        Template dict

    Raises:
        KeyError: If template_id not found
    """
    for template in TEMPLATES:
        if template['id'] == template_id:
            return template
    raise KeyError(f"Template ID '{template_id}' not found")
