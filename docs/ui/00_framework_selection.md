# Step 0 — UI Framework Selection

**Status**: Drafted, pending lock-in.
**Decision owner**: David
**Why this comes first**: Steps 4 (component vocabulary), 5 (framework implementation plan), 7 (presenter layer), and 8 (data volume testing) all depend on which framework renders the UI. Locking it now prevents rework.

---

## What the UI Has to Do

The Football Simulator is a deep, text-and-data-heavy management sim — closer to OOTP, Football Manager, or a portfolio tracker than to an action game. The UI must comfortably handle:

- **Dense data tables**: 53-man rosters, 32-team standings, league-wide stat leaders (1,696 players × multiple stat columns), draft boards (250+ prospects), play-by-play logs.
- **Sortable, filterable views**: every list screen needs sort-by-column and filter affordances.
- **Drill-down navigation**: click a player row → player card → contract detail → restructure dialog. 30+ screens with predictable back/forward behavior.
- **Persistent context** (week, team, cap) visible on every screen.
- **Recap moments**: post-game summary, week recap, awards ceremony, draft results — these reward typography and layout polish.
- **Steam shippable** on Windows as the launch target.

Frameworks that struggle with any of those are disqualified for this project.

## Candidates Evaluated

### 1. HTML + pywebview (embedded web view, Python backend)
- **What it is**: Python game logic exposes data to a local HTML/CSS/JS frontend rendered inside a native window via `pywebview` (Edge WebView2 on Windows). Same architectural pattern OOTP, Football Manager, and most modern data-heavy sims use.
- **Strengths**: Best-in-class for data tables, sortable grids, typography, and recap screens. Mature ecosystem (any HTML library — DataTables, AG-Grid Community, plain CSS Grid). Fast iteration. Easy to theme. Web devs and AI coding assistants have deep knowledge of the stack.
- **Weaknesses**: Requires HTML/CSS/JS alongside Python. Steam packaging needs care (must bundle WebView2 runtime check on Windows). Two languages = two debugging surfaces.
- **Steam track record**: Strong. OOTP, Football Manager (large portions), most "spreadsheet sim" games on Steam use embedded web.

### 2. Dear PyGui
- **What it is**: Pure-Python immediate-mode GUI library, GPU-accelerated, designed for tools/dashboards.
- **Strengths**: Single language. Fast. Modern look out of the box. Decent table widget. No HTML required.
- **Weaknesses**: Smaller community, thinner docs, fewer Steam-shipped examples. Immediate-mode paradigm is unfamiliar (every frame redraws — different mental model). Typography and layout polish for recap screens require more manual work than HTML.
- **Steam track record**: Limited. A handful of indie tools, few full sim games.

### 3. PySide6 (Qt for Python)
- **What it is**: Bindings to the mature Qt framework. Industrial-grade native widgets, including a powerful `QTableView` with model/view separation.
- **Strengths**: Best-in-class native table widget. Professional look. Excellent docs. LGPL licensing is fine for Steam commercial release.
- **Weaknesses**: Steeper learning curve. Heavier installer (~80–100 MB additional). Layout system is verbose. AI assistants are competent but slower at Qt than at HTML.
- **Steam track record**: Solid for tools and some sims, less common for management games specifically.

### 4. Tkinter + ttk (+ tksheet for tables)
- **What it is**: Python's built-in GUI toolkit. Free, no extra deps.
- **Strengths**: Zero install friction. Bundled with Python.
- **Weaknesses**: Dated look. Native table support is weak — requires `tksheet` or `pandastable` third-party libs that aren't as polished. Limited theming. Steam buyers expect modern UI; Tkinter often feels like a Python class project.
- **Steam track record**: Rare. Not recommended for commercial releases targeting paying customers.

### 5. Pygame
- **What it is**: General-purpose game library. Great for action games.
- **Strengths**: Strong Steam track record for indie action games.
- **Weaknesses**: No native widget system at all. You'd hand-roll text rendering, scrolling, sorting, table layouts, focus management, keyboard nav, copy-paste. For a data-heavy sim, this is a multi-month detour into UI primitives before you can render a single screen.
- **Steam track record**: Strong for action genres, almost nonexistent for management sims.

---

## Recommendation: HTML + pywebview

**Certainty: High.**

Three reasons drive the call:

1. **Information density is your dominant design constraint.** OOTP-style sims succeed or fail on how readably they show 1,000+ rows of player data. HTML/CSS does this better than every alternative. Every table screen — roster, standings, league leaders, draft board, FA market — is fundamentally a sortable grid. The web stack was built for this.

2. **Steam-bound management sims have already converged on this pattern.** OOTP and Football Manager both run embedded web for the bulk of their UI. You are building in the same genre with the same constraints; copying the proven architecture is the conservative choice.

3. **AI-assisted implementation is fastest in HTML.** Claude Code in your terminal will produce HTML/CSS/JS components faster and with fewer corrections than Dear PyGui or Qt code. Given your workflow (Cowork plans, Claude Code builds), framework choice should optimize for AI velocity. HTML wins this clearly.

### Concrete Stack Proposal

| Layer | Choice |
|---|---|
| Window/runtime | `pywebview` 5.x (Edge WebView2 on Windows, WebKit elsewhere) |
| Frontend framework | Vanilla HTML/CSS/JS to start; consider Alpine.js or htmx if reactivity gets noisy. **No React/Vue unless complexity justifies it.** |
| CSS approach | Plain CSS with CSS variables for theming. No Tailwind/Bootstrap unless adopted deliberately later. |
| Tables | DataTables (jQuery) or AG-Grid Community for sortable/filterable grids — decide in Step 4. |
| Charts (Phase 5+) | Chart.js (lightweight) or D3 (if heavy customization needed). |
| Bridge | `pywebview`'s native JS↔Python API (`window.pywebview.api.*`). |
| Packaging | PyInstaller for Steam .exe; bundle WebView2 bootstrapper. |

### Trade-Off Acknowledgments

- You will be writing HTML/CSS/JS in addition to Python. This is real cost.
- Steam packaging is non-trivial; budget time for it in Phase 5.
- Performance ceiling for 1,696-row tables in HTML is fine but not infinite — Step 8 (data volume testing) will validate.

### When to Reconsider

Re-open this decision only if:
- pywebview proves unstable on Windows during Phase 5 prototyping (unlikely — it's mature).
- You decide later you want a non-Steam target (mobile, web-hosted) where the architecture would shift anyway.
- Performance testing in Step 8 reveals an HTML wall we can't engineer past.

---

## Out-of-Scope Frameworks (Decided Against)

- **Pygame**: wrong tool for data sims.
- **Tkinter**: insufficient Steam-tier polish.
- **Electron**: heavier than pywebview, harder to bundle, no significant gain for this use case.
- **Native React Native / Flutter**: out-of-ecosystem, would force language switch.

---

## Action Items Before Step 1

- [ ] David confirms HTML + pywebview as locked framework.
- [ ] Add `pywebview` to `requirements.txt` (do not install yet — happens at Phase 5 implementation start).
- [ ] Update `docs/ui/README.md` to mark Step 0 as Locked.
