"""Presenter for F-41 FA Market Browser and F-42 FA Player Card. Read-only."""
from __future__ import annotations
import sqlite3

from src.db import queries
from src.ui.presenters import formatters
from src.ui.presenters import player as player_presenter
from src.utils.constants import (
    FA_ACTION_TOOLTIP_PITCH_ENABLED,
    FA_ACTION_TOOLTIP_WATCHLIST,
    FA_IDEAL_ROSTER,
    FA_INTEREST_SIGNALS,
    FA_INTEREST_TIER_LABELS,
    FA_MARKET_COLUMNS,
    FA_OFFER_DEFAULT_GUARANTEED_PCT,
    FA_OFFER_DEFAULT_SIGNING_BONUS_PCT,
    FA_OFFER_DEFAULT_YEARS,
    FA_OFFER_RANGE_LOW_MULT,
    FA_OFFER_RANGE_PREMIUM_MULT,
    FA_OUTCOME_ACCEPTED,
    FA_POSITION_SALARY_FRACTION,
    MAX_CONTRACT_YEARS,
    MAX_GUARANTEED_PERCENT,
    MAX_SIGNING_BONUS_PERCENT,
    MIN_CONTRACT_YEARS,
    SALARY_CAP_YEAR_ONE,
)


def build_market(conn: sqlite3.Connection) -> dict:
    league = queries.get_league_state(conn)
    user_team = queries.get_fo_user_team(conn)
    team_id = user_team["id"] if user_team else 1
    season_year = league["current_season"] if league else 2024
    cap = user_team["cap_space"] if user_team else 0

    players = queries.get_fa_players_with_interest(conn, team_id, season_year)
    rows = [_to_fa_player_row(p) for p in players]
    needs = _compute_team_needs(conn, team_id)

    return {
        "available_players": rows,
        "columns": FA_MARKET_COLUMNS,
        "your_team_needs": needs,
        "cap_available": formatters.money_m(cap),
        "active_negotiations": [],
        "watchlist_count": queries.count_watchlisted_players(conn),
    }


def build_player(conn: sqlite3.Connection, player_id: int) -> dict:
    league = queries.get_league_state(conn)
    user_team = queries.get_fo_user_team(conn)
    team_id = user_team["id"] if user_team else 1
    season_year = league["current_season"] if league else 2024

    p = queries.get_player(conn, player_id)
    if p is None:
        return {"ok": False, "error": f"Player {player_id} not found"}

    pos = p["position"]
    season_stats_list = queries.get_player_season_stats_list(conn, player_id)
    career_stats = queries.get_player_career_stats_for_player(conn, player_id)
    awards = queries.get_player_weekly_awards_all(conn, player_id)

    header = player_presenter._build_header(p, pos, "Free Agent", "FA")
    overview = _build_fa_overview(p, pos, season_stats_list, season_year)
    stats = player_presenter._build_stats(p, pos, season_stats_list, career_stats, awards)
    history = player_presenter._build_history(p, career_stats, awards)
    market_interest = _build_market_interest(conn, player_id, team_id, season_year)
    contract_history = _build_contract_history(conn, player_id)

    return {
        "header": header,
        "overview": overview,
        "stats": stats,
        "history": history,
        "market_interest": market_interest,
        "contract_history": contract_history,
        "is_watchlisted": bool(p["is_watchlisted"]) if "is_watchlisted" in p.keys() else False,
        "actions": [
            {"label": "★ Watching" if (("is_watchlisted" in p.keys()) and p["is_watchlisted"]) else "Add to Watchlist",
             "action_key": "add_to_watchlist", "enabled": True,
             "tooltip": FA_ACTION_TOOLTIP_WATCHLIST},
            {"label": "Pitch Meeting", "action_key": "pitch_meeting",
             "enabled": True, "tooltip": FA_ACTION_TOOLTIP_PITCH_ENABLED},
        ],
    }


