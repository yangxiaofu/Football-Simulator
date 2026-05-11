"""
Game constants and tuning values for Football Simulator.

CRITICAL: All numeric values used in simulation, generation, or business logic
must be defined here. Never inline magic numbers in code.

If you need a constant that doesn't exist here, add it to this file first,
then use it in your code.
"""

# ======================
# LEAGUE STRUCTURE
# ======================

NUM_TEAMS = 32
NUM_CONFERENCES = 2
NUM_DIVISIONS = 8
TEAMS_PER_DIVISION = 4

CONFERENCE_NAMES = ['AFC', 'NFC']

DIVISION_NAMES = [
    'AFC North', 'AFC South', 'AFC East', 'AFC West',
    'NFC North', 'NFC South', 'NFC East', 'NFC West'
]

# ======================
# ROSTER LIMITS
# ======================

ACTIVE_ROSTER_SIZE = 53
PRACTICE_SQUAD_SIZE = 16
INJURED_RESERVE_SIZE = 99  # unlimited for IR
MAX_CONTRACT_YEARS = 6
FRANCHISE_TAG_LIMIT = 1  # per team per year

# Minimum players per position to field a game day roster.
# Roster cuts must never drop a position below this floor.
POSITION_MINIMUM_ROSTER = {
    'QB': 1, 'RB': 1, 'WR': 2, 'TE': 1, 'OL': 5,
    'DL': 3, 'LB': 2, 'CB': 2, 'S': 1,
    'K': 1, 'P': 1,
}

# ======================
# POSITIONS
# ======================

# All positions in the game
ALL_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P']

# Offensive positions
OFFENSE_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OL']

# Defensive positions
DEFENSE_POSITIONS = ['DL', 'LB', 'CB', 'S']

# Special teams positions
SPECIAL_TEAMS_POSITIONS = ['K', 'P']

# Skill positions (for receiving stats)
SKILL_POSITIONS = ['WR', 'RB', 'TE']

# Typical roster composition (for generation)
ROSTER_COMPOSITION = {
    'QB': 3,
    'RB': 4,
    'WR': 6,
    'TE': 3,
    'OL': 9,
    'DL': 8,
    'LB': 7,
    'CB': 6,
    'S': 5,
    'K': 1,
    'P': 1,
}  # Total: 53

# ======================
# RATINGS
# ======================

RATING_MIN = 1
RATING_MAX = 99

# Letter grade thresholds (true rating → letter grade)
# Anything below 60 → "F"
LETTER_GRADE_THRESHOLDS = {
    97: "A+",
    93: "A",
    90: "A-",
    87: "B+",
    83: "B",
    80: "B-",
    77: "C+",
    73: "C",
    70: "C-",
    67: "D+",
    60: "D",
}

# Development trait rarities (for player generation)
DEVELOPMENT_TRAIT_WEIGHTS = {
    'superstar': 0.02,   # 2% of players
    'star': 0.10,        # 10% of players
    'normal': 0.70,      # 70% of players
    'slow': 0.18,        # 18% of players
}

# Age distributions for generated rosters
AGE_DISTRIBUTION = {
    'rookie': 0.20,      # 20% age 22-23
    'young': 0.30,       # 30% age 24-26
    'prime': 0.30,       # 30% age 27-29
    'veteran': 0.15,     # 15% age 30-32
    'old': 0.05,         # 5% age 33+
}

AGE_RANGES = {
    'rookie': (22, 23),
    'young': (24, 26),
    'prime': (27, 29),
    'veteran': (30, 32),
    'old': (33, 36),
}

# ======================
# SIMULATION ENGINE
# ======================

# Matchup probability (logistic function)
MATCHUP_K = 0.07  # Curve steepness - adjust only after 500+ test games

# Play outcome modifiers
VARIANCE_CAP = 15  # Max random modifier per play
BIG_PLAY_RATE = 0.08  # Probability of 20+ yard gain
TURNOVER_BASE_RATE = 0.010  # Base per-play fumble/INT probability

# Home field advantage
HOME_FIELD_MODIFIER = 3  # SAR bonus for home team

# Play type thresholds
BIG_PLAY_YARDS = 20  # Yards needed to flag a play as "big"
CHUNK_PLAY_YARDS = 10  # Medium gain threshold

# ======================
# INJURY SYSTEM
# ======================

BASE_INJURY_RATE = 0.004  # Per play baseline (0.4%)
FATIGUE_INJURY_MULTIPLIER = 1.3  # Applied when stamina < 40%

# High-contact situation multipliers (GDD Layer 2 §5.2)
INJURY_MULTIPLIERS = {
    'sack': 3.5,
    'goal_line': 2.5,
    'scramble': 2.8,
    'kickoff_return': 2.0,
    'punt_coverage': 1.8,
    'high_speed_collision': 2.0,
    'jump_ball': 2.2,
}

# Injury severity probabilities (GDD Layer 2 §5.3 — 6 tiers)
INJURY_SEVERITY_WEIGHTS = {
    'questionable': 0.50,       # miss 0-1 games
    'week_to_week': 0.25,       # miss 2-4 games
    'ir_short': 0.12,           # miss 5-8 games
    'ir_season_ending': 0.08,   # remainder of season
    'career_altering': 0.04,    # permanent -5 to -15 attribute reduction
    'career_ending': 0.01,      # immediate retirement
}

# Injury duration ranges (in weeks)
INJURY_DURATION = {
    'questionable': (0, 1),
    'week_to_week': (2, 4),
    'ir_short': (5, 8),
    'ir_season_ending': (9, 17),
    'career_altering': (6, 17),
    'career_ending': (99, 99),  # permanent
}

# Career-altering injury attribute reduction range
CAREER_ALTERING_REDUCTION = (-15, -5)

# ======================
# FATIGUE SYSTEM
# ======================

STAMINA_MAX = 100
STAMINA_REGEN_PER_WEEK = 100  # Full recovery each week

# Stamina thresholds and penalties
STAMINA_MILD_THRESHOLD = 60  # Below this: -3 to all ratings
STAMINA_MODERATE_THRESHOLD = 40  # Below this: -8 to all ratings
STAMINA_SEVERE_THRESHOLD = 20  # Below this: -15 to all ratings + 2x injury rate

STAMINA_PENALTIES = {
    'mild': -3,
    'moderate': -8,
    'severe': -15,
}

# Season wear (cumulative fatigue)
SEASON_WEAR_START_WEEK = 10  # Begins accumulating after Week 10

# Position-specific wear rates (per snap)
WEAR_RATE_BY_POSITION = {
    'QB': 0.15,
    'RB': 0.35,
    'WR': 0.20,
    'TE': 0.25,
    'OL': 0.30,
    'DL': 0.30,
    'LB': 0.28,
    'CB': 0.22,
    'S': 0.20,
    'K': 0.05,
    'P': 0.05,
}

# ======================
# SALARY CAP
# ======================

SALARY_CAP_YEAR_ONE = 255_000_000  # Starting salary cap (in dollars)
CAP_INFLATION_RATE = 0.05  # 5% annual increase

# Contract structure limits
MIN_PLAYER_SALARY = 750_000  # League minimum
MAX_SIGNING_BONUS_PERCENT = 0.50  # 50% of total value
MAX_GUARANTEED_PERCENT = 1.00  # 100% of total value

# Franchise tag values (% of position cap average)
FRANCHISE_TAG_MULTIPLIER = 1.20  # 120% of top 5 position average

# ======================
# CONTRACT SYSTEM
# ======================

# Contract structure
MIN_CONTRACT_YEARS = 1
VOID_YEAR_MAX = 3  # Max void years on any deal

# Salary distribution across contract years
# Back-loaded: base salary increases each year by this rate
CONTRACT_SALARY_ESCALATION_RATE = 0.05  # 5% annual base salary increase

# Dead cap rules
# When cut, remaining prorated bonus accelerates into cut year (NFL CBA rule)
DEAD_CAP_CURRENT_YEAR_FRACTION = 1.0  # 100% hits in release year

# Restructure limits
RESTRUCTURE_MIN_REMAINING_YEARS = 2  # Need at least 2 years left to restructure
RESTRUCTURE_MAX_CONVERSION_PERCENT = 0.90  # Can convert up to 90% of base salary

# Market value estimation by position
# Multiplier applied to base AAV formula. Based on real NFL market data.
# QB highest-paid (~$45M AAV elite), Edge/DL next (~$28M), WR (~$28M),
# CB (~$20M), OL (~$18M), S/LB (~$16M), TE/RB (~$12M), K/P lowest (~$5M).
# 1.0 = league average starter salary.
POSITION_MARKET_MULTIPLIER = {
    'QB': 2.50,
    'DL': 1.55,
    'WR': 1.50,
    'CB': 1.25,
    'OL': 1.15,
    'LB': 1.05,
    'S':  1.00,
    'TE': 0.85,
    'RB': 0.75,
    'K':  0.35,
    'P':  0.30,
}

# Market value tiers as fraction of "fair" value
MARKET_VALUE_LOW_MULTIPLIER = 0.80    # Team-friendly deal
MARKET_VALUE_PREMIUM_MULTIPLIER = 1.25  # Player gets paid top dollar

# Base AAV for a league-average starter (overall ~75), before position multiplier
MARKET_BASE_AAV = 8_000_000

# Rating-to-value curve: how much each overall point above/below 75 shifts AAV
# Exponential scaling so elite players (90+) command disproportionately more
MARKET_RATING_EXPONENT = 2.2  # Controls steepness of pay curve
MARKET_RATING_BASELINE = 75   # "Average starter" overall rating
MARKET_RATING_SCALE_FACTOR = 3500  # Dollars per (rating - baseline)^exponent unit

# Market value calculation constants
MARKET_RATING_DIFFERENTIAL_EXPONENT = 1.5  # Exponent for rating differential in market value
CONTRACT_ROUNDING_UNIT = 50_000  # Round contract values to nearest $50K

# ======================
# SEASON STRUCTURE
# ======================

REGULAR_SEASON_WEEKS = 17
PLAYOFF_TEAMS_PER_CONFERENCE = 7
SUPERBOWL_WEEK = 21  # Week number for Super Bowl

PLAYOFF_ROUNDS = ['wildcard', 'divisional', 'conference', 'superbowl']

# Schedule generation
MAX_GAMES_PER_TEAM_PER_WEEK = 1  # Hard constraint: no team plays >1 game per week
EXPECTED_GAMES_PER_TEAM = 17     # Regular season games per team
EXPECTED_TOTAL_GAMES = 272       # 32 teams × 17 games / 2
GAMES_PER_WEEK_TARGET = 16       # 272 games / 17 weeks

# Wildcard round matchup structure: (higher_seed, lower_seed) — higher seed hosts
WILDCARD_MATCHUP_PAIRS = [(2, 7), (3, 6), (4, 5)]

# Fallback seed value for unknown playoff teams
PLAYOFF_SEED_FALLBACK = 99

PLAYOFF_WEEK_NUMBERS = {
    'wildcard': 18,
    'divisional': 19,
    'conference': 20,
    'superbowl': 21,
}

# Playoff CLI messages
PLAYOFF_ALREADY_COMPLETE_MSG = (
    "Playoffs for season {year} are already complete.\n"
    "  Champion: {team_city} {team_nickname}\n"
    "  Use 'python run_offseason.py <save>' to begin the offseason."
)

# ======================
# PLAY LOG & ARCHIVAL
# ======================

KEY_PLAYS_PER_GAME = 8  # Top plays stored permanently after season archive
AVG_PLAYS_PER_GAME = 160  # For storage estimation

# Key play importance scoring weights (used to rank plays for permanent storage)
KEY_PLAY_TOUCHDOWN_SCORE = 100
KEY_PLAY_TURNOVER_SCORE = 80
KEY_PLAY_BIG_PLAY_BASE_SCORE = 50
KEY_PLAY_CLUTCH_SCORE = 40
KEY_PLAY_FG_SCORE = 30

# ======================
# DRAFT
# ======================

DRAFT_ROUNDS = 7
PICKS_PER_ROUND = 32
TOTAL_DRAFT_PICKS = DRAFT_ROUNDS * PICKS_PER_ROUND  # 224 picks

# Rookie contract lengths by round
ROOKIE_CONTRACT_YEARS = {
    1: 4,  # 1st round: 4 years + 5th year option
    2: 4,  # 2nd round: 4 years
    3: 4,  # 3rd-7th rounds: 4 years
}

