"""
Engine-only constants: narration templates, yard gain distributions,
and play subtypes. Too detailed for the main constants file.
"""

# ======================
# PLAY SUBTYPES
# ======================

# These are used internally by the engine to determine which matchups to resolve.
# The stored play_type in the DB stays as the broad category.

PASS_SUBTYPES = [
    'quick_out', 'slant', 'curl', 'dig', 'post',
    'go_route', 'screen', 'play_action', 'bootleg',
]

RUN_SUBTYPES = [
    'inside_zone', 'outside_zone', 'power', 'counter',
    'draw', 'sweep', 'toss', 'qb_sneak',
]

# ======================
# YARD GAIN DISTRIBUTIONS
# ======================

# Base yard distributions per play outcome (min, max) before variance
PASS_YARDS_BY_ZONE = {
    'short': (1, 7),
    'medium': (7, 15),
    'deep': (15, 28),
}

RUN_YARDS_BASE = (-1, 7)         # Base run play yard range
RUN_YARDS_GOOD_BLOCK = (3, 8)    # When OL wins convincingly
RUN_YARDS_BAD_BLOCK = (-2, 2)    # When DL dominates

# Scramble yards range
SCRAMBLE_YARDS = (-5, 15)

# Sack yard loss range
SACK_YARDS = (-12, -2)

# YAC (yards after catch) ranges by rating tier
YAC_RANGES = {
    'elite': (1, 10),     # YAC rating 85+
    'good': (0, 6),       # YAC rating 70-84
    'average': (0, 4),    # YAC rating 55-69
    'poor': (0, 2),       # YAC rating <55
}

# ======================
# SPECIAL TEAMS RANGES
# ======================

KICKOFF_TOUCHBACK_RATE = 0.55      # Base touchback probability
KICKOFF_RETURN_YARDS = (15, 35)    # If returned, base return yards
PUNT_YARDS_BASE = (35, 55)         # Base punt distance
PUNT_RETURN_YARDS = (0, 15)        # Base punt return yards

# FG accuracy modifiers by distance
FG_DISTANCE_MODIFIER = {
    'chip_shot': (0, 29, 0.97),    # (min, max, base_pct)
    'short': (30, 39, 0.88),
    'medium': (40, 49, 0.72),
    'long': (50, 59, 0.52),
    'extreme': (60, 70, 0.20),
}

# Extra point conversion rate
EXTRA_POINT_BASE_RATE = 0.94
TWO_POINT_BASE_RATE = 0.48

# Punt return modifiers
PUNT_DISTANCE_VARIANCE = (-5, 5)        # Variance when avoiding touchback
FAIR_CATCH_PROBABILITY = 0.40           # Base fair catch rate
PUNT_RETURN_BONUS_GOOD = (3, 15)        # Bonus yards for good returners (rating 80+)
PUNT_RETURN_RATING_GOOD = 80            # Rating threshold for return bonus
PUNT_RETURN_PENALTY = 3                 # Yards lost for poor returners
PUNT_RETURN_RATING_POOR = 50            # Rating threshold for return penalty
PUNT_BIG_RETURN_PROBABILITY = 0.03      # Chance of explosive return
PUNT_BIG_RETURN_RATING_MIN = 70         # Minimum rating for big return chance
PUNT_BIG_RETURN_YARDS = (20, 50)        # Extra yards on big return

# Kickoff return modifiers
KICKOFF_RETURN_BONUS_GOOD = (5, 15)     # Bonus yards for good returners (rating 80+)
KICKOFF_RETURN_RATING_GOOD = 80         # Rating threshold for return bonus
KICKOFF_RETURN_PENALTY = 5              # Yards lost for poor returners
KICKOFF_RETURN_RATING_POOR = 50         # Rating threshold for return penalty
KICKOFF_BIG_RETURN_PROBABILITY = 0.02   # Chance of explosive return
KICKOFF_BIG_RETURN_RATING_MIN = 75      # Minimum rating for big return chance
KICKOFF_BIG_RETURN_YARDS = (20, 60)     # Extra yards on big return

# ======================
# NARRATION TEMPLATES
# ======================

# Pass play narrations
PASS_COMPLETE_TEMPLATES = [
    "{qb} drops back, finds {receiver} {route_desc} for a {yards}-yard gain.",
    "{qb} throws to {receiver} on the {route_desc}. Caught for {yards} yards.",
    "{qb} connects with {receiver} over the {coverage_desc} for {yards}.",
    "{qb} hits {receiver} in stride for a {yards}-yard completion.",
    "Quick pass from {qb} to {receiver}. Gain of {yards}.",
]

PASS_COMPLETE_BIG_PLAY_TEMPLATES = [
    "{qb} launches a deep ball to {receiver} who hauls it in for a {yards}-yard gain!",
    "{qb} fires a strike to {receiver} who breaks free for {yards} yards!",
    "{receiver} gets behind the defense! {qb} delivers a perfect throw for {yards} yards!",
]

PASS_COMPLETE_TD_TEMPLATES = [
    "{qb} finds {receiver} in the end zone! TOUCHDOWN! {yards}-yard scoring strike!",
    "TOUCHDOWN! {qb} to {receiver} for {yards} yards! What a throw!",
    "{receiver} reaches up and pulls it down in the end zone! {yards}-yard TD from {qb}!",
]

PASS_INCOMPLETE_TEMPLATES = [
    "{qb} throws to {receiver}... pass is incomplete.",
    "{qb} fires toward {receiver}, broken up by {defender}.",
    "{qb} overthrows {receiver}. Incomplete.",
    "Pass intended for {receiver} falls incomplete. {defender} was in coverage.",
    "{qb}'s throw is off target. {receiver} can't make the catch.",
]

