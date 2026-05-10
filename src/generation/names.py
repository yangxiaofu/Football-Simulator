"""
Name generation for players, teams, and staff.

Contains lists of first names, last names, cities, and team nicknames
for generating fictional entities.
"""

import random

# ======================
# PLAYER NAMES
# ======================

FIRST_NAMES = [
    # A-D
    "Aaron", "Adam", "Adrian", "Alan", "Alex", "Andre", "Andrew", "Anthony", "Antonio", "Austin",
    "Ben", "Brandon", "Brent", "Brett", "Brian", "Bryan", "Caleb", "Calvin", "Cameron", "Carl",
    "Carlos", "Chad", "Charles", "Chris", "Christian", "Christopher", "Cody", "Colin", "Connor", "Corey",
    "Curtis", "Dakota", "Daniel", "Dante", "Darius", "Darren", "David", "Derek", "Devin", "Dominic",
    # E-J
    "Eric", "Ethan", "Evan", "Frank", "Gabriel", "Gary", "George", "Gerald", "Grant", "Gregory",
    "Harrison", "Henry", "Hunter", "Isaac", "Isaiah", "Jack", "Jacob", "Jalen", "James", "Jared",
    "Jason", "Javon", "Jay", "Jeff", "Jeffrey", "Jeremy", "Jerome", "Jesse", "Joe", "John",
    "Jonathan", "Jordan", "Jose", "Joseph", "Joshua", "Julian", "Justin", "Keith", "Kenneth", "Kevin",
    # K-O
    "Kyle", "Lance", "Larry", "Lawrence", "Leo", "Leonard", "Logan", "Luke", "Marcus", "Mario",
    "Mark", "Marlon", "Martin", "Mason", "Matt", "Matthew", "Maurice", "Max", "Michael", "Mike",
    "Mitchell", "Nathan", "Nathaniel", "Nicholas", "Nick", "Noah", "Oliver", "Omar", "Oscar",
    # P-Z
    "Patrick", "Paul", "Peter", "Philip", "Quentin", "Quincy", "Ralph", "Randall", "Randy", "Raymond",
    "Richard", "Ricky", "Robert", "Rodney", "Roger", "Ronald", "Russell", "Ryan", "Sam", "Samuel",
    "Scott", "Sean", "Sergio", "Seth", "Shane", "Shawn", "Spencer", "Stephen", "Steve", "Steven",
    "Terence", "Terry", "Thomas", "Tim", "Timothy", "Todd", "Tom", "Tony", "Travis", "Trevor",
    "Troy", "Tyler", "Victor", "Vincent", "Walter", "Wayne", "Will", "William", "Xavier", "Zachary",
]

LAST_NAMES = [
    # A-C
    "Adams", "Allen", "Anderson", "Bailey", "Baker", "Barnes", "Bell", "Bennett", "Brooks", "Brown",
    "Bryant", "Butler", "Campbell", "Carter", "Clark", "Coleman", "Collins", "Cook", "Cooper", "Cox",
    "Crawford", "Cruz",
    # D-G
    "Davis", "Diaz", "Dixon", "Edwards", "Ellis", "Evans", "Fisher", "Flores", "Ford", "Foster",
    "Fox", "Freeman", "Garcia", "Gibson", "Gonzalez", "Gordon", "Graham", "Grant", "Gray", "Green",
    "Griffin", "Hall", "Hamilton", "Harris", "Harrison", "Hayes", "Henderson", "Hernandez", "Hill",
    "Howard", "Hughes", "Hunt", "Hunter",
    # H-L
    "Jackson", "James", "Jenkins", "Johnson", "Jones", "Jordan", "Kelly", "King", "Knight", "Lawrence",
    "Lee", "Lewis", "Long", "Lopez", "Lynch",
    # M-P
    "Marshall", "Martin", "Martinez", "Mason", "Matthews", "McDonald", "Miller", "Mills", "Mitchell",
    "Moore", "Morales", "Morgan", "Morris", "Murphy", "Murray", "Nelson", "Nguyen", "Owens", "Parker",
    "Patterson", "Perez", "Perry", "Peterson", "Phillips", "Powell", "Price",
    # R-T
    "Ramirez", "Reed", "Reid", "Reynolds", "Rice", "Richardson", "Rivera", "Roberts", "Robertson",
    "Robinson", "Rodriguez", "Rogers", "Ross", "Russell", "Sanders", "Scott", "Shaw", "Simmons",
    "Simpson", "Smith", "Stevens", "Stewart", "Stone", "Sullivan", "Taylor", "Thomas", "Thompson",
    "Torres", "Tucker", "Turner",
    # U-Z
    "Wagner", "Walker", "Wallace", "Ward", "Warren", "Washington", "Watson", "Webb", "Wells", "West",
    "White", "Williams", "Wilson", "Wood", "Woods", "Wright", "Young",
]