# Rookie contract salary scaling
ROOKIE_GUARANTEE_BY_ROUND = {
    1: 2,   # years fully guaranteed
    2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1,
}
ROOKIE_SALARY_TOP_PICK_MULTIPLIER = 4.5    # pick #1 earns 4.5x minimum
ROOKIE_SALARY_SCALE_DECAY = 0.985          # salary scales down per pick slot
ROOKIE_SALARY_FLOOR_MULTIPLIER = 1.0       # never below 1x minimum

# AI draft behavior
AI_BOARD_NOISE = 8                         # ± random noise on AI board scores
AI_PICK_WEIGHTS_BY_PERSONALITY = {
    "draft_purist":  {"talent": 0.80, "need": 0.20},
    "win_now":       {"talent": 0.50, "need": 0.50},
    "analytics":     {"talent": 0.70, "need": 0.30},
    "loyalty":       {"talent": 0.60, "need": 0.40},
    "opportunist":   {"talent": None, "need": None},   # randomized per pick
}

# Live draft trading
DRAFT_LIVE_OFFER_PROBABILITIES = {
    0: 0.60, 1: 0.25, 2: 0.12, 3: 0.03,
}
DRAFT_EARLY_ROUND_OFFER_BOOST = 0.15       # +15% offer chance in rounds 1-2
DRAFT_BOARD_FALL_THRESHOLD = 10            # picks below mock = fall detected

# Draft AI decision constants
DRAFT_ANALYTICS_RED_FLAG_PENALTY = 20  # Points deducted from board score for red flags
DRAFT_LOYALTY_POWER5_BONUS = 5  # Bonus points for Power 5 conference prospects
DRAFT_OFFER_MIN_PROBABILITY = 0.20  # Minimum probability for draft day trade offers
DRAFT_OFFER_VALUE_PREMIUM = 1.1  # Multiplier for premium trade value
DRAFT_OFFER_VALUE_FLOOR = 0.8  # Multiplier for floor trade value
DRAFT_OFFER_VALUE_EXCELLENT = 1.15  # Multiplier for excellent trade value
DRAFT_OFFER_VALUE_FAIR = 0.95  # Multiplier for fair trade value
DRAFT_POSITIONAL_NEED_THRESHOLD = 50  # Threshold for high positional need
DRAFT_ROOKIE_SALARY_DIVISOR = 300  # Divisor for rookie salary calculation
DRAFT_ROOKIE_ESCALATION_FRACTION = 0.92  # Fraction for salary escalation
DRAFT_ROOKIE_BONUS_DIVISOR = 4  # Divisor for signing bonus calculation

# Draft class generation
DRAFT_CLASS_SIZE_RANGE = (300, 400)  # Total prospects per class

DRAFT_CLASS_STRENGTH_WEIGHTS = {
    'weak': 0.20,
    'average': 0.50,
    'strong': 0.25,
    'historic': 0.05,
}

# College conferences for prospect generation
COLLEGE_CONFERENCES = [
    'SEC', 'Big Ten', 'ACC', 'Pac-12', 'Big 12', 'AAC', 'Mountain West', 'C-USA', 'MAC', 'Sun Belt'
]

POWER_5_CONFERENCES = ['SEC', 'Big Ten', 'ACC', 'Pac-12', 'Big 12']
GROUP_OF_5_CONFERENCES = ['AAC', 'Mountain West', 'C-USA', 'MAC', 'Sun Belt']

# ======================
# SCOUTING
# ======================

# Scouting report accuracy (based on scout's talent_evaluation rating)
SCOUTING_BASE_CONFIDENCE_RANGE = 10  # ± this many rating points
SCOUTING_ELITE_CONFIDENCE_RANGE = 3  # For 95+ talent_evaluation scouts

# Scouting phases (weeks during season)
SCOUTING_PHASE_WEEKS = {
    'early_season': (1, 6),
    'film_study': (7, 13),
    'combine': (14, 16),
    'pre_draft': (17, 18),  # After season, before draft
}

# ======================
# SCOUTING SYSTEM (Phase 3)
# ======================

# Prospect generation — position counts in a draft class
DRAFT_CLASS_POSITION_COUNTS = {
    "QB": (8, 12), "RB": (18, 24), "WR": (30, 40), "TE": (12, 16),
    "OL": (40, 50), "DL": (45, 63), "LB": (22, 30),
    "CB": (28, 36), "S": (18, 24), "K": (2, 3), "P": (2, 3),
}

# Overall rating distribution by class strength: (mean, std_dev)
DRAFT_CLASS_OVERALL_BY_STRENGTH = {
    'weak':    (62, 10),
    'average': (65, 11),
    'strong':  (68, 12),
    'historic': (71, 12),
}

# Prospect flag rates
PROSPECT_INJURY_HISTORY_RATE = 0.08
PROSPECT_CHARACTER_FLAG_RATE = 0.15
PROSPECT_AGE_RANGE = (21, 23)
PROSPECT_FA_POOL_MIN_OVR = 58

# College-to-conference mapping (for prospect.college_conference)
COLLEGE_TO_CONFERENCE = {
    "Alabama": "SEC", "Auburn": "SEC", "Florida": "SEC", "Georgia": "SEC",
    "LSU": "SEC", "Tennessee": "SEC", "Texas A&M": "SEC", "Kentucky": "SEC",
    "Ohio State": "Big Ten", "Michigan": "Big Ten", "Penn State": "Big Ten",
    "Wisconsin": "Big Ten", "Iowa": "Big Ten", "Nebraska": "Big Ten",
    "Michigan State": "Big Ten",
    "Clemson": "ACC", "Florida State": "ACC", "Miami": "ACC",
    "North Carolina": "ACC", "Virginia Tech": "ACC", "NC State": "ACC",
    "USC": "Pac-12", "Oregon": "Pac-12", "Washington": "Pac-12",
    "Stanford": "Pac-12", "UCLA": "Pac-12", "Utah": "Pac-12",
    "Arizona State": "Pac-12",
    "Oklahoma": "Big 12", "Texas": "Big 12", "Oklahoma State": "Big 12",
    "TCU": "Big 12", "Baylor": "Big 12", "Kansas State": "Big 12",
    "UCF": "AAC", "Memphis": "AAC", "Cincinnati": "AAC", "Houston": "AAC",
    "SMU": "AAC", "Tulane": "AAC",
    "Boise State": "Mountain West", "San Diego State": "Mountain West",
    "Fresno State": "Mountain West", "Air Force": "Mountain West",
    "Marshall": "C-USA", "UAB": "C-USA", "Western Kentucky": "C-USA",
    "Florida Atlantic": "C-USA",
    "Central Michigan": "MAC", "Toledo": "MAC",
    "Northern Illinois": "MAC", "Ball State": "MAC",
    "Appalachian State": "Sun Belt", "Coastal Carolina": "Sun Belt",
    "Louisiana": "Sun Belt", "Troy": "Sun Belt",
}

# Scout capacity
SCOUT_CAPACITY_DIVISOR = 2              # capacity = regional_coverage // 2
SCOUT_OVERCAPACITY_PENALTY = 1.3        # widens accuracy range when over capacity

# Scout accuracy tiers (talent_evaluation thresholds)
SCOUT_ACCURACY_ELITE_THRESHOLD = 85
SCOUT_ACCURACY_GOOD_THRESHOLD = 70
SCOUT_ACCURACY_AVERAGE_THRESHOLD = 50
SCOUT_ACCURACY_RANGES = {
    "elite":   (3, 5),
    "good":    (8, 12),
    "average": (15, 20),
    "poor":    (25, 35),
}

# Scout default ratings (used when staff attributes are NULL)
SCOUT_DEFAULT_TALENT_EVALUATION = 50
SCOUT_DEFAULT_REGIONAL_COVERAGE = 50
SCOUT_DEFAULT_MEDICAL_EYE = 50
SCOUT_DEFAULT_CHARACTER_READ = 50

# Flag detection rates — keyed by rating threshold (walk downward to match)
SCOUT_FLAG_DETECT_RATES = {85: 0.90, 70: 0.70, 50: 0.40, 0: 0.15}
SCOUT_FALSE_POSITIVE_RATES = {85: 0.02, 70: 0.05, 50: 0.08, 0: 0.10}

# Injury history descriptions (assigned at generation time)
PROSPECT_INJURY_DESCRIPTIONS = [
    "Torn ACL (sophomore year)", "Recurring hamstring issues",
    "Shoulder surgery (junior year)", "Stress fracture in foot",
    "Concussion history (2 documented)", "Knee cartilage repair",
    "Back disc issue", "Ankle ligament damage",
]

# Character flag descriptions
PROSPECT_CHARACTER_DESCRIPTIONS = [
    "Attitude issues reported by coaching staff", "Multiple team suspensions",
    "Off-field incident under investigation", "Known for tuning out coaches",
    "Agent reputation for holdouts", "Poor work ethic in film sessions",
    "Locker room friction with teammates", "Social media controversies",
]

# Scout red flag character keywords for detection
SCOUT_RED_FLAG_CHARACTER_KEYWORDS = ['investigation', 'suspensions', 'holdouts']

# Green flag descriptions (used for false positives too)
PROSPECT_GREEN_FLAG_DESCRIPTIONS = [
    "Elite competitor", "Film junkie", "Position coach raves about preparation",
    "Outstanding combine interview", "Captain — two years running",
    "Community leader off the field", "Exceptional football IQ in interviews",
]

# Combine measurement ranges by position
COMBINE_FORTY_RANGES = {
    "QB": (4.55, 5.10), "RB": (4.35, 4.65), "WR": (4.30, 4.65),
    "TE": (4.50, 4.90), "OL": (4.90, 5.50), "DL": (4.60, 5.10),
    "LB": (4.45, 4.85), "CB": (4.28, 4.60), "S": (4.35, 4.65),
    "K": (4.70, 5.20), "P": (4.70, 5.20),
}
COMBINE_BENCH_RANGES = {
    "QB": (14, 24), "RB": (16, 26), "WR": (10, 20),
    "TE": (18, 28), "OL": (22, 38), "DL": (20, 35),
    "LB": (18, 30), "CB": (10, 20), "S": (12, 22),
    "K": (8, 16), "P": (8, 16),
}
COMBINE_VERTICAL_RANGES = {
    "QB": (28.0, 35.0), "RB": (32.0, 40.0), "WR": (33.0, 42.0),
    "TE": (30.0, 38.0), "OL": (24.0, 32.0), "DL": (27.0, 35.0),
    "LB": (30.0, 38.0), "CB": (33.0, 42.0), "S": (32.0, 40.0),
    "K": (24.0, 30.0), "P": (24.0, 30.0),
}
COMBINE_WONDERLIC_RANGE = (10, 45)
COMBINE_ATTENDANCE_RATE = 0.75

# Draft class notes templates
DRAFT_CLASS_NOTES = {
    'weak':    ["Thin class overall", "Weak at top, some depth", "Below average talent pool"],
    'average': ["Balanced class", "Solid mid-round depth", "Average across the board"],
    'strong':  ["Deep class", "Strong at the top", "Excellent depth at skill positions"],
    'historic': ["Generational talent at top", "Historic depth", "Multiple franchise-altering prospects"],
}

# ======================
# SCOUTING PHASE SYSTEM (Phase 3B)
# ======================

SCOUTING_PHASE_ACCURACY_BONUS = {
    "early": 0, "midseason": 8, "combine": 15, "predraft": 20,
}

SCOUTING_PHASE_REPORT_WEEK = {
    "early": 3, "midseason": 10, "combine": 15, "predraft": 18,
}

# Scouting phase trend detection threshold
SCOUTING_PHASE_GRADE_TREND_THRESHOLD = 5  # ± this many rating points to detect trend

# Scouting phases with flag detection (combine and predraft only)
SCOUTING_PHASES_WITH_FLAG_DETECTION = ['combine', 'predraft']

