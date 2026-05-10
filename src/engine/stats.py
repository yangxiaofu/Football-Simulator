"""
Stats accumulator: in-memory stat tracking during a game,
plus DB write methods for box_score, key_play, and play tables.

No engine dependencies.
"""

import sqlite3
from collections import defaultdict

from ..utils.constants import (
    KEY_PLAYS_PER_GAME,
    KEY_PLAY_TOUCHDOWN_SCORE,
    KEY_PLAY_TURNOVER_SCORE,
    KEY_PLAY_BIG_PLAY_BASE_SCORE,
    KEY_PLAY_CLUTCH_SCORE,
    KEY_PLAY_FG_SCORE,
)


class StatsAccumulator:
    """
    Accumulates player stats during a single game simulation.

    All stats are tracked in-memory and flushed to the database
    once the game is complete.
    """

    def __init__(self, game_id: int, home_team_id: int, away_team_id: int):
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

        # player_id -> stat_dict
        self._stats = defaultdict(lambda: {
            'team_id': 0,
            # Passing
            'pass_attempts': 0,
            'completions': 0,
            'pass_yards': 0,
            'pass_tds': 0,
            'interceptions_thrown': 0,
            'sacks_taken': 0,
            # Rushing
            'carries': 0,
            'rush_yards': 0,
            'rush_tds': 0,
            'fumbles': 0,
            # Receiving
            'targets': 0,
            'receptions': 0,
            'rec_yards': 0,
            'rec_tds': 0,
            # Defense
            'tackles': 0,
            'sacks': 0.0,
            'interceptions': 0,
            'pass_deflections': 0,
            'forced_fumbles': 0,
            # Kicking
            'fg_attempts': 0,
            'fg_made': 0,
            'fg_long': 0,
            'xp_attempts': 0,
            'xp_made': 0,
            'punts': 0,
            'punt_yards': 0,
            # Return stats
            'punt_returns': 0,
            'punt_return_yards': 0,
            'punt_return_tds': 0,
            'kick_returns': 0,
            'kick_return_yards': 0,
            'kick_return_tds': 0,
        })

        # Play log (all plays in order)
        self._plays = []

        # Key plays (candidates for permanent storage)
        self._key_play_candidates = []

    def _ensure_team(self, player_id: int, team_id: int) -> None:
        """Set the team for a player if not already set."""
        if self._stats[player_id]['team_id'] == 0:
            self._stats[player_id]['team_id'] = team_id

    # ========== Passing stats ==========

    def record_pass_attempt(self, qb_id: int, team_id: int) -> None:
        self._ensure_team(qb_id, team_id)
        self._stats[qb_id]['pass_attempts'] += 1

    def record_completion(self, qb_id: int, receiver_id: int, team_id: int, yards: int) -> None:
        self._ensure_team(qb_id, team_id)
        self._ensure_team(receiver_id, team_id)
        self._stats[qb_id]['completions'] += 1
        self._stats[qb_id]['pass_yards'] += yards
        self._stats[receiver_id]['receptions'] += 1
        self._stats[receiver_id]['rec_yards'] += yards

    def record_pass_td(self, qb_id: int, receiver_id: int, team_id: int) -> None:
        self._ensure_team(qb_id, team_id)
        self._ensure_team(receiver_id, team_id)
        self._stats[qb_id]['pass_tds'] += 1
        self._stats[receiver_id]['rec_tds'] += 1

    def record_target(self, receiver_id: int, team_id: int) -> None:
        self._ensure_team(receiver_id, team_id)
        self._stats[receiver_id]['targets'] += 1

    def record_interception_thrown(self, qb_id: int, team_id: int) -> None:
        self._ensure_team(qb_id, team_id)
        self._stats[qb_id]['interceptions_thrown'] += 1

    def record_sack_taken(self, qb_id: int, team_id: int) -> None:
        self._ensure_team(qb_id, team_id)
        self._stats[qb_id]['sacks_taken'] += 1

    # ========== Rushing stats ==========

    def record_carry(self, runner_id: int, team_id: int, yards: int) -> None:
        self._ensure_team(runner_id, team_id)
        self._stats[runner_id]['carries'] += 1
        self._stats[runner_id]['rush_yards'] += yards

    def record_rush_td(self, runner_id: int, team_id: int) -> None:
        self._ensure_team(runner_id, team_id)
        self._stats[runner_id]['rush_tds'] += 1

    def record_fumble(self, player_id: int, team_id: int) -> None:
        self._ensure_team(player_id, team_id)
        self._stats[player_id]['fumbles'] += 1

    # ========== Defensive stats ==========

    def record_tackle(self, defender_id: int, team_id: int) -> None:
        self._ensure_team(defender_id, team_id)
        self._stats[defender_id]['tackles'] += 1

    def record_sack(self, defender_id: int, team_id: int) -> None:
        self._ensure_team(defender_id, team_id)
        self._stats[defender_id]['sacks'] += 1.0

    def record_interception(self, defender_id: int, team_id: int) -> None:
        self._ensure_team(defender_id, team_id)
        self._stats[defender_id]['interceptions'] += 1

    def record_pass_deflection(self, defender_id: int, team_id: int) -> None:
        self._ensure_team(defender_id, team_id)
        self._stats[defender_id]['pass_deflections'] += 1

    def record_forced_fumble(self, defender_id: int, team_id: int) -> None:
        self._ensure_team(defender_id, team_id)
        self._stats[defender_id]['forced_fumbles'] += 1

    # ========== Kicking stats ==========

    def record_fg_attempt(self, kicker_id: int, team_id: int, distance: int, made: bool) -> None:
        self._ensure_team(kicker_id, team_id)
        self._stats[kicker_id]['fg_attempts'] += 1
        if made:
            self._stats[kicker_id]['fg_made'] += 1
            if distance > self._stats[kicker_id]['fg_long']:
                self._stats[kicker_id]['fg_long'] = distance

    def record_xp_attempt(self, kicker_id: int, team_id: int, made: bool) -> None:
        self._ensure_team(kicker_id, team_id)
        self._stats[kicker_id]['xp_attempts'] += 1
        if made:
            self._stats[kicker_id]['xp_made'] += 1

    def record_punt(self, punter_id: int, team_id: int, yards: int) -> None:
        self._ensure_team(punter_id, team_id)
        self._stats[punter_id]['punts'] += 1
        self._stats[punter_id]['punt_yards'] += yards

    def record_punt_return(self, player_id: int, team_id: int, yards: int, is_td: bool = False) -> None:
        """Record a punt return."""
        self._ensure_team(player_id, team_id)
        self._stats[player_id]['punt_returns'] += 1
        self._stats[player_id]['punt_return_yards'] += yards
        if is_td:
            self._stats[player_id]['punt_return_tds'] += 1

    def record_kick_return(self, player_id: int, team_id: int, yards: int, is_td: bool = False) -> None:
        """Record a kickoff return."""
        self._ensure_team(player_id, team_id)
        self._stats[player_id]['kick_returns'] += 1
        self._stats[player_id]['kick_return_yards'] += yards
        if is_td:
            self._stats[player_id]['kick_return_tds'] += 1

    # ========== Play logging ==========

    def record_play(self, play_data: dict) -> None:
        """
        Record a single play to the play log.

        Args:
            play_data: Dict matching the `play` table schema
        """
        self._plays.append(play_data)

        # Check if this is a key play candidate
        is_key = (
            play_data.get('is_touchdown', False)
            or play_data.get('is_turnover', False)
            or play_data.get('is_big_play', False)
            or play_data.get('clutch_activated', False)
            or play_data.get('result') in ('fg_good', 'fg_miss', 'blocked')
        )
        if is_key:
            self._key_play_candidates.append(play_data)

    # ========== DB writes ==========

    def write_box_scores(self, conn: sqlite3.Connection) -> int:
        """
        Write all accumulated stats to the box_score table.

        Args:
            conn: Database connection (must be in transaction)

        Returns:
            Number of box score records written
        """
        count = 0
        for player_id, stats in self._stats.items():
            # Skip players with no meaningful stats
            has_stats = any(
                stats[k] != 0 for k in stats if k != 'team_id'
            )
            if not has_stats:
                continue

            conn.execute("""
                INSERT INTO box_score (
                    game_id, player_id, team_id,
                    pass_attempts, completions, pass_yards, pass_tds,
                    interceptions_thrown, sacks_taken,
                    carries, rush_yards, rush_tds, fumbles,
                    targets, receptions, rec_yards, rec_tds,
                    tackles, sacks, interceptions, pass_deflections, forced_fumbles,
                    fg_attempts, fg_made, fg_long, xp_attempts, xp_made,
                    punts, punt_yards,
                    punt_returns, punt_return_yards, punt_return_tds,
                    kick_returns, kick_return_yards, kick_return_tds
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                self.game_id, player_id, stats['team_id'],
                stats['pass_attempts'], stats['completions'], stats['pass_yards'], stats['pass_tds'],
                stats['interceptions_thrown'], stats['sacks_taken'],
                stats['carries'], stats['rush_yards'], stats['rush_tds'], stats['fumbles'],
                stats['targets'], stats['receptions'], stats['rec_yards'], stats['rec_tds'],
                stats['tackles'], stats['sacks'], stats['interceptions'],
                stats['pass_deflections'], stats['forced_fumbles'],
                stats['fg_attempts'], stats['fg_made'], stats['fg_long'],
                stats['xp_attempts'], stats['xp_made'],
                stats['punts'], stats['punt_yards'],
                stats['punt_returns'], stats['punt_return_yards'], stats['punt_return_tds'],
                stats['kick_returns'], stats['kick_return_yards'], stats['kick_return_tds'],
            ))
            count += 1

        return count

    def write_plays(self, conn: sqlite3.Connection) -> int:
        """
        Write all plays to the play table.

        Args:
            conn: Database connection

        Returns:
            Number of plays written
        """
        for play in self._plays:
            conn.execute("""
                INSERT INTO play (
                    game_id, play_number, quarter, time_remaining,
                    possession_team_id, field_position, down, distance,
                    home_score, away_score,
                    play_type, is_penalty, penalty_type, penalty_team_id,
                    yards_gained, result, is_touchdown, is_turnover, is_big_play,
                    primary_player_id, target_player_id, defender_player_id,
                    pocket_time_grade, separation_yards, clutch_activated,
                    narration_text
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?
                )
            """, (
                self.game_id,
                play.get('play_number', 0),
                play.get('quarter', 1),
                play.get('time_remaining', 0),
                play.get('possession_team_id'),
                play.get('field_position', 0),
                play.get('down', 1),
                play.get('distance', 10),
                play.get('home_score', 0),
                play.get('away_score', 0),
                play.get('play_type', 'unknown'),
                play.get('is_penalty', 0),
                play.get('penalty_type'),
                play.get('penalty_team_id'),
                play.get('yards_gained', 0),
                play.get('result', 'unknown'),
                play.get('is_touchdown', 0),
                play.get('is_turnover', 0),
                play.get('is_big_play', 0),
                play.get('primary_player_id'),
                play.get('target_player_id'),
                play.get('defender_player_id'),
                play.get('pocket_time_grade'),
                play.get('separation_yards'),
                play.get('clutch_activated', 0),
                play.get('narration_text', ''),
            ))

        return len(self._plays)

    def write_key_plays(self, conn: sqlite3.Connection) -> int:
        """
        Write top KEY_PLAYS_PER_GAME plays to the key_play table.

        Selects the most important plays by priority:
        1. Touchdowns
        2. Turnovers
        3. Big plays
        4. Clutch moments
        5. Field goals

        Args:
            conn: Database connection

        Returns:
            Number of key plays written
        """
        # Sort candidates by importance
        def play_importance(play):
            score = 0
            if play.get('is_touchdown'):
                score += KEY_PLAY_TOUCHDOWN_SCORE
            if play.get('is_turnover'):
                score += KEY_PLAY_TURNOVER_SCORE
            if play.get('is_big_play'):
                score += KEY_PLAY_BIG_PLAY_BASE_SCORE + abs(play.get('yards_gained', 0))
            if play.get('clutch_activated'):
                score += KEY_PLAY_CLUTCH_SCORE
            if play.get('result') in ('fg_good', 'fg_miss'):
                score += KEY_PLAY_FG_SCORE
            return score

        sorted_plays = sorted(self._key_play_candidates, key=play_importance, reverse=True)
        top_plays = sorted_plays[:KEY_PLAYS_PER_GAME]

        for play in top_plays:
            conn.execute("""
                INSERT INTO key_play (
                    game_id, play_number, quarter, time_remaining,
                    result, yards_gained, narration_text, primary_player_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.game_id,
                play.get('play_number', 0),
                play.get('quarter', 1),
                play.get('time_remaining', 0),
                play.get('result', ''),
                play.get('yards_gained', 0),
                play.get('narration_text', ''),
                play.get('primary_player_id'),
            ))

        return len(top_plays)

    def get_team_stats_summary(self, team_id: int) -> dict:
        """
        Get aggregate stats for a team (for display/validation).

        Args:
            team_id: Team ID

        Returns:
            Dict of aggregate stats
        """
        total_pass_yards = 0
        total_rush_yards = 0
        total_pass_att = 0
        total_completions = 0
        total_carries = 0
        total_sacks_taken = 0
        total_turnovers = 0

        for player_id, stats in self._stats.items():
            if stats['team_id'] != team_id:
                continue
            total_pass_yards += stats['pass_yards']
            total_rush_yards += stats['rush_yards']
            total_pass_att += stats['pass_attempts']
            total_completions += stats['completions']
            total_carries += stats['carries']
            total_sacks_taken += stats['sacks_taken']
            total_turnovers += stats['interceptions_thrown'] + stats['fumbles']

        return {
            'pass_yards': total_pass_yards,
            'rush_yards': total_rush_yards,
            'total_yards': total_pass_yards + total_rush_yards,
            'pass_attempts': total_pass_att,
            'completions': total_completions,
            'completion_pct': total_completions / max(1, total_pass_att),
            'carries': total_carries,
            'yards_per_carry': total_rush_yards / max(1, total_carries),
            'sacks_taken': total_sacks_taken,
            'turnovers': total_turnovers,
            'total_plays': total_pass_att + total_carries,
        }
