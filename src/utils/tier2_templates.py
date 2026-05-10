"""
Tier 2 dramatic press conference template library (Phase 4 Prompt #6).

24 templates (3 per trigger × 8 triggers), each with 2-3 questions.
Voice: raw, exposed, memorable. NOT routine beat-reporter tone.

Placeholders: {star_name}, {opponent}, {streak_length}, {round_name},
{position}, {score}, {year}, {prev_year}

Deflect = stoic, holding back.
Accountable = exposed, vulnerable, real.
Confrontational = fire, edge, combative.
"""

import random
from typing import Optional


TIER2_TEMPLATES = [
    # ======================================================================
    # CHAMPIONSHIP_WON
    # ======================================================================
    {
        'id': 'championship_won_A',
        'trigger': 'championship_won',
        'questions': [
            {
                'question': "Coach. You just won the Super Bowl. What's the first thing through your head?",
                'responses': {
                    'deflect': "Relief.",
                    'accountable': "Every face that helped us get here. Every one.",
                    'confrontational': "That nobody picked us. Nobody. And here we are.",
                },
            },
            {
                'question': "This franchise hasn't won it all in a long time. What does this mean to the city?",
                'responses': {
                    'deflect': "It means a lot. That's all I can say right now.",
                    'accountable': "These fans stayed through the worst years. They earned this.",
                    'confrontational': "Every analyst who wrote us off can eat their words tonight.",
                },
            },
            {
                'question': "Where does this rank in your career?",
                'responses': {
                    'deflect': "I don't rank things. We won. That's enough.",
                    'accountable': "Top. Nothing else comes close. Nothing.",
                    'confrontational': "Ask the people who said I couldn't do it.",
                },
            },
        ],
    },
    {
        'id': 'championship_won_B',
        'trigger': 'championship_won',
        'questions': [
            {
                'question': "You're a champion. How long have you waited to hear that?",
                'responses': {
                    'deflect': "Longer than I'll admit.",
                    'accountable': "Every day since I took this job. Every single day.",
                    'confrontational': "I never doubted it was coming. Other people did.",
                },
            },
            {
                'question': "What was the moment you knew this team was special?",
                'responses': {
                    'deflect': "Hard to pinpoint one moment.",
                    'accountable': "Training camp. The look in their eyes. They were ready to suffer for this.",
                    'confrontational': "When we beat the team everyone said would destroy us. Week six.",
                },
            },
        ],
    },
    {
        'id': 'championship_won_C',
        'trigger': 'championship_won',
        'questions': [
            {
                'question': "Coach, confetti is falling. Your players are crying. What do you say to them?",
                'responses': {
                    'deflect': "I don't need to say anything. They know.",
                    'accountable': "Thank you. That's it. Thank you for trusting the process.",
                    'confrontational': "We took what was ours. Nobody gave us a damn thing.",
                },
            },
            {
                'question': "Is this validation for how you've built this team?",
                'responses': {
                    'deflect': "I'm not thinking about validation right now.",
                    'accountable': "It proves the people in this building are the right people.",
                    'confrontational': "I don't need validation. I need another one.",
                },
            },
            {
                'question': "What now?",
                'responses': {
                    'deflect': "Now I go home.",
                    'accountable': "We savor this. Then we start defending it.",
                    'confrontational': "Now they know we're coming for more.",
                },
            },
        ],
    },

    # ======================================================================
    # DYNASTY_MILESTONE
    # ======================================================================
    {
        'id': 'dynasty_milestone_A',
        'trigger': 'dynasty_milestone',
        'questions': [
            {
                'question': "Coach, you've officially built a dynasty. How does that word feel?",
                'responses': {
                    'deflect': "It's just a word.",
                    'accountable': "Heavy. And earned. By everyone in this building.",
                    'confrontational': "It feels like people finally ran out of excuses to deny it.",
                },
            },
            {
                'question': "What separates a dynasty from a team that just wins a lot?",
                'responses': {
                    'deflect': "Consistency, I suppose.",
                    'accountable': "Sacrifice. The guys who took less money to stay. The ones who chose the mission.",
                    'confrontational': "Dominance. We didn't sneak in. We broke the door down every year.",
                },
            },
        ],
    },
    {
        'id': 'dynasty_milestone_B',
        'trigger': 'dynasty_milestone',
        'questions': [
            {
                'question': "When you took over, did you envision something like this?",
                'responses': {
                    'deflect': "I tried not to envision anything. Just work.",
                    'accountable': "Honestly? No. This exceeded even my most optimistic projections.",
                    'confrontational': "Absolutely. I told the owner day one. He probably thought I was crazy.",
                },
            },
            {
                'question': "Legacy is a loaded word in this sport. Are you comfortable with yours?",
                'responses': {
                    'deflect': "Legacy is for retired people.",
                    'accountable': "I'm proud of what we've built. But it's fragile. We protect it daily.",
                    'confrontational': "My legacy speaks for itself. Loudly.",
                },
            },
            {
                'question': "What keeps you hungry after achieving what most never will?",
                'responses': {
                    'deflect': "Habit, mostly.",
                    'accountable': "The guys who haven't gotten their ring yet. I owe them one.",
                    'confrontational': "The people still betting against us. I hear every one of them.",
                },
            },
        ],
    },
    {
        'id': 'dynasty_milestone_C',
        'trigger': 'dynasty_milestone',
        'questions': [
            {
                'question': "Coach, pundits are calling this the most dominant stretch in league history. Fair?",
                'responses': {
                    'deflect': "I don't watch pundits.",
                    'accountable': "I won't compare to what came before. But this group deserves that kind of praise.",
                    'confrontational': "Fair? It's generous. They should say it louder.",
                },
            },
            {
                'question': "At what cost has this dynasty come?",
                'responses': {
                    'deflect': "Everything has a cost.",
                    'accountable': "Sleep. Family time. Players we loved who had to move on. Real cost.",
                    'confrontational': "Ask the thirty-one other teams about cost.",
                },
            },
        ],
    },

    # ======================================================================
    # PLAYOFF_LOSS
    # ======================================================================
    {
        'id': 'playoff_loss_A',
        'trigger': 'playoff_loss',
        'questions': [
            {
                'question': "Coach, your season is over. {round_name} exit against {opponent}. What happened?",
                'responses': {
                    'deflect': "They made more plays. That's the game.",
                    'accountable': "We weren't good enough when it mattered. That's on me.",
                    'confrontational': "I'm not going to dissect this for you right now. Not tonight.",
                },
            },
            {
                'question': "This team had championship expectations. How do you process falling short?",
                'responses': {
                    'deflect': "One day at a time.",
                    'accountable': "It's gutting. I told these guys we'd get there. I have to live with that.",
                    'confrontational': "Falling short? We were in the playoffs. Count how many teams weren't.",
                },
            },
            {
                'question': "Is this team's window still open?",
                'responses': {
                    'deflect': "We'll evaluate everything in the offseason.",
                    'accountable': "It better be. I'm not done. These players aren't done.",
                    'confrontational': "Anyone writing us off can save their draft articles. We'll be back.",
                },
            },
        ],
    },
    {
        'id': 'playoff_loss_B',
        'trigger': 'playoff_loss',
        'questions': [
            {
                'question': "You lost {score} in the {round_name}. Did you have this team prepared?",
                'responses': {
                    'deflect': "I thought so.",
                    'accountable': "Clearly not enough. The preparation is my responsibility.",
                    'confrontational': "That question is insulting and you know it.",
                },
            },
            {
                'question': "What do you say to fans who expected more?",
                'responses': {
                    'deflect': "I understand their frustration.",
                    'accountable': "They deserved better. We all know it. Nobody's hiding from that.",
                    'confrontational': "I don't answer to fans through a microphone. I answer with wins.",
                },
            },
        ],
    },
    {
        'id': 'playoff_loss_C',
        'trigger': 'playoff_loss',
        'questions': [
            {
                'question': "The locker room was silent after that loss. What's the mood?",
                'responses': {
                    'deflect': "Quiet. Appropriately quiet.",
                    'accountable': "Hurt. Real hurt. These men gave everything and came up short.",
                    'confrontational': "You don't need me to tell you what losing feels like. Use your imagination.",
                },
            },
            {
                'question': "Will there be changes this offseason?",
                'responses': {
                    'deflect': "Too early to discuss.",
                    'accountable': "There have to be. Staying the same isn't an option after this.",
                    'confrontational': "Changes happen when I decide they happen. Not at this podium.",
                },
            },
        ],
    },

    # ======================================================================
    # STAR_INJURY
    # ======================================================================
    {
        'id': 'star_injury_A',
        'trigger': 'star_injury',
        'questions': [
            {
                'question': "Coach, {star_name} is out for the season. How does this change things?",
                'responses': {
                    'deflect': "Next man up. That's always been the philosophy.",
                    'accountable': "It changes everything. He's irreplaceable. We all know that.",
                    'confrontational': "You want me to stand here and say we're fine? We lost our best player.",
                },
            },
            {
                'question': "What did you say to {star_name} after the diagnosis?",
                'responses': {
                    'deflect': "That's between us.",
                    'accountable': "That we'd still be here when he comes back. That this isn't the end.",
                    'confrontational': "I told him to watch us win without him. Fuel for his rehab.",
                },
            },
        ],
    },
    {
        'id': 'star_injury_B',
        'trigger': 'star_injury',
        'questions': [
            {
                'question': "{star_name} — season-ending injury. What's your honest reaction?",
                'responses': {
                    'deflect': "It's football. These things happen.",
                    'accountable': "Devastated. For him more than us. He worked all offseason for this.",
                    'confrontational': "Sick. I'm sick about it. And I'm angry. But that doesn't help anyone.",
                },
            },
            {
                'question': "Can this team still compete without a {position} of that caliber?",
                'responses': {
                    'deflect': "We'll find out.",
                    'accountable': "It'll take all of us doing more. Every single person in this building.",
                    'confrontational': "We better. Because I'm not lowering the standard.",
                },
            },
            {
                'question': "Does this change your plans for the trade deadline?",
                'responses': {
                    'deflect': "I'm not going to speculate on transactions.",
                    'accountable': "We have to be creative now. All options are on the table.",
                    'confrontational': "If there's a move to make, I'll make it. I don't wait for permission.",
                },
            },
        ],
    },
    {
        'id': 'star_injury_C',
        'trigger': 'star_injury',
        'questions': [
            {
                'question': "Losing {star_name} to injury — is this a season-defining moment?",
                'responses': {
                    'deflect': "Every week is defining. This one's no different.",
                    'accountable': "It's a gut punch. But defining moments are how you respond, not what hits you.",
                    'confrontational': "Defining? Only if we let it define us. And we won't.",
                },
            },
            {
                'question': "What does the depth chart look like at {position} now?",
                'responses': {
                    'deflect': "We'll announce that when we're ready.",
                    'accountable': "Thinner than I'd like. But someone's going to step up. They always do here.",
                    'confrontational': "That's an internal matter. You'll see on Sunday who plays.",
                },
            },
        ],
    },

    # ======================================================================
    # BLOCKBUSTER_TRADE
    # ======================================================================
    {
        'id': 'blockbuster_trade_A',
        'trigger': 'blockbuster_trade',
        'questions': [
            {
                'question': "Coach, you just made a blockbuster trade. What was the thinking?",
                'responses': {
                    'deflect': "We felt it was the right move for the organization.",
                    'accountable': "We saw a chance to get better and we took it. Simple as that.",
                    'confrontational': "While everyone else talks, we act. That's the difference.",
                },
            },
            {
                'question': "Some are calling this a gamble. Is it?",
                'responses': {
                    'deflect': "Everything in this league is uncertain.",
                    'accountable': "It's a calculated risk. We did our homework. I believe in this move.",
                    'confrontational': "A gamble? Sitting still is the gamble. This is conviction.",
                },
            },
        ],
    },
    {
        'id': 'blockbuster_trade_B',
        'trigger': 'blockbuster_trade',
        'questions': [
            {
                'question': "The trade involving {star_name} — walk us through that decision.",
                'responses': {
                    'deflect': "These decisions are never simple. We weighed everything.",
                    'accountable': "Hardest call I've made this year. But I trust the evaluation.",
                    'confrontational': "I don't owe anyone a play-by-play of my decision making.",
                },
            },
            {
                'question': "How does the locker room absorb a move like this?",
                'responses': {
                    'deflect': "They're professionals. They'll handle it.",
                    'accountable': "It shakes people. I talked to the leaders first. They understand the why.",
                    'confrontational': "If anyone in that locker room can't handle roster moves, this isn't the place for them.",
                },
            },
            {
                'question': "What does this say about your timeline?",
                'responses': {
                    'deflect': "It says we're building.",
                    'accountable': "It says we're not afraid to make uncomfortable moves for the future.",
                    'confrontational': "It says I'm all in. Right now. Not three years from now.",
                },
            },
        ],
    },
    {
        'id': 'blockbuster_trade_C',
        'trigger': 'blockbuster_trade',
        'questions': [
            {
                'question': "A first-round pick changed hands today. That's a big bet.",
                'responses': {
                    'deflect': "Picks are assets. Sometimes you spend them.",
                    'accountable': "A first-rounder for a proven commodity. I'd make that trade again tomorrow.",
                    'confrontational': "Draft picks are lottery tickets. I prefer sure things.",
                },
            },
            {
                'question': "Will fans understand this move six months from now?",
                'responses': {
                    'deflect': "I hope so.",
                    'accountable': "They will when they see what we're building on the field.",
                    'confrontational': "I don't make moves for approval. I make them to win.",
                },
            },
        ],
    },

    # ======================================================================
    # BLOWN_LEAD (stub — templates exist but trigger never fires)
    # ======================================================================
    {
        'id': 'blown_lead_A',
        'trigger': 'blown_lead',
        'questions': [
            {
                'question': "You were up big. Then it unraveled. What went wrong?",
                'responses': {
                    'deflect': "Momentum shifted. That's football.",
                    'accountable': "We took our foot off the gas. I let us get comfortable. Never again.",
                    'confrontational': "We gave that game away. Handed it to them. It won't happen twice.",
                },
            },
            {
                'question': "Can this team close games?",
                'responses': {
                    'deflect': "We'll get there.",
                    'accountable': "Today says no. But I believe in this group more than one bad quarter.",
                    'confrontational': "One collapse doesn't define us. Write whatever you want.",
                },
            },
        ],
    },
    {
        'id': 'blown_lead_B',
        'trigger': 'blown_lead',
        'questions': [
            {
                'question': "That second half was a disaster. Do you trust your players in crunch time?",
                'responses': {
                    'deflect': "I trust the process.",
                    'accountable': "I trust them. But trust doesn't fix execution. We have to be better.",
                    'confrontational': "I trust the players who want to be here. The rest know where the door is.",
                },
            },
            {
                'question': "Are you concerned about the mental toughness of this roster?",
                'responses': {
                    'deflect': "I'm concerned about getting better. That's it.",
                    'accountable': "Today tested us and we failed the test. We'll address it.",
                    'confrontational': "Mental toughness? We'll find out who has it real fast.",
                },
            },
        ],
    },
    {
        'id': 'blown_lead_C',
        'trigger': 'blown_lead',
        'questions': [
            {
                'question': "Sixteen-point lead. Gone. How do you explain that to the owner?",
                'responses': {
                    'deflect': "I'll handle that conversation privately.",
                    'accountable': "I tell him the truth. We didn't finish. And it starts with me.",
                    'confrontational': "The owner doesn't need an explanation. He needs a coach who fixes it. That's me.",
                },
            },
            {
                'question': "Is this a coaching failure or a player failure?",
                'responses': {
                    'deflect': "It's a team loss.",
                    'accountable': "Coaching. Always coaching first. I put them in those situations.",
                    'confrontational': "Don't try to split us apart. We win together, lose together.",
                },
            },
        ],
    },

    # ======================================================================
    # HOLDOUT_PUBLIC
    # ======================================================================
    {
        'id': 'holdout_public_A',
        'trigger': 'holdout_public',
        'questions': [
            {
                'question': "{star_name} is holding out. The fans want answers. What's the situation?",
                'responses': {
                    'deflect': "Contract matters stay internal.",
                    'accountable': "He wants to be paid what he's worth. I respect that. We're working on it.",
                    'confrontational': "He can hold out all he wants. We play football with the men who show up.",
                },
            },
            {
                'question': "Is there a rift between you and {star_name}?",
                'responses': {
                    'deflect': "No.",
                    'accountable': "There's frustration. On both sides. But there's no broken relationship here.",
                    'confrontational': "A rift? We have a disagreement about money. That's business. Don't dramatize it.",
                },
            },
        ],
    },
    {
        'id': 'holdout_public_B',
        'trigger': 'holdout_public',
        'questions': [
            {
                'question': "Your star {position} won't report. How does that affect the locker room?",
                'responses': {
                    'deflect': "The guys in the building are focused on their jobs.",
                    'accountable': "It creates tension. I won't pretend it doesn't. We're all human.",
                    'confrontational': "The locker room belongs to the guys who show up. Period.",
                },
            },
            {
                'question': "At what point does a holdout become a distraction you can't manage?",
                'responses': {
                    'deflect': "We're not there.",
                    'accountable': "Every day it continues is another day of uncertainty. I feel the clock ticking.",
                    'confrontational': "It's not a distraction if I don't let it be one. And I won't.",
                },
            },
            {
                'question': "Would you trade {star_name} if this isn't resolved?",
                'responses': {
                    'deflect': "I'm not going to speculate on hypotheticals.",
                    'accountable': "I don't want to. But I'll do whatever's best for this franchise.",
                    'confrontational': "Nobody is untradeable. Everyone knows that.",
                },
            },
        ],
    },
    {
        'id': 'holdout_public_C',
        'trigger': 'holdout_public',
        'questions': [
            {
                'question': "{star_name}'s absence is the biggest story in the league right now. Your response?",
                'responses': {
                    'deflect': "I can't control what the media focuses on.",
                    'accountable': "It's a big story because he's a big player. I get it. We're handling it.",
                    'confrontational': "The biggest story should be how we're winning without him.",
                },
            },
            {
                'question': "Do you feel let down by a player choosing money over the team?",
                'responses': {
                    'deflect': "I don't judge anyone's financial decisions.",
                    'accountable': "It's not about feeling let down. It's about finding a solution that works for everyone.",
                    'confrontational': "Let down? He earned the right to negotiate. But so did we.",
                },
            },
        ],
    },

    # ======================================================================
    # LOSING_STREAK_3
    # ======================================================================
    {
        'id': 'losing_streak_3_A',
        'trigger': 'losing_streak_3',
        'questions': [
            {
                'question': "Three straight losses. Is this team in freefall?",
                'responses': {
                    'deflect': "It's a rough stretch. We'll work through it.",
                    'accountable': "Something is broken. I don't have all the answers yet. But I will.",
                    'confrontational': "Freefall? We lost three games. This isn't a funeral.",
                },
            },
            {
                'question': "Are you losing the locker room?",
                'responses': {
                    'deflect': "No.",
                    'accountable': "I looked them in the eyes today. They're still with me. Frustrated, but with me.",
                    'confrontational': "That's a lazy question and you know it. Next.",
                },
            },
            {
                'question': "What needs to change?",
                'responses': {
                    'deflect': "We'll look at the film.",
                    'accountable': "Execution. Discipline. Focus. And it starts with me setting a higher standard.",
                    'confrontational': "Effort. If effort doesn't change, personnel will.",
                },
            },
        ],
    },
    {
        'id': 'losing_streak_3_B',
        'trigger': 'losing_streak_3',
        'questions': [
            {
                'question': "Three losses in a row. Is your job safe?",
                'responses': {
                    'deflect': "That's not my concern right now.",
                    'accountable': "If it's not, I've earned whatever comes. But I intend to fix this.",
                    'confrontational': "You want to fire me? Get in line. I'm not going anywhere.",
                },
            },
            {
                'question': "The body language on the sideline looked defeated. Are your players giving up?",
                'responses': {
                    'deflect': "I wouldn't characterize it that way.",
                    'accountable': "There's frustration showing. I see it. We need a breakthrough.",
                    'confrontational': "Any player who's given up won't be here next week. I guarantee that.",
                },
            },
        ],
    },
    {
        'id': 'losing_streak_3_C',
        'trigger': 'losing_streak_3',
        'questions': [
            {
                'question': "The losing keeps mounting. What do you tell a fanbase that's running out of patience?",
                'responses': {
                    'deflect': "I understand their frustration.",
                    'accountable': "That I see it. That I own it. And that I'll fix it or answer for it.",
                    'confrontational': "Patience? We're not asking for patience. We're demanding better of ourselves.",
                },
            },
            {
                'question': "Have you considered making drastic changes to the lineup or scheme?",
                'responses': {
                    'deflect': "We evaluate everything weekly.",
                    'accountable': "Everything is on the table. Comfort zones are gone. Starting now.",
                    'confrontational': "Drastic? Nothing's drastic when you're losing. It's called urgency.",
                },
            },
            {
                'question': "Where does the accountability lie?",
                'responses': {
                    'deflect': "With all of us.",
                    'accountable': "Right here. This podium. It starts and ends with me.",
                    'confrontational': "You'll see accountability on the field. Not at press conferences.",
                },
            },
        ],
    },
]


# ============================================================
# LOOKUP FUNCTIONS
# ============================================================

def get_tier2_templates_by_trigger(trigger_type: str) -> list:
    """Get all templates matching a given trigger type."""
    return [t for t in TIER2_TEMPLATES if t['trigger'] == trigger_type]


def get_tier2_template_by_id(template_id: str) -> Optional[dict]:
    """Get a specific template by its ID."""
    for t in TIER2_TEMPLATES:
        if t['id'] == template_id:
            return t
    return None


def format_tier2_question(question_text: str, context: dict) -> str:
    """
    Format a question template with context values.

    Uses format_map with a fallback dict that returns '{key}' for missing keys,
    so missing placeholders don't crash.
    """
    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    return question_text.format_map(SafeDict(context))