# Phase-specific scouting notes templates — {phase: {direction: [notes]}}
SCOUTING_PHASE_NOTES = {
    "early": {
        "improving": [
            "Limited film available. Grade based on 3 games, but flashes are encouraging.",
            "Early tape shows promising traits. Needs more reps to confirm.",
        ],
        "declining": [
            "Limited film available. Initial tape raises some questions.",
            "Early projection is cautious — competition level is weak.",
        ],
        "stable": [
            "Limited film available. Grade based on 3 games.",
            "Projection-heavy grade at this stage. Waiting for conference play.",
        ],
    },
    "midseason": {
        "improving": [
            "Consistent performer against Power 5 competition. Grade stabilizing upward.",
            "Midseason update positive after 8 games of film. Trending up.",
        ],
        "declining": [
            "Struggled against top competition. Grade adjusted downward.",
            "Film study reveals concerns that didn't show in early tape.",
        ],
        "stable": [
            "Consistent performer against Power 5 competition. Grade stabilizing.",
            "Midseason grade holds steady after deeper film review.",
        ],
    },
    "combine": {
        "improving": [
            "Combine performance exceeded expectations. Stock rising.",
            "Athletic testing confirms film evaluation. Moving up boards.",
        ],
        "declining": [
            "Combine numbers below projections. Questions emerging.",
            "Positional drills exposed technique concerns. Slipping.",
        ],
        "stable": [
            "Combine confirmed expectations. No surprises, grade holds.",
            "Measured as expected. Interview was solid.",
        ],
    },
    "predraft": {
        "improving": [
            "Final board recommendation: high conviction. Medical cleared.",
            "Private workout was excellent. Scout confident in assessment.",
        ],
        "declining": [
            "Late-stage concerns surfaced. Confidence wavering.",
            "Medical recheck raised a minor flag. Adjusting projection.",
        ],
        "stable": [
            "Final board recommendation submitted. Steady throughout process.",
            "Highest confidence grade of the cycle. Ready for draft day.",
        ],
    },
}

# ======================
# COMBINE EVENT SYSTEM
# ======================

COMBINE_EVENT_WEIGHTS = {
    "breakout": 0.08, "solid": 0.63, "underwhelming": 0.18,
    "red_flag_surfaces": 0.05, "injury_concern": 0.06,
}
COMBINE_INJURY_HISTORY_CONCERN_BOOST = 0.10
COMBINE_BREAKOUT_EVAL_BONUS = 25
COMBINE_UNDERWHELMING_EVAL_OVERRIDE = 5

COMBINE_EVENT_NARRATIVES = {
    "breakout": [
        "{name} ran a blazing 40 — fastest at the position this year.",
        "{name} dominated positional drills. Multiple teams scrambling to trade up.",
        "{name} aced the interview and tested off the charts athletically.",
        "{name} was the combine's biggest riser. Draft stock soaring.",
    ],
    "solid": [
        "{name} tested as expected. Stock holds steady.",
        "{name} had a clean, professional combine showing.",
        "{name} confirmed projections with solid testing across the board.",
        "{name} showed well in drills. No surprises.",
    ],
    "underwhelming": [
        "40 time slower than projected; scouts split on whether it's conditioning or decline.",
        "{name} struggled in positional drills. Lateral agility a concern.",
        "{name} looked stiff in movement drills. Some teams pulling back.",
        "{name}'s interview raised concerns about football IQ.",
    ],
    "red_flag_surfaces": [
        "Walked out of the interview. Two teams confirmed dropping him.",
        "Multiple sources report character concerns about {name} emerged at combine.",
        "A leaked report suggests {name} has a previously undisclosed issue.",
        "{name} refused to participate in medical portion. Teams alarmed.",
    ],
    "injury_concern": [
        "{name} was visibly favoring a limb during drills. Severity unknown.",
        "{name}'s medical report raised a flag. Teams requesting follow-ups.",
        "{name} pulled up during the 40. MRI requested by multiple teams.",
        "{name}'s shoulder flexibility test was abnormal.",
    ],
}

# ======================
# MOCK DRAFT SYSTEM
# ======================

MOCK_DRAFT_PICKS = 32
MOCK_DRAFT_NOISE = 15
MOCK_DRAFT_VOLATILITY_COUNT = (3, 5)
MOCK_DRAFT_AGENT_LEAK_RATE = 0.02
MOCK_DRAFT_BREAKOUT_MOVE = (5, 15)
MOCK_DRAFT_RED_FLAG_DROP = (8, 20)

MOCK_DRAFT_NARRATIVES = [
    "{team} addresses their biggest need at {position}.",
    "A perfect fit for {team}'s scheme.",
    "{team} gets a steal if {name} falls this far.",
    "Some see this as a reach, but {team} loves the upside.",
    "{name} fills an immediate starting role for {team}.",
    "Best player available for {team} at this spot.",
    "{team} couldn't pass on the talent of {name}.",
    "A surprise pick that fills a hidden need for {team}.",
]

# ======================
# COMPETITOR INTELLIGENCE
# ======================

INTEL_SIGNAL_TYPES = ['visit', 'private_workout', 'combine_attention', 'rumored_trade_up', 'board_drop']

INTEL_ACCURACY_BY_COVERAGE = {
    85: 0.85, 70: 0.75, 50: 0.60, 0: 0.40,
}

# Intel signal count range (number of signals per team)
INTEL_SIGNAL_COUNT_RANGE = (2, 4)

INTEL_NARRATIVES = {
    "visit": [
        "{team} visited {name} at {college} this week.",
        "Scouts spotted {team} personnel evaluating {name} in person.",
        "{team} sent their position coach and head scout to watch {name}.",
    ],
    "private_workout": [
        "{team} requested a private session with {name} — no other team had done so.",
        "Sources confirm {team} brought {name} in for a private workout.",
        "{name} held a private session for {team} at their facility.",
    ],
    "combine_attention": [
        "{name} drew the largest position group crowd at the combine.",
        "Multiple front office personnel from {team} watched {name}'s every drill.",
        "{team}'s GM was spotted in extended conversation with {name}'s agent.",
    ],
    "rumored_trade_up": [
        "Intel suggests {team} is exploring a trade into the top 10. Unknown target.",
        "Rumor: {team} called about moving up. Could be targeting {name}.",
        "{team}'s GM has been making calls — believed to be shopping picks.",
    ],
    "board_drop": [
        "Word is {name} has fallen on multiple boards after the combine interview.",
        "Sources say {team} removed {name} from their top tier.",
        "Buzz: {name}'s stock is sliding. Off-field concerns cited.",
    ],
}

INTEL_FALSE_NARRATIVES = [
    "{team} leaked interest in {name} — believed to be a smokescreen.",
    "Don't trust the noise: {team} may be faking interest in {name}.",
    "Sources say {team} showed {name} around, but insiders doubt genuine interest.",
    "Rumor mill says {team} loves {name}, but our intel says otherwise.",
]

# ======================
# DRAFT BOARD
# ======================

BOARD_WEIGHT_GRADE = 0.70
BOARD_WEIGHT_NEED = 0.20
BOARD_WEIGHT_CHARACTER = 0.10

POSTDRAFT_ACCURATE_THRESHOLD = 5
POSTDRAFT_CLOSE_THRESHOLD = 10

# Board character score neutral value
BOARD_CHARACTER_SCORE_NEUTRAL = 50

# ======================
# WEATHER
# ======================

WEATHER_CONDITIONS = ['clear', 'wind', 'rain', 'snow', 'cold', 'extreme_cold']

# Weather modifiers (applied to accuracy, speed, fumble rate)
WEATHER_MODIFIERS = {
    'clear': {'accuracy': 0, 'speed': 0, 'fumble': 1.0, 'kick': 0},
    'wind': {'accuracy': -5, 'speed': 0, 'fumble': 1.0, 'kick': -8},
    'rain': {'accuracy': -3, 'speed': -2, 'fumble': 1.5, 'kick': -3},
    'snow': {'accuracy': -8, 'speed': -5, 'fumble': 1.8, 'kick': -10},
    'cold': {'accuracy': -2, 'speed': -1, 'fumble': 1.2, 'kick': -2},
    'extreme_cold': {'accuracy': -10, 'speed': -8, 'fumble': 2.0, 'kick': -15},
}

# Climate types (for team home cities)
CLIMATE_TYPES = ['cold', 'warm', 'neutral']

# ======================
# STAFF
# ======================

STAFF_ROLES = [
    'OC',           # Offensive Coordinator
    'DC',           # Defensive Coordinator
    'QB_coach',
    'RB_coach',
    'WR_coach',
    'OL_coach',
    'DL_coach',
    'LB_coach',
    'DB_coach',
    'ST_coord',     # Special Teams Coordinator
    'head_scout',
    'regional_scout',
    'fa_scout',     # Free agent scout
]

COORDINATOR_ROLES = ['OC', 'DC']
POSITION_COACH_ROLES = ['QB_coach', 'RB_coach', 'WR_coach', 'OL_coach', 'DL_coach', 'LB_coach', 'DB_coach']
SCOUT_ROLES = ['head_scout', 'regional_scout', 'fa_scout']

# Staff per team
STAFF_PER_TEAM = {
    'coordinators': 2,      # OC + DC
    'position_coaches': 5,  # Typical position coaches
    'scouts': 4,            # Head scout + 3 regional scouts
}

# ======================
# GM PERSONALITIES
# ======================

GM_PERSONALITIES = ['draft_purist', 'win_now', 'analytics', 'loyalty', 'opportunist']

GM_PERSONALITY_TRAITS = {
    'draft_purist': {
        'draft_focus': 0.90,
        'fa_aggression': 0.30,
        'trade_willingness': 0.40,
        'rebuild_patience': 0.85,
    },
    'win_now': {
        'draft_focus': 0.40,
        'fa_aggression': 0.90,
        'trade_willingness': 0.80,
        'rebuild_patience': 0.20,
    },
    'analytics': {
        'draft_focus': 0.70,
        'fa_aggression': 0.50,
        'trade_willingness': 0.75,
        'rebuild_patience': 0.60,
    },
    'loyalty': {
        'draft_focus': 0.60,
        'fa_aggression': 0.40,
        'trade_willingness': 0.30,
        'rebuild_patience': 0.70,
    },
    'opportunist': {
        'draft_focus': 0.55,
        'fa_aggression': 0.65,
        'trade_willingness': 0.85,
        'rebuild_patience': 0.50,
    },
}

# ======================
# STADIUM TYPES
# ======================

STADIUM_TYPES = ['dome', 'outdoor']

# ======================
# TEAM ATTRIBUTES
# ======================

# Prestige scale (affects FA interest)
PRESTIGE_MIN = 1
PRESTIGE_MAX = 99

# Market size scale (affects FA interest)
MARKET_SIZE_MIN = 1
MARKET_SIZE_MAX = 99

# Fan sentiment scale
FAN_SENTIMENT_MIN = 0
FAN_SENTIMENT_MAX = 100
FAN_SENTIMENT_DEFAULT = 50

# ======================
# FREE AGENCY
# ======================

# Interest tiers (player's interest in a team)
INTEREST_TIER_1 = 1  # High interest
INTEREST_TIER_2 = 2  # Medium interest
INTEREST_TIER_3 = 3  # Low interest

# FA market timing modifiers
FA_EARLY_PREMIUM = 1.20  # Early signers cost 20% more
FA_LATE_DISCOUNT = 0.75  # Late signers cost 25% less

FA_MARKET_PHASES = ['frenzy', 'steady', 'bargain']  # Week 0-2, 3-6, 7+

# Preference weight distribution for FA destination ranking (sum = 1.0)
FA_PREF_WEIGHT_WINNING = 0.30
FA_PREF_WEIGHT_SCHEME_FIT = 0.25
FA_PREF_WEIGHT_ROLE_CLARITY = 0.20
FA_PREF_WEIGHT_MARKET_SIZE = 0.15
FA_PREF_WEIGHT_COACH_HISTORY = 0.10

# Interest tier boundaries (rank among 32 teams by preference score)
FA_TIER_1_MAX_RANK = 3       # Top 3 destinations = Tier 1
FA_TIER_2_MAX_RANK = 10      # Ranks 4-10 = Tier 2; 11-32 = Tier 3

# Tier 3 overpay required to force a signing
FA_TIER_3_OVERPAY_THRESHOLD = 1.20   # 20% above fair market value

# Offer resolution thresholds (ratio of offered AAV to adjusted fair AAV)
FA_ACCEPT_THRESHOLD = 1.00           # At or above fair = accept (Tier 1)
FA_COUNTER_THRESHOLD = 0.85          # Within 15% below fair = counter
FA_TIER_2_ACCEPT_PREMIUM = 1.10      # Tier 2 needs 10% above fair to accept

# Pitch meeting parameters
FA_PITCH_FAILURE_DROP_CHANCE = 0.30   # 30% chance a failed pitch drops Tier 2 -> 3
FA_PITCH_DESPERATION_DELTA = -3       # Satisfaction penalty for money_first emphasis
FA_PITCH_EMPHASIS_TO_MOTIVATION = {
    'winning': 'winning',
    'scheme_fit': 'role',
    'role': 'role',
    'money_first': 'money',
}

