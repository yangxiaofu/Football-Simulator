# Step 7 — Presenter Layer

**Status**: Drafted, pending review.
**Purpose**: Define the layer that sits between `src/db/queries.py` and `src/ui/api.py` — the place where raw data becomes display-ready view-models. Lock the contract so Claude Code builds presenters consistently across all 64 screens.
**Inputs to this step**: CLAUDE.md layer rule (UI never computes), Step 4 format conventions (letter grades, currency, dates), Step 5 folder structure (`src/ui/presenters/`), Step 6 read-only-first discipline.
**Output of this step**: View-model contract, presenter pattern, shared formatters, caching policy, testing approach, concrete view-model shapes for primary screens.

---

## Why the Presenter Layer Exists

CLAUDE.md is explicit: UI must not compute. The simulation engine never exposes `true_overall` outside `src/engine/`. The cap is a cached value, not summed live. Currency, dates, and letter grades have one canonical format.

These rules don't enforce themselves. Without a deliberate layer, every screen will end up doing its own conversions — some right, some subtly wrong, all inconsistent. The presenter layer is the single seam where:

1. **Raw data becomes display-ready** (ratings → letter grades, raw cap → `$23.4M`, `season_year=2026, week_number=8` → `Wk 8 · 2026 Reg Season`).
2. **Layer boundaries get enforced** (presenters can import from `src/db/queries.py` and `src/utils/`, nothing else).
3. **The shape of every view-model is documented and testable** (a screen that breaks because the schema changed will fail at the presenter boundary, not deep inside JS).
4. **The bridge contract is honored** (everything returned is JSON-serializable, no `sqlite3.Row` objects, no `datetime` instances unformatted).

Without this layer, the read-only-first discipline (Step 6) silently fails — because if presenters and screens are coupled, you can't render with real data without also wiring everything else.

---

## Resolutions to Step 6 Open Questions

| Question | Resolution |
|---|---|
| View-model shape | **Explicit `TypedDict` per screen** in `src/ui/presenters/types.py`. Type-checked in Python, JSON-serializable to JS, self-documenting. |
| Caching strategy | **No caching at v1.** Recompute on every call. Add caching only after Step 8 testing identifies a hot path that needs it. Cache invalidation is the wrong cost to take on early. |
| Testing approach | **Golden file pattern.** For each presenter, store expected output JSON for known inputs (e.g., `test_franchise.db` at week 1, week 8, mid-offseason). Tests compare presenter output to the golden file — easy to update intentionally, catches accidental drift. |

---

## 1. The Presenter Pattern

Every presenter is a single Python module with a public `build()` function returning a typed view-model.

```python
# src/ui/presenters/roster.py
from typing import TypedDict
from src.db import queries
from src.ui.presenters.formatters import letter_grade, money_m, status_icons


class RosterRow(TypedDict):
    id: int
    pos: str
    name_short: str       # "J. Kim"
    age: int
    overall: str          # letter grade pill string, e.g. "A+"
    scheme_fit: str       # letter grade
    contract_summary: str # "4yr · $42M/yr"
    status_icons: list[str]   # ["⚕"] for injured, ["⚠"] for satisfaction warning


class RosterView(TypedDict):
    team: dict            # {id, name, abbr, primary_color, secondary_color}
    columns: list[str]    # ordered column keys for table rendering
    players: list[RosterRow]
    counts: dict          # {active: 53, ir: 2, practice_squad: 16}


def build(conn, team_id: int) -> RosterView:
    team = queries.get_team(conn, team_id)
    raw_players = queries.get_team_roster(conn, team_id)

    rows: list[RosterRow] = []
    for p in raw_players:
        rows.append({
            "id": p["id"],
            "pos": p["position"],
            "name_short": _shorten_name(p["first_name"], p["last_name"]),
            "age": p["age"],
            "overall": letter_grade(p["true_overall"]),
            "scheme_fit": letter_grade(p["scheme_fit_score"]),
            "contract_summary": _summarize_contract(p["contract"]),
            "status_icons": status_icons(p),
        })

    return {
        "team": {
            "id": team["id"],
            "name": team["name"],
            "abbr": team["abbreviation"],
            "primary_color": team["primary_color"],
            "secondary_color": team["secondary_color"],
        },
        "columns": ["pos", "name_short", "age", "overall", "scheme_fit", "contract_summary", "status_icons"],
        "players": rows,
        "counts": queries.get_roster_counts(conn, team_id),
    }
```

### Pattern Rules

