# Step 4 — Component Vocabulary

**Status**: Drafted, pending review.
**Purpose**: Lock the design system. Define every reusable building block — colors, typography, formats, components — so Claude Code can build a small library once and reuse it across ~64 screens.
**Inputs to this step**: Step 3 wireframes (which patterns appear repeatedly), Step 2 phase badge palette draft.
**Output of this step**: Color tokens, typography scale, format conventions, component specs, empty/loading state rules.

**Implementation note**: All values here are intended to become CSS custom properties (`--color-bg`, `--space-3`, etc.) in the eventual stylesheet. Keep them centralized so theme changes happen in one file.

---

## Theme Direction

**Default theme: dark.** Sim-game players run hours-long sessions, often at night, on data-heavy screens. Dark backgrounds reduce eye strain and let colored elements (letter grades, phase badges) carry signal more vividly. OOTP and Football Manager both default dark for the same reason.

**Light theme**: deferred. Build dark first, design tokens with theme swap in mind, ship light theme post-launch if requested. Step 4 commits to dark only.

---

## 1. Color Palette

### Surface & Text (Neutral)

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#0f1419` | App background |
| `--bg-surface` | `#1a2027` | Cards, table rows (default) |
| `--bg-elevated` | `#232b34` | Modals, dropdowns, hover states |
| `--bg-hover` | `#2d3640` | Row hover, button hover |
| `--border` | `#2d3640` | Card borders, table dividers |
| `--border-strong` | `#3d4854` | Active borders, focused inputs |
| `--text-primary` | `#e6e9ed` | Body text, headers |
| `--text-secondary` | `#a0a8b1` | Supporting labels, helper text |
| `--text-muted` | `#6b727a` | Disabled, placeholder, footnote |

### Semantic Colors

| Token | Hex | Usage |
|---|---|---|
| `--color-success` | `#22a06b` | Wins, positive trends, "Saved" indicator |
| `--color-warning` | `#d4a017` | Cap caution ($5–20M), satisfaction warnings |
| `--color-danger` | `#d4351c` | Cap red, save failure, urgent alerts |
| `--color-info` | `#1d6cc7` | Informational banners, scouting notes |
| `--color-purple` | `#7c3aed` | Free agency phase accent |
| `--color-gold` | `#c89c1a` | Draft phase accent, awards |
| `--color-slate` | `#5b6b7c` | Neutral phase accents (Tags/Camp/Review) |

### Phase Badge Colors (locked from Step 2)

| Phase | Background | Text |
|---|---|---|
| `REG` | `--color-success` | white |
| `PLAYOFFS` | `--color-danger` | white |
| `REVIEW` | `--color-slate` | white |
| `TAGS` | `--color-slate` | white |
| `SCOUTING` | `--color-info` | white |
| `FA` | `--color-purple` | white |
| `DRAFT` | `--color-gold` | `#1a1a1a` (dark on gold for contrast) |
| `CAMP` | `--color-slate` | white |

### Letter Grade Colors

The most-rendered colored element in the game. Must be scannable at a glance across 53-row rosters and 250-row draft classes.

| Grade | Background | Text | Approximate hex |
|---|---|---|---|
| A+ | `--grade-elite` | white | `#0f8a4f` (deep green) |
| A | `--grade-elite-2` | white | `#22a06b` (green) |
| A- | `--grade-elite-3` | white | `#3eb87f` (light green) |
| B+ | `--grade-good` | white | `#2a7ab8` (steel blue) |
| B | `--grade-good-2` | white | `#3a8fcc` (blue) |
| B- | `--grade-good-3` | white | `#5ba3d6` (lighter blue) |
| C+ | `--grade-avg` | `#1a1a1a` | `#e8b94a` (amber, dark text for contrast) |
| C | `--grade-avg-2` | `#1a1a1a` | `#d4a017` (yellow) |
| C- | `--grade-avg-3` | `#1a1a1a` | `#b8881a` (dark amber) |
| D+ | `--grade-poor` | white | `#d68c3a` (orange) |
| D | `--grade-poor-2` | white | `#c4731a` (dark orange) |
| F | `--grade-fail` | white | `#a3261c` (deep red) |

