"""pywebview API bridge for Football Simulator GUI.

This module is one of only two Python files in src/ui/ that touch pywebview
(the other is window.py). Public methods on Api become available as
window.pywebview.api.* in the embedded browser.

Bridge contract (per docs/ui/05_framework_implementation_plan.md §4):
  - get_*  methods: read-only, return JSON-serializable dicts
  - do_*   methods: mutations (Prompt 2+)
  - Errors: return {"ok": False, "error": "<message>"}, never raise to JS
  - No import sqlite3 here — DB access goes through src.db.queries
"""
from __future__ import annotations

import threading

from src.db import queries
from src.ui.presenters import formatters
from src.utils.constants import (
    MSG_CUT_SUCCESS,
    MSG_MUTATION_BUSY,
    MSG_PLAYER_NOT_FA,
    MSG_PLAYER_NOT_ON_TEAM,
    MSG_RESTRUCTURE_SUCCESS,
    MSG_SIGN_REJECTED,
    MSG_SIGN_SUCCESS,
)

# Process-global single-flight lock for synchronous contract mutations.
# All three FA/contract mutations are O(1) (no AI loops), so they run inline
# on the bridge thread rather than via JobManager. A second mutation attempted
# while one holds the lock returns MSG_MUTATION_BUSY (concurrency guard).
_MUTATION_LOCK = threading.Lock()


