"""
Weather system: generate weather for a game based on city/climate/week,
and apply weather modifiers to ratings.

Pure module — reads constants only, no engine dependencies.
"""

import random

from ..utils.constants import WEATHER_MODIFIERS, LATE_SEASON_WEEK


# Climate → weather probability distributions by time of year
# Early season (weeks 1-8): milder
# Late season (weeks 9-17): harsher for cold climates
_WEATHER_WEIGHTS_BY_CLIMATE = {
    'cold': {
        'early': {'clear': 0.50, 'wind': 0.20, 'rain': 0.20, 'snow': 0.00, 'cold': 0.10, 'extreme_cold': 0.00},
        'late':  {'clear': 0.20, 'wind': 0.15, 'rain': 0.10, 'snow': 0.20, 'cold': 0.25, 'extreme_cold': 0.10},
    },
    'warm': {
        'early': {'clear': 0.60, 'wind': 0.15, 'rain': 0.20, 'snow': 0.00, 'cold': 0.05, 'extreme_cold': 0.00},
        'late':  {'clear': 0.55, 'wind': 0.15, 'rain': 0.20, 'snow': 0.00, 'cold': 0.10, 'extreme_cold': 0.00},
    },
    'neutral': {
        'early': {'clear': 0.55, 'wind': 0.20, 'rain': 0.15, 'snow': 0.00, 'cold': 0.10, 'extreme_cold': 0.00},
        'late':  {'clear': 0.35, 'wind': 0.15, 'rain': 0.15, 'snow': 0.10, 'cold': 0.20, 'extreme_cold': 0.05},
    },
}


def generate_weather(stadium_type: str, climate: str, week_number: int) -> dict:
    """
    Generate weather conditions for a game.

    Dome stadiums always get clear weather.

    Args:
        stadium_type: 'dome' or 'outdoor'
        climate: 'cold', 'warm', or 'neutral'
        week_number: Current week (1-21)

    Returns:
        dict with:
            'condition': str (weather condition key)
            'wind_speed': int (mph)
            'temperature': int (Fahrenheit)
            'precipitation': bool
    """
    if stadium_type == 'dome':
        return {
            'condition': 'clear',
            'wind_speed': 0,
            'temperature': 72,
            'precipitation': False,
        }

    # Determine season phase
    phase = 'late' if week_number >= LATE_SEASON_WEEK else 'early'

    # Get probability distribution for this climate/phase
    weights_dict = _WEATHER_WEIGHTS_BY_CLIMATE.get(climate, _WEATHER_WEIGHTS_BY_CLIMATE['neutral'])
    phase_weights = weights_dict[phase]

    conditions = list(phase_weights.keys())
    weights = list(phase_weights.values())
    condition = random.choices(conditions, weights=weights, k=1)[0]

    # Generate temperature based on condition and climate
    temperature = _generate_temperature(condition, climate, week_number)

    # Generate wind speed
    wind_speed = _generate_wind_speed(condition)

    # Precipitation
    precipitation = condition in ('rain', 'snow')

    return {
        'condition': condition,
        'wind_speed': wind_speed,
        'temperature': temperature,
        'precipitation': precipitation,
    }


def _generate_temperature(condition: str, climate: str, week: int) -> int:
    """Generate realistic temperature based on conditions."""
    base_temps = {
        'cold': {'early': (50, 70), 'late': (15, 40)},
        'warm': {'early': (75, 95), 'late': (55, 75)},
        'neutral': {'early': (60, 80), 'late': (35, 55)},
    }
    phase = 'late' if week >= LATE_SEASON_WEEK else 'early'
    temp_range = base_temps.get(climate, base_temps['neutral'])[phase]
    base_temp = random.randint(temp_range[0], temp_range[1])

    # Adjust for specific conditions
    if condition == 'extreme_cold':
        base_temp = random.randint(-5, 15)
    elif condition == 'cold':
        base_temp = min(base_temp, random.randint(20, 35))
    elif condition == 'snow':
        base_temp = min(base_temp, random.randint(20, 34))

    return base_temp


def _generate_wind_speed(condition: str) -> int:
    """Generate wind speed based on condition."""
    if condition == 'wind':
        return random.randint(15, 30)
    elif condition in ('snow', 'rain'):
        return random.randint(5, 20)
    elif condition in ('cold', 'extreme_cold'):
        return random.randint(5, 25)
    else:
        return random.randint(0, 10)


def get_weather_modifiers(weather: dict) -> dict:
    """
    Get rating modifiers for the current weather condition.

    Args:
        weather: Weather dict from generate_weather()

    Returns:
        dict with modifier keys: 'accuracy', 'speed', 'fumble', 'kick'
    """
    base_mods = WEATHER_MODIFIERS.get(weather['condition'], WEATHER_MODIFIERS['clear']).copy()

    # Additional wind penalty for deep passes when wind > 15 mph
    if weather['wind_speed'] > 15:
        extra_accuracy = -(weather['wind_speed'] - 15) // 3
        base_mods['deep_pass_accuracy'] = base_mods.get('accuracy', 0) + extra_accuracy
    else:
        base_mods['deep_pass_accuracy'] = base_mods.get('accuracy', 0)

    return base_mods


def apply_weather_to_rating(rating: int, modifier: int) -> int:
    """
    Apply a weather modifier to a rating, clamping to valid range.

    Args:
        rating: Base rating (1-99)
        modifier: Weather modifier (can be negative)

    Returns:
        Modified rating (clamped 1-99)
    """
    return max(1, min(99, rating + modifier))