1. **Single public function**, named `build()`, accepting `(conn, *params)` and returning a typed view-model.
2. **All raw rating fields converted via `formatters.letter_grade()` before leaving the presenter.** No `true_overall` in the output. Ever.
3. **All currency converted via `formatters.money_m()`.** Returns `"$23.4M"` strings, not floats.
4. **All dates formatted to display strings.** Per Step 4 conventions.
5. **No business logic.** Presenters compose data; they don't decide things. "Should this player be flagged as on the trade block?" is a query result, not a presenter computation.
6. **No mutations.** Presenters are pure functions of `conn` + parameters. Calling `build()` twice in a row returns equivalent data (modulo concurrent writes, which only happen via `do_*` methods).
7. **No imports outside `src/db/queries.py` and `src/utils/`.** Enforced by code review and (eventually) a CI lint rule.

### Helper Convention

Private helpers prefixed `_` live in the same module. Cross-presenter helpers (name shortening, contract summarization, status icons) live in `formatters.py`.

---

## 2. The Shared `formatters.py`

One canonical implementation of every Step 4 format convention. Every presenter imports from here. No screen ever defines its own letter-grade or currency function.

```python
# src/ui/presenters/formatters.py
from src.utils.constants import LETTER_GRADE_THRESHOLDS

def letter_grade(rating: int | None) -> str:
    """1-99 rating → 'A+' through 'F'. None → '—'."""
    if rating is None:
        return "—"
    for threshold, grade in sorted(LETTER_GRADE_THRESHOLDS.items(), reverse=True):
        if rating >= threshold:
            return grade
    return "F"

def money_m(amount: int | float | None) -> str:
    """Cents/dollars → '$23.4M'. None → '—'. Negative → '−$2.1M'."""
    if amount is None:
        return "—"
    if amount == 0:
        return "$0"
    millions = amount / 1_000_000
    if millions < 0:
        return f"−${abs(millions):.1f}M"
    return f"${millions:.1f}M"

def short_name(first: str, last: str) -> str:
    """'Jordan Kim' → 'J. Kim'."""
    return f"{first[0]}. {last}"

def date_short(year: int, month: int, day: int) -> str:
    """2026, 9, 7 → 'Sep 7'."""
    return f"{MONTH_ABBR[month]} {day}"

def week_label(season_year: int, week: int, phase: str) -> str:
    """Build the date string for the context bar."""
    if phase == "regular":
        return f"Wk {week} · {season_year} Reg Season"
    if phase == "wildcard":
        return f"Wildcard · {season_year} Playoffs"
    # ... etc

def phase_badge(phase: str, offseason_phase: str | None = None) -> dict:
    """Return {label: 'FA', color_token: '--color-purple'} for the badge component."""
    ...

def record(wins: int, losses: int, ties: int = 0) -> str:
    """5, 3, 0 → '5-3'. 5, 3, 1 → '5-3-1'."""
    return f"{wins}-{losses}" + (f"-{ties}" if ties else "")

def status_icons(player: dict) -> list[str]:
    """Inspect player flags, return list of unicode icons in canonical order."""
    icons = []
    if player.get("injury_status") in ("OUT", "QUESTIONABLE", "DOUBTFUL"):
        icons.append("⚕")
    if player.get("satisfaction_tier") in ("WARNING", "CRITICAL"):
        icons.append("⚠")
    if player.get("on_trade_block"):
        icons.append("🔄")
    if player.get("franchise_tagged"):
        icons.append("🔒")
    return icons
```

The constants used (`LETTER_GRADE_THRESHOLDS`, `MONTH_ABBR`) live in `src/utils/constants.py` per CLAUDE.md.

---

## 3. View-Model Catalog (Primary Screens)

Concrete `TypedDict` shapes for the screens Claude Code will build first. Each screen's view-model corresponds to one method on `Api`.

### Dashboard (T-01)

```python
class DashboardView(TypedDict):
    context: ContextBarData
    next_game: NextGameCard | None      # None during offseason
    team_status: TeamStatusCard
    news: list[NewsItem]                # max 5
    alerts: list[AlertItem]
    top_performers: list[PerformerLine] # last week's
    offseason_card: OffseasonCard | None  # rendered when in offseason
```

### Roster (T-02)

(See §1 above — `RosterView`.)

### Player Card (T-05)

```python
class PlayerView(TypedDict):
    header: PlayerHeader        # photo, identity line, headline grades
    overview: PlayerOverview    # key attributes, contract snapshot, season stats, satisfaction
    stats: PlayerStatsTabs      # by season, by category
    contract: ContractDetail
    satisfaction: SatisfactionDetail
    history: PlayerHistory
    actions: list[ActionDef]    # available action buttons (some disabled per Milestone)
```