**Render as**: fixed-width pill, monospace font, 32px wide × 22px tall, centered text, 4px corner radius. Critical: width must be fixed so letter grades align in vertical columns across table rows.

### Team Accent (per-franchise)

Each franchise gets the user's team colors (`team.primary_color`, `team.secondary_color`) applied as accent in:

| Where | Effect |
|---|---|
| Active section tab | Underline in primary color |
| Logo border (context bar) | 2px primary border |
| Hover on team-name links | Primary color text |
| Loading spinner | Primary color stroke |
| Section heading underlines | Subtle 1px primary tint |

**Never used for**: backgrounds (would conflict with neutral surfaces), body text, semantic states (a green-team's wins shouldn't render as their team color — they render as `--color-success`).

**Fallback**: if `team.primary_color` is too dark to be visible on `--bg-base` (luminance check), use `team.secondary_color`. Lock the rule, implement the check in Phase 5.

---

## 2. Typography

### Font Stack

| Use | Stack |
|---|---|
| UI body / labels | `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Helvetica Neue", sans-serif` |
| Tabular numerics (tables, stats) | `"SF Mono", "Cascadia Code", Consolas, "Roboto Mono", monospace` |
| Display (recap headlines) | Same as UI body, but heavier weight (700) and larger size |

System fonts chosen for: zero install cost, OS-native rendering, full localization support, and the practical reality that no one is buying a Steam sim for its custom typeface.

### Type Scale

| Token | Size | Weight | Line height | Usage |
|---|---|---|---|---|
| `--text-display` | 32px | 700 | 1.2 | Recap moment headlines, championship reveals |
| `--text-h1` | 24px | 700 | 1.3 | Screen titles |
| `--text-h2` | 20px | 600 | 1.3 | Section headers within a screen |
| `--text-h3` | 16px | 600 | 1.4 | Card titles, sub-section labels |
| `--text-body` | 14px | 400 | 1.5 | Default body text |
| `--text-small` | 12px | 400 | 1.4 | Secondary info, metadata |
| `--text-micro` | 11px | 500 | 1.3 | Uppercase labels, table column headers (with letter-spacing 0.04em) |

### Tabular Numerics Rule

All numeric columns in tables (cap hits, stats, ages, ratings) **must** use the monospace stack and `font-variant-numeric: tabular-nums`. Without this, "1,234" and "9,876" misalign in columns and the table becomes unscannable. This is non-negotiable for a sim-game UI.

---

## 3. Spacing Scale

8px grid. Stick to these values; do not introduce arbitrary spacing.

| Token | Value | Usage |
|---|---|---|
| `--space-1` | 4px | Tight inline gaps (icon + text) |
| `--space-2` | 8px | Default gap inside compact components |
| `--space-3` | 12px | Form fields, table cell padding |
| `--space-4` | 16px | Default card padding, section gaps |
| `--space-5` | 24px | Major section breaks |
| `--space-6` | 32px | Page margins, hero zone padding |
| `--space-7` | 48px | Recap moment vertical rhythm |

### Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 2px | Letter grade pills, phase badges |
| `--radius-md` | 4px | Buttons, inputs, cards |
| `--radius-lg` | 8px | Modals, hero zones |

### Elevation (subtle in dark theme — use border + bg shift, not heavy shadows)

| Token | Style |
|---|---|
| `--elev-0` | No shadow. Default surface. |
| `--elev-1` | `box-shadow: 0 1px 2px rgba(0,0,0,0.3)`. Hover state. |
| `--elev-2` | `box-shadow: 0 4px 12px rgba(0,0,0,0.4)`. Modals, dropdowns. |

---

## 4. Format Conventions

### Currency

