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
from src.ui.presenters import draft as draft_presenter
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
    def __init__(self, save_path: str | None = None) -> None:
        self.save_path = save_path
        self._conn = None

    def _get_conn(self):
        if self.save_path is None:
            raise ValueError("No franchise loaded")
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

    # -- Phase 6 P8 read accessors: Scouting + Trade --

    def get_scout_dashboard(self) -> dict:
        try:
            from src.ui.presenters import scouting
            return scouting.build_scout_dashboard(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_prospect_list(self, filters: dict | None = None) -> dict:
        try:
            from src.ui.presenters import scouting
            return scouting.build_prospect_list(self._get_conn(), filters)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_prospect_card(self, prospect_id: int) -> dict:
        try:
            from src.ui.presenters import scouting
            return scouting.build_prospect_card(self._get_conn(), prospect_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_scout_assignments(self) -> dict:
        try:
            from src.ui.presenters import scouting
            return scouting.build_scout_assignments(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_draft_board(self) -> dict:
        try:
            from src.ui.presenters import scouting
            return scouting.build_draft_board_view(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_trade_hub(self) -> dict:
        try:
            from src.ui.presenters import trades
            return trades.build_trade_hub(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_trade_block(self) -> dict:
        try:
            from src.ui.presenters import trades
            return trades.build_trade_block(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_incoming_offers(self) -> dict:
        try:
            from src.ui.presenters import trades
            return trades.build_incoming_offers(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_all_teams(self) -> dict:
        """Flat list of all teams for Trade Builder dropdown. Excludes user team."""
        try:
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            user_tid = state["user_team_id"] if state else None
            rows = queries.get_all_teams(conn)
            return {"ok": True, "teams": [
                {
                    "team_id": r["id"],
                    "abbreviation": r["abbreviation"],
                    "name": f"{r['city']} {r['nickname']}",
                    "is_user": r["id"] == user_tid,
                }
                for r in rows
            ]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_trade_builder_context(self, their_team_id: int) -> dict:
        try:
            from src.ui.presenters import trades
            return trades.build_trade_builder_context(self._get_conn(), their_team_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_trade_preview(
        self,
        my_player_ids: list,
        my_pick_codes: list,
        their_player_ids: list,
        their_pick_codes: list,
        their_team_id: int,
    ) -> dict:
        try:
            from src.ui.presenters import trades
            return trades.build_trade_preview(
                self._get_conn(),
                my_player_ids or [], my_pick_codes or [],
                their_player_ids or [], their_pick_codes or [],
                their_team_id,
            )
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

    # -- Phase 6 P8: Trade + Scouting mutations (single-flight lock) --
    # All mutations are O(1) (no AI loops) → run inline like 7b, not via
    # JobManager. The underlying business layer (trades.execute_trade,
    # scouts.assign_scout, board.update_board_rank) commits + recalcs cap
    # where applicable; UI wrappers must NOT re-call recalculate_cap_space.

    def do_propose_trade(
        self, their_team_id: int, my_assets: dict, their_assets: dict,
    ) -> dict:
        """Propose a user-initiated trade. Returns the response view.

        propose_trade itself calls execute_trade on accept (cap recalced
        inside). On counter/decline, no DB state changes.
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions import trades as trades_module
            from src.ui.presenters import trades as trades_presenter
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            user_team_id = state["user_team_id"]

            if their_team_id == user_team_id:
                return {"ok": False, "error": "Cannot trade with your own team."}

            try:
                with conn:
                    result = trades_module.propose_trade(
                        user_team_id, their_team_id,
                        my_assets or {}, their_assets or {}, conn,
                    )
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}

            self._invalidate_conn()
            receiving = queries.get_team(self._get_conn(), their_team_id)
            return trades_presenter.build_trade_response_view(result, receiving)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_respond_to_trade(self, trade_id: int, response: str) -> dict:
        """Accept or decline a pending trade row. response in {'accept','decline'}."""
        if response not in ("accept", "decline"):
            return {"ok": False, "error": f"Invalid response: {response!r}"}
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions import trades as trades_module
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            user_team_id = state["user_team_id"]

            trade_row = queries.get_trade_by_id(conn, trade_id)
            if trade_row is None:
                return {"ok": False, "error": f"Trade {trade_id} not found"}
            if trade_row["status"] != "pending":
                return {"ok": False, "error": f"Trade {trade_id} is not pending"}
            if user_team_id not in (trade_row["team_a_id"], trade_row["team_b_id"]):
                return {"ok": False, "error": "Trade does not involve your team"}

            if response == "decline":
                with conn:
                    queries.update_trade_status(conn, trade_id, "rejected")
                self._invalidate_conn()
                return {"ok": True, "trade_id": trade_id, "status": "rejected"}

            # Accept: rebuild asset dicts and call execute_trade
            assets = queries.get_trade_assets_for_trade(conn, trade_id)
            a_gives = {"players": [], "picks": []}
            b_gives = {"players": [], "picks": []}
            team_a = trade_row["team_a_id"]
            team_b = trade_row["team_b_id"]
            for a in assets:
                bucket = a_gives if a["from_team_id"] == team_a else b_gives
                if a["asset_type"] == "player":
                    bucket["players"].append(a["player_id"])
                else:
                    bucket["picks"].append({
                        "year": a["pick_season"],
                        "round": a["pick_round"],
                    })
            with conn:
                exec_result = trades_module.execute_trade(
                    team_a, team_b, a_gives, b_gives, conn,
                )
                # execute_trade writes its own 'completed' trade row; mark
                # this pending row resolved so it no longer surfaces.
                queries.update_trade_status(conn, trade_id, "completed")
            self._invalidate_conn()
            return {
                "ok": True,
                "trade_id": trade_id,
                "status": "completed",
                "players_moved": exec_result["players_moved"],
                "picks_moved": exec_result["picks_moved"],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_counter_trade(
        self, trade_id: int, my_assets: dict, their_assets: dict,
    ) -> dict:
        """Send a counter offer in response to a pending trade.

        Marks the original pending row as 'countered' and inserts a new
        pending trade row carrying the user's revised terms.
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            user_team_id = state["user_team_id"]
            season = state["current_season"]
            week = state["current_week"]

            original = queries.get_trade_by_id(conn, trade_id)
            if original is None:
                return {"ok": False, "error": f"Trade {trade_id} not found"}
            other_team_id = (
                original["team_a_id"] if original["team_b_id"] == user_team_id
                else original["team_b_id"]
            )

            with conn:
                queries.update_trade_status(conn, trade_id, "countered")
                new_id = queries.insert_trade(
                    conn, season, week, user_team_id, other_team_id,
                    "countered", "user",
                )
                for pid in (my_assets or {}).get("players", []):
                    queries.insert_trade_asset(
                        conn, new_id, user_team_id, other_team_id, "player",
                        player_id=pid,
                    )
                for pid in (their_assets or {}).get("players", []):
                    queries.insert_trade_asset(
                        conn, new_id, other_team_id, user_team_id, "player",
                        player_id=pid,
                    )
            self._invalidate_conn()
            return {"ok": True, "original_trade_id": trade_id, "new_trade_id": new_id}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_add_to_trade_block(self, player_id: int) -> dict:
        """Flag a player as on the trade block. User team only."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]
            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            if p["team_id"] != team_id:
                return {"ok": False, "error": MSG_PLAYER_NOT_ON_TEAM}
            with conn:
                conn.execute(
                    "UPDATE player SET is_on_trade_block = 1 WHERE id = ?",
                    (player_id,),
                )
            self._invalidate_conn()
            return {"ok": True, "player_id": player_id, "is_on_trade_block": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_remove_from_trade_block(self, player_id: int) -> dict:
        """Clear the trade-block flag on a user-team player."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]
            p = queries.get_player(conn, player_id)
            if p is None:
                return {"ok": False, "error": f"Player {player_id} not found"}
            if p["team_id"] != team_id:
                return {"ok": False, "error": MSG_PLAYER_NOT_ON_TEAM}
            with conn:
                conn.execute(
                    "UPDATE player SET is_on_trade_block = 0 WHERE id = ?",
                    (player_id,),
                )
            self._invalidate_conn()
            return {"ok": True, "player_id": player_id, "is_on_trade_block": False}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_assign_scout(self, scout_id: int, prospect_ids: list) -> dict:
        """Assign a scout to one or more prospects."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.scouting.scouts import assign_scout
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            season = state["current_season"]
            try:
                result = assign_scout(scout_id, list(prospect_ids or []), season, conn)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            self._invalidate_conn()
            return {"ok": True, **result}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_set_board_rank(self, prospect_id: int, new_rank: int) -> dict:
        """Reorder a prospect on the draft board with sibling-shifting."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.scouting import board as board_module
            from src.ui.presenters import scouting as scouting_presenter
            conn = self._get_conn()
            state = queries.get_league_state(conn)
            team_id = state["user_team_id"]
            season = state["current_season"]
            board_module.update_board_rank(
                prospect_id, team_id, int(new_rank), season, conn,
                shift_siblings=True,
            )
            self._invalidate_conn()
            view = scouting_presenter.build_draft_board_view(self._get_conn())
            return {"ok": True, "board": view.get("board", [])}
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

    # ------------------------------------------------------------------
    # Draft Room (F-60) — Prompt 9a
    # ------------------------------------------------------------------

    def get_draft_room(self) -> dict:
        """Full draft room state: live feed, on-the-clock, trade offers."""
        try:
            return draft_presenter.build_draft_room(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_available_board(self) -> dict:
        """User's draft board filtered to undrafted prospects only."""
        try:
            return draft_presenter.build_available_board(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def do_initialize_draft(self) -> dict:
        """Initialize draft_state pick order. Idempotent."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions import draft as draft_module
            conn = self._get_conn()
            league = queries.get_league_state(conn)
            draft_year = league["current_season"] + 1
            result = draft_module.initialize_draft(draft_year, conn)
            self._invalidate_conn()
            return {"ok": True, **result}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_make_pick(self, prospect_id: int) -> dict:
        """Make the user's draft pick. User must be on the clock."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions import draft as draft_module
            conn = self._get_conn()
            league = queries.get_league_state(conn)
            user_team_id = league["user_team_id"]
            draft_year = league["current_season"] + 1
            result = draft_module.make_pick(user_team_id, int(prospect_id), draft_year, conn)
            self._invalidate_conn()
            return {"ok": True, **result}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    def do_sim_ai_picks(self, until_user_pick: bool = False) -> dict:
        """Sim AI picks.

        until_user_pick=False: advance exactly one AI pick.
        until_user_pick=True: sim all AI picks until user is on clock or draft ends.
        Returns list of pick results for JS to animate into the feed.
        """
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.transactions import draft as draft_module
            conn = self._get_conn()
            league = queries.get_league_state(conn)
            user_team_id = league["user_team_id"]
            draft_year = league["current_season"] + 1

            picks_made = []
            _MAX_PICKS = 7 * 32  # safety guard

            for _ in range(_MAX_PICKS):
                current = draft_module.get_on_the_clock(draft_year, conn)
                if not current:
                    break  # draft complete
                if current["team_id"] == user_team_id:
                    break  # user's turn — stop
                result = draft_module.run_ai_pick(current["team_id"], draft_year, conn)
                picks_made.append(result)
                if not until_user_pick:
                    break

            self._invalidate_conn()
            return {"ok": True, "picks_made": picks_made, "count": len(picks_made)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()

    # ------------------------------------------------------------------
    # Season Review (F-10) — Prompt 10
    # ------------------------------------------------------------------

    def get_season_review(self) -> dict:
        """Season recap for the most recently completed season."""
        try:
            from src.ui.presenters import season_review as season_review_presenter
            return season_review_presenter.build_season_review(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Playoff Bracket + Super Bowl Recap (S-08, S-11) — Prompt 10b
    # ------------------------------------------------------------------

    def get_playoff_bracket(self) -> dict:
        """Bracket view-model for S-08 Playoff Bracket screen."""
        try:
            from src.ui.presenters import playoff as playoff_presenter
            return playoff_presenter.build_playoff_bracket(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_super_bowl_recap(self) -> dict:
        """Super Bowl Recap view-model for S-11."""
        try:
            from src.ui.presenters import playoff as playoff_presenter
            return playoff_presenter.build_super_bowl_recap(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Milestone 5.10c: Combine Results (F-34), Post-Draft Review (F-62),
    # Past Season Summary (D-04)
    # ------------------------------------------------------------------

    def get_combine_results(self) -> dict:
        """Combine Results view-model for F-34."""
        try:
            from src.ui.presenters import combine_results as combine_results_presenter
            return combine_results_presenter.build_combine_results(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_post_draft_review(self) -> dict:
        """Post-Draft Review view-model for F-62."""
        try:
            from src.ui.presenters import post_draft_review as post_draft_presenter
            return post_draft_presenter.build_post_draft_review(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_past_season(self, season_year: int) -> dict:
        """Past Season Summary view-model for D-04."""
        try:
            from src.ui.presenters import past_season as past_season_presenter
            return past_season_presenter.build_past_season(self._get_conn(), season_year)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Milestone 5.11: Dynasty Section (D-01, D-02, D-03, D-05, D-06, D-07)
    # ------------------------------------------------------------------

    def get_dynasty_hub(self) -> dict:
        """Dynasty Hub view-model for D-01."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_dynasty_hub(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_franchise_history(self) -> dict:
        """Franchise History view-model for D-02."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_franchise_history(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_season_archive(self) -> dict:
        """Season Archive view-model for D-03."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_season_archive(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_awards_history(self) -> dict:
        """Awards History view-model for D-05."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_awards_history(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_legacy_tracker(self) -> dict:
        """Legacy Tracker view-model for D-06."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_legacy_tracker(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_retired_player(self, player_id: int) -> dict:
        """Retired Player Card view-model for D-07."""
        try:
            from src.ui.presenters import dynasty as dynasty_presenter
            return dynasty_presenter.build_retired_player(self._get_conn(), player_id)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Milestone 5.12: Title Screen / Load Franchise / Settings / Scheme
    # ------------------------------------------------------------------

    def get_save_files(self) -> dict:
        """Scan the saves directory. Returns list sorted by last-modified descending."""
        try:
            import sqlite3 as _sqlite3
            from datetime import datetime
            from src.ui.settings import _saves_dir
            saves_dir = _saves_dir()
            results = []
            if saves_dir.exists():
                for p in sorted(saves_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
                    try:
                        c = _sqlite3.connect(str(p))
                        c.row_factory = _sqlite3.Row
                        row = c.execute("SELECT user_team_id, current_season, current_week FROM league WHERE id=1").fetchone()
                        team = c.execute("SELECT city, nickname FROM team WHERE id=?", (row["user_team_id"],)).fetchone()
                        c.close()
                        mtime = p.stat().st_mtime
                        results.append({
                            "path": str(p),
                            "team_name": f"{team['city']} {team['nickname']}",
                            "season": row["current_season"],
                            "week": row["current_week"],
                            "mtime_iso": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                        })
                    except Exception:  # noqa: BLE001
                        pass  # skip corrupt or unreadable files
            return {"ok": True, "saves": results}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def do_load_franchise(self, path: str) -> dict:
        """Switch to a different save file. Returns get_app_info() for the new franchise."""
        try:
            from src.ui import settings as settings_module
            self._invalidate_conn()
            self.save_path = path
            settings_module.add_recent_save(path)
            return self.get_app_info()
        except Exception as exc:  # noqa: BLE001
            self.save_path = None
            return {"ok": False, "error": str(exc)}

    def get_settings(self) -> dict:
        """Return current user settings."""
        try:
            from src.ui import settings as settings_module
            return {"ok": True, "settings": settings_module.load()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def do_save_settings(self, settings: dict) -> dict:
        """Persist user settings. Only keys in DEFAULTS are accepted."""
        try:
            from src.ui import settings as settings_module
            current = settings_module.load()
            current.update({k: v for k, v in settings.items() if k in settings_module.DEFAULTS})
            settings_module.save(current)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_scheme_settings(self) -> dict:
        """Scheme Settings view-model for T-10."""
        try:
            from src.ui.presenters import scheme as scheme_presenter
            return scheme_presenter.build_scheme_settings(self._get_conn())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def do_update_scheme(self, offense: str, defense: str) -> dict:
        """Persist offense + defense scheme selection for the user's team."""
        if not _MUTATION_LOCK.acquire(blocking=False):
            return {"ok": False, "error": MSG_MUTATION_BUSY}
        try:
            from src.ui.presenters import scheme as scheme_presenter
            result = scheme_presenter.apply_scheme_update(self._get_conn(), offense, defense)
            self._invalidate_conn()
            return result
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            _MUTATION_LOCK.release()
