# Phase 5 Kickoff — Milestone 5.1 Hand-Off Prompt

**Purpose**: Self-contained prompt for the first Claude Code (terminal) session of Phase 5. Copy the section under `--- PROMPT BELOW ---` into Claude Code as-is.

**Scope**: Milestone 5.1 only — Window + Shell. Subsequent milestones (5.2 Dashboard, 5.3 Roster + Player Card, etc.) get their own prompts following the same pattern.

**Model recommendation**: **Claude Sonnet 5.6** — handles multi-file scaffolding well, fast iteration, sufficient for this scope. Use Claude Opus 5.6 only if 5.1 stalls on architectural reasoning, which is unlikely given the design docs already exist.

**Planning mode**: **ON.** First milestone of a phase — plan the file layout, confirm the bridge contract reads cleanly, flag any gaps in the design docs before writing code.

---

## How to Use This File

1. Open Claude Code in the terminal at the project root: `cd /Users/fudong/Library/CloudStorage/OneDrive-Personal/00\ Projects/Football\ Simulator`
2. Start a Claude Code session with the model and planning mode noted above.
3. Copy the prompt below into the session.
4. After Milestone 5.1 closes successfully (test command passes), draft the prompt for Milestone 5.2 by referencing `docs/ui/05_framework_implementation_plan.md` §6 and `docs/ui/01_information_architecture.md` for the Team Dashboard (T-01) screen ID.

---

## --- PROMPT BELOW ---

I'm starting Phase 5 of the Football Simulator project. Phases 0–3 are complete (foundation, simulation engine, full season, offseason). Phase 5 builds the UI per the design-of-record locked in `docs/ui/`.

**Milestone 5.1 — Window + Shell.**

Read these documents first, in this order, before writing any code:
1. `CLAUDE.md` (project conventions, layer boundaries, code quality rules)
2. `docs/ui/README.md` (index of the 9 design docs)
3. `docs/ui/05_framework_implementation_plan.md` (§3 folder structure, §4 bridge contract, §6 Milestone 5.1 specifically, §7 dev workflow)
4. `docs/ui/03_wireframes.md` (universal shell template — context bar + section tabs + sub-nav rail + content area)
5. `docs/ui/02_persistent_context_bar.md` (context bar contents and behavior)
6. `docs/ui/04_component_vocabulary.md` (design tokens, typography, spacing — needed for `tokens.css` and `components.css`)

After reading, draft a plan covering:
- Files to create (and their paths under `src/ui/`)
- The `Api` stub method signature
- The router pattern (hash-based, ~30 lines)
- Token list to extract from Step 4 into `tokens.css`
- Open questions or design-doc gaps (none expected, but flag if any)

Wait for my approval before writing code.

### Scope (Milestone 5.1 only — do NOT exceed)

Build the empty shell. No live data. No screen content. The window opens, the shell renders, the router responds to hash changes by clearing/re-rendering an empty content panel. Subsequent milestones (5.2 Dashboard, 5.3 Roster) wire actual screens.

### Deliverables

Per `docs/ui/05_framework_implementation_plan.md` §3:

```
src/ui/
├── __init__.py                       (already exists)
├── api.py                            ← NEW: pywebview Api class with one stub method
├── window.py                         ← NEW: pywebview window entry point
├── presenters/
│   ├── __init__.py                   ← NEW: empty (populated in 5.2)
│   ├── formatters.py                 ← NEW: letter_grade(), money_m(), short_name(), date_short(), week_label(), record() (per Step 7 §2)
│   └── types.py                      ← NEW: empty TypedDict module (populated in 5.2)
├── static/
│   ├── index.html                    ← NEW: universal shell with context bar (placeholder data) + section tabs + sub-nav rail + content area
│   ├── css/
│   │   ├── tokens.css                ← NEW: all Step 4 design tokens as CSS custom properties
│   │   ├── reset.css                 ← NEW: minimal CSS reset
│   │   ├── components.css            ← NEW: 10 components from Step 4 §5 (Button, Badge, Card, Table, Tabs, Modal, Toast, Form Inputs, Alert, Tooltip)
│   │   └── screens.css               ← NEW: empty for now (per-screen overrides start in 5.2)
│   └── js/
│       ├── alpine.min.js             ← NEW: vendor Alpine.js v3 latest (~15KB)
│       ├── shell.js                  ← NEW: hash-based router, context bar wiring, top nav, sub-nav rail
│       ├── api.js                    ← NEW: thin promise wrapper over window.pywebview.api
│       └── format.js                 ← NEW: empty for now (Step 7 says most formatting is presenter-side)
```

### Required: Api Stub

`src/ui/api.py` exposes one method for this milestone:

```python
def get_app_info(self) -> dict:
    """Returns {name, version, save_path, current_season, current_week}."""
```

