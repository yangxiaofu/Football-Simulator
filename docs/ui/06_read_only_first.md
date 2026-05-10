# Step 6 — Read-Only First Discipline

**Status**: Drafted, pending review.
**Purpose**: Formalize the development discipline for Phase 5 — every screen ships in a read-only state before any mutation is wired. This catches data-shape problems early, produces a testable "viewer build" mid-Phase-5, and prevents UI bugs from corrupting save files.
**Inputs to this step**: Step 5 build order, CLAUDE.md rule "never build UI for a system that isn't working," Phases 0-3 complete (live data exists in `test_franchise.db`).
**Output of this step**: Per-milestone enablement plan, error-state assignments, "viewer build" definition.

---

## The Rule

> **Render every screen with real data, buttons disabled, before wiring any action.**

This is one rule with three implications:

1. **Real data, not mock.** Phases 0-3 are complete; `test_franchise.db` contains 32 teams, 1,696 players, multi-season stats. Build presenters against this from day one. Mock data hides data-shape mismatches that only surface against the real schema.

2. **Buttons disabled, not absent.** Render the Continue button, Cut button, Sign Offer button — all of them — but with disabled state and tooltip explaining "Action wiring pending — Milestone 5.X." This forces the visual layout to be honest about what the screen will eventually do.

3. **Action wiring follows a deliberate order**, not "whatever comes next." See §3.

---

## Why This Discipline Matters

Three failure modes this prevents:

| Failure | What goes wrong without the rule |
|---|---|
| **Data-shape drift** | Presenter assumes `player.scheme_fit` is a number; it's actually an enum. Caught at first render with real data, expensive if caught after wiring 6 screens to a wrong shape. |
| **Layout dishonesty** | Screen looks fine in the wireframe, but the real Roster has 53 rows of varying name lengths and the column widths are wrong. Only real-data rendering surfaces this. |
| **Save-file corruption** | A buggy mutation (wrong cap math, double-write) corrupts the franchise save. A disabled button can't corrupt data. Read-only first means save files stay safe through 80% of Phase 5. |

The cost of the discipline is low: ~10% extra work to add disabled-state styling and tooltips. The benefit is high.

---

## Resolutions to Step 5 Open Questions

| Question | Resolution |
|---|---|
| Mock data first, or live data from day one? | **Live data, from Milestone 5.1.** `test_franchise.db` exists and is populated. Mock data is rejected — it diverges from real shape. |
| When does the Continue button get enabled? | **Milestone 5.5.** Schedule + Game Recap is when the in-season loop becomes end-to-end. Before that, Continue is disabled with tooltip "In-season loop wiring pending." |
| Where do error states appear per screen? | **Layered**: toast for transient (save confirmation), banner for persistent (cap red, satisfaction crisis), modal for blocking (save corrupted, action requires confirmation). Locked in §4. |

---

## 1. Per-Milestone Read-Only / Action Enablement Plan

Each milestone from Step 5 is split into a render phase (read-only) and a wire phase (actions enabled). For most milestones these are sequential within the same build session; for complex milestones they're separate prompts in Claude Code.

