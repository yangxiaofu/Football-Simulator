"""Player card presenter — builds PlayerView for the T-05 Player Card screen."""
from __future__ import annotations

from src.db import queries
from src.ui.presenters import formatters
from src.utils.constants import (
    PLAYER_CARD_KEY_ATTRS,
    PLAYER_ACTION_TOOLTIP_TRADE_BLOCK,
    PLAYER_ACTION_TOOLTIP_RESTRUCTURE,
    PLAYER_ACTION_TOOLTIP_CUT_PLAYER,
    PLAYER_ACTION_TOOLTIP_CUT_ENABLED,
    PLAYER_ACTION_TOOLTIP_RESTRUCTURE_ENABLED,
    RESTRUCTURE_MAX_CONVERSION_PERCENT,
    RESTRUCTURE_MIN_REMAINING_YEARS,
    SATISFACTION_TIER_LABELS,
)


def build(conn, player_id: int) -> dict:
    state = queries.get_league_state(conn)
    season = state["current_season"]

    p = queries.get_player(conn, player_id)
    if p is None:
        raise ValueError(f"Player {player_id} not found")

    team = queries.get_team(conn, p["team_id"]) if p["team_id"] else None
    contract = queries.get_active_contract_for_player(conn, player_id)
    contract_years = queries.get_contract_years(conn, contract["id"]) if contract else []
    season_stats_list = queries.get_player_season_stats_list(conn, player_id)
    career_stats = queries.get_player_career_stats_for_player(conn, player_id)
    sat_events = queries.get_satisfaction_events_for_player(conn, player_id, season)
    awards = queries.get_player_weekly_awards_all(conn, player_id)

    pos = p["position"]
    team_name = f"{team['city']} {team['nickname']}" if team else "Free Agent"
    team_abbr = team["abbreviation"] if team else "FA"

    header = _build_header(p, pos, team_name, team_abbr)
    overview = _build_overview(p, pos, contract, contract_years, season_stats_list, sat_events, season)
    stats = _build_stats(p, pos, season_stats_list, career_stats, awards)
    contract_detail = _build_contract(contract, contract_years, season)

    on_user_team = (
        p["team_id"] is not None
        and state["user_team_id"] is not None
        and p["team_id"] == state["user_team_id"]
    )
    cut_view = _build_cut_view(p, contract, contract_years, season, on_user_team, team)
    restructure_view = _build_restructure_view(
        p, contract, contract_years, season, on_user_team
    )
    contract_detail["cut"] = cut_view
    contract_detail["restructure"] = restructure_view

    satisfaction = _build_satisfaction(p, sat_events)
    history = _build_history(p, career_stats, awards)
    actions = [
        {"label": "Add to Trade Block", "action_key": "add_to_trade_block",
         "enabled": False, "tooltip": PLAYER_ACTION_TOOLTIP_TRADE_BLOCK},
        {"label": "Restructure", "action_key": "restructure_contract",
         "enabled": restructure_view["can_restructure"],
         "tooltip": (PLAYER_ACTION_TOOLTIP_RESTRUCTURE_ENABLED
                     if restructure_view["can_restructure"]
                     else PLAYER_ACTION_TOOLTIP_RESTRUCTURE)},
        {"label": "Cut Player", "action_key": "cut_player",
         "enabled": cut_view["can_cut"],
         "tooltip": (PLAYER_ACTION_TOOLTIP_CUT_ENABLED
                     if cut_view["can_cut"]
                     else PLAYER_ACTION_TOOLTIP_CUT_PLAYER)},
    ]

    return {
        "header": header,
        "overview": overview,
        "stats": stats,
        "contract": contract_detail,
        "satisfaction": satisfaction,
        "history": history,
        "actions": actions,
    }


def _build_header(p, pos, team_name, team_abbr) -> dict:
    exp = p["years_experience"]
    if exp == 0:
        exp_label = "Rookie"
    elif exp == 1:
        exp_label = "2nd season"
    elif exp == 2:
        exp_label = "3rd season"
    else:
        exp_label = f"{exp + 1}th season"

    dy = p["draft_year"]
    dr = p["draft_round"]
    dp = p["draft_pick"]
    if dy and dr and dp:
        draft_label = f"Drafted {dy} · R{dr} · Pick {dp}"
    else:
        draft_label = "Undrafted"

    return {
        "player_id": p["id"],
        "full_name": f"{p['first_name']} {p['last_name']}",
        "position": pos,
        "team_name": team_name,
        "team_abbr": team_abbr,
        "age": p["age"],
        "years_experience": exp,
        "experience_label": exp_label,
        "draft_label": draft_label,
        "college": p["college"],
        "overall": formatters.letter_grade(p["true_overall"]),
        "clutch": formatters.letter_grade(p["true_clutch"]),
    }