| Context | Format | Example |
|---|---|---|
| Cap space (top bar) | `$XX.XM cap` | `$23.4M cap` |
| Contract APY | `$X.XM/yr` | `$11.5M/yr` |
| Contract total | `Xyr · $XXM total` | `4yr · $46M total` |
| Cap hit (year-by-year) | `$X.XM` | `$8.2M` |
| Signing bonus | `$X.XM bonus` | `$5M bonus` |
| Dead cap | `$X.XM dead` | `$24M dead` |
| Penny precision | Never used. Always millions, one decimal. | |
| Zero | `$0` (not `$0.0M`) | |
| Negative (over cap) | Prefix minus, red color: `−$2.1M cap` | |

### Letter Grades

Always render as colored pill (see §1). Never expose raw `true_overall` outside the engine. UI receives a string `"A+"`, `"B-"`, `"F"` from the presenter layer (Step 7).

### Dates

| Context | Format | Example |
|---|---|---|
| Schedule rows | `MMM D` | `Sep 7` |
| News feed (recent) | Relative | `2 days ago` |
| News feed (older) | `MMM D` | `Sep 7` |
| Game time stamps | `Q# MM:SS` | `Q3 08:42` |
| Save indicator | `H:MM AM/PM` | `3:42 PM` |
| Date inputs (rare) | ISO 8601 | `2026-09-07` |
| Season year | 4-digit | `2026` |
| Week | `Wk N` | `Wk 8` |

### Numbers

| Context | Format | Example |
|---|---|---|
| Stats (yards, attempts) | Integer with comma | `1,284` |
| Percentages | One decimal | `65.3%` |
| Ratings (display) | Letter grade pill (never raw) | `A+` |
| Pick numbers | `R# #N` | `R2 #51` |
| Records | `W-L` or `W-L-T` | `5-3` or `5-3-1` |
| Streaks | `W#` or `L#` | `W2` |

### Player Identity

| Context | Format | Example |
|---|---|---|
| First mention in a screen | `First Last · POS` | `Jordan Kim · QB` |
| Subsequent mentions / table rows | `F. Last` | `J. Kim` |
| Box score listings | `F. Last` (always abbreviated) | |
| Headers / cards | Full name | `Jordan Kim` |

---

## 5. Component Library

These ten components are referenced by every wireframe in Step 3. Build once, use everywhere.

### Button

| Variant | Use | Example |
|---|---|---|
| `primary` | Main CTA on a screen | `Sim Game ▶` |
| `secondary` | Supporting action | `View Box Score` |
| `ghost` | Tertiary, low-weight | `Cancel` |
| `destructive` | Cuts, releases, irreversible | `Cut Player` |
| `icon` | Compact icon-only | gear, bell, search |

States: default / hover / active / disabled / loading. Disabled buttons must show why (tooltip with blocker reason — see Continue button rules in Step 2).

### Badge

Letter grade badges and phase badges share the same component with different color tokens. Other uses: status flags ("INJURED", "TRADE BLOCK", "ROOKIE").

| Variant | Style |
|---|---|
| `grade` | Fixed 32×22, monospace, color from §1 grade map |
| `phase` | Auto-width, color from §1 phase map |
| `status` | Auto-width, semantic color, uppercase text-micro |

### Card

Standard surface for grouping content. Used in Hub patterns (C) and as the building block for Dashboard tiles.

```
┌─ Card ─────────────────┐
│ Title (text-h3)        │
│ ────────────────────── │  ← optional divider
│ Body content           │
│                        │
│ [Optional CTA button]  │
└────────────────────────┘
```

Padding: `--space-4`. Border: 1px `--border`. Background: `--bg-surface`. Hover (when clickable): elevate to `--elev-1` and shift border to `--border-strong`.

### Table

The most-used component in the game. Spec must be tight.

- **Header row**: text-micro uppercase, `--text-secondary` color, sortable on click (▲▼ indicator).
- **Body rows**: text-body, `--text-primary`, alternating background optional (some screens look better without zebra — decide per-screen).
- **Row hover**: `--bg-hover`.
- **Row click**: opens detail (per Step 3 Pattern A).
- **Numeric columns**: right-aligned, monospace, tabular-nums.
- **Text columns**: left-aligned, system font.
- **Status icons**: rightmost column, fixed width (24px each).
- **Sticky header** when table scrolls.
- **Empty state**: see §7.