### Standings (L-02)

```python
class StandingsView(TypedDict):
    season_year: int
    view: str  # "division" | "conference" | "league" | "playoff_picture"
    divisions: list[DivisionStandings]   # for division/league views
    conferences: list[ConferenceStandings]  # for conference view
    playoff_picture: PlayoffPicture | None
```

### Game Recap (S-05)

```python
class GameRecapView(TypedDict):
    final_score: ScoreLine
    headline: str               # generated narrative
    setting: str                # "Foxborough · 41°F, clear"
    key_plays: list[KeyPlay]    # 8 max, time-ordered
    top_performers: list[PerformerLine]
    box_score_preview: BoxScorePreview
    injuries: list[InjuryLine]
    next_screen_hint: str       # "Continue advances to Wk 9"
```

### Front Office Hub (F-01) — Mode-Aware

```python
class FrontOfficeView(TypedDict):
    mode: str                   # "in_season" | "postseason" | offseason phase name
    cards: list[FOCard]         # rendered cards depend on mode
    sub_nav: list[SubNavItem]   # phase indicators, completed/active/upcoming
    deadline: DeadlineInfo | None  # offseason phase deadlines
```

### FA Market (F-41)

```python
class FAMarketView(TypedDict):
    available_players: list[FAPlayerRow]
    columns: list[str]
    your_team_needs: list[str]      # ["LB depth", "CB2", "Backup QB"]
    cap_available: str              # "$23.4M"
    active_negotiations: list[NegotiationLine]
    watchlist_count: int
```

### Draft Room (F-60)

```python
class DraftRoomView(TypedDict):
    state: DraftState               # round, pick number, on-the-clock team
    your_next_pick: PickInfo
    live_feed: list[DraftEvent]     # newest first
    your_board: list[ProspectRow]   # ranked, filtered to available
    league_status: LeagueDraftStatus
    decision_modal: DecisionModalData | None  # populated when you're on the clock
```

The remaining ~50 screens follow the same pattern — one `TypedDict` per view-model, all defined in `src/ui/presenters/types.py`.

---

## 4. The `Api` Method ↔ Presenter Mapping

Every `Api` method calls exactly one presenter. The mapping is one-to-one, no exceptions:

| Bridge Method | Presenter | View-Model |
|---|---|---|
| `get_dashboard()` | `presenters.dashboard.build()` | `DashboardView` |
| `get_roster(team_id)` | `presenters.roster.build()` | `RosterView` |
| `get_player(player_id)` | `presenters.player.build()` | `PlayerView` |
| `get_standings(view)` | `presenters.standings.build()` | `StandingsView` |
| `get_schedule()` | `presenters.schedule.build()` | `ScheduleView` |
| `get_game_recap(game_id)` | `presenters.game_recap.build()` | `GameRecapView` |
| `get_front_office()` | `presenters.front_office.build()` | `FrontOfficeView` |
| `get_fa_market()` | `presenters.free_agency.build_market()` | `FAMarketView` |
| `get_fa_player(player_id)` | `presenters.free_agency.build_player()` | `FAPlayerView` |
| `get_trade_hub()` | `presenters.trades.build_hub()` | `TradeHubView` |
| `get_scouting_hub()` | `presenters.scouting.build_hub()` | `ScoutingHubView` |
| `get_draft_class()` | `presenters.scouting.build_class()` | `DraftClassView` |
| `get_prospect(player_id)` | `presenters.scouting.build_prospect()` | `ProspectView` |
| `get_draft_room()` | `presenters.draft.build_room()` | `DraftRoomView` |
| `get_dynasty()` | `presenters.dynasty.build_hub()` | `DynastyView` |
| ... | ... | ... |

This means: when adding a new screen, you write exactly one presenter file, one `TypedDict`, and one Api method. The pattern is mechanical.

---

## 5. Mutation Methods Don't Use Presenters

Presenters are read-only. Mutation methods (`do_*`) call into the appropriate business logic module directly:

```python
# src/ui/api.py
class Api:
    def do_cut_player(self, player_id: int) -> dict:
        from src.transactions.contracts import release_player
        result = release_player(self._conn, player_id)
        return {
            "ok": True,
            "dead_cap": money_m(result.dead_cap),
            "new_cap_space": money_m(result.new_cap_space),
            "message": f"{result.player_name} released. Dead cap: {money_m(result.dead_cap)}.",
        }
```