def _build_overview(p, pos, contract, contract_years, season_stats_list, sat_events, season) -> dict:
    attrs = PLAYER_CARD_KEY_ATTRS.get(pos, PLAYER_CARD_KEY_ATTRS.get("OL", []))
    key_attributes = []
    for label, col in attrs:
        val = p[col] if col in p.keys() else None
        key_attributes.append({"label": label, "grade": formatters.letter_grade(val)})

    # Contract snapshot (overview version — up to 4 future years)
    contract_snapshot = None
    if contract:
        future_years = [cy for cy in contract_years if cy["season_year"] >= season][:4]
        years_remaining = [
            {"season_year": cy["season_year"],
             "cap_hit": formatters.money_m(cy["cap_hit"]),
             "dead_cap": formatters.money_m(cy["dead_cap_value"]),
             "base_salary": formatters.money_m(cy["base_salary"])}
            for cy in future_years
        ]
        # dead cap if cut = dead_cap_value of current year
        current_year_row = next((cy for cy in contract_years if cy["season_year"] == season), None)
        dead_cap_if_cut = formatters.money_m(current_year_row["dead_cap_value"]) if current_year_row else "—"

        total_years = contract["total_years"]
        aav = formatters.money_m(contract["aav"])
        is_franchise_tag = bool(contract["is_franchise_tag"])
        is_rookie_contract = bool(contract["is_rookie_contract"])
        if is_franchise_tag:
            summary_line = f"Franchise Tag · {aav}"
        elif is_rookie_contract:
            summary_line = f"Rookie · {total_years}yr · {aav} APY"
        else:
            summary_line = f"{total_years}yr · {aav} APY"

        contract_snapshot = {
            "summary_line": summary_line,
            "years_remaining": years_remaining,
            "dead_cap_if_cut": dead_cap_if_cut,
            "is_franchise_tag": is_franchise_tag,
            "is_rookie_contract": is_rookie_contract,
        }

    # Season summary
    season_summary = None
    current_stats = next((s for s in season_stats_list if s["season_year"] == season), None)
    if current_stats and current_stats["games_played"] > 0:
        season_summary = {
            "season_year": season,
            "games_played": current_stats["games_played"],
            "stat_line": _stat_line(pos, current_stats),
        }

    # Satisfaction status
    sat = p["satisfaction"] if p["satisfaction"] is not None else 75
    tier = _sat_tier(sat)
    satisfaction_status = SATISFACTION_TIER_LABELS.get(tier, tier.upper())

    return {
        "key_attributes": key_attributes,
        "contract_snapshot": contract_snapshot,
        "season_summary": season_summary,
        "satisfaction_status": satisfaction_status,
    }