# ======================
# TEAM NAMES
# ======================

# City names for fictional teams (mix of real and slightly altered)
TEAM_CITIES = [
    # AFC North
    "Baltimore", "Cincinnati", "Cleveland", "Pittsburgh",
    # AFC South
    "Houston", "Indianapolis", "Jacksonville", "Nashville",
    # AFC East
    "Buffalo", "Miami", "Boston", "New York",
    # AFC West
    "Denver", "Kansas City", "Las Vegas", "Los Angeles",
    # NFC North
    "Chicago", "Detroit", "Green Bay", "Minneapolis",
    # NFC South
    "Atlanta", "Charlotte", "New Orleans", "Tampa Bay",
    # NFC East
    "Dallas", "Philadelphia", "Phoenix", "Washington",
    # NFC West
    "San Francisco", "Seattle", "Tucson", "Portland",
]

# Team nicknames
TEAM_NICKNAMES = [
    # Animals
    "Bears", "Bengals", "Broncos", "Cardinals", "Colts", "Eagles", "Falcons", "Jaguars", "Lions",
    "Panthers", "Ravens", "Seahawks", "Stallions", "Wolves", "Cougars", "Raptors",
    # Occupations/Warriors
    "Buccaneers", "Chiefs", "Cowboys", "Miners", "Patriots", "Pirates", "Raiders", "Rangers",
    "Steelers", "Titans", "Commanders", "Guardians", "Outlaws", "Thunder",
    # Other
    "Bolts", "Storm", "Blaze", "Impact",
]

# Abbreviations will be generated from city names (first 3 letters or custom)
TEAM_ABBREVIATIONS = {
    "Baltimore": "BAL",
    "Cincinnati": "CIN",
    "Cleveland": "CLE",
    "Pittsburgh": "PIT",
    "Houston": "HOU",
    "Indianapolis": "IND",
    "Jacksonville": "JAX",
    "Nashville": "NSH",
    "Buffalo": "BUF",
    "Miami": "MIA",
    "Boston": "BOS",
    "New York": "NYJ",
    "Denver": "DEN",
    "Kansas City": "KC",
    "Las Vegas": "LV",
    "Los Angeles": "LAC",
    "Chicago": "CHI",
    "Detroit": "DET",
    "Green Bay": "GB",
    "Minneapolis": "MIN",
    "Atlanta": "ATL",
    "Charlotte": "CAR",
    "New Orleans": "NO",
    "Tampa Bay": "TB",
    "Dallas": "DAL",
    "Philadelphia": "PHI",
    "Phoenix": "ARI",
    "Washington": "WAS",
    "San Francisco": "SF",
    "Seattle": "SEA",
    "Tucson": "TUC",
    "Portland": "POR",
}

# ======================
# COLLEGE NAMES
# ======================

COLLEGES = [
    # Power 5
    "Alabama", "Auburn", "Florida", "Georgia", "LSU", "Tennessee", "Texas A&M", "Kentucky",
    "Ohio State", "Michigan", "Penn State", "Wisconsin", "Iowa", "Nebraska", "Michigan State",
    "Clemson", "Florida State", "Miami", "North Carolina", "Virginia Tech", "NC State",
    "USC", "Oregon", "Washington", "Stanford", "UCLA", "Utah", "Arizona State",
    "Oklahoma", "Texas", "Oklahoma State", "TCU", "Baylor", "Kansas State",
    # Group of 5
    "UCF", "Memphis", "Cincinnati", "Houston", "SMU", "Tulane",
    "Boise State", "San Diego State", "Fresno State", "Air Force",
    "Marshall", "UAB", "Western Kentucky", "Florida Atlantic",
    "Central Michigan", "Toledo", "Northern Illinois", "Ball State",
    "Appalachian State", "Coastal Carolina", "Louisiana", "Troy",
]

# ======================
# GENERATION FUNCTIONS
# ======================

def generate_player_name() -> tuple[str, str]:
    """
    Generate a random player name.

    Returns:
        Tuple of (first_name, last_name)
    """
    return (random.choice(FIRST_NAMES), random.choice(LAST_NAMES))


def generate_staff_name() -> tuple[str, str]:
    """
    Generate a random staff member name.

    Returns:
        Tuple of (first_name, last_name)
    """
    return (random.choice(FIRST_NAMES), random.choice(LAST_NAMES))


def generate_college() -> str:
    """
    Generate a random college name.

    Returns:
        College name
    """
    return random.choice(COLLEGES)