def build_pitch_meeting(conn: sqlite3.Connection, player_id: int) -> dict:
    """F-43 Pitch Meeting view-model (informational; CTA → Offer Builder)."""
    league = queries.get_league_state(conn)
    user_team = queries.get_fo_user_team(conn)
    team_id = user_team["id"] if user_team else 1
    season_year = league["current_season"] if league else 2024

    p = queries.get_player(conn, player_id)
    if p is None:
        return {"ok": False, "error": f"Player {player_id} not found"}

    pos = p["position"]
    mi = _build_market_interest(conn, player_id, team_id, season_year)
    is_fa = p["team_id"] is None
    note = ("" if is_fa
            else f"{p['first_name']} {p['last_name']} is not a free agent.")

    return {
        "player_id": player_id,
        "player_name": f"{p['first_name']} {p['last_name']}",
        "position": pos,
        "overall": formatters.letter_grade(p["true_overall"]),
        "asking_salary": _estimate_asking_salary(pos, p["true_overall"]),
        "interest_label": mi["interest_label"],
        "interest_signal": mi["interest_signal"],
        "market": _market_range(pos, p["true_overall"]),
        "can_offer": is_fa,
        "note": note,
    }


def build_offer_builder(conn: sqlite3.Connection, player_id: int) -> dict:
    """F-44 Offer Builder view-model — form defaults + validation bounds."""
    user_team = queries.get_fo_user_team(conn)
    cap = user_team["cap_space"] if user_team else 0

    p = queries.get_player(conn, player_id)
    if p is None:
        return {"ok": False, "error": f"Player {player_id} not found"}

    pos = p["position"]
    fair = _estimate_aav(pos, p["true_overall"])
    years = FA_OFFER_DEFAULT_YEARS
    total = fair * years

    return {
        "player_id": player_id,
        "player_name": f"{p['first_name']} {p['last_name']}",
        "position": pos,
        "market": _market_range(pos, p["true_overall"]),
        "cap_available": formatters.money_m(cap),
        "defaults": {
            "years": years,
            "aav": fair,
            "signing_bonus": int(total * FA_OFFER_DEFAULT_SIGNING_BONUS_PCT),
            "guaranteed_money": int(total * FA_OFFER_DEFAULT_GUARANTEED_PCT),
        },
        "bounds": {
            "min_years": MIN_CONTRACT_YEARS,
            "max_years": MAX_CONTRACT_YEARS,
            "max_signing_bonus_pct": MAX_SIGNING_BONUS_PERCENT,
            "max_guaranteed_pct": MAX_GUARANTEED_PERCENT,
        },
    }


