"""
GameState: dataclass representing the complete state of a game in progress.

Includes clock management, drive tracking, and possession management.

Pure dataclass — no engine imports.
"""

from dataclasses import dataclass, field

from ..utils.constants import QUARTER_LENGTH_SECONDS, OT_LENGTH_SECONDS


@dataclass
class GameState:
    """
    Complete mutable state of a game in progress.

    All game loop operations modify this object.
    """
    # Teams
    home_team_id: int = 0
    away_team_id: int = 0
    home_team_name: str = ""
    away_team_name: str = ""
    home_team_abbr: str = ""
    away_team_abbr: str = ""

    # Score
    home_score: int = 0
    away_score: int = 0

    # Clock
    quarter: int = 1
    time_remaining: int = QUARTER_LENGTH_SECONDS  # seconds left in current quarter
    play_clock: int = 40

    # Possession
    possession_team_id: int = 0
    field_position: int = 25  # yards from own end zone (1-99)
    down: int = 1
    distance: int = 10
    is_kickoff: bool = True

    # Drive tracking
    drive_plays: int = 0
    drive_yards: int = 0
    drive_start_position: int = 25

    # Timeouts
    home_timeouts: int = 3
    away_timeouts: int = 3

    # Game state flags
    is_halftime: bool = False
    is_overtime: bool = False
    is_game_over: bool = False
    coin_toss_winner: int = 0
    coin_toss_deferred: bool = False

    # Play tracking
    play_number: int = 0
    total_plays: int = 0

    # Player stamina tracking (player_id -> current_stamina)
    player_stamina: dict = field(default_factory=dict)

    # In-game injuries (player_id -> injury_dict)
    in_game_injuries: dict = field(default_factory=dict)

    @property
    def score_diff(self) -> int:
        """Score difference from possession team's perspective."""
        if self.possession_team_id == self.home_team_id:
            return self.home_score - self.away_score
        return self.away_score - self.home_score

    @property
    def defending_team_id(self) -> int:
        """ID of the team currently on defense."""
        if self.possession_team_id == self.home_team_id:
            return self.away_team_id
        return self.home_team_id

    @property
    def yards_to_endzone(self) -> int:
        """Yards from current position to the opponent's end zone."""
        return 100 - self.field_position

    @property
    def is_red_zone(self) -> bool:
        """Is the offense inside the opponent's 20-yard line?"""
        return self.yards_to_endzone <= 20

    @property
    def is_goal_line(self) -> bool:
        """Is the offense inside the opponent's 5-yard line?"""
        return self.yards_to_endzone <= 5

    @property
    def is_two_minute_drill(self) -> bool:
        """Is the clock under 2 minutes in 2nd or 4th quarter?"""
        return self.time_remaining <= 120 and self.quarter in (2, 4)

    @property
    def possession_team_name(self) -> str:
        if self.possession_team_id == self.home_team_id:
            return self.home_team_name
        return self.away_team_name

    @property
    def possession_team_abbr(self) -> str:
        if self.possession_team_id == self.home_team_id:
            return self.home_team_abbr
        return self.away_team_abbr

    @property
    def defending_team_name(self) -> str:
        if self.possession_team_id == self.home_team_id:
            return self.away_team_name
        return self.home_team_name

    def advance_clock(self, seconds: int) -> None:
        """
        Subtract time from the game clock.

        Handles quarter transitions via check_quarter_end().

        Args:
            seconds: Seconds to subtract
        """
        self.time_remaining = max(0, self.time_remaining - seconds)

    def check_quarter_end(self) -> bool:
        """
        Check if the current quarter has ended. If so, advance to next.

        Returns:
            True if quarter ended (caller should handle halftime/game end)
        """
        if self.time_remaining <= 0:
            if self.quarter == 2:
                self.is_halftime = True
                return True
            elif self.quarter == 4 and not self.is_overtime:
                if self.home_score != self.away_score:
                    self.is_game_over = True
                    return True
                else:
                    # Tied — go to overtime
                    self.is_overtime = True
                    self.quarter = 5
                    self.time_remaining = OT_LENGTH_SECONDS
                    return True
            elif self.is_overtime:
                self.is_game_over = True
                return True
            else:
                self.quarter += 1
                self.time_remaining = QUARTER_LENGTH_SECONDS
                return True
        return False

    def start_second_half(self) -> None:
        """Reset state for the second half."""
        self.quarter = 3
        self.time_remaining = QUARTER_LENGTH_SECONDS
        self.is_halftime = False
        self.home_timeouts = 3
        self.away_timeouts = 3

    def new_drive(self, team_id: int, field_pos: int = 25) -> None:
        """
        Start a new drive for the specified team.

        Args:
            team_id: Team taking possession
            field_pos: Starting field position (yards from own end zone)
        """
        self.possession_team_id = team_id
        self.field_position = field_pos
        self.down = 1
        self.distance = 10
        self.drive_plays = 0
        self.drive_yards = 0
        self.drive_start_position = field_pos
        self.is_kickoff = False

    def advance_play(self, yards: int) -> None:
        """
        Update state after a play gains/loses yards.

        Handles first down logic and end zone detection.

        Args:
            yards: Yards gained (negative for losses)
        """
        self.field_position += yards
        self.drive_yards += yards
        self.drive_plays += 1
        self.play_number += 1
        self.total_plays += 1

        # Clamp field position
        self.field_position = max(1, min(99, self.field_position))

        # Check for first down
        self.distance -= yards
        if self.distance <= 0:
            self.down = 1
            self.distance = min(10, self.yards_to_endzone)
        else:
            self.down += 1

    def score_touchdown(self) -> None:
        """Add 6 points for a touchdown (PAT/2pt handled separately)."""
        if self.possession_team_id == self.home_team_id:
            self.home_score += 6
        else:
            self.away_score += 6

    def score_field_goal(self) -> None:
        """Add 3 points for a field goal."""
        if self.possession_team_id == self.home_team_id:
            self.home_score += 3
        else:
            self.away_score += 3

    def score_extra_point(self) -> None:
        """Add 1 point for an extra point."""
        if self.possession_team_id == self.home_team_id:
            self.home_score += 1
        else:
            self.away_score += 1

    def score_two_point(self) -> None:
        """Add 2 points for a two-point conversion."""
        if self.possession_team_id == self.home_team_id:
            self.home_score += 2
        else:
            self.away_score += 2

    def score_safety(self) -> None:
        """Add 2 points for a safety (scored by defending team)."""
        if self.possession_team_id == self.home_team_id:
            self.away_score += 2
        else:
            self.home_score += 2

    def change_possession(self) -> None:
        """Flip possession to the other team."""
        if self.possession_team_id == self.home_team_id:
            self.possession_team_id = self.away_team_id
        else:
            self.possession_team_id = self.home_team_id

    def use_timeout(self, team_id: int) -> bool:
        """
        Use a timeout for the specified team.

        Returns:
            True if timeout was available and used
        """
        if team_id == self.home_team_id and self.home_timeouts > 0:
            self.home_timeouts -= 1
            return True
        elif team_id == self.away_team_id and self.away_timeouts > 0:
            self.away_timeouts -= 1
            return True
        return False

    def get_game_state_dict(self) -> dict:
        """
        Get current state as a dict for passing to rating/clutch calculations.

        Returns:
            Dict compatible with is_clutch_situation() etc.
        """
        return {
            'quarter': self.quarter,
            'time_remaining': self.time_remaining,
            'score_diff': self.score_diff,
            'down': self.down,
            'distance': self.distance,
        }
