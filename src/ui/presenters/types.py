# TypedDict view-model shapes for the GUI presenter layer.
# Populated in Phase 6 Prompt 2 (Dashboard) onward.
# Every TypedDict here corresponds to one Api.get_*() method return shape.
from __future__ import annotations

from typing import TypedDict


class ContextBarData(TypedDict):
    name: str           # "Chicago Bears"
    abbr: str           # "CHI"
    season: int
    week: int
    week_label: str     # "Wk 5 · 2024 Reg Season"
    phase: str          # "regular" | "playoffs" | "preseason" | "offseason"
    phase_badge: dict   # {label: str, css_class: str}
    record: str         # "5-3"
    cap_space: str      # "$23.4M"


class NextGameCard(TypedDict):
    opponent_name: str      # "Green Bay Packers"
    opponent_abbr: str      # "GB"
    opponent_record: str    # "4-4"
    location: str           # "Home · Soldier Field" or "Away · Lambeau Field"
    week: int
    week_label: str         # "Week 9"
    is_home: bool
    weather: str | None     # "38°F, Light Snow" or None
    spread: str | None      # always None in Prompt 2


class TeamStatusCard(TypedDict):
    record: str             # "5-3"
    division_rank: str      # "2nd NFC North"
    division_name: str      # "NFC North"
    off_rank: int | None    # league rank by points_for; None if no games played
    def_rank: int | None    # league rank by points_against; None if no games played
    health_summary: str     # "2 OUT, 1 Questionable"
    out_count: int
    questionable_count: int
    cap_space: str          # "$23.4M"
    active_count: int


class NewsItem(TypedDict):
    text: str
    category: str   # "award" | "warning" | "transaction" | "info"


class AlertItem(TypedDict):
    icon: str           # "⚠" | "✏" | "ℹ"
    text: str
    severity: str       # "warning" | "info" | "critical"
    link_route: str | None


class PerformerLine(TypedDict):
    name_short: str     # "J. Kim"
    team_abbr: str      # "CHI"
    award_type: str     # "OFFENSE" | "DEFENSE" | "SPECIAL_TEAMS"
    blurb: str          # "312 pass yds"


class DashboardView(TypedDict):
    context: ContextBarData
    next_game: NextGameCard | None      # None during offseason
    team_status: TeamStatusCard
    news: list[NewsItem]                # max 5 items
    alerts: list[AlertItem]             # max 5 items
    top_performers: list[PerformerLine] # max 4 items
    offseason_card: None                # stub; full implementation in Prompt 6


# ---------------------------------------------------------------------------
# Phase 6 Prompt 3 — Roster (T-02) + Player Card (T-05)
# ---------------------------------------------------------------------------

class RosterRow(TypedDict):
    id: int
    pos: str
    name_short: str
    age: int
    overall: str
    contract_summary: str
    status_icons: list
    _status_filter_value: str   # synthetic: "Active"|"Questionable"|"Doubtful"|"Out"
    _age_filter_value: str      # synthetic: "Under 25"|"25-29"|"30+"


class RosterView(TypedDict):
    team: dict
    columns: list
    players: list
    counts: dict
    position_options: list
    status_options: list
    age_options: list


class KeyAttribute(TypedDict):
    label: str
    grade: str


class ContractYearLine(TypedDict):
    season_year: int
    cap_hit: str
    dead_cap: str
    base_salary: str


class ContractSnapshotOv(TypedDict):
    summary_line: str
    years_remaining: list
    dead_cap_if_cut: str
    is_franchise_tag: bool
    is_rookie_contract: bool


class SeasonSummary(TypedDict):
    season_year: int
    games_played: int
    stat_line: str


class PlayerSeasonStatLine(TypedDict):
    season_year: int
    team_abbr: str
    games_played: int
    stat_line: str
    awards: list


class PlayerStatsTabs(TypedDict):
    current_season: "dict | None"
    season_history: list
    career_totals: dict


class ContractDetail(TypedDict):
    has_contract: bool
    contract_type: str
    aav: str
    total_value: str
    total_years: int
    signed_season: int
    years: list
    restructure_room: "str | None"


class SatisfactionEvent(TypedDict):
    week: int
    delta: int
    reason: str
    new_score: int


class SatisfactionDetail(TypedDict):
    current_score: int
    tier: str
    tier_label: str
    events: list


class PlayerHistoryLine(TypedDict):
    type: str
    label: str


class PlayerHistory(TypedDict):
    draft_info: str
    college: "str | None"
    seasons_played: int
    career_pro_bowls: int
    career_all_pro: int
    peak_overall: str
    timeline: list


class ActionDef(TypedDict):
    label: str
    action_key: str
    enabled: bool
    tooltip: str