INTERCEPTION_TEMPLATES = [
    "{defender} picks off {qb}! The pass intended for {receiver} is intercepted!",
    "INTERCEPTED! {defender} reads {qb}'s throw and picks it off!",
    "{qb}'s pass is tipped and {defender} comes down with it! Interception!",
]

SACK_TEMPLATES = [
    "{defender} breaks through and sacks {qb} for a loss of {yards}!",
    "{qb} is brought down behind the line by {defender}! Loss of {yards}.",
    "The pocket collapses! {defender} gets to {qb} for a {yards}-yard sack.",
]

SCRAMBLE_TEMPLATES = [
    "{qb} scrambles out of the pocket for {yards} yards.",
    "{qb} tucks it and runs, gaining {yards} before sliding.",
    "Nothing open downfield. {qb} takes off and picks up {yards}.",
]

# Run play narrations
RUN_TEMPLATES = [
    "{runner} takes the handoff {direction} for {yards} yards.",
    "{runner} hits the {direction} hole for a gain of {yards}.",
    "{runner} carries it {direction} for {yards} before being brought down by {defender}.",
    "Handoff to {runner}. {yards}-yard gain up the {direction}.",
]

RUN_BIG_PLAY_TEMPLATES = [
    "{runner} bursts through the {direction} side for {yards} yards!",
    "{runner} breaks a tackle and races for {yards}! Big run!",
    "{runner} finds a seam and takes off for {yards} yards!",
]

RUN_TD_TEMPLATES = [
    "{runner} punches it in from {yards} yards out! TOUCHDOWN!",
    "TOUCHDOWN! {runner} takes it {direction} for {yards} yards to score!",
    "{runner} dives into the end zone! {yards}-yard TD run!",
]

RUN_LOSS_TEMPLATES = [
    "{runner} is stuffed at the line by {defender}. Loss of {loss_yards}.",
    "{defender} meets {runner} in the backfield for a {loss_yards}-yard loss.",
    "No room for {runner}. Tackled for a loss of {loss_yards} by {defender}.",
]

FUMBLE_TEMPLATES = [
    "{runner} is hit hard and loses the ball! FUMBLE! {defender} recovers!",
    "The ball is loose! {runner} fumbles and {defender} falls on it!",
    "{defender} strips the ball from {runner}! Fumble recovered by the defense!",
]

# Special teams narrations
FG_GOOD_TEMPLATES = [
    "{kicker} lines up the {distance}-yard attempt... it's GOOD!",
    "The {distance}-yard field goal by {kicker} is up... and it's good!",
    "{kicker} nails the {distance}-yarder! Field goal is good!",
]

FG_MISS_TEMPLATES = [
    "{kicker}'s {distance}-yard attempt is... no good. Wide {direction}.",
    "The {distance}-yard field goal by {kicker} misses {direction}.",
    "{kicker} pushes the {distance}-yard attempt wide {direction}. No good.",
]

FG_BLOCKED_TEMPLATES = [
    "The {distance}-yard attempt by {kicker} is BLOCKED!",
    "{kicker}'s kick is blocked at the line! No good!",
]

PUNT_TEMPLATES = [
    "{punter} punts it {distance} yards to the {yard_line}.",
    "{punter} booms a {distance}-yard punt.",
    "A {distance}-yard punt by {punter}. Fair catch at the {yard_line}.",
]

KICKOFF_TEMPLATES = [
    "{kicker} kicks it deep. Touchback.",
    "Kickoff by {kicker}. Returned to the {yard_line} by {returner}.",
    "{kicker}'s kickoff is returned by {returner} to the {yard_line}.",
]

XP_GOOD_TEMPLATES = [
    "{kicker}'s extra point is good.",
    "PAT is good. {kicker} adds the extra point.",
]

XP_MISS_TEMPLATES = [
    "{kicker}'s extra point attempt is NO GOOD!",
    "The extra point is missed by {kicker}!",
]

TWO_POINT_GOOD_TEMPLATES = [
    "Two-point conversion is GOOD! {player} scores!",
    "They go for two and get it! {player} into the end zone!",
]

TWO_POINT_FAIL_TEMPLATES = [
    "Two-point attempt fails. {player} is stopped short.",
    "Going for two... no good. {player} can't get in.",
]

# Penalty narrations
PENALTY_TEMPLATES = [
    "FLAG on the play. {penalty_type} on {team_name}. {yards}-yard penalty.",
    "Penalty flag: {penalty_type}, {team_name}. {yards} yards.",
]

# Quarter/game state narrations
QUARTER_START_TEMPLATES = [
    "--- Start of Q{quarter} ---",
]

HALFTIME_TEMPLATE = "--- HALFTIME ---"
OVERTIME_TEMPLATE = "--- OVERTIME ---"
GAME_END_TEMPLATE = "--- FINAL: {away_team} {away_score}, {home_team} {home_score} ---"

# Two-minute warning
TWO_MINUTE_WARNING_TEMPLATE = "--- Two-Minute Warning ---"

# Drive summary
DRIVE_SUMMARY_TEMPLATE = "{team} drive: {plays} plays, {yards} yards, {result}."

# Coin toss
COIN_TOSS_TEMPLATE = "{winner} wins the coin toss and elects to {choice}."

# Run directions for narration
RUN_DIRECTIONS = ['left', 'right', 'up the middle', 'off left tackle', 'off right tackle']

# Route descriptions for narration
ROUTE_DESCRIPTIONS = [
    'on a quick out', 'on a slant', 'over the middle',
    'on a deep post', 'down the sideline', 'on a crossing route',
    'on a curl route', 'on a screen', 'on a wheel route',
]

# Coverage descriptions for narration
COVERAGE_DESCRIPTIONS = [
    'over the middle', 'along the sideline', 'in tight coverage',
    'in single coverage', 'against zone coverage',
]