# Market timing (day-based phases within FA period)
FA_FRENZY_MAX_DAY = 7                 # Days 1-7 = frenzy (early premium)
FA_STEADY_MAX_DAY = 21                # Days 8-21 = steady (fair market)
FA_FRENZY_MODIFIER = 0.12            # +12% to fair value in frenzy
FA_STEADY_MODIFIER = 0.00            # No modifier in steady market
FA_BARGAIN_MODIFIER = -0.15          # -15% discount in late market

# Win percentage lookback for preference scoring
FA_WIN_PCT_LOOKBACK_SEASONS = 2

# Satisfaction delta on FA signing (by interest tier)
FA_SIGNING_SATISFACTION_TIER_1 = 10   # Signing with a preferred team
FA_SIGNING_SATISFACTION_TIER_2 = 5    # Signing with a neutral team
FA_SIGNING_SATISFACTION_TIER_3 = 0    # Signing out of desperation

# AI GM free agency behavior
FA_AI_NEEDS_COUNT = 3                 # Each AI team targets top 3 positional needs
FA_AI_MAX_OFFERS = 5                  # Max offers per AI team per cycle
FA_AI_OVERPAY_BY_PERSONALITY = {
    'draft_purist': 0.00,             # Never overpays
    'win_now': 0.15,                  # Pays 15% premium for top talent
    'analytics': 0.05,               # Slight premium for scheme fits
    'loyalty': 0.10,                 # Overpays to keep own players
    'opportunist': 0.20,             # Sometimes overbids irrationally
}

# Ideal roster composition by position (sums to 53)
FA_IDEAL_ROSTER = {
    'QB': 3, 'RB': 4, 'WR': 5, 'TE': 3,
    'OL': 9, 'DL': 7, 'LB': 6, 'CB': 5,
    'S': 4, 'K': 1, 'P': 1,
}

# Offensive vs defensive position groups (for scheme fit coordinator lookup)
FA_OFFENSIVE_POSITIONS = {'QB', 'RB', 'WR', 'TE', 'OL'}
FA_DEFENSIVE_POSITIONS = {'DL', 'LB', 'CB', 'S'}

# Interest signal messages (qualitative front-office intelligence)
FA_INTEREST_SIGNALS = {
    1: [
        "His agent has been returning our calls quickly.",
        "Word is he's very interested in what we're building here.",
        "Our scouts say we're on his short list.",
    ],
    2: [
        "His agent is taking meetings but hasn't committed to anyone.",
        "We're in the mix, but not his first choice.",
        "He's open to hearing our pitch.",
    ],
    3: [
        "Word is he'd prefer to play somewhere else.",
        "His agent hasn't been returning our calls.",
        "Our front office doesn't think he's interested without a significant overpay.",
    ],
}

# FA market calculation constants
FA_POSITIONAL_NEED_QUALITY_THRESHOLD = 70  # Overall threshold for quality depth check
FA_POSITIONAL_NEED_QUALITY_SCALE = 30.0  # Scale factor for positional need scoring
FA_EARLY_ACCEPTANCE_THRESHOLD = 10  # Delta threshold for early offer acceptance
FA_VETERAN_PRESTIGE_THRESHOLD = 80  # Overall threshold for veteran prestige consideration
FA_AI_TOLERANCE_MULTIPLIER = 0.80  # AI teams accept offers at 80% of fair value

# ======================
# FRANCHISE TAG SYSTEM
# ======================

# Tag limits and salary calculation
FRANCHISE_TAGS_PER_TEAM = 1                  # max tags per team per offseason
FRANCHISE_TAG_TOP_N = 5                      # uses top-N cap hits at position (exclusive)
TRANSITION_TAG_TOP_N = 10                    # transition tag uses top-10 average
CONSECUTIVE_TAG_SALARY_MULTIPLIER = 1.20     # 20% increase per consecutive tag year

# Satisfaction penalties (one-time, applied when tag is first used)
FRANCHISE_TAG_SATISFACTION_PENALTY_1 = -15  # first tag
FRANCHISE_TAG_SATISFACTION_PENALTY_2 = -25  # second consecutive tag
FRANCHISE_TAG_SATISFACTION_PENALTY_3 = -35  # third consecutive tag

# ======================
# TRADE SYSTEM
# ======================

# Player trade value scaling
TRADE_VALUE_MULTIPLIER = 28              # scales true_overall (50-99) to trade point range

# Dead cap to trade point conversion
TRADE_DEAD_CAP_DIVISOR = 75_000          # $75K per trade point penalty

# Age modifier breakpoints
TRADE_AGE_MODIFIER_PEAK_MIN = 24
TRADE_AGE_MODIFIER_PEAK_MAX = 27
TRADE_AGE_MODIFIER_FLOOR_AGE = 34
TRADE_AGE_MODIFIERS = {
    21: 0.75, 22: 0.85, 23: 0.92,
    24: 1.00, 25: 1.00, 26: 1.00, 27: 1.00,
    28: 0.90, 29: 0.80, 30: 0.65,
    31: 0.50, 32: 0.35, 33: 0.20, 34: 0.10,
}
TRADE_AGE_MODIFIER_DEFAULT = 0.05        # age 35+

# Years remaining on contract → value modifier
TRADE_YEARS_REMAINING_MODIFIERS = {
    0: 0.40, 1: 0.60, 2: 0.75, 3: 0.88, 4: 1.00,
}
TRADE_YEARS_REMAINING_MAX = 1.00         # 5+ years

# Pick value chart — (round, tier) → base points
# Derived from Jimmy Johnson NFL Draft Trade Value Chart (1991),
# moderated by Rich Hill/Harvard analytics (2014) showing original
# chart overvalued top picks ~40%. Our values split the difference.
TRADE_PICK_VALUES = {
    (1, "early"): 2500, (1, "mid"): 1500, (1, "late"): 900,
    (2, "early"): 600,  (2, "mid"): 450,  (2, "late"): 300,
    (3, "early"): 250,  (3, "mid"): 200,  (3, "late"): 150,
    (4, "early"): 130,  (4, "mid"): 110,  (4, "late"): 90,
    (5, "early"): 70,   (5, "mid"): 55,   (5, "late"): 40,
    (6, "early"): 35,   (6, "mid"): 28,   (6, "late"): 20,
    (7, "early"): 18,   (7, "mid"): 13,   (7, "late"): 8,
}

# Pick tier boundaries (within a 32-pick round)
TRADE_PICK_TIER_EARLY_MAX = 10           # picks 1-10
TRADE_PICK_TIER_MID_MAX = 21             # picks 11-21; 22-32 = late

# Future pick discounting
TRADE_FUTURE_PICK_DISCOUNT = 0.15        # 15% discount per year out
TRADE_MAX_YEARS_FORWARD = 3              # Stepien Rule — max 3 years forward

# Need scoring
TRADE_NEED_SCORE_HIGH = 70               # threshold for AI unsolicited offers

# GM personality trade behavior
TRADE_OPPORTUNIST_IRRATIONAL_RATE = 0.20  # 20% chance of accepting any trade
TRADE_COUNTER_MAX_GAP_PERCENT = 0.30      # max value gap % for counter vs decline

# Trade deadline
TRADE_DEADLINE_WEEK = 8                   # no player trades after this regular season week

# Satisfaction adjustments for traded players
TRADE_SATISFACTION_UPGRADE = 5            # traded to higher-prestige team
TRADE_SATISFACTION_LATERAL = -3           # neutral trade (disruption cost)
TRADE_SATISFACTION_DOWNGRADE = -10        # traded to lower-prestige team
TRADE_PRESTIGE_THRESHOLD = 15            # prestige difference for upgrade/downgrade

# GM personality loyalty penalty for trading own players
TRADE_LOYALTY_PENALTY_PERCENT = 0.15     # 15% added to threshold

# Trade calculation constants
TRADE_YEARS_REMAINING_CHECK = 5  # Max years to check for contract value
TRADE_NEED_ADJUSTMENT_DIVISOR = 200  # Divisor for positional need adjustment
TRADE_NEED_SCALE_MAX = 100  # Maximum need score scale
TRADE_VETERAN_OVERALL_THRESHOLD = 80  # Overall threshold for veteran consideration

# Phase 5 — Trade Depth
DEADLINE_BEHAVIOR_WEEKS = 2  # last N weeks where deadline multipliers apply

# Seller multipliers (rebuild/decline phase): asks effectively drop
TRADE_DEADLINE_SELLER_MULTIPLIER_REBUILD = 1.15
TRADE_DEADLINE_SELLER_MULTIPLIER_DECLINE = 1.10

# Buyer multipliers (contend/win_now phase): willing to overpay slightly
TRADE_DEADLINE_BUYER_MULTIPLIER_CONTEND = 1.05
TRADE_DEADLINE_BUYER_MULTIPLIER_WIN_NOW = 1.10

TRADE_DEADLINE_BRIDGE_MULTIPLIER = 1.00  # bridge/neutral — no shift

# Typed rejection reasons (returned with every declined trade)
TRADE_REJECTION_REASONS = {
    'overvalued':           'overvalues the player relative to current market',
    'not_phase_fit':        'not a fit for current rebuild phase',
    'not_phase_fit_winnow': 'preferring to keep win-now veterans',
    'position_depth':       'prefers to retain position depth',
    'cap_unworkable':       'cap impact unworkable this season',
    'age_curve':            'aging curve concerns',
    'scheme_mismatch':      'scheme mismatch',
    'roster_lock':          'core roster lock — not available',
}

# Trade shopping interest tiers
TRADE_SHOP_HIGH_INTEREST_PCT     = 0.80   # team would pay ≥80% of value → HIGH
TRADE_SHOP_MODERATE_INTEREST_PCT = 0.50   # 50-80% → MODERATE
TRADE_SHOP_LOW_INTEREST_PCT      = 0.20   # 20-50% → LOW
# Below 20% → NO interest

# ======================
# PLAYER SATISFACTION
# ======================

SATISFACTION_MIN = 0
SATISFACTION_MAX = 100
SATISFACTION_DEFAULT = 75

# Satisfaction change rates (per week)
SATISFACTION_CHANGE_RATES = {
    'winning': +2,
    'losing': -3,
    'starter_role': +1,
    'backup_role': -1,
    'underpaid': -2,
    'overpaid': +1,
}

# Satisfaction thresholds for events
SATISFACTION_HOLDOUT_THRESHOLD = 25
SATISFACTION_TRADE_DEMAND_THRESHOLD = 35
SATISFACTION_RETIREMENT_THRESHOLD = 20

# Warning signal tiers — maps tier name to (lower_bound, upper_bound)
SATISFACTION_WARNING_TIERS = {
    'healthy':          (70, 100),
    'distracted':       (55, 69),
    'agent_calls':      (40, 54),
    'declined_meeting': (25, 39),
    'trade_request':    (10, 24),
    'holdout':          (0, 9),
}

# Signal narrative messages (for front office briefing)
SATISFACTION_SIGNAL_MESSAGES = {
    'distracted':       "{name} seemed distracted in practice this week.",
    'agent_calls':      "{name}'s agent has been making calls around the league.",
    'declined_meeting': "{name} declined a meeting with the coaching staff.",
    'trade_request':    "{name} has formally requested a trade through his agent.",
    'holdout':          "{name} is refusing to participate in team activities.",
}

# Contract fairness thresholds (AAV ratio vs market fair value)
SATISFACTION_UNDERPAID_THRESHOLD = 0.80  # Below this = underpaid
SATISFACTION_OVERPAID_THRESHOLD = 1.00   # At or above = overpaid (satisfied)

# Franchise tag one-time satisfaction penalty
SATISFACTION_FRANCHISE_TAG_PENALTY = -15

# Playoff history bonus per appearance in lookback window
SATISFACTION_PLAYOFF_BONUS = 1
SATISFACTION_PLAYOFF_LOOKBACK = 2  # seasons

# Starter-caliber detection: within N overall points of best at position
SATISFACTION_STARTER_CALIBER_THRESHOLD = 5

# Intervention parameters
SATISFACTION_INTERVENTION = {
    'private_meeting': {
        'success_range': (10, 20),   # delta if motivation matched
        'failure_range': (-5, 0),    # delta if motivation mismatched
        'cooldown_weeks': 4,         # weeks between meetings
    },
    'extension_offer': {
        'fair_range': (15, 25),      # delta if offer at/above fair market
        'lowball_penalty': -10,      # delta if offer below 80% of fair
    },
    'role_adjustment': {
        'effective_range': (5, 15),  # delta if role-based dissatisfaction
        'ineffective_range': (0, 3), # delta if not role-based
    },
}

