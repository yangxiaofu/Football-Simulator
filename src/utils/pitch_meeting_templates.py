"""Pitch meeting narrative templates (Phase 5 P7).

Each template is a dict:
  signal_type:  one of PITCH_SIGNAL_TYPES
  intensity:    'low' | 'medium' | 'high'
  template:     string with {TOKEN} placeholders
  match:        optional lambda(ctx: dict) -> bool; absent = signal_type match is sufficient

Valid tokens: {PLAYER_NAME}, {POSITION}, {TEAM_NAME}, {RIVAL_TEAM_NAME}, {AGENT_NAME},
              {OFFER_YEARS}, {OFFER_VALUE_M}
"""

from ..utils.constants import (
    PITCH_SIGNAL_INTEREST_LEVEL,
    PITCH_SIGNAL_COMPETING_OFFER,
    PITCH_SIGNAL_AGENT_POSTURE,
    PITCH_SIGNAL_FIT_VIBE,
    PITCH_SIGNAL_MONEY_PRIMARY,
    PITCH_SIGNAL_WINNING_PRIMARY,
)

PITCH_TEMPLATES = [
    # ── interest_level (4 templates) ──────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_INTEREST_LEVEL,
        'intensity': 'high',
        'template': (
            "{PLAYER_NAME} leaned forward the moment your staff walked in. "
            "His body language said it all — this is a meeting he wanted to have."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_INTEREST_LEVEL,
        'intensity': 'high',
        'template': (
            "Sources close to {AGENT_NAME} say {PLAYER_NAME} has been asking "
            "about {TEAM_NAME} for weeks. He showed up today ready to listen."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_INTEREST_LEVEL,
        'intensity': 'medium',
        'template': (
            "{PLAYER_NAME} was professional but guarded. He's keeping his options "
            "open and wants to see the full picture before committing to anyone."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_INTEREST_LEVEL,
        'intensity': 'low',
        'template': (
            "{AGENT_NAME} controlled every moment of the meeting. "
            "{PLAYER_NAME} barely spoke — he's letting his representation do the "
            "talking while he weighs a crowded field of suitors."
        ),
    },

    # ── competing_offer (4 templates) ─────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_COMPETING_OFFER,
        'intensity': 'high',
        'template': (
            "Before the pleasantries were over, {AGENT_NAME} slid a sheet across "
            "the table. {RIVAL_TEAM_NAME} has already made a strong offer. "
            "You're being asked to beat it."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_COMPETING_OFFER,
        'intensity': 'medium',
        'template': (
            "{AGENT_NAME} mentioned — casually, almost too casually — that "
            "{RIVAL_TEAM_NAME} reached out. No number yet, but the interest is real. "
            "The clock is ticking."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_COMPETING_OFFER,
        'intensity': 'low',
        'template': (
            "Word is circulating that {PLAYER_NAME} has drawn attention from "
            "{RIVAL_TEAM_NAME}. Nothing concrete yet, but {AGENT_NAME} didn't "
            "deny it when asked."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_COMPETING_OFFER,
        'intensity': 'high',
        'match': lambda ctx: True,
        'template': (
            "This meeting has a deadline baked in. {AGENT_NAME} made clear that "
            "{RIVAL_TEAM_NAME} is waiting on an answer — if {TEAM_NAME} wants "
            "{PLAYER_NAME}, the offer needs to come fast."
        ),
    },

    # ── agent_posture (4 templates) ────────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_AGENT_POSTURE,
        'intensity': 'high',
        'template': (
            "{AGENT_NAME} opened with a number before your scouts could pull "
            "out a chair. This isn't a listening tour — it's a negotiation, "
            "and he's setting the terms."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_AGENT_POSTURE,
        'intensity': 'medium',
        'template': (
            "{AGENT_NAME} was cordial but pointed. Every question circled back "
            "to guaranteed money. {PLAYER_NAME} may prefer {TEAM_NAME}, but his "
            "representation will make sure the ledger reflects that."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_AGENT_POSTURE,
        'intensity': 'low',
        'template': (
            "{AGENT_NAME} played it relaxed, almost dismissive. "
            "Hard to tell if that's a power move or genuine disinterest — "
            "either way, {PLAYER_NAME} holds the leverage in this room."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_AGENT_POSTURE,
        'intensity': 'high',
        'match': lambda ctx: True,
        'template': (
            "The meeting barely started before {AGENT_NAME} put a floor on the "
            "conversation. Below a certain number, he said, {PLAYER_NAME} won't "
            "be available — to anyone. They mean it."
        ),
    },

    # ── fit_vibe (4 templates) ─────────────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_FIT_VIBE,
        'intensity': 'high',
        'template': (
            "When your coordinator walked through the scheme on the whiteboard, "
            "{PLAYER_NAME}'s eyes lit up. He's been waiting for a system that "
            "plays to what he does naturally — and this looks like it."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_FIT_VIBE,
        'intensity': 'medium',
        'template': (
            "{PLAYER_NAME} had specific questions about his role — not the "
            "spotlight, but the alignment. He wants to know where he fits "
            "before he buys in."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_FIT_VIBE,
        'intensity': 'low',
        'template': (
            "The scheme conversation got quiet fast. {PLAYER_NAME} has heard "
            "pitches before, and he's learned to read between the lines. "
            "He'll need more than a highlight reel to be convinced."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_FIT_VIBE,
        'intensity': 'medium',
        'match': lambda ctx: True,
        'template': (
            "{PLAYER_NAME} asked about the offensive staff's philosophy before "
            "anyone mentioned money. Scheme fit is the real filter here — "
            "get that right and the rest follows."
        ),
    },

    # ── money_primary (3 templates) ────────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_MONEY_PRIMARY,
        'intensity': 'high',
        'template': (
            "{AGENT_NAME} didn't mince words: {PLAYER_NAME} wants to be the "
            "highest-paid {POSITION} in the league, or close to it. "
            "Fit matters, but not as much as the number at the top of the contract."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_MONEY_PRIMARY,
        'intensity': 'medium',
        'template': (
            "The meeting circled back to guaranteed money three times. "
            "{PLAYER_NAME} wants security, not just a big AAV. Structure matters "
            "as much as the headline figure."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_MONEY_PRIMARY,
        'intensity': 'high',
        'match': lambda ctx: True,
        'template': (
            "{AGENT_NAME} dropped a competing number to frame the ceiling. "
            "Any offer from {TEAM_NAME} needs to clear that bar — "
            "or {PLAYER_NAME} doesn't need a follow-up meeting."
        ),
    },

    # ── winning_primary (4 templates) ─────────────────────────────────────────

    {
        'signal_type': PITCH_SIGNAL_WINNING_PRIMARY,
        'intensity': 'high',
        'template': (
            "{PLAYER_NAME} leaned across the table and asked one question: "
            "'Do you think we can win a championship?' "
            "Your answer to that is the only thing that matters in this room."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_WINNING_PRIMARY,
        'intensity': 'medium',
        'template': (
            "He's been on losing rosters long enough. {PLAYER_NAME} told your "
            "scouts that he'd leave money on the table for a real shot — "
            "but only if the roster is built to compete now."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_WINNING_PRIMARY,
        'intensity': 'low',
        'template': (
            "{PLAYER_NAME} brought up {RIVAL_TEAM_NAME}'s playoff run without "
            "prompting. He's tracking contenders, not contracts. "
            "{TEAM_NAME} needs to sell the vision, not just the cap room."
        ),
    },
    {
        'signal_type': PITCH_SIGNAL_WINNING_PRIMARY,
        'intensity': 'high',
        'match': lambda ctx: True,
        'template': (
            "{AGENT_NAME} confirmed it plainly: his client will take a discount "
            "for a legitimate contender. {TEAM_NAME}'s pitch needs to be about "
            "trophies, not paychecks."
        ),
    },
]