class Api:
    def __init__(self, save_path: str) -> None:
        self.save_path = save_path
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            from src.db.connection import get_connection
            self._conn = get_connection(self.save_path)
        return self._conn

    def _invalidate_conn(self) -> None:
        """Drop the cached read connection so the next get_* reopens.

        A background mutation commits via a *different* connection; the
        cached one would otherwise serve a stale snapshot. Called from
        get_task_status when a mutation task finishes.
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_app_info(self) -> dict:
        """Return context-bar bootstrap data.

        Shape: {name, abbr, version, save_path, current_season,
                current_week, phase, cap_space}
        """
        try:
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            if state is None:
                return {"ok": False, "error": "Save file has no league state."}
            user_team = queries.get_team(conn, state["user_team_id"])
            if user_team is None:
                return {"ok": False, "error": "User team not found in save."}
            phase = state["current_phase"]
            week = state["current_week"]
            season = state["current_season"]
            return {
                "name": f"{user_team['city']} {user_team['nickname']}",
                "abbr": user_team["abbreviation"],
                "version": "0.6.0",
                "save_path": self.save_path,
                "current_season": season,
                "current_week": week,
                "phase": phase,
                "cap_space": formatters.money_m(user_team["cap_space"]),
                "week_label": formatters.week_label(season, week, phase),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_dashboard(self) -> dict:
        """Return full DashboardView for the Team Dashboard screen (T-01)."""
        try:
            from src.ui.presenters import dashboard
            conn = self._get_conn()
            return dashboard.build(conn)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_roster(self, team_id=None) -> dict:
        """View-model for T-02 Roster. team_id=None defaults to user team."""
        try:
            from src.ui.presenters import roster
            conn = self._get_conn()
            return roster.build(conn, team_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_player(self, player_id: int) -> dict:
        """View-model for T-05 Player Card."""
        try:
            from src.ui.presenters import player
            conn = self._get_conn()
            return player.build(conn, player_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_standings(self, view: str = "division") -> dict:
        """View-model for L-01 Standings screen."""
        try:
            from src.ui.presenters import standings
            return standings.build(self._get_conn(), view)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_leaders(self, category: str = "passing") -> dict:
        """View-model for L-02 Leaders screen."""
        try:
            from src.ui.presenters import leaders
            return leaders.build(self._get_conn(), category)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_transactions(self) -> dict:
        """View-model for L-03 Transactions screen."""
        try:
            from src.ui.presenters import transactions
            return transactions.build(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_schedule(self) -> dict:
        """View-model for S-01 Schedule screen."""
        try:
            from src.ui.presenters import schedule
            return schedule.build(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_game_preview(self, game_id=None) -> dict:
        """View-model for S-02 Game Preview. game_id=None = next user game."""
        try:
            from src.ui.presenters import game_preview
            return game_preview.build(self._get_conn(), game_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_game_recap(self, game_id: int) -> dict:
        """View-model for S-05 Game Recap (structural)."""
        try:
            from src.ui.presenters import game_recap
            return game_recap.build(self._get_conn(), game_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_front_office(self) -> dict:
        """View-model for F-01 FO Hub. Mode derived from league + offseason_state."""
        try:
            from src.ui.presenters import front_office
            return front_office.build(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_fa_market(self) -> dict:
        """View-model for F-41 FA Market Browser."""
        try:
            from src.ui.presenters import free_agency
            return free_agency.build_market(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_fa_player(self, player_id: int) -> dict:
        """View-model for F-42 FA Player Card."""
        try:
            from src.ui.presenters import free_agency
            return free_agency.build_player(self._get_conn(), player_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_pitch_meeting(self, player_id: int) -> dict:
        """View-model for F-43 Pitch Meeting modal."""
        try:
            from src.ui.presenters import free_agency
            return free_agency.build_pitch_meeting(self._get_conn(), player_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_offer_builder(self, player_id: int) -> dict:
        """View-model for F-44 Offer Builder modal."""
        try:
            from src.ui.presenters import free_agency
            return free_agency.build_offer_builder(self._get_conn(), player_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Write methods (mutations) — run off-thread via JobManager
    # ------------------------------------------------------------------

    def do_advance_week(self) -> dict:
        """Sim the current week off-thread. Returns {task_id, status}."""
        try:
            from src.ui.jobs import JOBS
            return JOBS.submit("advance_week", self.save_path)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def do_sim_game(self, game_id: int) -> dict:
        """Sim a single game off-thread. Returns {task_id, status}."""
        try:
            from src.ui.jobs import JOBS
            return JOBS.submit("sim_game", self.save_path, game_id=game_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # -- Phase 6 P7b: synchronous contract mutations (single-flight lock) --
    # Each wraps existing src.transactions business logic which opens its own
    # `with conn:` transaction AND calls recalculate_cap_space() internally —
    # the cap-cache rule is satisfied at the business layer; do not re-call it
    # here. On failure the business-layer transaction auto-rolls back, leaving
    # the save unchanged. _invalidate_conn() drops the cached read snapshot so
    # the next get_* sees the committed writes.

    def do_add_to_watchlist(self, player_id: int) -> dict:
        """Toggle the FA watchlist flag for a player. Returns {ok, is_watchlisted}."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            conn = self._get_conn()
            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            new_flag = not bool(p["is_watchlisted"])
            with conn:
                queries.set_player_watchlist(conn, player_id, new_flag)
            self._invalidate_conn()
            return {"ok": True, "is_watchlisted": new_flag}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_sign_free_agent(self, player_id: int, offer: dict) -> dict:
        """Submit + resolve an FA offer. Returns a NegotiationResultView.

        Accepted → contract created via offer_contract (cap recalced inside).
        countered/shopped/walked → surfaced as a rejection this prompt
        (counter-offer flow is a later prompt).
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions.free_agency import resolve_offer, submit_offer
            from src.ui.presenters import free_agency
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]

            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            player_name = f"{p['first_name']} {p['last_name']}"
            if p["team_id"] is not None:
                return {"ok": False,
                        "error": MSG_PLAYER_NOT_FA.format(player_name=player_name)}

            years = int(offer["years"])
            aav = int(offer["aav"])
            signing_bonus = int(offer.get("signing_bonus", 0))
            guaranteed_money = int(offer.get("guaranteed_money", 0))

            cap_before = queries.get_team_cap_space(conn, team_id)
            sub = submit_offer(
                player_id, team_id, years, aav,
                signing_bonus, guaranteed_money, conn,
            )
            res = resolve_offer(sub["id"], conn)
            self._invalidate_conn()

            accepted = bool(res["signed"])
            if accepted:
                conn2 = self._get_conn()
                cap_after = queries.get_team_cap_space(conn2, team_id)
                cap_impact = formatters.money_m(cap_before - cap_after)
                message = MSG_SIGN_SUCCESS.format(
                    player_name=player_name, cap_impact=cap_impact,
                )
            else:
                cap_impact = formatters.money_m(0)
                message = MSG_SIGN_REJECTED.format(reason=res["message"].strip())

            return free_agency.build_negotiation_result({
                "ok": True,
                "accepted": accepted,
                "player_name": player_name,
                "cap_impact": cap_impact,
                "message": message,
            })
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_cut_player(self, player_id: int, post_june_1: bool = False) -> dict:
        """Release a user-team player. Returns {ok, dead_cap, new_cap_space, message}.

        `post_june_1` is accepted for forward-compat but NOT yet honored —
        only a standard (pre-June-1) release is performed this prompt.
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions.contracts import release_player
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]
            season = state["current_season"]

            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            if p["team_id"] != team_id:
                return {"ok": False, "error": MSG_PLAYER_NOT_ON_TEAM}

            result = release_player(player_id, team_id, season, conn)
            self._invalidate_conn()
            dead_cap = formatters.money_m(result["dead_cap"])
            new_cap = formatters.money_m(result["new_cap_space"])
            return {
                "ok": True,
                "player_name": result["player_name"],
                "dead_cap": dead_cap,
                "new_cap_space": new_cap,
                "message": MSG_CUT_SUCCESS.format(
                    player_name=result["player_name"],
                    dead_cap=dead_cap, new_cap=new_cap,
                ),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_restructure_contract(self, player_id: int, new_terms: dict) -> dict:
        """Restructure a user-team player's contract.

        new_terms = {"amount_to_convert": <dollars>}.
        Returns {ok, new_cap_space, restructured_years, cap_savings, message}.
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions.contracts import restructure_contract
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]

            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            if p["team_id"] != team_id:
                return {"ok": False, "error": MSG_PLAYER_NOT_ON_TEAM}
            player_name = f"{p['first_name']} {p['last_name']}"

            amount = int(new_terms["amount_to_convert"])
            result = restructure_contract(player_id, team_id, amount, conn)
            self._invalidate_conn()
            new_cap = formatters.money_m(result["new_cap_space"])
            restructured_years = len(result["updated_schedule"])
            return {
                "ok": True,
                "player_name": player_name,
                "new_cap_space": new_cap,
                "restructured_years": restructured_years,
                "cap_savings": formatters.money_m(
                    result["cap_savings_current_year"]
                ),
                "message": MSG_RESTRUCTURE_SUCCESS.format(
                    player_name=player_name,
                    years=restructured_years, new_cap=new_cap,
                ),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def get_task_status(self, task_id: str) -> dict:
        """Poll a background task.

        Returns {progress, message, result, error, done}. When a mutation
        task finishes, the cached read connection is invalidated so the
        next get_* sees the committed writes.
        """
        try:
            from src.ui.jobs import JOBS
            st = JOBS.get(task_id)
            if st is None:
                return {"ok": False, "error": "Unknown task id."}
            if st["done"]:
                self._invalidate_conn()
            return {
                "progress": st["progress"],
                "message": st["message"],
                "result": st["result"],
                "error": st["error"],
                "done": st["done"],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