# Contagion mechanic thresholds
CONTAGION_SATISFACTION_THRESHOLD = 30    # veteran must be below this to influence
CONTAGION_VETERAN_MIN_OVERALL = 80       # minimum overall to be influential
CONTAGION_VETERAN_MIN_EXPERIENCE = 5     # minimum years experience
CONTAGION_TARGET_MAX_EXPERIENCE = 3      # young players susceptible
CONTAGION_WEEKLY_PROBABILITY = 0.30      # 30% chance per affected player per week
CONTAGION_DELTA_RANGE = (-3, -1)         # impact range on affected player

# Motivation derivation heuristics (no motivation column in schema)
MOTIVATION_YOUNG_AGE_MAX = 25            # <=25: role-focused
MOTIVATION_VETERAN_AGE_MIN = 30          # >=30: money/legacy-focused
MOTIVATION_TYPES = ['role', 'money', 'winning', 'legacy']

# Position groups for contagion spread (same group = affected)
SATISFACTION_POSITION_GROUPS = {
    'QB': ['QB'],
    'RB': ['RB'],
    'receivers': ['WR', 'TE'],
    'o_line': ['OL'],
    'd_line': ['DL'],
    'linebackers': ['LB'],
    'secondary': ['CB', 'S'],
    'specialists': ['K', 'P'],
}

# Reverse lookup: position -> group name (computed at module load)
POSITION_TO_GROUP = {}
for _group_name, _positions in SATISFACTION_POSITION_GROUPS.items():
    for _pos in _positions:
        POSITION_TO_GROUP[_pos] = _group_name

# Legacy threshold for satisfaction calculation
SATISFACTION_LEGACY_THRESHOLD = 85  # Threshold for high legacy score bonus

# ======================
# LEGACY SCORING
# ======================

# Legacy score component weights
LEGACY_WEIGHTS = {
    'championships': 0.30,
    'win_percentage': 0.25,
    'playoff_appearances': 0.15,
    'stars_developed': 0.15,
    'cap_efficiency': 0.10,
    'media_score': 0.05,
}

# Dynasty qualification
DYNASTY_CHAMPIONSHIPS_REQUIRED = 3
DYNASTY_WINDOW_YEARS = 10

# Hall of Fame threshold
HOF_LEGACY_THRESHOLD = 8500  # Total legacy score needed
HOF_MIN_SEASONS = 10

# Legacy score component multipliers (applied with weights)
LEGACY_CHAMP_MULTIPLIER = 1000
LEGACY_WIN_PCT_MULTIPLIER = 10000
LEGACY_PLAYOFF_MULTIPLIER = 500
LEGACY_STARS_MULTIPLIER = 300
LEGACY_CAP_MULTIPLIER = 50
LEGACY_MEDIA_MULTIPLIER = 50

# Legacy media score calculation
LEGACY_MEDIA_RECENT_WIN_WEIGHT = 2
LEGACY_MEDIA_SCORE_CAP = 100
LEGACY_RECENT_SEASONS_COUNT = 3

# Star development threshold (attribute improvement)
LEGACY_STAR_DEVELOPMENT_JUMP = 10

# ======================
# CLOCK MANAGEMENT
# ======================

QUARTER_LENGTH_SECONDS = 900        # 15 minutes per quarter
PLAY_CLOCK_SECONDS = 40
HALFTIME_EXISTS = True
OT_LENGTH_SECONDS = 600             # 10 minutes for overtime
MAX_PLAYS_PER_GAME = 250            # Safety valve to prevent infinite loops

# Time consumed per play type (seconds off game clock)
PLAY_TIME_RANGES = {
    'pass_complete': (5, 8),
    'pass_incomplete': (3, 5),      # clock stops
    'run': (25, 40),                # includes huddle
    'sack': (5, 8),
    'scramble': (5, 8),
    'fg_attempt': (5, 7),
    'punt': (5, 7),
    'kickoff': (5, 7),
    'kneel': (40, 40),
    'spike': (1, 3),
    'penalty': (0, 0),              # clock already handled
}

# Clock stop conditions
CLOCK_STOPS_ON = [
    'pass_incomplete', 'out_of_bounds', 'timeout',
    'touchdown', 'turnover', 'two_minute_warning',
    'penalty', 'spike',
]

# Huddle time between plays (seconds)
HUDDLE_TIME_NORMAL = (10, 18)
HUDDLE_TIME_HURRY = (3, 8)
HUDDLE_TIME_2MIN = (2, 5)

# ======================
# PASS PLAY CONSTANTS
# ======================

# Pass distance zones (yards from LOS)
PASS_ZONE_SHORT = (0, 10)
PASS_ZONE_MEDIUM = (11, 20)
PASS_ZONE_DEEP = (21, 50)

# Pocket time grades from OL win count
POCKET_TIME_CLEAN = 4       # 4-5 OL wins
POCKET_TIME_DISRUPTED = 2   # 2-3 OL wins
POCKET_TIME_COLLAPSED = 1   # 0-1 OL wins

# Accuracy penalties by pocket time
POCKET_PENALTY = {
    'clean': 0,
    'disrupted': -10,
    'collapsed': -20,
}

# Sack probability by pocket grade
SACK_PROBABILITY_BY_POCKET = {
    'clean': 0.01,
    'disrupted': 0.08,
    'collapsed': 0.30,
}

# Pre-snap read bonus range (QB IQ beats DC disguise)
PRE_SNAP_BONUS_RANGE = (2, 5)

# Pass play separation modifiers (yards adjustment based on coverage)
SEPARATION_BONUS_RANGE = (1, 5)      # When receiver has good separation (>2.0)
SEPARATION_PENALTY_RANGE = (1, 3)    # When receiver is tightly covered (<-1.0)

# Run play open field bonus ranges
OPEN_FIELD_BONUS_RANGE = (2, 5)      # RB beats secondary defender
BIG_RUN_BONUS_RANGE = (5, 12)        # Explosive run extension

# ======================
# STAMINA DRAIN (IN-GAME)
# ======================

# Stamina drain per snap by position
STAMINA_DRAIN_PER_SNAP = {
    'QB': 0.6, 'RB': 1.2, 'WR': 0.8, 'TE': 0.9,
    'OL': 1.0, 'DL': 1.0, 'LB': 0.9,
    'CB': 0.7, 'S': 0.6, 'K': 0.2, 'P': 0.2,
}

# High-effort play bonus stamina drain multiplier
HIGH_EFFORT_STAMINA_DRAIN = 1.5

# Season wear per week (from Week 10, GDD §6.2)
SEASON_WEAR_PER_WEEK = {
    'RB': 1.5, 'OL': 0.8, 'DL': 0.8, 'LB': 0.7,
    'QB': 0.5, 'WR': 0.4, 'TE': 0.4,
    'CB': 0.0, 'S': 0.0, 'K': 0.0, 'P': 0.0,
}

# Substitution thresholds by position (fatigue-based rotation)
SUBSTITUTION_THRESHOLDS = {
    'QB': 20,   # Only sub QB in extreme fatigue
    'RB': 55,   # Sub RBs frequently
    'WR': 35,
    'TE': 40,
    'OL': 40,
    'DL': 50,   # DL rotates heavily
    'LB': 45,
    'CB': 35,
    'S': 35,
    'K': 5,
    'P': 5,
}

# ======================
# DURABILITY MODIFIER
# ======================

# Maps durability rating to injury rate multiplier
DURABILITY_MODIFIER_TABLE = [
    (97, 0.5), (90, 0.6), (80, 0.7), (70, 0.85),
    (60, 1.0), (50, 1.3), (40, 1.5), (0, 1.8),
]

# ======================
# COACH BONUS CAPS
# ======================

OL_COACH_BONUS_MAX = 5
WR_COACH_SITUATIONAL_BONUS = 3
QB_COACH_PRESSURE_REDUCTION = 5
RB_COACH_VISION_BONUS = 3
DB_COACH_COVERAGE_BONUS = 3

# STC global modifier by letter grade
STC_MODIFIER_TABLE = {
    'A': 8, 'B': 3, 'C': 0, 'D': -5, 'F': -10,
}

# Blocked kick base rate
BLOCKED_KICK_BASE_RATE = 0.015

# ======================
# SPECIAL TEAMS MECHANICS
# ======================

# Field goal constants
FG_SNAP_HOLD_DISTANCE = 17  # yards added to distance for snap + hold
FG_EXTREME_RANGE_BASE_PROB = 0.20  # Base probability for 60+ yard attempts
FG_KICK_ACCURACY_BASELINE = 70  # Neutral accuracy rating
FG_KICK_ACCURACY_DIVISOR = 200.0  # Scales accuracy modifier (±15% swing)
FG_PROB_MIN = 0.05  # Minimum FG probability
FG_PROB_MAX = 0.99  # Maximum FG probability
FG_WEATHER_DIVISOR = 100.0  # Scales weather modifier to probability
FG_STC_DIVISOR = 100.0  # Scales STC modifier to probability
FG_BLOCK_RATE_STC_DIVISOR = 1000.0  # Scales defensive STC modifier
FG_BLOCK_RATE_MIN = 0.005  # Minimum block probability
FG_BLOCK_RATE_MAX = 0.08  # Maximum block probability

# Extra point constants
XP_KICK_ACCURACY_BASELINE = 70  # Neutral accuracy rating
XP_KICK_ACCURACY_DIVISOR = 500.0  # Tiny accuracy modifier for XP
XP_WEATHER_DIVISOR = 200.0  # Scales weather modifier for XP
XP_STC_DIVISOR = 200.0  # Scales STC modifier for XP
XP_PROB_MIN = 0.80  # Minimum XP probability (99%+ in NFL)
XP_PROB_MAX = 0.99  # Maximum XP probability

# Two-point conversion constants
TWO_POINT_QB_ACCURACY_BASELINE = 70  # Neutral QB accuracy
TWO_POINT_QB_ACCURACY_DIVISOR = 200.0  # Scales QB accuracy modifier
TWO_POINT_PROB_MIN = 0.30  # Minimum 2pt probability
TWO_POINT_PROB_MAX = 0.65  # Maximum 2pt probability

# Punt constants
PUNT_POWER_BASELINE = 70  # Neutral punt power rating
PUNT_POWER_DIVISOR = 5.0  # Scales power modifier to yards
PUNT_WEATHER_DIVISOR = 2  # Divides weather kick modifier for punts
PUNT_DISTANCE_MIN = 20  # Minimum punt distance (yards)
PUNT_DISTANCE_MAX = 70  # Maximum punt distance (yards)
PUNT_TOUCHBACK_BUFFER = 10  # Yards before endzone to avoid touchback
PUNT_RETURN_INJURY_THRESHOLD = 10  # Min return yards to trigger injury check
PUNT_RETURNER_RATING_DIVISOR = 2  # Averages speed + elusiveness

# Kickoff constants
KICKOFF_POWER_BASELINE = 70  # Neutral kick power rating
KICKOFF_POWER_DIVISOR = 100.0  # Scales power modifier to touchback prob
KICKOFF_WEATHER_DIVISOR = 100.0  # Scales weather modifier to touchback prob
KICKOFF_STC_DIVISOR = 200.0  # Scales STC modifier to touchback prob
KICKOFF_TOUCHBACK_PROB_MIN = 0.30  # Minimum touchback probability
KICKOFF_TOUCHBACK_PROB_MAX = 0.80  # Maximum touchback probability
KICKOFF_TOUCHBACK_YARD_LINE = 25  # Starting field position after touchback
KICKOFF_RETURN_MIN_YARDS = 10  # Minimum return yards (for poor returners)
KICKOFF_RETURN_INJURY_THRESHOLD = 15  # Min return yards to trigger injury check
KICKOFF_RETURNER_RATING_DIVISOR = 2  # Averages speed + elusiveness

# Field position constants
FIELD_POSITION_MIN = 1  # Minimum yard line (own 1)
FIELD_POSITION_MAX = 99  # Maximum yard line (opponent 1)
FIELD_LENGTH = 100  # Total field length for calculations
ENDZONE_THRESHOLD = 99  # Yard line that triggers touchdown

# ======================
# GAME PLAN DEFAULTS
# ======================

DEFAULT_GAME_PLAN = {
    'run_pass_ratio': 0.45,             # 45% run, 55% pass
    'short_medium_deep': (0.45, 0.35, 0.20),
    'blitz_frequency': 0.25,
    'coverage_man_zone': 0.50,          # 50% man, 50% zone
    'aggressiveness_4th': 'situational',
    'red_zone_preference': 'balanced',
}