class PlayerHeader(TypedDict):
    player_id: int
    full_name: str
    position: str
    team_name: str
    team_abbr: str
    age: int
    years_experience: int
    experience_label: str
    draft_label: str
    college: "str | None"
    overall: str
    clutch: str


class PlayerOverview(TypedDict):
    key_attributes: list
    contract_snapshot: "dict | None"
    season_summary: "dict | None"
    satisfaction_status: str


class PlayerView(TypedDict):
    header: dict
    overview: dict
    stats: dict
    contract: dict
    satisfaction: dict
    history: dict
    actions: list


# ---------------------------------------------------------------------------
# Phase 6 Prompt 4 — League Section (L-01 Standings, L-02 Leaders, L-03 Transactions)
# ---------------------------------------------------------------------------

class TeamStandingsRow(TypedDict):
    id: int
    rank: int
    name: str
    abbr: str
    wins: int
    losses: int
    wins_losses: str      # "5-3"
    pct: str              # ".625"
    div_record: str       # "3-0"
    conf_record: str      # "4-1"
    pf: int
    pa: int
    streak: str           # "W3" | "L1" | "—"
    division_id: int
    conference_id: int
    division_name: str
    conference_name: str
    _group_label: None    # always None; group headers are separate entries


class StandingsView(TypedDict):
    view: str
    season_year: int
    current_week: int
    rows: list            # mix of TeamStandingsRow and {"_group_label": str}
    columns: list


class LeaderRow(TypedDict):
    id: int
    rank: int
    name_short: str
    team_abbr: str
    position: str
    games_played: int
    stat_line: str        # formatted, category-specific
    _sort_key: float      # raw numeric for sorting


class LeadersView(TypedDict):
    category: str
    category_label: str
    season_year: int
    columns: list
    rows: list


class TransactionRow(TypedDict):
    id: int
    season_year: int
    week_number: int
    transaction_type: str
    type_label: str
    team_abbr: str
    team_name: str
    player_id: "int | None"
    player_name: str
    description: str
    _group_label: None    # always None; group headers are separate entries


class TransactionsView(TypedDict):
    rows: list            # mix of TransactionRow and {"_group_label": str}
    columns: list


# ---------------------------------------------------------------------------
# Phase 6 Prompt 5 — Schedule (S-01) / Game Preview (S-02) / Game Recap (S-05)
# ---------------------------------------------------------------------------


class ScheduleRow(TypedDict):
    id: int               # game_id, or synthetic negative id for BYE rows
    wk: int
    date: str             # synthetic "Sep 7"
    opp: str              # "@NE" (away) / "NE" (home) / "BYE"
    loc: str              # "Home" | "Away" | "—"
    result: str           # "W" | "L" | "T" | "—"
    score: str            # "24-17" | "—"
    status: str           # "[Recap]" | "Game Preview ▶" | "Upcoming" | "──"
    _variant: "str | None"  # "current" | "bye" | "muted" | None
    _group_label: None


class ScheduleView(TypedDict):
    team: dict            # {id, name, abbr}
    header: str           # "CHICAGO BEARS · 2024 REGULAR SEASON"
    subline: str          # "Record: 5-3 · Streak: W2"
    columns: list         # list.js column defs
    rows: list            # ScheduleRow list


class PreviewNextGame(TypedDict):
    opponent_name: str
    opponent_abbr: str
    opponent_record: str
    location: str         # "Home · Soldier Field" / "Away · Lambeau Field"
    week: int
    week_label: str
    is_home: bool
    weather: "str | None"
    spread: None


class PreviewHealthLine(TypedDict):
    name_short: str
    position: str
    status: str           # "Out" | "Doubtful" | "Questionable"


class GamePreviewView(TypedDict):
    game_id: int
    can_sim: bool
    next_game: PreviewNextGame
    team_status: dict     # {record, streak}
    opponent_status: dict  # {record}
    health: list          # PreviewHealthLine list
    key_matchups: list    # [] in v1 (omitted per scope decision)


class ScoreLine(TypedDict):
    home_abbr: str
    home_name: str
    home_score: int
    away_abbr: str
    away_name: str
    away_score: int
    winner_abbr: str


class KeyPlay(TypedDict):
    quarter: int
    clock: str            # "12:08"
    text: str             # narration_text


class RecapPerformerLine(TypedDict):
    name_short: str
    team_abbr: str
    stat_line: str        # "24 car, 142 yd"


class BoxScorePreview(TypedDict):
    home: str             # "CHI: 412 total"
    away: str             # "NE: 308 total"


class InjuryLine(TypedDict):
    name_short: str
    position: str
    status: str