For the v1 implementation, vanilla HTML `<table>` with custom CSS. If Step 8 reveals performance issues with 1,696-row stat browser, swap in DataTables or AG-Grid Community — defer that decision to Phase 5.

### Tab Navigation

Used inside detail screens (Pattern B) and within sub-sections.

```
[Overview] Stats   Contract   Satisfaction   History
─────────
```

- Active tab: underline in team accent color, text in `--text-primary`.
- Inactive tab: text in `--text-secondary`, no underline.
- Hover: text shifts to `--text-primary`.
- Tab content area below has 1px top border in `--border`.

### Modal

```
┌─ Modal Title ─────────────── × ┐
│                                │
│ Modal body                     │
│                                │
│         [Cancel] [Confirm]     │
└────────────────────────────────┘
```

- Centered overlay over a `rgba(0,0,0,0.6)` scrim.
- Background: `--bg-elevated`.
- Min width 480px, max width 720px (decision modals like Pitch Meeting can be wider — up to 960px).
- Always keyboard-dismissible (Esc).
- Never blocks the persistent context bar — bar stays interactive (per Step 2).
- Action row: ghost cancel on left, primary confirm on right.

### Toast Notification

Transient confirmations: "Player signed", "Trade accepted", "Auto-saved".

- Bottom-right corner.
- Auto-dismisses after 3.5 seconds.
- Icon + label only — never include actions in toasts. (Use modals for decisions.)
- Stack vertically up to 3; older toasts dismiss when the 4th appears.

### Form Inputs

| Component | Spec |
|---|---|
| Text input | 36px tall, `--space-3` padding, `--border` 1px, focus = `--border-strong` |
| Search input | Same as text, with leading magnifier icon |
| Dropdown | Same height, trailing chevron, opens overlay below (matches modal styling) |
| Filter pill | Compact, removable on click, used for active filter chips |
| Checkbox | 18×18, custom styled (default browser is ugly) |
| Radio | Same dimensions as checkbox |

Forms are minimal in this game — most actions are buttons in modals, not multi-field forms. Don't over-build form components.

### Alert / Banner

Inline info/warning/error blocks. Used on screens where context-bar notifications aren't enough.

| Variant | Color | Use |
|---|---|---|
| `info` | `--color-info` | Scouting tips, gameplay hints |
| `warning` | `--color-warning` | Satisfaction warnings, cap caution |
| `danger` | `--color-danger` | Cap red, save failure |
| `success` | `--color-success` | Confirmation of major action |

Layout: icon + label + optional description + optional CTA. Dismissible with × on the right.

### Tooltip

Hover-triggered, max 280px wide, `--bg-elevated` background, 200ms delay before appearing. Used to explain disabled buttons (per Step 2 Continue button rule), letter grade meanings, and stat abbreviations.

---

## 6. Status Icons

Single-character or small SVG icons used consistently across screens. Lock these now so Claude Code uses the same icon for the same meaning everywhere.

| Icon | Meaning | Where used |
|---|---|---|
| ⚕ | Injury | Roster row, Player Card, Game Recap |
| ⚠ | Warning (satisfaction, cap) | Roster row, Dashboard alerts |
| 🔄 | On trade block | Roster row, Trade Hub |
| 🔒 | Locked / cannot modify | Tagged players, capped fields |
| ★ | Pro Bowl / award winner | Player Card history, Dashboard top performers |
| 🔔 | Notification bell | Context bar |
| ✓ | Saved / completed | Save indicator, completed offseason phases |
| ✏ | Pending decision (action required) | Dashboard alerts, sub-nav phase indicators |
| ▶ | Continue / advance | Continue button, replay actions |
| ▾ ▴ | Sort indicators | Table headers |
| × | Close / dismiss | Modal close, toast dismiss, filter pill remove |