# Situational play-calling thresholds
THIRD_DOWN_LONG_DISTANCE = 7            # Yards for 3rd and long
THIRD_DOWN_LONG_PASS_BIAS = 0.3         # Run rate multiplier on 3rd and long
THIRD_DOWN_SHORT_DISTANCE = 3           # Yards for 3rd and short
THIRD_DOWN_SHORT_RUN_BIAS = 1.5         # Run rate multiplier on 3rd and short
SECOND_DOWN_LONG_DISTANCE = 8           # Yards for 2nd and long
SECOND_DOWN_LONG_PASS_LEAN = 0.7        # Run rate multiplier on 2nd and long
TRAILING_SCORE_DIFF = -7                # Score difference for trailing adjustments
TRAILING_PASS_BIAS = 0.4                # Run rate multiplier when trailing late
LEADING_SCORE_DIFF = 7                  # Score difference for leading adjustments
LEADING_TIME_THRESHOLD = 300            # Seconds remaining for clock management
LEADING_RUN_BIAS = 1.8                  # Run rate multiplier when leading late
TWO_MINUTE_PASS_BIAS = 0.3              # Run rate multiplier in 2-minute drill
RED_ZONE_YARDS = 20                     # Yards from endzone for red zone
RED_ZONE_MIN_RUN_RATE = 0.35            # Minimum run rate in red zone
GOAL_LINE_YARDS = 5                     # Yards from endzone for goal line

# Weather season threshold
LATE_SEASON_WEEK = 9                    # Week number when weather shifts to late season

# ======================
# CLUTCH SITUATIONS
# ======================

CLUTCH_SCORE_MARGIN = 7
CLUTCH_2MIN_THRESHOLD = 120            # seconds
CLUTCH_3RD_DOWN_DISTANCE = 5
CLUTCH_PLAYOFF_BONUS = 5

# ======================
# SCHEME FIT
# ======================

# Offensive scheme → valued player attributes
SCHEME_ATTRIBUTE_MAP_OFFENSE = {
    'spread': ['true_accuracy_short', 'true_accuracy_mid', 'true_route_running', 'true_speed'],
    'west_coast': ['true_accuracy_short', 'true_catch', 'true_catch'],
    'air_raid': ['true_accuracy_deep', 'true_arm_strength', 'true_speed'],
    'pro_style': ['true_accuracy_mid', 'true_pocket_presence', 'true_blocking'],
    'run_heavy': ['true_blocking', 'true_strength', 'true_strength'],
    'option': ['true_speed', 'true_elusiveness', 'true_football_iq'],
    'power_run': ['true_blocking', 'true_strength', 'true_strength', 'true_blocking'],
    'zone_run': ['true_blocking', 'true_vision', 'true_elusiveness'],
}

# Defensive scheme → valued player attributes
SCHEME_ATTRIBUTE_MAP_DEFENSE = {
    '4_3': ['true_pass_rush', 'true_tackling', 'true_coverage_zone'],
    '3_4': ['true_pass_rush', 'true_tackling', 'true_strength'],
    'cover_2': ['true_coverage_zone', 'true_speed', 'true_tackling'],
    'cover_3': ['true_coverage_zone', 'true_speed', 'true_football_iq'],
    'man': ['true_coverage_man', 'true_speed', 'true_coverage_man'],
    'zone': ['true_coverage_zone', 'true_coverage_zone', 'true_football_iq'],
    'blitz': ['true_pass_rush', 'true_speed', 'true_tackling'],
    'blitz_heavy': ['true_pass_rush', 'true_speed', 'true_tackling'],
}

# Scheme fit bonus clamp range
SCHEME_FIT_BONUS_MIN = -8
SCHEME_FIT_BONUS_MAX = 8

# ======================
# NFL TARGET AVERAGES
# ======================

# For tuning validation (per team per game)
NFL_AVG_TARGETS = {
    'pass_yards_per_game': 225,
    'rush_yards_per_game': 115,
    'completion_pct': 0.645,
    'yards_per_carry': 4.3,
    'total_plays_per_game': 65,     # per team
    'points_per_game': 22,
    'turnovers_per_game': 1.1,
    'sacks_per_game': 2.5,         # per team
    'penalties_per_game': 6,
}

# ======================
# GAME DAY STARTERS
# ======================

# Number of starters per position on game day
STARTERS_BY_POSITION = {
    'QB': 1, 'RB': 1, 'WR': 3, 'TE': 1, 'OL': 5,
    'DL': 4, 'LB': 3, 'CB': 2, 'S': 2,
    'K': 1, 'P': 1,
}

# Penalty injection rate (per team per game, Phase 1 simplified)
PENALTY_RATE_PER_GAME = 6
PENALTY_YARDS = {
    'offensive_holding': 10,
    'false_start': 5,
    'pass_interference': 15,     # average, actually spot foul
    'illegal_formation': 5,
    'roughing_passer': 15,
    'unnecessary_roughness': 15,
    'offsides': 5,
    'delay_of_game': 5,
}

# ======================
# HELPER FUNCTIONS
# ======================

def to_letter_grade(rating: int) -> str:
    """
    Convert internal 1-99 rating to display letter grade.

    Args:
        rating: True rating (1-99)

    Returns:
        Letter grade string (A+ through F)
    """
    if rating < RATING_MIN or rating > RATING_MAX:
        return "?"  # Invalid rating

    for threshold, grade in sorted(LETTER_GRADE_THRESHOLDS.items(), reverse=True):
        if rating >= threshold:
            return grade

    return "F"  # Below 60


# ======================
# DEVELOPMENT & AGING (Phase 2)
# ======================

# Development gain ranges by trait (per season, for ages 22-26)
DEVELOPMENT_GAIN_SUPERSTAR = (3, 8)
DEVELOPMENT_GAIN_STAR = (2, 5)
DEVELOPMENT_GAIN_NORMAL = (1, 3)
DEVELOPMENT_GAIN_SLOW = (0, 2)

# Development multipliers by age bracket
DEVELOPMENT_AGE_PEAK = (22, 26)     # Full development gain
DEVELOPMENT_AGE_PLATEAU = (27, 29)  # Half development gain
DEVELOPMENT_AGE_DECLINE = 30        # Aging decline begins

# Aging decline ranges by position (per season for age 30+)
AGING_DECLINE_BY_POSITION = {
    'QB': (-1, -2), 'RB': (-3, -5), 'WR': (-2, -4), 'TE': (-2, -3),
    'OL': (-1, -3), 'DL': (-2, -4), 'LB': (-2, -4),
    'CB': (-3, -5), 'S': (-2, -4), 'K': (-1, -2), 'P': (-1, -2),
}

# Attribute-specific decline multipliers
AGING_SPEED_MULTIPLIER = 1.5       # Speed declines 50% faster
AGING_STRENGTH_MULTIPLIER = 0.8    # Strength declines 20% slower
AGING_IQ_MULTIPLIER = 0.5          # IQ declines 50% slower (experience)

# IQ development bonus during youth (experience-based faster growth)
IQ_DEVELOPMENT_MULTIPLIER = 1.2

# Speed-type attributes (decline faster with age)
SPEED_ATTRIBUTES = [
    'true_speed', 'true_elusiveness',
]

# Strength-type attributes (decline slower with age)
STRENGTH_ATTRIBUTES = [
    'true_strength', 'true_blocking',
]

# IQ-type attributes (decline slowest)
IQ_ATTRIBUTES = [
    'true_football_iq', 'true_pocket_presence', 'true_vision',
]

# All modifiable true attributes (for development/aging passes)
ALL_TRUE_ATTRIBUTES = [
    'true_overall', 'true_speed', 'true_strength', 'true_football_iq',
    'true_durability', 'true_clutch',
]

# Position-specific optional attributes
POSITION_ATTRIBUTES = {
    'QB': ['true_accuracy_short', 'true_accuracy_mid', 'true_accuracy_deep',
           'true_pocket_presence', 'true_arm_strength'],
    'RB': ['true_elusiveness', 'true_vision', 'true_catch'],
    'WR': ['true_catch', 'true_route_running', 'true_yac', 'true_elusiveness'],
    'TE': ['true_catch', 'true_route_running', 'true_blocking', 'true_yac'],
    'OL': ['true_blocking'],
    'DL': ['true_pass_rush', 'true_tackling'],
    'LB': ['true_pass_rush', 'true_tackling', 'true_coverage_man', 'true_coverage_zone'],
    'CB': ['true_coverage_man', 'true_coverage_zone', 'true_tackling'],
    'S': ['true_coverage_man', 'true_coverage_zone', 'true_tackling'],
    'K': ['true_kick_accuracy', 'true_kick_power'],
    'P': ['true_kick_accuracy', 'true_kick_power'],
}

# ======================
# AWARDS (Phase 2)
# ======================

# Pro Bowl selections per position
PRO_BOWL_SELECTIONS = {
    'QB': 4, 'RB': 4, 'WR': 6, 'TE': 3, 'OL': 8,
    'DL': 6, 'LB': 6, 'CB': 4, 'S': 4, 'K': 2, 'P': 2,
}

# All-Pro selections per position (First Team)
ALL_PRO_SELECTIONS = {
    'QB': 1, 'RB': 1, 'WR': 2, 'TE': 1, 'OL': 5,
    'DL': 4, 'LB': 3, 'CB': 2, 'S': 2, 'K': 1, 'P': 1,
}

# Award stat minimums
MVP_MIN_GAMES_PLAYED = 10
OPOY_MIN_GAMES_PLAYED = 10
DPOY_MIN_GAMES_PLAYED = 10
QB_AWARD_MIN_ATTEMPTS = 200
RB_AWARD_MIN_CARRIES = 100
WR_AWARD_MIN_TARGETS = 50

# MVP scoring weights
MVP_STAT_WEIGHT = 0.7
MVP_TEAM_SUCCESS_WEIGHT = 0.3

# QB bias multiplier for MVP (QBs win MVP ~80% of time in NFL)
QB_MVP_BIAS_MULTIPLIER = 1.15

# Award offensive scoring weights (for composite score calculation)
AWARD_PASS_YARDS_WEIGHT = 0.04
AWARD_PASS_TDS_WEIGHT = 4.0
AWARD_INTERCEPTIONS_PENALTY = 6.0
AWARD_PASSER_RATING_WEIGHT = 0.3
AWARD_RUSH_YARDS_WEIGHT = 0.08
AWARD_RUSH_TDS_WEIGHT = 6.0
AWARD_REC_YARDS_WEIGHT = 0.08
AWARD_REC_TDS_WEIGHT = 6.0
AWARD_RECEPTIONS_WEIGHT = 0.5
AWARD_FG_MADE_WEIGHT = 3.0
AWARD_FUMBLE_PENALTY = 4.0

# Award defensive scoring weights
AWARD_TACKLES_WEIGHT = 1.0
AWARD_SACKS_WEIGHT = 8.0
AWARD_DEF_INT_WEIGHT = 12.0
AWARD_PASS_DEFLECTIONS_WEIGHT = 3.0


# ======================
# WEEKLY STATS & AWARDS (Phase 5)
# ======================

# Stat columns for programmatic access (DRY principle)
STAT_COLUMNS_PLAYER = [
    'pass_attempts', 'completions', 'pass_yards', 'pass_tds',
    'interceptions_thrown', 'sacks_taken', 'carries', 'rush_yards',
    'rush_tds', 'fumbles', 'targets', 'receptions', 'rec_yards',
    'rec_tds', 'tackles', 'sacks', 'interceptions', 'pass_deflections',
    'forced_fumbles', 'fg_attempts', 'fg_made', 'fg_long',
    'xp_attempts', 'xp_made', 'punts', 'punt_yards', 'punt_returns',
    'punt_return_yards', 'punt_return_tds', 'kick_returns',
    'kick_return_yards', 'kick_return_tds',
]

STAT_COLUMNS_TEAM = [
    'points_scored', 'total_yards', 'pass_yards', 'rush_yards',
    'turnovers', 'third_down_conversions', 'third_down_attempts',
    'points_allowed', 'yards_allowed', 'sacks_recorded', 'takeaways',
]

# Stars of the Week minimum thresholds
STAR_MIN_PASS_YARDS = 200
STAR_MIN_RUSH_YARDS = 80
STAR_MIN_REC_YARDS = 80
STAR_MIN_TACKLES = 8
STAR_MIN_SACKS = 1.0

# Special teams scoring weights (reuse offensive/defensive weights from AWARD_ constants)
STAR_FG_WEIGHT = 3.0
STAR_FG_LONG_BONUS = 10.0        # Bonus for 50+ yard FG
STAR_RETURN_TD_WEIGHT = 50.0      # Punt/kick return TDs