| Milestone | Render Phase (Read-Only) | Wire Phase (Actions Enabled) |
|---|---|---|
| **5.1 Window + Shell** | Shell renders with placeholder context bar | Hash-based router navigates between empty content panels |
| **5.2 Dashboard** | All cards render with live data from `test_franchise.db` | Card click → navigate to relevant screen (no mutations yet) |
| **5.3 Roster + Player Card** | Both screens render fully populated | Right-click context menu actions disabled with tooltip |
| **5.4 League Section** | Standings, Leaders, Transactions all render | Click-through navigation only |
| **5.5 Schedule + Game Recap** | Schedule renders all 17 weeks, past games show recaps | **Continue button enabled** for `do_advance_week` and `do_sim_game`. First mutations live. |
| **5.6 FO Hub Mode-Aware** | Hub renders correctly across all 7 game phases | Phase advancement still triggered via CLI; UI button enables in 5.6.b |
| **5.7 Free Agency** | FA Market, Player Card, Pitch Meeting modal all render | `do_sign_free_agent` wired; counter-offer flow live |
| **5.8 Trades + Scouting** | Trade Builder + Scouting Hub render | `do_propose_trade`, `do_assign_scout` wired |
| **5.9 Draft Room** | Three-column layout renders during simulated draft | `do_draft_pick` wired; auto-advance enabled |
| **5.10 Recap Polish** | Recap moments rendered with generated narrative | No new mutations; polish only |
| **5.11 Dynasty** | History screens render | Read-only by definition (history doesn't mutate) |
| **5.12 Settings + Packaging** | Settings UI renders | `do_save_settings`, save/load flows wired |

---

## 2. The "Viewer Build" Milestone

Between Milestone 5.4 and 5.5, the project hits a meaningful checkpoint: **every read-only league/team screen works**. This is the "viewer build" — a fully navigable read-only UI where the user can browse rosters, standings, player cards, and league data, but cannot advance the season.

**Why this checkpoint matters:**

- **Playtestable.** A friend can install the viewer build, browse the test franchise, and react to navigation friction. Catches IA mistakes before they're locked into 30 more screens.
- **Steam packaging spike.** Test PyInstaller + WebView2 packaging on a known-good read-only build, separately from action-wiring complexity.
- **Confidence forcing function.** If the viewer build feels boring or hard to navigate, that's the IA telling you something. Better to discover at Milestone 5.4 than at 5.10.

**Recommended action**: After Milestone 5.4 completes, take one prompt to:
- Run the viewer build through 5 user flows from Step 1 (just the read-only ones).
- Take screenshots of each primary screen.
- Capture any IA, layout, or component surprises in `docs/ui/_viewer_build_notes.md`.
- Decide whether to proceed to 5.5 or course-correct earlier docs.

This is the only mid-walkthrough deliverable in the plan. It's small, but it de-risks the back half of Phase 5.

---

## 3. Action Enablement Order (Most-Leveraged First)

Within Milestones 5.5–5.9, mutations are wired in this order:

| Order | Action | Milestone | Why first |
|---|---|---|---|
| 1 | `do_advance_week` | 5.5 | The single most-used action in the game. Unblocks every other in-season test. |
| 2 | `do_sim_game` | 5.5 | Pairs with advance-week; tests the Game View → Recap flow. |
| 3 | `do_sign_free_agent` | 5.7 | Highest-leverage offseason mutation. Tests presenter assumptions on contracts. |
| 4 | `do_cut_player` | 5.7 | Tests dead-cap calculation through the UI for the first time. |
| 5 | `do_restructure_contract` | 5.7 | Tests cap recalculation post-mutation (per CLAUDE.md cap-cache rule). |
| 6 | `do_propose_trade` | 5.8 | Tests AI evaluation surface. |
| 7 | `do_draft_pick` | 5.9 | Tests Draft Room three-pane reactivity. |
| 8 | `do_assign_scout` | 5.8 | Lower urgency — read-only scouting works without it. |

Anything not on this list (rare actions like `do_release_practice_squad`, `do_franchise_tag`) gets wired opportunistically as the surrounding screen lands. No need to schedule rare mutations explicitly.

---

## 4. Error State Assignment per Surface

Locked from Step 5 open question. Maps Step 4 component vocabulary to specific surfaces.

| Surface | Component | Examples |
|---|---|---|
| **Toast** | Bottom-right transient | "Saved", "Player signed", "Trade accepted", "Auto-save complete" |
| **Banner** (alert) | Top of content area | "Cap is over by $2.1M — fix before advancing week", "Star player satisfaction critical", "Save file conflict detected" |
| **Modal** | Centered overlay | "Cut M. Olsen? Dead cap impact: $4M. [Confirm] [Cancel]", "Save file is corrupted — please load a backup", "Quit without saving?" |
| **Inline field error** | Below input | "Offer below market minimum — increase APY", "Contract years exceed allowed maximum" |
| **Disabled button + tooltip** | Action affordance | "Continue ▶ — disabled: 3 pending decisions" |

**Rules:**

1. **Never two surfaces for the same error.** Pick one. A cap-red event surfaces in a single banner, not in a banner *and* a toast *and* a modal.
2. **Modals only for irreversible/blocking actions.** Use sparingly — modal fatigue is real.
3. **Toasts auto-dismiss in 3.5s.** Anything important enough to need acknowledgment gets a banner or modal.
4. **Banners are dismissible** but reappear if the underlying condition persists (cap red banner reappears on next screen until the cap is fixed).

---

## 5. What "Read-Only" Specifically Allows and Disallows

| Allowed (does not mutate save) | Disallowed (mutates save) |
|---|---|
| Reading from any DB query | Writing to any DB table |
| Computing presenter view-models | Triggering simulation loops |
| Hovering, scrolling, sorting, filtering | Submitting offers, picks, trades |
| Opening modals (visual only) | Confirming actions inside modals |
| Switching between tabs and screens | Advancing week, simulating games |
| Right-clicking for context menus (menu opens, items disabled) | Selecting any context-menu item that would mutate |

**Implementation hint**: a single Python decorator `@requires_action_milestone(5.5)` on `do_*` methods can centrally enforce this. Methods raise a structured error if called before their milestone is hit, which the JS layer translates to the disabled-button tooltip. This means the Python API and the UI stay in sync without manual coordination.

---

## 6. Observability During Read-Only Phase

While building screens read-only, log every presenter call to a dev-only logfile:

```
2026-05-09 14:33:12 · presenter:roster · team_id=1 · 53 rows · 28ms
2026-05-09 14:33:14 · presenter:player · player_id=421 · 12ms
2026-05-09 14:33:18 · presenter:standings · view=division · 32 rows · 8ms
```

Reasons:
- **Performance baseline.** Step 8 will validate against 1,696-row tables; having Phase 5 timing data from day one makes regression detection easy.
- **Frequency baseline.** Tells you which presenters are hot paths and worth caching.
- **Schema drift detection.** A presenter that suddenly returns `KeyError` after a DB migration shows up immediately.

Implementation: simple wrapper in `src/ui/presenters/__init__.py` that times each `build()` call.

---

## 7. Out of Scope for Read-Only Phase

These do not get built in read-only mode — they require mutations by definition:

- Save/Load flow (write to disk).
- Settings persistence (write to config).
- Game sim (writes box scores, plays).
- All of Milestones 5.5+.

For Milestones 5.1-5.4, none of these are touched. The viewer build at the end of 5.4 explicitly does not include them.

---

## 8. Open Questions for Step 7

1. The presenter layer needs an explicit interface contract — what shape do view-models take? Step 7 owns this.
2. Should presenters cache results, or is fresh-on-every-call fine? Step 7 will resolve.
3. How are presenters tested in isolation from the UI? Unit tests on the view-model output, with golden files? Step 7.

---

## Action Items Before Step 7

- [ ] David confirms the read-only-first discipline is workable for his Claude Code workflow (per his memory: sequential prompts with test commands).
- [ ] Confirm the viewer build checkpoint after Milestone 5.4 — worth the half-prompt of overhead?
- [ ] Confirm action enablement order — is `do_advance_week` truly the most-leveraged first action, or would something else surface bigger problems?
- [ ] Confirm the `@requires_action_milestone` decorator pattern as the enforcement mechanism, or prefer a different gate?
