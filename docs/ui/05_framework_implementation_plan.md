# Step 5 — Framework Implementation Plan

**Status**: Drafted, pending review.
**Purpose**: Translate the design (Steps 0-4) into a concrete code architecture. Lock the folder structure, the Python↔JS bridge pattern, the JS toolchain, and the order in which screens get built. This is the file Claude Code reads first when Phase 5 implementation starts.
**Inputs to this step**: Step 0 framework lock (HTML + pywebview), Steps 1-4 design decisions, CLAUDE.md layer boundaries (`src/ui/` cannot compute or call engine/db directly).
**Output of this step**: Folder structure, bridge contract, JS architecture, build order.

---

## Resolutions to Step 4 Open Questions

| Question | Resolution |
|---|---|
| CSS framework | **Vanilla CSS with custom properties.** No Tailwind, no PostCSS. Tokens from Step 4 become CSS variables in a single `tokens.css` file. Reasoning: the design system is small enough that Tailwind's overhead (build tooling, class soup, larger HTML) outweighs its benefit. AI assistance for vanilla CSS is mature. |
| Table library | **Vanilla `<table>` for v1.** Swap to AG-Grid Community only if Step 8 testing shows the 1,696-row stat browser stutters. Pre-optimization is the wrong call here. |
| Icon library | **Unicode-first** (per David's confirmation). Swap to Lucide SVGs only if testing reveals rendering inconsistencies in WebView2. |
| JS state management | **Alpine.js** (~15KB, no build step, declarative reactivity). Lighter than React/Vue, more structured than vanilla. Loads via `<script>` tag — no bundler required. Strong fit for pywebview's serve-static-files pattern. |
| Folder structure under `src/ui/` | Detailed below in §3. |
| Keyboard nav scope | **Full keyboard control** (per David). Every action reachable without mouse. OOTP-style power-user shortcuts. Locked. |

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Native Window (pywebview · 64px chrome)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Embedded Web View (Edge WebView2 on Windows)             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  index.html (single SPA shell)                      │  │  │
│  │  │   ├─ tokens.css     (Step 4 design tokens)          │  │  │
│  │  │   ├─ components.css (10 components from Step 4 §5)  │  │  │
│  │  │   ├─ alpine.min.js  (vendored)                      │  │  │
│  │  │   ├─ shell.js       (router, context bar, nav)      │  │  │
│  │  │   └─ screens/       (one JS module per screen)      │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ▲                                                        │  │
│  │  │ window.pywebview.api.* (JSON over local bridge)        │  │
│  │  ▼                                                        │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Python API (src/ui/api.py)                         │  │  │
│  │  │   exposes: get_dashboard(), get_roster(), ...       │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │              │                                            │  │
│  │              ▼                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Presenter Layer (src/ui/presenters/)               │  │  │
│  │  │   - converts ratings → letter grades                │  │  │
│  │  │   - formats currency, dates                         │  │  │
│  │  │   - assembles view-models                           │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │              │                                            │  │
│  │              ▼                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  src/db/queries.py · src/league/* · src/transactions/* │ │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

The presenter layer is the topic of Step 7, but its existence is locked here because the JS frontend depends on it. UI receives only display-ready data.

---

## 2. SPA Shell, Not Multi-Page

Two architectural options were considered:

| Option | Verdict |
|---|---|
| **Multi-page** — each screen is its own HTML file, navigation = full page load | ✗ Rejected. Context bar would reload on every navigation, breaking continuity. Also forces re-fetching shell assets per screen. |
| **SPA shell** — single `index.html` with content-area swaps via JS router | ✓ Chosen. Persistent context bar stays in DOM. Navigation feels instant. Standard pattern for apps like this. |

The SPA shell uses a hash-based router (`#/team/roster`, `#/league/standings`, `#/draft-room`). No backend routing — pywebview serves a single file.

---

## 3. Folder Structure under `src/ui/`

```
src/ui/
├── __init__.py
├── api.py                    ← pywebview JS API surface (the bridge)
├── window.py                 ← creates the pywebview window, exposes api.py, points at index.html
├── presenters/               ← view-model assembly (Step 7 detail)
│   ├── __init__.py
│   ├── dashboard.py          ← presenter for T-01
│   ├── roster.py             ← presenter for T-02 (covers L-10 too)
│   ├── player.py             ← presenter for T-05 / L-11 / F-32 / F-42
│   ├── schedule.py
│   ├── game_recap.py
│   ├── standings.py
│   ├── front_office.py       ← mode-aware FO Hub
│   ├── free_agency.py
│   ├── trades.py
│   ├── scouting.py
│   ├── draft.py
│   ├── dynasty.py
│   └── formatters.py         ← shared: letter grades, currency, dates (used by all presenters)
├── static/                   ← all front-end assets, served by pywebview
│   ├── index.html
│   ├── css/
│   │   ├── tokens.css        ← Step 4 design tokens (CSS custom properties)
│   │   ├── reset.css         ← minimal reset
│   │   ├── components.css    ← 10 components from Step 4
│   │   └── screens.css       ← per-screen overrides (kept thin)
│   ├── js/
│   │   ├── alpine.min.js     ← vendored Alpine.js
│   │   ├── shell.js          ← router, context bar, top nav, sub-nav
│   │   ├── api.js            ← thin wrapper over window.pywebview.api
│   │   ├── format.js         ← client-side formatters (mostly reuses presenter output)
│   │   └── screens/          ← one module per screen archetype
│   │       ├── dashboard.js
│   │       ├── list.js       ← shared logic for Pattern A (Roster, FA Market, etc.)
│   │       ├── detail.js     ← shared logic for Pattern B (Player Card, Prospect)
│   │       ├── recap.js      ← shared logic for Pattern D (Game Recap, Season Review)
│   │       ├── draft_room.js ← Pattern E
│   │       └── ...
│   └── assets/
│       ├── logos/            ← team logos (Phase 0+ data; placeholder PNGs at start)
│       └── icons/            ← SVG icons if/when Unicode is swapped out (deferred)
└── tests/
    └── test_presenters.py    ← unit tests on the presenter layer
```

**Rules:**

- `src/ui/api.py` and `src/ui/window.py` are the **only** Python files in `src/ui/` that touch pywebview. Everything else is plain Python.
- `src/ui/presenters/` may import from `src/db/queries.py` only — never from `engine/`, `league/`, `transactions/` directly. Those modules expose their own query-layer-friendly interfaces.
- `src/ui/static/` is read-only at runtime — pywebview serves it as static files. Hot-reload during development is handled by a dev flag (see §6).

---

## 4. The Python↔JS Bridge (Contract)

`src/ui/api.py` exposes a single class `Api` whose public methods become available as `window.pywebview.api.*` in the browser.

### Contract Rules

1. **All bridge methods return JSON-serializable data only.** No SQLite Row objects, no datetime objects unformatted, no raw player records with `true_overall`.
2. **All methods are read-only by default.** Mutations (cut, sign, trade) use methods prefixed with `do_*` (e.g., `do_cut_player`).
3. **Methods accept primitives or simple dicts.** No complex Python objects passed across the bridge.
4. **Errors return as `{"ok": false, "error": "message"}`.** Exceptions are caught and serialized — never crash the JS side.
5. **Long-running calls return a task ID immediately, then the JS polls.** Used for game sim, week advance, draft round.

### Example API Surface

```python
class Api:
    def __init__(self, save_path: str):
        self.save_path = save_path
        self._conn = None  # lazy

    # === Read methods ===

    def get_dashboard(self) -> dict:
        """View-model for T-01 Team Dashboard."""
        return presenters.dashboard.build(self._conn)

    def get_roster(self, team_id: int | None = None) -> dict:
        """View-model for T-02 (or L-10 if team_id != user team)."""
        return presenters.roster.build(self._conn, team_id)

    def get_player(self, player_id: int) -> dict:
        """View-model for T-05 / L-11 / F-32 / F-42."""
        return presenters.player.build(self._conn, player_id)

    def get_standings(self, view: str = "division") -> dict:
        """L-02. view ∈ {division, conference, league, playoff_picture}."""
        return presenters.standings.build(self._conn, view)

    # === Write methods (mutations) ===

    def do_advance_week(self) -> dict:
        """Sim through the current week. Returns task ID for polling."""
        ...

    def do_sign_free_agent(self, player_id: int, offer: dict) -> dict:
        """Submit FA offer. Returns negotiation result."""
        ...

    def do_cut_player(self, player_id: int) -> dict:
        """Release a player. Returns dead cap impact and confirmation."""
        ...

    # === Long-running task polling ===

    def get_task_status(self, task_id: str) -> dict:
        """Returns {progress: 0.0-1.0, message: str, result: dict | None}."""
        ...
```

### JS Side Wrapper

`src/ui/static/js/api.js` wraps the bridge with promise-based ergonomics:

```js
export const api = {
    async getDashboard() {
        return await window.pywebview.api.get_dashboard();
    },
    async getRoster(teamId = null) {
        return await window.pywebview.api.get_roster(teamId);
    },
    async doAdvanceWeek(onProgress) {
        const taskId = await window.pywebview.api.do_advance_week();
        return await pollTask(taskId, onProgress);
    },
    // ...
};
```

This wrapper means every screen's JS imports `api` and calls strongly-named methods — no scattered `window.pywebview.api.foo` strings throughout the codebase.

---

## 5. JS Architecture (Alpine + Module Pattern)

### Why Alpine over Vanilla or React

| Choice | Trade-off |
|---|---|
| Vanilla JS | Most flexible but every screen reinvents reactivity. Tedious for sortable tables, modal state, filter chips. |
| **Alpine.js** | Declarative reactivity in HTML attributes (`x-data`, `x-show`, `x-for`). Small enough to read in a sitting (~3,000 LoC). No build step. Imports via `<script>`. **Chosen.** |
| React/Vue | Build tooling overhead, JSX/SFC complexity, state management libs. Overkill for ~64 screens that are mostly read-only. |

### Screen Module Pattern

Each screen has a JS module exporting an `init(container, params)` function called by the router. Pattern D (recap moments) and Pattern A (lists) share base logic via `screens/list.js` and `screens/recap.js`.

Example for Roster screen (Pattern A):

```js
// src/ui/static/js/screens/roster.js
import { api } from '../api.js';
import { initListScreen } from './list.js';

export async function init(container, params) {
    const data = await api.getRoster(params.teamId);
    initListScreen(container, {
        title: `${data.team.name} Roster`,
        columns: data.columns,           // pre-shaped by presenter
        rows: data.players,              // pre-shaped, letter grades already strings
        sortBy: 'overall',
        onRowClick: (row) => router.navigate(`#/player/${row.id}`),
        rowMenu: [
            { label: 'Add to Trade Block', action: (row) => api.doToggleTradeBlock(row.id) },
            { label: 'Cut Player', action: (row) => confirmCut(row) },
        ],
    });
}
```

The pattern: presenter assembles view-model in Python → bridge sends JSON → screen module passes it into a shared template (`initListScreen`) → Alpine handles sort/filter/click reactivity inside the template.

This means **adding a new list screen is mostly a presenter + a thin screen module**. The list rendering logic is written once.

---

## 6. Build Order (Phase 5 Implementation Plan)

The build order optimizes for "every increment is testable end-to-end." Each milestone produces a working window the user can click around in.

### Milestone 5.1 — Window + Shell (target: 1 prompt)

- Create `src/ui/window.py` that opens a pywebview window pointed at `index.html`.
- Create `src/ui/api.py` with a single stub `get_app_info()` returning `{name, version}`.
- Create `src/ui/static/index.html` with the universal shell (Step 3): context bar (placeholder data), section tabs, sub-nav rail, content area.
- Create `tokens.css`, `reset.css`, `components.css` with all Step 4 tokens and components.
- Vendor Alpine.js.
- Implement hash-based router in `shell.js`.
- Test command: `python -m src.ui.window saves/test_franchise.db` opens a window with the empty shell.

### Milestone 5.2 — Team Dashboard (T-01)

- Build presenter `presenters/dashboard.py`.
- Build screen `screens/dashboard.js` using Pattern C (Hub).
- Wire context bar to live data (week, record, cap).
- Test command: launch and verify dashboard renders week 1 data correctly.

### Milestone 5.3 — Roster Overview (T-02) + Player Card (T-05)

- Build `presenters/roster.py` and `presenters/player.py` with full letter-grade conversion.
- Build `screens/list.js` (shared Pattern A) and `screens/roster.js`.
- Build `screens/detail.js` (shared Pattern B) and `screens/player.js`.
- Test: navigate Dashboard → Roster → Player Card and back without losing context bar state.

### Milestone 5.4 — League Section (L-02 Standings, L-05 Leaders, L-07 Transactions)

- Three list screens reusing `screens/list.js`.
- Validates that the list pattern is genuinely reusable.

### Milestone 5.5 — Schedule + Game Recap (S-01, S-02, S-05)

- Schedule reuses list pattern.
- Game Preview is a Hub variant.
- Game Recap is the first **Pattern D recap moment** — earns extra polish budget per Step 9.
- Test: full in-season loop from Dashboard → Sim Game → Recap → back.

### Milestone 5.6 — Front Office Hub (F-01) + Mode Awareness

- Build mode-aware FO Hub that swaps cards based on `offseason_state.current_phase`.
- Test by running the offseason CLI to advance phases and verifying FO Hub rerenders.

### Milestone 5.7 — Free Agency Flow (F-40 to F-45)

- Build `screens/free_agency.js` with FA Market list + FA Player Card + Pitch Meeting modal + Offer Builder modal.
- Tests Pattern A + Pattern B + modal stack.

### Milestone 5.8 — Trade Hub (F-50 to F-55) + Scouting (F-30 to F-37)

- Trade Builder is a custom screen — it's the most complex form in the game.
- Scouting reuses list/detail patterns.

### Milestone 5.9 — Draft Room (F-60) — Pattern E

- Most complex screen. Three-column layout, live event feed, decision modal.
- Validates Pattern E (Live Event Screen) for both Draft Room and Game View.

### Milestone 5.10 — Recap Moments (Pattern D) Polish

- Season Review (F-10), Conference Championship Recap (S-10), Super Bowl Recap (S-11), Draft Class Reveal, Career Retirement.
- Step 9 owns the polish spec; this milestone is the implementation pass.

### Milestone 5.11 — Dynasty Section (D-01 to D-08)

- Mostly read-only history screens. Reuses list pattern heavily.

### Milestone 5.12 — Settings, Save/Load, Help, System

- Wraps the v1 UI scope.
- Steam packaging spike (PyInstaller + WebView2 bootstrapper) — separate task.

---

## 7. Dev Workflow

### Hot Reload During Development

`pywebview` doesn't ship hot reload, but a `--debug` flag enables Chromium DevTools. Combined with watching the `static/` folder and reloading the window on file change, the dev loop is fast:

```python
# src/ui/window.py
def main(save_path, debug=False):
    api = Api(save_path)
    window = webview.create_window(
        "Football Simulator",
        url="src/ui/static/index.html",
        js_api=api,
        width=1440, height=900, min_size=(1280, 720),
    )
    webview.start(debug=debug, http_server=True)
```

Test command pattern: `python -m src.ui.window saves/test_franchise.db --debug`.

### Layer Boundary Enforcement

CLAUDE.md says UI must not compute or call engine/db directly. Concretely:

- **Allowed**: `src/ui/presenters/*.py` imports from `src/db/queries.py` and from utility modules in `src/utils/`.
- **Allowed**: `src/ui/api.py` calls into `src/league/season.py` for week-advance, but **only via methods on those modules' public API**.
- **Forbidden**: any `import sqlite3` or raw SQL inside `src/ui/`.
- **Forbidden**: any reference to `player.true_overall` or other raw rating fields outside `src/engine/`.

These rules go into a CI check or pre-commit hook in Phase 5 — captured as an action item.

---

## 8. Steam Packaging (deferred to end of Phase 5)

Captured here so it's not forgotten:

- **PyInstaller** with `--onefile` or `--onedir` — onedir easier to debug, onefile cleaner for distribution.
- **WebView2 bootstrapper**: bundle Microsoft's WebView2 runtime check; many Windows 10 machines need the runtime installer prompt.
- **Code signing**: Steam release should be code-signed to avoid SmartScreen warnings.
- **Asset bundling**: ensure `src/ui/static/**/*` is included in the PyInstaller spec.
- **Save path**: Steam apps should write saves to `%APPDATA%/FootballSimulator/saves/`, not relative to the .exe.

---

## 9. Out of Scope for v1

Defer:

- Server-side rendering (we're a desktop app, not a web app).
- WebSocket-style live updates from Python to JS (use polling for the game-sim progress case; it's simpler).
- Service workers / offline mode (irrelevant for a desktop sim).
- TypeScript (would be nice but adds a build step; revisit if JS complexity grows).
- Component testing framework on the JS side (Cypress/Playwright) — manual testing fine for v1.

---

## 10. Open Questions for Step 6

1. How "read-only first" applies in practice: does Milestone 5.2 ship with the Continue button disabled, or with `do_advance_week` working? (Step 6 will resolve.)
2. Should every screen render mock data first, then swap to live data, or live data from day one? (Step 6.)
3. Where do error states appear — toast, banner, modal? (Already partially answered in Step 4 §5; Step 6 will lock per-screen.)

---

## Action Items Before Step 6

- [ ] David reviews the build order — flag if any milestone should be reordered or split.
- [ ] Confirm Alpine.js as the JS layer (vs vanilla or htmx).
- [ ] Confirm SPA shell (vs multi-page).
- [ ] Confirm the bridge contract pattern (`get_*` for reads, `do_*` for writes, task IDs for long-running).
- [ ] Confirm presenter folder structure under `src/ui/presenters/`.
