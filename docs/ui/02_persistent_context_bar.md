# Step 2 — Persistent Context Bar

**Status**: Drafted, pending review.
**Purpose**: Define the always-visible header that anchors the player in time, team, and game state. This is the single most-rendered UI element in the game — it appears on every screen except the Main Menu.
**Inputs to this step**: CLAUDE.md ("every screen should show date/week, team, cap, season phase"), Step 1 IA (5 sections, mode-aware Front Office), Phase 3 `offseason_state` model.
**Output of this step**: Bar contents, layout, formatting rules, state-transition behavior, edge-case handling.

---

## Why a Persistent Context Bar Matters

Sim-game players spend hours per session navigating dozens of screens. Without a fixed anchor, they routinely lose track of: what week it is, what their cap looks like, what offseason phase they're in, and whether the game has saved. Every OOTP-style sim solves this with a persistent header — and the games that get the bar wrong (incomplete info, hidden behind menus) feel disorienting even when the underlying systems are good.

The bar is also the one piece of UI a returning player sees first when reopening a save. It must communicate "where you are" within five seconds.

---

## What the Bar Contains

### Tier 1 — Always Visible (every screen)

| Element | Purpose | Source |
|---|---|---|
| **Team Identity** | Confirm whose franchise this is | `team.name`, `team.abbreviation`, `team.colors` |
| **Date / Week** | Locate the player in time | `season_state.season_year`, `season_state.week_number` |
| **Phase Badge** | Indicate game mode (Reg/Playoffs/Offseason phase) | `season_state.phase`, `offseason_state.current_phase` |
| **Record** | Snapshot of season standing | `team_season_stats` (wins/losses) |
| **Cap Space** | Critical financial constraint, color-coded | `team.cap_space` (cached, per CLAUDE.md) |
| **Continue Button** | Primary action — advance week / sim next event | depends on phase |
| **Save Indicator** | Confirm autosave is working | last commit timestamp |
| **Section Nav** | Top-level navigation (5 sections + System) | from Step 1 IA |

### Tier 2 — Conditional

| Element | Shown when | Purpose |
|---|---|---|
| **Playoff Seed** | Postseason | Replace W-L with seed (e.g., "AFC #3 Seed") |
| **Offseason Deadline** | Offseason | Days remaining in current phase |
| **Notification Badge** | Pending decisions exist | Player satisfaction warnings, incoming trades, FA offers |
| **Coach Name** | Coach identity available | Coach identity is first-class per CLAUDE.md Phase 5 (dynasty) — independent of UI work |

### Deliberately Excluded

| Element | Why excluded |
|---|---|
| Live in-game score/clock | Game View screen (S-03) gets its own dedicated bar — see §"Edge Cases" |
| Player search | Step 3 will decide; likely a sidebar element, not header |
| News ticker | Lives on Team Dashboard as a card, not in the bar — too noisy persistent |
| Weather forecast | Game Preview screen only |
| Detailed cap breakdown | Cap Overview screen (T-07) only — bar shows the topline number |

---

## Layout Proposal

The bar is a **fixed top header**, full width, ~64px tall. The left sidebar from Step 1 sits below it, not next to it — the bar always wins for top real estate.

```
+------------------------------------------------------------------------------------------------+
| [LOGO] Chicago Bears  |  Week 8 · 2026 Reg Season  · 5-3  |  $23.4M cap  | [⓵] [Continue ▶] [⚙] |
+------------------------------------------------------------------------------------------------+
| Team | League | Schedule | Front Office | Dynasty                                              |
+------------------------------------------------------------------------------------------------+
|                                                                                                |
|                              Active screen content                                             |
|                                                                                                |
+------------------------------------------------------------------------------------------------+
```

**Zones, left-to-right:**

1. **Identity zone (left)** — team logo + name + abbreviation. Uses team colors as accent. Click returns to Team Dashboard (T-01).
2. **State zone (left-center)** — week / phase / record. Phase badge is the visual anchor; it changes color per game mode.
3. **Cap zone (center-right)** — single dollar figure, color-coded.
4. **Action zone (right)** — notifications bell with badge count, primary "Continue" button, settings gear.

The section nav (Team / League / etc.) sits as a secondary row immediately below — it is part of the persistent shell but conceptually a separate component, decided in Step 1.

---

## Format Conventions

These conventions apply only to the context bar. Step 4 will define the broader component vocabulary.

### Team Identity

```
[Logo 32×32]  Chicago Bears  CHI
```

- Logo on left, then full name, then 3-letter abbreviation in muted color.
- On screens narrower than the minimum 1280px target, drop full name and keep only abbreviation. (Steam desktop assumption — narrow case is rare.)

### Date / Week

| Game Phase | Format Example |
|---|---|
| Regular season | `Week 8 · 2026 Reg Season` |
| Playoffs (Wildcard) | `Wildcard · 2026 Playoffs` |
| Playoffs (Divisional) | `Divisional · 2026 Playoffs` |
| Conference Championship | `Conference · 2026 Playoffs` |
| Super Bowl | `Super Bowl · 2026 Season` |
| Offseason | `Offseason · Free Agency · Mar 14` |

Use the middle dot (`·`) as separator across the bar — not pipes, not hyphens. Consistent visual rhythm.

### Phase Badge

A small colored pill, immediately right of the date. Color is the most important signal because it conveys mode at a glance:

| Phase | Color | Label |
|---|---|---|
| Regular Season | Green `#22a06b` | `REG` |
| Playoffs | Red `#d4351c` | `PLAYOFFS` |
| Offseason: Review | Slate `#5b6b7c` | `REVIEW` |
| Offseason: Tags | Slate | `TAGS` |
| Offseason: Scouting | Blue `#1d6cc7` | `SCOUTING` |
| Offseason: Free Agency | Purple `#7c3aed` | `FA` |
| Offseason: Draft | Gold `#c89c1a` | `DRAFT` |
| Offseason: Camp | Slate | `CAMP` |