def build_negotiation_result(result: dict) -> dict:
    """F-45 Negotiation Result view-model. Shapes a do_sign_free_agent result.

    `result` keys: ok, accepted, player_name, cap_impact (str), message.
    Counter/shopped/walked all surface as a rejection this prompt.
    """
    accepted = bool(result.get("accepted"))
    return {
        "ok": result.get("ok", True),
        "accepted": accepted,
        "outcome": FA_OUTCOME_ACCEPTED if accepted else "rejected",
        "player_name": result.get("player_name", ""),
        "cap_impact": result.get("cap_impact", formatters.money_m(0)),
        "message": result.get("message", ""),
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _estimate_aav(position: str, true_overall: int) -> int:
    """Presenter-side fair-AAV estimate (display/prefill only).

    The authoritative valuation lives in transactions; the offer is
    re-evaluated server-side by resolve_offer(). This only brackets the
    Offer Builder form so the presenter stays free of the transaction layer.
    """
    fraction = FA_POSITION_SALARY_FRACTION.get(position, 0.05)
    return int(SALARY_CAP_YEAR_ONE * fraction * (true_overall / 99))


def _estimate_asking_salary(position: str, true_overall: int) -> str:
    return formatters.money_m(_estimate_aav(position, true_overall)) + "/yr"


def _market_range(position: str, true_overall: int) -> dict:
    fair = _estimate_aav(position, true_overall)
    return {
        "low": formatters.money_m(int(fair * FA_OFFER_RANGE_LOW_MULT)),
        "fair": formatters.money_m(fair),
        "premium": formatters.money_m(int(fair * FA_OFFER_RANGE_PREMIUM_MULT)),
    }


def _age_bucket(age: int) -> str:
    if age < 25:
        return "Under 25"
    if age < 30:
        return "25-29"
    return "30+"


def _to_fa_player_row(p: sqlite3.Row) -> dict:
    tier = p["interest_tier"] if p["interest_tier"] is not None else 0
    return {
        "id": p["id"],
        "pos": p["position"],
        "name_short": formatters.short_name(p["first_name"], p["last_name"]),
        "age": p["age"],
        "overall": formatters.letter_grade(p["true_overall"]),
        "asking_salary": _estimate_asking_salary(p["position"], p["true_overall"]),
        "interest_label": FA_INTEREST_TIER_LABELS.get(tier, "Unknown"),
        "interest_tier": tier,
        "status_icons": _fa_status_icons(p),
        "is_watchlisted": bool(p["is_watchlisted"]) if "is_watchlisted" in p.keys() else False,
        "_pos_filter_value": p["position"],
        "_age_filter_value": _age_bucket(p["age"]),
    }


def _fa_status_icons(p: sqlite3.Row) -> list[str]:
    icons = []
    injury = p["injury_status"] if "injury_status" in p.keys() else None
    if injury:
        icons.append("⚕")
    return icons


def _compute_team_needs(conn: sqlite3.Connection, team_id: int) -> list[str]:
    current = queries.get_team_positional_counts(conn, team_id)
    needs = []
    for pos, target in FA_IDEAL_ROSTER.items():
        have = current.get(pos, 0)
        if have < target:
            label = f"{pos} depth" if have > 0 else f"Starting {pos}"
            needs.append(label)
    return needs[:5]


def _build_fa_overview(p: sqlite3.Row, pos: str, season_stats_list: list, season: int) -> dict:
    from src.utils.constants import PLAYER_CARD_KEY_ATTRS
    attrs = PLAYER_CARD_KEY_ATTRS.get(pos, PLAYER_CARD_KEY_ATTRS.get("OL", []))
    key_attributes = []
    for label, col in attrs:
        val = p[col] if col in p.keys() else None
        key_attributes.append({"label": label, "grade": formatters.letter_grade(val)})

    current_stats = next((s for s in season_stats_list if s["season_year"] == season), None)
    season_summary = None
    if current_stats and current_stats["games_played"] > 0:
        from src.ui.presenters.player import _stat_line
        season_summary = {
            "season_year": season,
            "games_played": current_stats["games_played"],
            "stat_line": _stat_line(pos, current_stats),
        }

    return {
        "key_attributes": key_attributes,
        "asking_salary": _estimate_asking_salary(pos, p["true_overall"]),
        "season_summary": season_summary,
    }


def _build_market_interest(
    conn: sqlite3.Connection, player_id: int, team_id: int, season_year: int
) -> dict:
    interests = queries.get_fa_interests_for_player(conn, player_id, season_year)
    user_interest = next((i for i in interests if i["team_id"] == team_id), None)
    tier = user_interest["tier"] if user_interest else 0
    signals = FA_INTEREST_SIGNALS.get(tier, [])
    signal_text = signals[player_id % len(signals)] if signals else "No intel available."

    top_teams = [
        {
            "name": f"{i['city']} {i['nickname']}",
            "abbr": i["abbreviation"],
            "preference_score": round(i["preference_score"], 2),
        }
        for i in interests[:3]
    ]
    return {
        "interest_tier": tier,
        "interest_label": FA_INTEREST_TIER_LABELS.get(tier, "Unknown"),
        "interest_signal": signal_text,
        "top_preferred_teams": top_teams,
    }


def _build_contract_history(conn: sqlite3.Connection, player_id: int) -> list[dict]:
    rows = queries.get_fa_player_contract_history(conn, player_id)
    result = []
    for r in rows:
        first = r["first_year"] or r["signed_season"]
        last = r["last_year"] or (r["signed_season"] + r["total_years"] - 1)
        seasons_str = str(first) if first == last else f"{first}–{last}"
        if r["is_franchise_tag"]:
            contract_type = "Tag"
        elif r["is_rookie_contract"]:
            contract_type = "Rookie"
        else:
            contract_type = "FA"
        result.append({
            "team_name": f"{r['city']} {r['nickname']}",
            "seasons": seasons_str,
            "total_value": formatters.money_m(r["total_value"]),
            "aav": formatters.money_m(r["aav"]) + "/yr",
            "type": contract_type,
        })
    return result