This validates the bridge works end-to-end. The shell renders these values in the context bar at startup.

### Required: Router Behavior

Hash-based router in `shell.js`. Routes for this milestone (just route, render placeholder):
- `#/team/dashboard` → renders empty content panel labeled "Team Dashboard (5.2)"
- `#/team/roster` → "Roster (5.3)"
- `#/league/standings` → "Standings (5.4)"
- `#/schedule` → "Schedule (5.5)"
- `#/front-office` → "Front Office (5.6)"
- `#/dynasty` → "Dynasty (5.11)"
- Default (no hash) → `#/team/dashboard`

Section tab clicks update the URL hash; the router responds.

### Constraints (per CLAUDE.md and Step 7 §8)

- `src/ui/api.py` and `src/ui/window.py` are the **only** Python files in `src/ui/` that touch pywebview.
- No `import sqlite3` anywhere in `src/ui/`. Database access goes through `src/db/queries.py` (which `Api` will call into starting in 5.2).
- No magic numbers. Any tuning value (window width, min size, etc.) added to `src/utils/constants.py` first.
- Continue button in the context bar is rendered but **disabled with tooltip** "Action wiring pending — Milestone 5.5" (per Step 6 §1).
- Use Unicode glyphs for icons (✓ ⚕ ⚠ 🔔 ⚙ ▶ ▾ ▴ ×). No icon library at v1 (per Step 4 §6).

### Test Command

After implementation, the milestone is complete when this command opens a window with the empty shell rendering correctly:

```bash
python -m src.ui.window saves/test_franchise.db --debug
```

Verification:
- Window opens at 1440×900, minimum size 1280×720.
- Context bar shows team name (Chicago Bears or whichever team the test save uses), week, year, and `$XX.XM cap` from `Api.get_app_info()`.
- Phase badge renders with placeholder color (REG green).
- Section tabs (Team / League / Schedule / Front Office / Dynasty) are visible and clickable.
- Clicking each tab updates the URL hash and the content panel shows the placeholder text.
- Continue button is rendered, disabled, with tooltip on hover.
- DevTools opens on `--debug` flag.

Do not close this milestone until the test command passes cleanly.

### Out of Scope for 5.1 (defer to later milestones)

- Any screen content (Dashboard cards, roster table, etc.) — 5.2 onward.
- Live game view bar replacement — 5.5.
- Modal component implementation beyond CSS — first usage in 5.7.
- Notification dropdown beyond the bell icon — 5.7.
- Save/load UI — 5.12.
- Steam packaging (PyInstaller, WebView2) — 5.12.

### When Complete

Update `CLAUDE.md` Phase 5 checklist:
- Mark Milestone 5.1 deliverables as `[x]`
- Add the test command to the "Phase 5 Build Status" section

Then we close this Claude Code session and start a new one for Milestone 5.2.

## --- PROMPT ENDS ---

---

## After Milestone 5.1 Closes — Pattern for Subsequent Milestones

Each milestone gets its own prompt following this template:

1. **Header**: model recommendation (Sonnet 5.6 default, Opus 5.6 if architectural complexity is high), planning mode (ON for first prompt of complex milestones, OFF for clear-scope work).
2. **Reading list**: which `docs/ui/*.md` files to read for that milestone's scope.
3. **Scope statement**: explicit "this milestone only — do not exceed."
4. **Deliverables**: file list with paths.
5. **Constraints**: relevant CLAUDE.md rules + Step 7 §8 layer boundaries.
6. **Test command**: ends every prompt (per David's sequential-builds memory).
7. **Out of scope**: what defers to later milestones.

Subsequent milestones in priority order (per Step 5 §6):
- **5.2 Team Dashboard** — first live-data screen. Reads: Steps 1, 3 (T-01), 4, 7.
- **5.3 Roster + Player Card** — proves Pattern A and Pattern B. Reads: Steps 3 (T-02, T-05), 4, 7.
- **5.4 League Section** — Standings + Leaders + Transactions, all reuse Pattern A. **Viewer Build checkpoint at end** (Step 6 §2).
- **5.5 Schedule + Game Recap** — first mutations enabled (`do_advance_week`, `do_sim_game`). First Pattern D recap moment.
- **5.6 FO Hub Mode-Aware** — validates phase-driven content swapping.
- **5.7 Free Agency** — first complex modal stack.
- **5.8 Trades + Scouting** — Trade Builder is the most complex form.
- **5.9 Draft Room** — most complex screen, Pattern E.
- **5.10 Recap Polish** — Pattern D ship-it pass on all 9 recap moments.
- **5.11 Dynasty** — read-only history.
- **5.12 Settings + Steam Packaging** — closes Phase 5.

After 5.12, Phase 5 is complete and the v1 UI is shippable subject to the pre-launch performance gate (Step 8 §7).