class GameRecapView(TypedDict):
    final_score: ScoreLine
    headline: str
    setting: str          # "Wk 8 · Oct 24, 2024 · Chicago · 41°F, clear"
    key_plays: list       # KeyPlay list (<= 8)
    top_performers: list  # RecapPerformerLine list
    box_score_preview: BoxScorePreview
    injuries: list        # InjuryLine list
    next_screen_hint: str


# === Front Office Hub (F-01) ===

class SubNavItem(TypedDict):
    label: str
    key: str      # FO_MODE_* string or "hub"/"satisfaction"/"trades" for always-present nav items
    state: str    # "completed" | "active" | "upcoming" | "nav" | "separator"
    route: str    # "#/front-office" for active, "" for upcoming


class DeadlineInfo(TypedDict):
    label: str              # e.g., "Day 4 of 14"
    days_remaining: int | None


class FOCard(TypedDict):
    id: str             # unique within the view, e.g., "satisfaction-dashboard"
    title: str
    body: list[dict]    # list of {"label": str, "value": str} stat lines
    cta_label: str      # primary button label
    cta_route: str      # always non-empty; placeholder route if screen unbuilt
    badge: str | None   # optional badge text, e.g., "LOCKED" or "2 Active"


class FrontOfficeView(TypedDict):
    mode: str                    # FO_MODE_* constant
    cards: list[FOCard]
    sub_nav: list[SubNavItem]    # mode-aware; includes separator items
    deadline: DeadlineInfo | None


# === FA Market Browser (F-41) + FA Player Card (F-42) ===

class FAPlayerRow(TypedDict):
    id: int
    pos: str
    name_short: str
    age: int
    overall: str            # letter grade
    asking_salary: str      # "$X.XM/yr"
    interest_label: str     # "High" | "Neutral" | "Low" | "Unknown"
    interest_tier: int      # 1 | 2 | 3 | 0
    status_icons: list[str]
    _pos_filter_value: str
    _age_filter_value: str  # "Under 25" | "25-29" | "30+"


class NegotiationLine(TypedDict):
    player_id: int
    player_name: str
    position: str
    offer_aav: str
    status: str
    round_number: int


class FAMarketView(TypedDict):
    available_players: list[FAPlayerRow]
    columns: list[str]
    your_team_needs: list[str]      # ["LB depth", "WR depth"] or []
    cap_available: str              # "$23.4M"
    active_negotiations: list[NegotiationLine]
    watchlist_count: int


class FAMarketInterestTab(TypedDict):
    interest_tier: int
    interest_label: str
    interest_signal: str
    top_preferred_teams: list[dict]  # [{name, abbr, preference_score}], max 3


class FAContractHistoryLine(TypedDict):
    team_name: str
    seasons: str       # "2021–2023"
    total_value: str   # "$45M"
    aav: str           # "$15M/yr"
    type: str          # "Rookie" | "Extension" | "FA" | "Tag"


class FAPlayerView(TypedDict):
    header: dict
    overview: dict
    stats: dict
    history: dict
    market_interest: FAMarketInterestTab
    contract_history: list[FAContractHistoryLine]
    actions: list[dict]  # [{label, action_key, enabled, tooltip}]


# ---------------------------------------------------------------------------
# Phase 6 Prompt 7b — Modal view-models (F-43/F-44/F-45 + Cut/Restructure)
# ---------------------------------------------------------------------------

class MarketRange(TypedDict):
    low: str        # money_m
    fair: str       # money_m
    premium: str    # money_m


class PitchMeetingView(TypedDict):
    player_id: int
    player_name: str
    position: str
    overall: str            # letter grade
    asking_salary: str      # "$X.XM/yr"
    interest_label: str
    interest_signal: str
    market: MarketRange
    can_offer: bool
    note: str


class OfferBuilderView(TypedDict):
    player_id: int
    player_name: str
    position: str
    market: MarketRange
    cap_available: str
    defaults: dict          # {years, aav, signing_bonus, guaranteed_money} (ints, dollars)
    bounds: dict            # {min_years, max_years, max_signing_bonus_pct, max_guaranteed_pct}


class NegotiationResultView(TypedDict):
    ok: bool
    accepted: bool
    outcome: str            # "accepted" | "rejected"
    player_name: str
    cap_impact: str         # money_m
    message: str


class CutConfirmView(TypedDict):
    can_cut: bool
    player_id: int
    player_name: str
    dead_cap: str           # money_m
    current_cap_space: str  # money_m
    note: str


class RestructureView(TypedDict):
    can_restructure: bool
    player_id: int
    player_name: str
    current_season: int
    base_salary: int        # dollars (current year)
    max_convertible: int    # dollars
    current_cap_hit: str    # money_m
    years: list             # [{season_year, base_salary, prorated_bonus, cap_hit}] display strings
    note: str