# Weekly award types
WEEKLY_AWARD_TYPES = ['OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'USER_TEAM_MVP']

# ======================
# STARS OF THE WEEK SELECTION (Phase 5 Prompt #4)
# ======================

# Context weights
STARS_WIN_BONUS = 5.0
STARS_OPPONENT_STRENGTH_BONUS = 8.0
STARS_CLUTCH_BONUS = 0.0        # deferred: quarter splits not tracked by engine
STARS_KEY_PLAY_TIEBREAKER = 0.5

# Position group routing (must match actual player.position values in DB)
STARS_OFFENSE_POSITIONS = ('QB', 'RB', 'WR', 'TE')   # FB maps to RB in actual schema
STARS_DEFENSE_POSITIONS = ('DL', 'LB', 'CB', 'S')    # grouped positions, not granular
STARS_SPECIAL_TEAMS_POSITIONS = ('K', 'P')

# Base stat value coefficients — design doc §4.2, adapted for actual player_week_stats columns
STARS_BSV_QB_PASS_YARDS = 0.04
STARS_BSV_QB_PASS_TD = 4.0
STARS_BSV_QB_PASS_INT = -2.0
STARS_BSV_QB_RUSH_YARDS = 0.5

STARS_BSV_RB_RUSH_YARDS = 0.1
STARS_BSV_RB_RUSH_TD = 6.0
STARS_BSV_RB_REC_YARDS = 0.05

STARS_BSV_RECEIVER_REC_YARDS = 0.1
STARS_BSV_RECEIVER_REC_TD = 6.0
STARS_BSV_RECEIVER_RECEPTIONS = 0.5

STARS_BSV_DLLB_SACKS = 4.0
STARS_BSV_DLLB_TACKLES = 1.5
STARS_BSV_DLLB_FF = 6.0
# NOTE: fumble_recoveries and def_tds are not columns in player_week_stats → dropped.
# Scoped for a future prompt that extends the engine's defensive event surface.

STARS_BSV_DB_TACKLES = 0.5
STARS_BSV_DB_INT = 8.0
STARS_BSV_DB_FF = 6.0
# NOTE: fumble_recoveries and def_tds not tracked → terms dropped (same reason as above).

STARS_BSV_K_FG_MADE = 3.0
STARS_BSV_K_FG_50PLUS = 4.0     # additive bonus applied when fg_long >= 50
STARS_BSV_K_XP_MADE = 1.0

STARS_BSV_P_PUNT_YARDS = 0.05
# NOTE: punts_inside_20 not tracked in player_week_stats → term dropped. Future prompt.

STARS_BSV_RET_RETURN_YARDS = 0.1
STARS_BSV_RET_RETURN_TDS = 12.0

# ST threshold: at least ONE of these must be met to award SPECIAL_TEAMS star
# Uses actual columns: fg_long (distance, not count) and computed return_tds
STARS_ST_FG_LONG_THRESHOLD = 50  # fg_long >= this value → qualifies
# (return_tds > 0 is the other gate; checked inline in _st_meets_threshold)

# Award type strings — must exactly match WEEKLY_AWARD_TYPES values
STARS_AWARD_OFFENSE = 'OFFENSE'
STARS_AWARD_DEFENSE = 'DEFENSE'
STARS_AWARD_SPECIAL_TEAMS = 'SPECIAL_TEAMS'
STARS_AWARD_USER_TEAM_MVP = 'USER_TEAM_MVP'

# Phase 5 Prompt #5 — Tier 2 streak trigger (design doc §4.7)
STREAK_LENGTH_WEEKS = 3
STREAK_AWARD_TYPES = ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS')
TIER2_EVENT_RISING_STAR_STREAK = 'rising_star_streak'

# Phase 5 Prompt #5 — Lineup controversy thresholds (design doc §2.5)
LINEUP_CONTROVERSY_A_GRADE_THRESHOLD = 90   # outgoing starter true_overall >= this
LINEUP_CONTROVERSY_C_GRADE_THRESHOLD = 76   # incoming player true_overall <= this
LINEUP_CONTROVERSY_SENTIMENT_DELTA = -3
LINEUP_CONTROVERSY_SENTIMENT_REASON_CODE = 'lineup_controversy'
TIER1_CONTEXT_LINEUP_CONTROVERSY = 'lineup_controversy'


# ======================
# LEADERBOARD DISPLAY (Phase 5 Prompt #2)
# ======================

# Leaderboard defaults
LEADERBOARD_DEFAULT_LIMIT = 10
LEADERBOARD_MAX_LIMIT = 50

# Stat category map (CLI argument → database column name)
LEADERBOARD_STAT_MAP = {
    # Offense
    'passing': 'pass_yards',
    'rushing': 'rush_yards',
    'receiving': 'rec_yards',
    # Defense
    'defense': 'tackles',
    'sacks': 'sacks',
    'interceptions': 'interceptions',
    # Special Teams (future)
    'kicking': 'fg_made',
    'punting': 'punts',
}

# NFL-style leaderboard qualifiers (minimum attempts per game)
# Formula: MIN = qualifier × games_played
LEADERBOARD_QUALIFIER_PASS_ATT_PER_GAME = 14.0    # 14 att/game for passer rating
LEADERBOARD_QUALIFIER_RUSH_CAR_PER_GAME = 6.25    # 6.25 car/game for rushing title

# Display column widths (for consistent table formatting)
LEADERBOARD_RANK_WIDTH = 5
LEADERBOARD_NAME_WIDTH = 25
LEADERBOARD_TEAM_WIDTH = 5
LEADERBOARD_STAT_WIDTH = 6


# ======================
# OFFSEASON ORCHESTRATION
# ======================

OFFSEASON_PHASE_SEQUENCE = [
    "end_of_season_review",
    "staff_evaluation",
    "franchise_tag_window",
    "scouting_early",
    "combine",
    "free_agency",
    "predraft",
    "draft",
    "training_camp",
    "season_ready",
]

TRAINING_CAMP_ROSTER_LIMIT = 53
OFFSEASON_WEEK = 0

OFFSEASON_PHASE_NARRATIVES = {
    'end_of_season_review': "Season {season_year} is complete. Review your performance.",
    'staff_evaluation': "Evaluate your coaching staff.",
    'franchise_tag_window': "You may apply one franchise tag.",
    'scouting_early': "Scouts assigned to the {draft_year} draft class.",
    'combine': "The NFL Combine is underway.",
    'free_agency': "Free agency has opened. {fa_count} players available.",
    'predraft': "Final draft preparation. Review your board.",
    'draft': "The {draft_year} NFL Draft is underway.",
    'training_camp': "Training camp. Cut to 53 before Week 1.",
    'season_ready': "Roster set for {next_season} season.",
}


def from_letter_grade(grade: str) -> int:
    """
    Convert letter grade to approximate midpoint rating.

    Useful for generation and testing.

    Args:
        grade: Letter grade (A+ through F)

    Returns:
        Approximate rating (midpoint of range)
    """
    grade_midpoints = {
        "A+": 98,
        "A": 95,
        "A-": 91,
        "B+": 88,
        "B": 85,
        "B-": 81,
        "C+": 78,
        "C": 75,
        "C-": 71,
        "D+": 68,
        "D": 63,
        "F": 50,
    }
    return grade_midpoints.get(grade, 50)


# ==============================
# COACH IDENTITY (Phase 4)
# ==============================
COACH_MIN_AGE = 35
COACH_MAX_AGE = 65
DEFAULT_PLAYER_COACH_FIRST_NAME = "Head"
DEFAULT_PLAYER_COACH_LAST_NAME = "Coach"
DEFAULT_PLAYER_COACH_ARCHETYPE = "analytics"

COACH_TENURE_END_REASONS = ('fired', 'resigned', 'mutual', 'championship_walkout', 'current', 'replaced')
GM_PERSONALITIES_TUPLE = ('draft_purist', 'win_now', 'analytics', 'loyalty', 'opportunist')


# ==============================
# AI GM BEHAVIOR (Phase 4 Prompt #3)
# ==============================

# Team phases
TEAM_PHASES = ('rebuild', 'bridge', 'contend', 'win_now', 'decline')
TEAM_PHASE_DEFAULT = 'bridge'

# Phase classifier thresholds
PHASE_STAR_THRESHOLD = 90              # true_overall >= 90 = "star"
PHASE_MIN_STARS_CONTEND = 3
PHASE_MIN_STARS_BRIDGE = 2             # <2 = rebuild
PHASE_ROSTER_YOUNG_AGE_MAX = 24.5
PHASE_ROSTER_OLD_AGE_MIN = 28.5
PHASE_CAP_HEALTHY_THRESHOLD = 30_000_000
PHASE_CAP_STRESSED_THRESHOLD = 5_000_000
PHASE_WINNING_RECORD_PCT = 0.500
PHASE_STRONG_RECORD_PCT = 0.588        # ~10+ wins
PHASE_LOOKBACK_SEASONS = 2
PHASE_CONSECUTIVE_LOSING_DECLINE = 2

# Personality transition speed modifiers
PHASE_TRANSITION_SPEED = {
    'draft_purist': {'to_rebuild': 1.0, 'to_win_now': 0.3},
    'win_now':      {'to_rebuild': 0.3, 'to_win_now': 1.0},
    'analytics':    {'to_rebuild': 0.7, 'to_win_now': 0.6},
    'loyalty':      {'to_rebuild': 0.5, 'to_win_now': 0.5},
    'opportunist':  {'to_rebuild': 0.6, 'to_win_now': 0.8},
}

# Draft strategy weights
DRAFT_STRATEGY_WEIGHTS = {
    'bpa':    {'talent': 0.75, 'need': 0.25},
    'need':   {'talent': 0.35, 'need': 0.65},
    'upside': {'talent': 0.70, 'need': 0.30},
}
DRAFT_UPSIDE_NOISE_BOOST = 5

# AI coaching carousel
CAROUSEL_CONSECUTIVE_LOSING_THRESHOLD = 2
CAROUSEL_NO_PLAYOFFS_CONTENDER_THRESHOLD = 3
CAROUSEL_FIRE_PROBABILITY_LOSING = 0.80
CAROUSEL_FIRE_PROBABILITY_NO_PLAYOFFS = 0.60
CAROUSEL_MIN_TENURE_SEASONS = 2
CAROUSEL_HIRE_WEIGHTS_BY_PHASE = {
    'rebuild':  {'draft_purist': 0.35, 'analytics': 0.30, 'loyalty': 0.15, 'win_now': 0.05, 'opportunist': 0.15},
    'bridge':   {'draft_purist': 0.20, 'analytics': 0.30, 'loyalty': 0.20, 'win_now': 0.10, 'opportunist': 0.20},
    'contend':  {'draft_purist': 0.10, 'analytics': 0.25, 'loyalty': 0.15, 'win_now': 0.30, 'opportunist': 0.20},
    'win_now':  {'draft_purist': 0.05, 'analytics': 0.15, 'loyalty': 0.10, 'win_now': 0.45, 'opportunist': 0.25},
    'decline':  {'draft_purist': 0.30, 'analytics': 0.30, 'loyalty': 0.15, 'win_now': 0.05, 'opportunist': 0.20},
}


# ==============================
# OWNER SENTIMENT (Phase 4 Prompt #4)
# ==============================

# Sentiment range
SENTIMENT_MIN = 0
SENTIMENT_MAX = 100
SENTIMENT_DEFAULT = 70

# Preseason expectations
EXPECTATION_TIERS = ('rebuild', 'competitive', 'playoff', 'championship')
EXPECTATION_WIN_TARGETS = {
    'rebuild': 4,
    'competitive': 8,
    'playoff': 10,
    'championship': 12,
}

# Sentiment driver weights
SENTIMENT_WEIGHT_PER_WIN_ABOVE = 5
SENTIMENT_WEIGHT_PER_WIN_BELOW = -5
SENTIMENT_CAP_HEALTHY_THRESHOLD = 30_000_000
SENTIMENT_CAP_HEALTHY_BONUS = 20
SENTIMENT_CAP_OVER_PENALTY = -20
SENTIMENT_STAR_HOLDOUT_PENALTY = -10
SENTIMENT_PLAYOFF_BONUS = 15
SENTIMENT_CHAMPIONSHIP_BONUS = 25

# Hot seat tiers (inclusive ranges)
HOT_SEAT_TIERS = {
    'untouchable': (70, 100),
    'stable': (40, 69),
    'warm': (20, 39),
    'hot': (10, 19),
    'termination': (0, 9),
}

# Firing probabilities by tier
FIRING_PROB_MID_SEASON = {
    'untouchable': 0.0,
    'stable': 0.0,
    'warm': 0.0,
    'hot': 0.25,
    'termination': 0.75,
}

FIRING_PROB_END_SEASON = {
    'untouchable': 0.0,
    'stable': 0.05,
    'warm': 0.30,
    'hot': 0.70,
    'termination': 0.95,
}

MID_SEASON_FIRING_START_WEEK = 6
MID_SEASON_FIRING_END_WEEK = 16

# ==============================
# COACH JOB OFFERS (Phase 4 Prompt #4)
# ==============================

VACANCY_OFFER_WINDOW_WEEKS = 2
VACANCY_MIN_OFFERS = 1
VACANCY_MAX_OFFERS = 3

OFFER_QUALITY_TIERS = ('elite', 'good', 'average', 'struggling')
OFFER_QUALITY_THRESHOLDS = {
    'elite': {'cap_min': 20_000_000, 'wpct_min': 0.600},
    'good': {'cap_min': 10_000_000, 'wpct_min': 0.470},
    'average': {'cap_min': 0, 'wpct_min': 0.0},
}

OFFER_COUNT_BY_LEGACY_QUARTILE = {
    4: 3,  # top 25%
    3: 2,
    2: 2,
    1: 1,  # bottom 25%
}

MUTUAL_PARTING_TIER_BOOST = True


# ==============================
# TIER 1 PRESS CONFERENCE (Phase 4 Prompt #5)
# ==============================

PRESS_AUTOPILOT_VALID_CHOICES = ('deflect', 'accountable', 'confrontational')
PRESS_AUTOPILOT_HARNESS_FALLBACK = 'accountable'  # stress harness default

# Effect magnitudes (small per §5.3)
PRESS_EFFECTS = {
    'deflect': {
        'owner': -1, 'fan': -1, 'locker_room': +1,
    },
    'accountable': {
        'owner': +1, 'fan': +1, 'locker_room': 0,
    },
    'confrontational': {
        'owner': -2, 'fan': +2, 'locker_room': -1,
    },
}

# Context detection
PRESS_BLOWOUT_MARGIN = 14
PRESS_LOSING_STREAK_THRESHOLD = 3
PRESS_WINNING_STREAK_THRESHOLD = 3
PRESS_LOCKER_ROOM_TOP_N_PLAYERS = 10  # MVP simplification


# ==============================
# TIER 2 DRAMATIC PRESS CONFERENCE (Phase 4 Prompt #6)
# ==============================

TIER2_MAX_PER_SEASON = 8
TIER2_HEADLESS_FALLBACK = 'accountable'
TIER2_VALID_CHOICES = ('deflect', 'accountable', 'confrontational')

TIER2_EFFECTS = {
    'deflect':         {'owner': -3, 'fan': -3, 'locker_room': +2},
    'accountable':     {'owner': +4, 'fan': +4, 'locker_room': +1},
    'confrontational': {'owner': -5, 'fan': +5, 'locker_room': -3},
}

TIER2_STAR_RATING_THRESHOLD = 88
TIER2_LOSING_STREAK_GAMES = 3

TIER2_TRIGGER_PRIORITY = (
    'championship_won',
    'dynasty_milestone',
    'playoff_loss',
    'star_injury',
    'blockbuster_trade',
    'blown_lead',
    'holdout_public',
    'losing_streak_3',
    'rising_star_streak',  # Phase 5 P5 — lowest drama priority
)


# ==============================
# STRESS HARNESS (Phase 4)
# ==============================
STRESS_TEST_DEFAULT_SEASONS = 3
STRESS_TEST_SMOKE_SEASONS = 10
STRESS_TEST_TIMEOUT_SECONDS_PER_SEASON = 300

MAX_CAP_OVERAGE_TOLERANCE = 0
MIN_RETIREMENT_RATE = 0.08

HEALTH_STAR_RATING_THRESHOLD = 90
HEALTH_AGE_BUCKETS = [(20, 24), (25, 28), (29, 32), (33, 99)]
HEALTH_CAP_BUCKETS = [
    ('healthy', 30_000_000, float('inf')),
    ('tight', 0, 30_000_000),
    ('over', float('-inf'), 0),
]


# ==============================
# LEGACY EXPANSION (Phase 4 Prompt #7)
# ==============================

# Era difficulty
ERA_DIFFICULTY_BASELINE_VARIANCE = 0.16        # NFL typical W% stdev
ERA_DIFFICULTY_VARIANCE_RANGE = 0.05           # ±0.05 → ±0.15 multiplier
ERA_DIFFICULTY_MIN = 0.85
ERA_DIFFICULTY_MAX = 1.15
ERA_DIFFICULTY_SMOOTHING_WINDOW = 3            # 3-season avg

# Starting condition (locked at hire)
STARTING_CONDITION_BUCKETS = (
    (0.300, 1.20),    # Inherited disaster
    (0.450, 1.10),
    (0.550, 1.00),    # Baseline
    (0.700, 0.95),
    (1.001, 0.90),    # Inherited contender
)

# Tenure stability bonus
TENURE_STABILITY_THRESHOLD_YEARS = 5
TENURE_STABILITY_PER_YEAR = 5
TENURE_STABILITY_CAP = 25

# Dynasty / HOF triggers (re-exported here for narrative system)
# Note: HOF_LEGACY_THRESHOLD defined earlier in LEGACY constants section

# Narrative triggers
NARRATIVE_DRAMATIC_TRIGGERS = (
    'championship_won',
    'dynasty_flag_activated',
    'hof_eligible_first_time',
    'narrow_firing_escape',
    'star_player_developed',
    'first_playoff_appearance',
    'first_division_title',
)
NARRATIVE_TEMPLATE_COUNT_PER_TRIGGER = 4

# ======================
# HISTORICAL RECORDS (Phase 4 Prompt #8)
# ======================

# === League record categories ===
# Verified against schema.sql (box_score/player_season_stats/player_career_stats)
LEAGUE_RECORD_CATEGORIES = {
    # Player records — passing
    'passing_yards':    ('Passing yards',    'pass_yards'),
    'passing_tds':      ('Passing TDs',      'pass_tds'),
    'completions':      ('Completions',      'completions'),
    'pass_attempts':    ('Pass attempts',    'pass_attempts'),

    # Player records — rushing
    'rushing_yards':    ('Rushing yards',    'rush_yards'),
    'rushing_tds':      ('Rushing TDs',      'rush_tds'),
    'rush_attempts':    ('Rush attempts',    'carries'),  # NOTE: column is 'carries'

    # Player records — receiving
    'receiving_yards':  ('Receiving yards',  'rec_yards'),
    'receptions':       ('Receptions',       'receptions'),
    'receiving_tds':    ('Receiving TDs',    'rec_tds'),

    # Player records — defense
    'sacks':            ('Sacks',            'sacks'),  # REAL type
    'interceptions':    ('Interceptions',    'interceptions'),
    'tackles':          ('Tackles',          'tackles'),

    # Player records — kicking
    'field_goals':      ('Field goals made', 'fg_made'),
    'fg_long':          ('Longest FG',       'fg_long'),
}

LEAGUE_RECORD_SCOPES = ('single_game', 'single_season', 'career')

# === Team records ===
TEAM_RECORD_CATEGORIES = {
    'season_wins':        ('Most wins, season',     'wins'),
    'season_points_for':  ('Most points scored',    'points_for'),
}

# === Display config ===
CHAMPION_HISTORY_DEFAULT_LIMIT = 25
ALL_TIME_LEADERS_DEFAULT_TOP_N = 10


# ==============================
# PHASE 4 — DISPLAY LAYER (Prompt #9)
# ==============================

DISPLAY_WIDTH = 70
DISPLAY_BORDER_HEAVY = '=' * DISPLAY_WIDTH
DISPLAY_BORDER_LIGHT = '-' * DISPLAY_WIDTH

# ANSI color codes (optional, gracefully degrade if not supported)
ANSI_RESET = '\033[0m'
ANSI_BOLD = '\033[1m'
ANSI_DIM = '\033[2m'
ANSI_CYAN = '\033[36m'
ANSI_YELLOW = '\033[33m'
ANSI_GREEN = '\033[32m'
ANSI_RED = '\033[31m'

SEASON_SUMMARY_SECTIONS = (
    'header',
    'outcome',
    'narrative',
    'owner_relationship',
    'legacy_update',
    'peer_rank',
    'records_broken',
    'press_summary',
)

# ====================================
# PHASE 4 REFACTOR — MISSING CONSTANTS
# ====================================

# Team Phase Classification
PHASE_WIN_NOW_AGE_MIN = 26.5  # Minimum roster age for win-now phase

# Narrative Beats
NARRATIVE_STAR_DEVELOPMENT_MIN_JUMP = 15  # OVR increase for star narrative
NARRATIVE_DOMINANT_SEASON_WINS = 12  # Wins threshold for dominant season
NARRATIVE_STRUGGLING_SEASON_WINS = 4  # Wins threshold for struggling season
NARRATIVE_LARGE_POINT_DIFF = 100  # Point differential threshold

# Coach Offers
OFFER_QUALITY_RANK_MAP = {'elite': 4, 'good': 3, 'average': 2, 'struggling': 1}
OFFER_QUALITY_WPCT_LOOKBACK = 2  # Seasons for W% evaluation

# Tier 2 Triggers
PLAYOFF_WEEK_TO_ROUND_MAP = {18: 'wildcard', 19: 'divisional', 20: 'conference', 21: 'super_bowl'}
CHAMPIONSHIP_MVP_SACK_VALUE_MULTIPLIER = 20  # Sack value for MVP calc

# UI Display
CAREER_VIEW_RECENT_SEASONS_LIMIT = 10
CAREER_VIEW_RECORDS_DISPLAY_LIMIT = 10
COLOR_CODE_LENGTH_OFFSET_YELLOW = 11  # ANSI centering offset
COLOR_CODE_LENGTH_OFFSET_BOLD = 8

# Era Context
TIE_VALUE_IN_WIN_PCT = 0.5  # Tie value in win percentage


# ======================
# DEPTH CHART SYSTEM (Phase 5 Prompt #3)
# ======================

# 27 granular depth chart positions
DEPTH_CHART_POSITIONS = [
    # Offense (12)
    'QB', 'RB', 'FB', 'WR1', 'WR2', 'WR3', 'TE',
    'LT', 'LG', 'C', 'RG', 'RT',
    # Defense (11)
    'LE', 'DT1', 'DT2', 'RE', 'LOLB', 'MLB', 'ROLB',
    'CB1', 'CB2', 'FS', 'SS',
    # Special Teams (4 - LS/KR/PR are roles, not starter positions)
    'K', 'P', 'KR', 'PR',
]

# Map depth chart position to generic player position
DEPTH_CHART_TO_PLAYER_POSITION = {
    'QB': 'QB', 'RB': 'RB', 'FB': 'RB',  # FB maps to RB
    'WR1': 'WR', 'WR2': 'WR', 'WR3': 'WR',
    'TE': 'TE',
    'LT': 'OL', 'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
    'LE': 'DL', 'DT1': 'DL', 'DT2': 'DL', 'RE': 'DL',
    'LOLB': 'LB', 'MLB': 'LB', 'ROLB': 'LB',
    'CB1': 'CB', 'CB2': 'CB',
    'FS': 'S', 'SS': 'S',
    'K': 'K', 'P': 'P',
    'KR': 'WR',  # Kick returner typically WR or RB
    'PR': 'WR',  # Punt returner typically WR
}

# Positions that can be played interchangeably without penalty
FLEXIBLE_POSITION_EQUIVALENTS = {
    'OL': ['LT', 'LG', 'C', 'RG', 'RT'],  # All O-line positions interchangeable
    'DL': ['LE', 'DT1', 'DT2', 'RE'],     # D-line positions interchangeable
    'WR': ['WR1', 'WR2', 'WR3'],          # WR positions interchangeable
    'CB': ['CB1', 'CB2'],                 # CB positions interchangeable
    'S': ['FS', 'SS'],                    # Safety positions interchangeable
}

# SAR penalty when player's position doesn't match depth chart slot
# (and not in FLEXIBLE_POSITION_EQUIVALENTS)
OUT_OF_POSITION_SAR_PENALTY = 10

# Max depth per position (starter + backups)
MAX_DEPTH_PER_POSITION = 3  # slot_order 1, 2, 3

# Injury statuses that trigger auto-promotion
AUTO_PROMOTE_INJURY_STATUSES = ['Out', 'IR', 'PUP']
