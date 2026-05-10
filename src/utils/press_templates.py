"""
Press conference template library for Tier 1 weekly pressers.

Provides dry, beat-reporter style questions and responses across 8 context types.
Voice: flat, no exclamation points, under 15 words per response.

Context types:
- post_win: routine win (1-13 point margin)
- post_loss: routine loss (1-13 point margin)
- post_blowout_win: 14+ point margin
- post_blowout_loss: 14+ point margin
- post_division_loss: lost to division opponent
- losing_streak: 3+ consecutive losses
- winning_streak: 3+ consecutive wins
- routine: fallback (bye week, no game result, etc.)
"""

TEMPLATES = [
    # ========== POST_WIN (routine win) ==========
    {
        'id': 'post_win_1',
        'context': 'post_win',
        'question': "Coach, the team got the W today. What's your read on the performance?",
        'responses': {
            'deflect': "Just happy to come away with the win. Lots to clean up.",
            'accountable': "Pleased with the execution but we left plays on the field.",
            'confrontational': "Anyone who thought we wouldn't win this hasn't been watching.",
        },
    },
    {
        'id': 'post_win_2',
        'context': 'post_win',
        'question': "How do you feel about the way the game plan came together?",
        'responses': {
            'deflect': "Credit goes to the players. They made the plays.",
            'accountable': "We stuck to our identity and it paid off today.",
            'confrontational': "We imposed our will. That's what good teams do.",
        },
    },
    {
        'id': 'post_win_3',
        'context': 'post_win',
        'question': "What adjustments did you make at halftime to secure the win?",
        'responses': {
            'deflect': "Just tried to stay out of the way. Players won it.",
            'accountable': "We tightened up the coverage and got better pressure up front.",
            'confrontational': "They couldn't adjust to us. We dictated every series.",
        },
    },
    {
        'id': 'post_win_4',
        'context': 'post_win',
        'question': "Can you build momentum from this performance into next week?",
        'responses': {
            'deflect': "We'll see. One week at a time.",
            'accountable': "Win helps confidence but we know there's work to do.",
            'confrontational': "We should have been doing this all season. Finally clicked.",
        },
    },

    # ========== POST_LOSS (routine loss) ==========
    {
        'id': 'post_loss_1',
        'context': 'post_loss',
        'question': "Tough loss today. Where did things break down?",
        'responses': {
            'deflect': "They made more plays than we did. Give them credit.",
            'accountable': "We didn't execute when it mattered. That falls on me.",
            'confrontational': "We beat ourselves with mistakes. Totally avoidable.",
        },
    },
    {
        'id': 'post_loss_2',
        'context': 'post_loss',
        'question': "How do you keep the locker room together after a game like this?",
        'responses': {
            'deflect': "Guys know what they need to do. They'll be fine.",
            'accountable': "We'll watch the tape, own our mistakes, and move forward.",
            'confrontational': "If they can't handle adversity, they shouldn't be here.",
        },
    },
    {
        'id': 'post_loss_3',
        'context': 'post_loss',
        'question': "What needs to change to avoid this result next week?",
        'responses': {
            'deflect': "Just need to keep grinding. Results will come.",
            'accountable': "Better discipline, better execution. We know the standard.",
            'confrontational': "Same mistakes every week. Someone has to be held accountable.",
        },
    },
    {
        'id': 'post_loss_4',
        'context': 'post_loss',
        'question': "Do you feel like the team is trending in the right direction?",
        'responses': {
            'deflect': "Win some, lose some. That's the league.",
            'accountable': "Process is good. Scoreboard didn't reflect that today.",
            'confrontational': "We're better than this. Today was unacceptable.",
        },
    },

    # ========== POST_BLOWOUT_WIN (14+ point margin) ==========
    {
        'id': 'post_blowout_win_1',
        'context': 'post_blowout_win',
        'question': "Dominant performance today. How does it feel to win convincingly?",
        'responses': {
            'deflect': "Just glad to get the win. On to next week.",
            'accountable': "Team showed up ready. We played a complete game.",
            'confrontational': "This is what happens when we play to our potential.",
        },
    },
    {
        'id': 'post_blowout_win_2',
        'context': 'post_blowout_win',
        'question': "Did you expect the margin to be this wide?",
        'responses': {
            'deflect': "Never know how these things go. Players executed.",
            'accountable': "We came out fast and never let up. That was the goal.",
            'confrontational': "Absolutely. We're better and everyone could see it today.",
        },
    },
    {
        'id': 'post_blowout_win_3',
        'context': 'post_blowout_win',
        'question': "Can this performance set the tone for the rest of the season?",
        'responses': {
            'deflect': "We'll see. One game at a time.",
            'accountable': "Shows what we're capable of when everything clicks.",
            'confrontational': "This is the baseline. Anything less is unacceptable.",
        },
    },

    # ========== POST_BLOWOUT_LOSS (14+ point margin) ==========
    {
        'id': 'post_blowout_loss_1',
        'context': 'post_blowout_loss',
        'question': "That was a rough one. What happened out there?",
        'responses': {
            'deflect': "They played well. We didn't. That's the game.",
            'accountable': "We got outcoached and outplayed. I take full responsibility.",
            'confrontational': "Embarrassing effort. Nobody should feel good about this.",
        },
    },
    {
        'id': 'post_blowout_loss_2',
        'context': 'post_blowout_loss',
        'question': "How do you bounce back from a loss like this?",
        'responses': {
            'deflect': "Just have to move on. Season's not over.",
            'accountable': "We'll address it, correct it, and come back better.",
            'confrontational': "Someone's job should be on the line after that performance.",
        },
    },
    {
        'id': 'post_blowout_loss_3',
        'context': 'post_blowout_loss',
        'question': "Was there a turning point where the game got away from you?",
        'responses': {
            'deflect': "They just made more plays. Tip your cap and move on.",
            'accountable': "We never established rhythm. That's on the preparation.",
            'confrontational': "We were never in it. Complete breakdown from start to finish.",
        },
    },

    # ========== POST_DIVISION_LOSS (lost to division rival) ==========
    {
        'id': 'post_division_loss_1',
        'context': 'post_division_loss',
        'question': "Tough divisional loss. How much does this hurt the standings outlook?",
        'responses': {
            'deflect': "We'll see how it plays out. Still games to play.",
            'accountable': "Division games matter. We needed this one and didn't get it.",
            'confrontational': "This might cost us the division. Unacceptable to lose here.",
        },
    },
    {
        'id': 'post_division_loss_2',
        'context': 'post_division_loss',
        'question': "What adjustments do you need to make before you face them again?",
        'responses': {
            'deflect': "We'll watch the tape. Long season ahead.",
            'accountable': "We need to match their physicality. That was the difference.",
            'confrontational': "They wanted it more. That's a coaching failure.",
        },
    },
    {
        'id': 'post_division_loss_3',
        'context': 'post_division_loss',
        'question': "How do you keep playoff hopes alive after dropping this one?",
        'responses': {
            'deflect': "Just win the next game. That's all we can control.",
            'accountable': "Season's not over but margin for error is gone.",
            'confrontational': "If we keep playing like this, playoffs are a fantasy.",
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
]


def get_templates_by_context(context_type: str) -> list:
    """
    Return all templates matching the given context type.
    Falls back to 'routine' if no matches found.

    Args:
        context_type: One of the 8 context types

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