The mutation methods still **pass through `formatters`** for any user-visible strings in the response. That's the only formatter use outside presenters.

---

## 6. Caching Policy (locked: NO at v1)

**No caching.** Every presenter call hits the database fresh.

Reasoning:
- Cache invalidation is harder to get right than the entire presenter layer combined.
- Phases 0-3 are working without UI caching; queries against `test_franchise.db` are sub-50ms for everything except possibly the league-wide stat browser.
- Step 8 (data volume testing) will identify if any presenter exceeds an acceptable budget. If so, that specific presenter gets a memoization decorator with an explicit invalidation key (e.g., `season_year + week_number`). Targeted, not blanket.
- `team.cap_space` is *already* a cached value at the data layer (per CLAUDE.md). Presenters don't re-cache.

If Step 8 testing surfaces a slow presenter:
1. First, look for an `N+1` query pattern (loop calling `queries.get_player()` 53 times).
2. If still slow, add an explicit cache **at the queries layer**, not the presenter layer. The presenter stays simple.

---

## 7. Testing Strategy — Golden Files

Each presenter has a test in `src/ui/tests/test_presenters.py`. Tests follow this pattern:

```python
def test_roster_presenter():
    conn = connection.get_connection("saves/test_franchise.db")
    result = roster.build(conn, team_id=1)
    expected = json.loads(open("src/ui/tests/golden/roster_team1_wk1.json").read())
    assert result == expected
```

Golden files are JSON dumps of the expected view-model for known fixture states. Saved in `src/ui/tests/golden/`. Workflow:

1. Implement presenter.
2. Run it once against `test_franchise.db`, dump output to a golden file, eyeball-verify it's correct.
3. Commit golden file alongside the presenter.
4. CI runs the test on every change.
5. When the schema or design intentionally changes, run the presenter, eyeball-diff the new output, overwrite the golden file.

This catches:
- Schema drift (a column rename will break the golden file).
- Format regressions (a letter-grade conversion bug surfaces immediately).
- Presenter logic changes that weren't intended.

It does NOT catch:
- Visual regressions (handled by manual review).
- JS-side bugs (handled by manual testing of the live UI).

For Phase 5 v1, golden-file unit tests are the only automated UI testing. Sufficient for a solo build.

---

## 8. Layer Boundary Enforcement

Concrete rules for `src/ui/presenters/*.py`:

**Allowed imports:**
- `src.db.queries`
- `src.db.connection` (for `Row` typing only)
- `src.utils.constants`
- `src.ui.presenters.formatters`
- `src.ui.presenters.types`
- Standard library

**Forbidden imports:**
- `src.engine.*` (engine internals never leak to presenters)
- `src.league.*` (business logic stays out)
- `src.transactions.*` (mutations stay out — those are `do_*` territory)
- `src.scouting.*` (same — scouting business logic, not display)
- `sqlite3` directly (must go through `src.db.queries`)

**Recommended pre-commit check** (Phase 5 task): a simple grep-based linter that scans `src/ui/presenters/` for forbidden imports and fails CI.

---

## 9. The Presenter is the Documentation

A subtle but important consequence: once presenters exist, they become the canonical documentation of "what does this screen show." A developer (or AI) reading `presenters/dashboard.py` sees the exact shape of the dashboard's view-model — better than any wireframe in describing the data dependencies.

This means:
- Wireframes (Step 3) describe **layout and intent**.
- Presenters describe **data**.
- Component vocabulary (Step 4) describes **rendering**.

Together, the three artifacts are sufficient for Claude Code to build any screen without ambiguity.

---

## 10. Open Questions for Step 8

1. What's the performance budget per presenter? (e.g., <50ms for primary screens, <200ms for stat browser.) Step 8 will set thresholds.
2. Are 1,696-row views actually rendered all at once, or paginated/virtualized? Affects both presenter shape and table component.
3. How is the `test_franchise.db` snapshotted to provide stable fixtures for golden files? (Avoid drift across test runs.)

---

## Action Items Before Step 8

- [ ] David confirms the one-presenter-per-screen pattern (no shared mega-presenters).
- [ ] Confirm "no caching at v1" — willing to revisit only after Step 8 testing surfaces a problem.
- [ ] Confirm golden-file test approach as the v1 testing strategy.
- [ ] Confirm `TypedDict` over `dataclass` for view-models. (TypedDict serializes to JSON natively; dataclasses need extra work.)
- [ ] Confirm the layer boundary rules — comfortable with strict no-import-from-engine/league/transactions in presenters.