**For Phase 5 implementation**: prefer Unicode glyphs where they render consistently across Windows/Mac/Linux WebView2 stacks. Replace with SVG icons (Lucide or Phosphor library) only if Unicode rendering is inconsistent in testing.

---

## 7. Empty States

Every list, table, and feed needs a designed empty state — not a blank space.

**Template**: icon (subtle, `--text-muted` color) → headline (text-body, `--text-secondary`) → optional helper line → optional CTA button.

| Screen | Empty state |
|---|---|
| Notifications dropdown | ✓ "No notifications" / "You're all caught up." |
| Trade Block | "No players on trade block" / "Right-click any roster player to add." |
| FA Watchlist | "No players watched" / `[Browse FA Market]` |
| Active Negotiations (FA Hub) | "No active negotiations" / "Open a Pitch Meeting from the FA Market." |
| News Feed | "Quiet around the league" / "Storylines appear after games and major events." |
| Trade Offers | "No incoming offers" / "Other GMs will reach out as the deadline nears." |

**Tone**: friendly, instructive when actionable, neutral otherwise. Never apologetic ("Sorry, no data") and never blank.

---

## 8. Loading States

Tied to perceived performance. Different durations get different treatments.

| Duration | Treatment |
|---|---|
| `< 200ms` | No indicator. Showing one creates visual flicker that feels slower. |
| `200ms – 2s` | Inline spinner replacing the action target. |
| `2s – 5s` | Skeleton screens — gray placeholder boxes shaped like the real content. |
| `> 5s` | Progress bar with task description. Example: `Simulating week 8: 14/16 games · 87%`. |

**Special case — Live Game Sim (S-03)**: not "loading" — it's the screen's primary content. Streams narration as it generates. No spinner; the play-by-play log itself is the progress indicator.

**Special case — Save**: per CLAUDE.md, autosave is per-action. Saves should be sub-200ms (single SQLite transaction). If a save exceeds 500ms, surface a banner — that's an unusual condition worth flagging to the player.

---

## 9. Accessibility Floor (locked)

Not exhaustive, but these rules are non-negotiable:

- **Color is never the sole signal.** Phase, status, and grade all pair color with a text label or icon (per Step 3 resolution).
- **Minimum contrast ratio 4.5:1** for body text on its background. Verified in palette §1.
- **Keyboard navigation** for primary flows: Tab/Shift-Tab move focus, Enter activates buttons and rows, Esc closes modals.
- **Focus indicator** visible on every interactive element — 2px `--border-strong` outline.
- **No flashing/strobing** content (epilepsy guideline).
- **Tooltip text** for any icon-only button.

---

## 10. Out of Scope for v1

Defer until post-launch:

- Light theme (build infrastructure now via tokens, ship light theme later).
- Localization beyond English.
- Custom user themes (community modding hook — interesting later, distracting now).
- Animated transitions between screens (subtle 150ms fades only at v1; deeper motion design is a polish phase).
- Sound effects.

---

## Open Questions for Step 5 (Framework Implementation Plan)

1. **CSS framework choice** — vanilla CSS with custom properties (recommended), or pull in Tailwind? Tailwind would speed iteration but adds build tooling.
2. **Table library** — vanilla `<table>` for v1 vs DataTables/AG-Grid Community from day 1?
3. **Icon library** — Unicode-only (smallest footprint) vs Lucide/Phosphor (consistent rendering)?
4. **State management on JS side** — vanilla event handlers vs Alpine.js vs htmx?
5. **Folder structure** under `src/ui/` for static assets — html/, css/, js/, assets/ subfolders.

---

## Action Items Before Step 5

- [ ] David reviews color palette — particularly letter grade colors (most visible element in the game).
- [ ] Confirm currency format (`$23.4M` standard, no commas).
- [ ] Confirm dark theme as v1, light theme deferred.
- [ ] Confirm icon strategy — Unicode first, swap to icon library if testing reveals inconsistencies.
- [ ] Confirm hot keys / keyboard nav scope — full keyboard control or mouse-first with selective shortcuts?