def _build_stats(p, pos, season_stats_list, career_stats, awards) -> dict:
    # Use the most recent season entry for current stats display
    current_season = None
    if season_stats_list:
        row = season_stats_list[0]
        if row["games_played"] > 0:
            current_season = {
                "season_year": row["season_year"],
                "games_played": row["games_played"],
                "stat_line": _stat_line(pos, row),
            }

    history = []
    for row in season_stats_list:
        season_awards = []
        if row["won_mvp"]:
            season_awards.append("MVP")
        if row["made_all_pro"]:
            season_awards.append("All-Pro")
        if row["made_pro_bowl"]:
            season_awards.append("Pro Bowl")
        history.append({
            "season_year": row["season_year"],
            "team_abbr": row["team_abbr"],
            "games_played": row["games_played"],
            "stat_line": _stat_line(pos, row),
            "awards": season_awards,
        })

    career_totals = {}
    if career_stats:
        pos_upper = pos.upper()
        if pos_upper == "QB":
            career_totals = {
                "Pass Yards": f"{career_stats['career_pass_yards']:,}",
                "Pass TDs": str(career_stats["career_pass_tds"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        elif pos_upper == "RB":
            career_totals = {
                "Rush Yards": f"{career_stats['career_rush_yards']:,}",
                "Rush TDs": str(career_stats["career_rush_tds"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        elif pos_upper in ("WR", "TE"):
            career_totals = {
                "Rec Yards": f"{career_stats['career_rec_yards']:,}",
                "Rec TDs": str(career_stats["career_rec_tds"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        elif pos_upper in ("DL", "LB"):
            career_totals = {
                "Sacks": f"{career_stats['career_sacks']:.1f}",
                "Interceptions": str(career_stats["career_interceptions"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        elif pos_upper in ("CB", "S"):
            career_totals = {
                "Interceptions": str(career_stats["career_interceptions"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        elif pos_upper == "K":
            career_totals = {
                "FG Made": str(career_stats["career_fg_made"]),
                "Seasons": str(career_stats["seasons_played"]),
            }
        else:
            career_totals = {"Seasons": str(career_stats["seasons_played"])}

    return {
        "current_season": current_season,
        "season_history": history,
        "career_totals": career_totals,
    }


def _build_contract(contract, contract_years, season) -> dict:
    if not contract:
        return {
            "has_contract": False,
            "contract_type": "None",
            "aav": "—",
            "total_value": "—",
            "total_years": 0,
            "signed_season": 0,
            "years": [],
            "restructure_room": None,
        }

    if contract["is_franchise_tag"]:
        contract_type = "Franchise Tag"
    elif contract["is_rookie_contract"]:
        contract_type = "Rookie"
    else:
        contract_type = "Active"

    years = [
        {"season_year": cy["season_year"],
         "cap_hit": formatters.money_m(cy["cap_hit"]),
         "dead_cap": formatters.money_m(cy["dead_cap_value"]),
         "base_salary": formatters.money_m(cy["base_salary"])}
        for cy in contract_years
    ]

    return {
        "has_contract": True,
        "contract_type": contract_type,
        "aav": formatters.money_m(contract["aav"]),
        "total_value": formatters.money_m(contract["total_value"]),
        "total_years": contract["total_years"],
        "signed_season": contract["signed_season"],
        "years": years,
        "restructure_room": None,
    }


def _build_cut_view(p, contract, contract_years, season, on_user_team, team) -> dict:
    """Cut-confirmation sub-view (dead-cap preview). post_june_1 not modeled."""
    player_name = f"{p['first_name']} {p['last_name']}"
    if not on_user_team or not contract:
        return {
            "can_cut": False,
            "player_id": p["id"],
            "player_name": player_name,
            "dead_cap": formatters.money_m(0),
            "current_cap_space": formatters.money_m(team["cap_space"] if team else 0),
            "note": "" if contract else "No active contract to release.",
        }
    current_year_row = next(
        (cy for cy in contract_years if cy["season_year"] == season), None
    )
    dead_cap = current_year_row["dead_cap_value"] if current_year_row else 0
    return {
        "can_cut": True,
        "player_id": p["id"],
        "player_name": player_name,
        "dead_cap": formatters.money_m(dead_cap),
        "current_cap_space": formatters.money_m(team["cap_space"] if team else 0),
        "note": "",
    }


def _build_restructure_view(p, contract, contract_years, season, on_user_team) -> dict:
    """Restructure sub-view: current schedule + max convertible base salary."""
    player_name = f"{p['first_name']} {p['last_name']}"
    remaining = [cy for cy in contract_years if cy["season_year"] >= season]
    current_year_row = next(
        (cy for cy in contract_years if cy["season_year"] == season), None
    )
    base_salary = current_year_row["base_salary"] if current_year_row else 0
    enough_years = len(remaining) >= RESTRUCTURE_MIN_REMAINING_YEARS
    can_restructure = bool(
        on_user_team and contract and enough_years and base_salary > 0
    )
    if not can_restructure:
        if not contract:
            note = "No active contract to restructure."
        elif not on_user_team:
            note = "Only players on your team can be restructured."
        elif not enough_years:
            note = (
                f"Needs at least {RESTRUCTURE_MIN_REMAINING_YEARS} remaining "
                f"years to restructure."
            )
        else:
            note = "No convertible base salary remaining."
    else:
        note = ""
    return {
        "can_restructure": can_restructure,
        "player_id": p["id"],
        "player_name": player_name,
        "current_season": season,
        "base_salary": base_salary,
        "max_convertible": int(base_salary * RESTRUCTURE_MAX_CONVERSION_PERCENT),
        "current_cap_hit": formatters.money_m(
            current_year_row["cap_hit"] if current_year_row else 0
        ),
        "years": [
            {
                "season_year": cy["season_year"],
                "base_salary": formatters.money_m(cy["base_salary"]),
                "prorated_bonus": formatters.money_m(cy["prorated_bonus"]),
                "cap_hit": formatters.money_m(cy["cap_hit"]),
            }
            for cy in remaining
        ],
        "note": note,
    }


def _build_satisfaction(p, sat_events) -> dict:
    sat = p["satisfaction"] if p["satisfaction"] is not None else 75
    tier = _sat_tier(sat)
    tier_label = SATISFACTION_TIER_LABELS.get(tier, tier.upper())

    events = []
    for ev in reversed(list(sat_events)):   # oldest first
        # Safely access columns — reason_code was added in Phase 5 P8
        keys = ev.keys()
        if "reason_code" in keys:
            reason = ev["reason_code"] or "Unknown"
        elif "reason" in keys:
            reason = ev["reason"] or "Unknown"
        else:
            reason = "Unknown"
        delta = ev["delta"] if "delta" in keys else 0
        new_score = ev["score_after"] if "score_after" in keys else sat
        week = ev["week_number"] if "week_number" in keys else 0
        events.append({
            "week": week,
            "delta": delta,
            "reason": reason,
            "new_score": new_score,
        })

    return {
        "current_score": sat,
        "tier": tier,
        "tier_label": tier_label,
        "events": events,
    }


def _build_history(p, career_stats, awards) -> dict:
    dy = p["draft_year"]
    dr = p["draft_round"]
    dp = p["draft_pick"]
    if dy and dr and dp:
        draft_info = f"Drafted {dy} · R{dr} · Pick {dp}"
    else:
        draft_info = "Undrafted"

    seasons_played = career_stats["seasons_played"] if career_stats else 0
    career_pro_bowls = career_stats["career_pro_bowls"] if career_stats else 0
    career_all_pro = career_stats["career_all_pro"] if career_stats else 0
    peak_overall_int = career_stats["peak_overall"] if career_stats else p["true_overall"]
    peak_overall = formatters.letter_grade(peak_overall_int)

    timeline = []
    if dy and dr and dp:
        timeline.append({"type": "draft", "label": draft_info})
    for aw in awards:
        blurb = (aw["narrative_blurb"] or "")[:60]
        timeline.append({
            "type": "award",
            "label": f"{aw['season_year']} Wk {aw['week_number']} — {aw['award_type'].replace('_', ' ')}: {blurb}",
        })

    return {
        "draft_info": draft_info,
        "college": p["college"],
        "seasons_played": seasons_played,
        "career_pro_bowls": career_pro_bowls,
        "career_all_pro": career_all_pro,
        "peak_overall": peak_overall,
        "timeline": timeline,
    }


def _sat_tier(satisfaction: int) -> str:
    """Map 0-100 satisfaction integer to tier key for SATISFACTION_TIER_LABELS."""
    if satisfaction >= 70:
        return "healthy"
    if satisfaction >= 55:
        return "distracted"
    if satisfaction >= 40:
        return "agent_calls"
    if satisfaction >= 25:
        return "declined_meeting"
    return "trade_request"


def _stat_line(pos: str, row) -> str:
    """Build position-appropriate stat line string from a stats row."""
    pos = pos.upper()
    gp = row["games_played"] or 0
    try:
        if pos == "QB":
            py = row["pass_yards"] or 0
            pt = row["pass_tds"] or 0
            pi = row["interceptions_thrown"] or 0
            rtg = row["passer_rating"] or 0.0
            return f"{gp} GP · {py:,} pass yds · {pt} TD · {pi} INT · {rtg:.1f} RTG"
        elif pos == "RB":
            ry = row["rush_yards"] or 0
            rt = row["rush_tds"] or 0
            ypc = row["yards_per_carry"] or 0.0
            return f"{gp} GP · {ry:,} rush yds · {rt} TD · {ypc:.1f} YPC"
        elif pos in ("WR", "TE"):
            rec = row["receptions"] or 0
            ry = row["rec_yards"] or 0
            rt = row["rec_tds"] or 0
            return f"{gp} GP · {rec} rec · {ry:,} yds · {rt} TD"
        elif pos in ("DL", "LB"):
            tkl = row["tackles"] or 0
            sacks = row["sacks"] or 0.0
            return f"{gp} GP · {tkl} tkl · {sacks:.1f} sacks"
        elif pos in ("CB", "S"):
            tkl = row["tackles"] or 0
            ints = row["interceptions"] or 0
            pd = row["pass_deflections"] or 0
            return f"{gp} GP · {tkl} tkl · {ints} INT · {pd} PD"
        elif pos == "K":
            fgm = row["fg_made"] or 0
            fga = row["fg_attempts"] or 0
            pct = row["fg_percentage"] or 0.0
            return f"{gp} GP · {fgm}/{fga} FG · {pct:.1f}%"
        elif pos == "P":
            punts = row["punts"] or 0
            punt_yds = row["punt_yards"] or 0
            avg = (punt_yds / punts) if punts else 0.0
            return f"{gp} GP · {punts} punts · {avg:.1f} avg"
        else:
            return f"{gp} GP"
    except Exception:
        return f"{gp} GP"