Hex values are placeholders — finalize in Step 4 (component vocabulary), where the full color palette is locked. The shape (pill, ~22px tall) and position (after date, before record) is locked here.

### Record

| State | Format |
|---|---|
| Regular season | `5-3` |
| Regular season w/ tie | `5-3-1` |
| Playoff seed | `AFC #3 Seed` (replaces W-L) |
| Eliminated from playoffs | `5-3 · Eliminated` (muted) |
| Offseason | hide record, show prior season summary: `2025: 11-6, Lost DIV` |

### Cap Space

Single dollar figure, abbreviated to one decimal of millions:

```
$23.4M cap
```

Color rules:

| Cap Level | Color |
|---|---|
| `> $20M` | Neutral (default text) |
| `$5M to $20M` | Yellow caution |
| `$0 to $5M` | Orange warning |
| `< $0` (over cap) | Red alert |

Click target: opens Salary Cap Overview (T-07). The whole cap zone is clickable.

### Continue Button

The single most-pressed button in the game. Must be visually dominant in the action zone.

| Phase | Button label |
|---|---|
| Regular season — game day | `Sim Game ▶` |
| Regular season — between games | `Advance Week ▶` |
| Postseason | `Sim Playoff Round ▶` |
| Offseason — phase complete | `Continue to [Next Phase] ▶` |
| Offseason — actions pending | `Continue ▶` (disabled if blockers exist) |
| Offseason — actions blocked | Show tooltip: "Resolve [N] pending decisions first" |

When disabled, the button shows the count of blockers and links to the most relevant screen via the notification bell.

### Save Indicator

Per CLAUDE.md, autosave happens on every committed action (SQLite transaction = save). The bar should reassure but not nag.

States:

| State | Visual |
|---|---|
| Saved | small ✓ icon + "Saved" text in muted gray, fades after 2s |
| Saving | spinner |
| Save failed | red banner replaces normal bar — manual intervention required |

Position: rightmost, before settings gear.

### Notification Bell

| State | Visual |
|---|---|
| No notifications | gray bell, no badge |
| 1+ pending | bell + badge with count (e.g., `3`) |
| Urgent (e.g., satisfaction crisis) | red badge instead of neutral |

Click opens a dropdown showing the pending items, each linking to the relevant screen (Satisfaction Detail, Trade Offers, etc.).

---

## State Transitions

The bar must visibly update on these events. Implementation note for Claude Code: these are the states the bar's view-model must subscribe to.

| Event | Bar response |
|---|---|
| Advance week | Date, record, cap (if contracts triggered) update |
| Game completes | Record updates immediately |
| Phase change (Reg → Playoff) | Badge color + label change with subtle transition |
| Offseason phase advances | Badge label changes, deadline counter resets |
| Player signed / cut / traded | Cap updates; notification may appear if cap goes red |
| Satisfaction event triggered | Notification badge increments |
| Save committed | "Saved" indicator pulses then fades |
| Save fails | Bar replaced by red error banner until resolved |

---

## Edge Cases

### Main Menu / Pre-Franchise (P-01 to P-05)
**No bar.** No franchise loaded → no context to show. These screens use a different shell.

### Live Game View (S-03)
The franchise context bar is **replaced** by a game-context bar showing score, clock, possession, down/distance. Returning to any other screen restores the franchise bar.

```
+------------------------------------------------------------------------------------------------+
| CHI 14 — 7 GB  |  Q3 8:42  |  CHI ball, 2nd & 7 at GB 38  |  [Pause] [Speed: 1x ▼] [Box Score] |
+------------------------------------------------------------------------------------------------+
```

Section nav remains hidden during live sim — exiting requires explicit "End Game" action.

### Draft Room (F-60)
Franchise bar stays visible (player still wants to see cap). A **secondary** draft-state bar appears below it showing: current pick, on-the-clock team, time remaining, your next pick number.

### Modals (F-43 Pitch Meeting, F-44 Offer Builder, etc.)
Bar remains fully visible behind/above the modal. Modals do not blank the shell.

### Loading / Long Operation
If sim takes more than ~500ms, replace the Continue button with a progress indicator showing what's being simulated ("Week 8 — Sim 14/16 games"). The rest of the bar stays interactive.

---

## Resolutions to Step 1 Open Questions

| Open Question | Resolution |
|---|---|
| Continue/Advance button placement | **In the bar's right action zone, on every screen.** Globally accessible. |
| Phase indicator visual | **Colored pill badge** next to the date. Color is the primary signal; label is secondary. |
| Save indicator placement | **Right side of bar, before settings gear.** Subtle when working, prominent only on failure. |

---

## Open Questions for Step 3 (Wireframes)

1. Visual weight of phase badge — pill vs underline vs background tint of the whole state zone?
2. Sidebar style — does the section nav row sit horizontally below the bar, or vertically in a left rail? (My current draft assumes horizontal; reconsider in Step 3.)
3. Notification dropdown anchoring — does it overlay or push content?
4. Accessibility: does color alone suffice for phase badge, or pair with icon/label always? (My recommendation: always pair, never rely on color alone.)

---

## Action Items Before Step 3

- [ ] David reviews bar contents — flag anything missing or oversized.
- [ ] Confirm Continue button label conventions match how he expects to play.
- [ ] Confirm phase badge color taxonomy (Reg/Playoffs/each offseason phase).
- [ ] Confirm replacement bar pattern for live game view (S-03).
