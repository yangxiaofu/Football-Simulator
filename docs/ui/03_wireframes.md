# Step 3 — Low-Fidelity Wireframes

**Status**: Drafted, pending review.
**Purpose**: Visualize the highest-leverage screens before any code. Lock layout patterns so Claude Code has a concrete reference when implementing `src/ui/`.
**Inputs to this step**: Step 1 IA (screen inventory + IDs), Step 2 context bar.
**Output of this step**: Shell template + 8 wireframes covering primary screen archetypes + extracted layout patterns + resolved navigation style.

**Fidelity intent**: ASCII art deliberately. Low-fi wireframes catch layout problems faster than polished mockups, and Claude Code parses them perfectly. Step 4 will lock typography, color, and spacing.

---

## Resolutions to Step 2 Open Questions

| Question | Resolution |
|---|---|
| Visual weight of phase badge | Pill with colored background, white text, ~22px tall, sits inline with date text |
| Sidebar style — horizontal tabs vs vertical rail | **Hybrid**: horizontal top tabs for the 5 sections, left rail for contextual sub-nav within sections that have multiple sub-screens (Team, Front Office). Pure horizontal tabs would force too many sub-nav clicks; pure left rail steals horizontal real estate from data tables. |
| Notification dropdown anchoring | **Overlay** (anchored to bell icon, doesn't push content). |
| Color-only signaling | **Always pair color with text label or icon.** Color carries meaning but is never the sole signal. Locked here as accessibility rule for the rest of the project. |

---

## Universal Shell Template

Every screen except the Main Menu and Live Game View uses this shell. The active screen renders only inside the **Content** zone — everything outside is the persistent shell.

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] Chicago Bears CHI │ Wk 8 · 2026 Reg [REG] · 5-3 │ $23.4M cap │ 🔔3 │ Continue▶│ ⚙ │  ← Context Bar (Step 2)
├──────────────────────────────────────────────────────────────────────────────────────┤
│  Team │ League │ Schedule │ Front Office │ Dynasty                                   │  ← Section Tabs
├──────────────┬───────────────────────────────────────────────────────────────────────┤
│              │                                                                        │
│  Sub-nav     │                                                                        │
│  rail        │                  Content Zone                                          │
│  (contextual)│                  (active screen renders here)                          │
│              │                                                                        │
│              │                                                                        │
└──────────────┴───────────────────────────────────────────────────────────────────────┘
```

**Sub-nav rail rules:**

- Visible when the active section has multiple sub-screens (Team, Front Office, Dynasty).
- Hidden when the active section has a single primary screen (Schedule shows the schedule grid full-width).
- ~180px wide.
- Highlights the active sub-screen.

**Section tab rules:**

- Always visible (5 tabs).
- The active tab is underlined in team accent color.
- Tab order is fixed (Team → League → Schedule → Front Office → Dynasty).
- System (settings/save/quit) lives in the gear icon at far right of the context bar — not in the tab row.

---

## Wireframe 1 — Team Dashboard (T-01) · HOME

The home base. Every session starts here. Aggregates: next-event preview, news, key alerts, quick-access cards. Designed so a returning player can read "what's happening" in 5 seconds.

```
┌─ Context Bar ────────────────────────────────────────────────────────────────────────┐
│ [Logo] Chicago Bears  Wk 8 · 2026 [REG] · 5-3  $23.4M cap  🔔3  [Sim Game ▶] ⚙       │
├─ Tabs ──────────────────────────────────────────────────────────────────────────────┤
│ [Team▾] League  Schedule  Front Office  Dynasty                                      │
├─ Sub-nav ──┬─ Content ─────────────────────────────────────────────────────────────┤
│            │                                                                        │
│ Dashboard  │  ┌─ NEXT GAME ──────────────────┬─ TEAM STATUS ──────────────────────┐│
│ Roster     │  │ vs Green Bay Packers (4-4)   │ 5-3 · 2nd NFC North                ││
│ Depth Chart│  │ Sun Wk 9 · Soldier Field     │ Off rank: 8th  · Def rank: 14th    ││
│ Practice   │  │ Weather: 38°F, light snow    │ Health: 2 OUT, 4 questionable      ││
│ Cap        │  │ Spread: CHI -3               │ Cap: $23.4M · 49 active            ││
│ Staff      │  │ [Game Plan] [Sim Game ▶]     │ [Roster] [Cap] [Health Report]     ││
│ Scheme     │  └──────────────────────────────┴────────────────────────────────────┘│
│            │                                                                        │
│            │  ┌─ NEWS & STORYLINES ────────────────────────────────────────────────┐│
│            │  │ • RB M. Carter named NFC Player of the Week                        ││
│            │  │ • LB D. Reed (QB1 backup) requested trade — satisfaction: WARNING  ││
│            │  │ • DET trades 2026 R3 to PIT for WR — division foe loaded up        ││
│            │  │ • Power Rankings: CHI moves up to #11 (from #14)                   ││
│            │  │                                                          [View All]││
│            │  └────────────────────────────────────────────────────────────────────┘│
│            │                                                                        │
│            │  ┌─ ALERTS (3) ──────────────────┬─ TOP PERFORMERS (Wk 8) ──────────┐ │
│            │  │ ⚠ LB D. Reed satisfaction     │ Pass: 312 yds, 3 TD (J. Kim)    │ │
│            │  │ ⚠ Cap warning: <$5M in 3 wks  │ Rush: 142 yds (M. Carter)       │ │
│            │  │ ✏ Game plan unset for Wk 9    │ Sacks: 2.5 (A. Williams)        │ │
│            │  │             [Resolve All]     │                  [Box Score]    │ │
│            │  └───────────────────────────────┴──────────────────────────────────┘ │
│            │                                                                        │
└────────────┴───────────────────────────────────────────────────────────────────────┘
```

**Behavior notes:**

- Cards are clickable — clicking the NEXT GAME card opens Game Preview (S-02).
- ALERTS card mirrors the bell icon's badge count. Each alert links to the relevant resolver screen.
- NEWS card is a feed view; "View All" opens the News Feed (L-08).
- The card grid is responsive — collapses 2-col to 1-col below 1100px.
- During offseason, this dashboard rerenders with offseason-mode cards (Season Review, Phase Status, Pending Decisions). Same screen ID, different cards — implementing this is a view-model concern not a navigation one.

---

## Wireframe 2 — Roster Overview (T-02) · LIST PATTERN

The most-visited list screen. Sets the pattern for every other table-based screen (FA Market, Draft Class, Standings, etc.).

```
┌─ Context Bar ─────────────────────────────────────────────────────────────────────┐
├─ Tabs: Team active ──────────────────────────────────────────────────────────────┤
├─ Sub-nav ──┬─ Content ─────────────────────────────────────────────────────────┤
│ Dashboard  │ ┌─ FILTERS ────────────────────────────────────────────────────────┐│
│[Roster]    │ │ Position: [All ▼] Status: [All ▼] Age: [All ▼]  Search: [____]   ││
│ Depth Chart│ │ Sort by: [OVR ▼]  Showing 53 of 53 players                       ││
│ Practice   │ └──────────────────────────────────────────────────────────────────┘│
│ Cap        │                                                                       │
│ Staff      │ ┌─ TABLE ──────────────────────────────────────────────────────────┐│
│ Scheme     │ │ POS │ Name              │ AGE │ OVR │ FIT │ CONTRACT       │STATUS││
│            │ ├─────┼───────────────────┼─────┼─────┼─────┼────────────────┼──────┤│
│            │ │ QB  │ J. Kim            │ 27  │  A  │ A+  │ 4yr · $42M/yr  │      ││
│            │ │ QB  │ T. Brooks         │ 24  │ B-  │ B   │ Rookie · 3yr   │      ││
│            │ │ RB  │ M. Carter         │ 26  │ A-  │ A   │ 2yr · $11M/yr  │      ││
│            │ │ RB  │ K. Davis          │ 29  │ C+  │ B-  │ 1yr · $4M       │ ⚕  ││
│            │ │ WR  │ R. Lopez          │ 25  │ A   │ A   │ 3yr · $18M/yr  │      ││
│            │ │ WR  │ D. Park           │ 22  │ B+  │ A-  │ Rookie · 4yr   │      ││
│            │ │ WR  │ S. Hayes          │ 31  │ B   │ B   │ 1yr · $6M       │      ││
│            │ │ TE  │ M. Olsen          │ 28  │ B+  │ A-  │ 3yr · $9M/yr   │ ⚕  ││
│            │ │ ... 45 more rows ...                                              ││
│            │ └──────────────────────────────────────────────────────────────────┘│
│            │                                                                       │
│            │  Click row → Player Card (T-05). Right-click → context menu.          │
└────────────┴────────────────────────────────────────────────────────────────────┘
```

**Pattern rules extracted:**

- **Filter row at top** with: dropdowns (Position/Status/Age), search box, sort selector, count indicator ("Showing 53 of 53").
- **Headers are sortable** — click to toggle asc/desc. Sort indicator (▲▼) shown on active column.
- **All ratings rendered as letter grades** (per CLAUDE.md). Never raw `true_overall`.
- **Status icons** (⚕ for injury, ⚠ for satisfaction warning, 🔄 for trade block) on right side of row.
- **Clicking a row** opens the detail screen — never select-then-click-button.
- **Right-click context menu** offers row-level actions (Add to Trade Block, Cut, Restructure) without leaving the list.

---

## Wireframe 3 — Player Card (T-05) · DETAIL PATTERN

The most-visited detail screen. Sets the pattern for FA Player, Prospect Card, Coach Card. Built around tabs since one player has many faces (bio, stats, contract, satisfaction, history).

```
┌─ Context Bar ─────────────────────────────────────────────────────────────────────┐
├─ Tabs: Team active ──────────────────────────────────────────────────────────────┤
├─ Sub-nav ──┬─ Content ─────────────────────────────────────────────────────────┤
│ Dashboard  │ ┌─ HEADER ────────────────────────────────────────────────────────┐│
│[Roster]    │ │ [Photo] Jordan Kim · QB · #11 · Chicago Bears                   ││
│ Depth Chart│ │         Age 27 · 6'4" 220 · 5th season · Drafted 2022 R1 P14   ││
│ Practice   │ │                          OVR: A   Scheme Fit: A+   Clutch: B+   ││
│ Cap        │ └─────────────────────────────────────────────────────────────────┘│
│ Staff      │                                                                      │
│ Scheme     │ ┌─ TABS ──────────────────────────────────────────────────────────┐│
│            │ │ [Overview] Stats   Contract   Satisfaction   History            ││
│            │ ├─────────────────────────────────────────────────────────────────┤│
│            │ │                                                                  ││
│            │ │ ┌─ KEY ATTRIBUTES (letter grades) ──┬─ CONTRACT (snapshot) ─┐ ││
│            │ │ │ Throw Power      A                │ 4yr · $42M/yr APY    │ ││
│            │ │ │ Throw Accuracy   A+               │ 2026: $38M cap hit   │ ││
│            │ │ │ Pocket Awareness A                │ 2027: $44M cap hit   │ ││
│            │ │ │ Mobility         B                │ 2028: $46M cap hit   │ ││
│            │ │ │ Read Progression A-               │ Dead cap if cut: $24M│ ││
│            │ │ │ Composure        B+               │ [Restructure] [Cut]  │ ││
│            │ │ └───────────────────────────────────┴──────────────────────┘ ││
│            │ │                                                                  ││
│            │ │ ┌─ 2026 SEASON ───────────────────────────────────────────────┐ ││
│            │ │ │ 8 GP · 2,184 PASS YDS · 16 TD · 5 INT · 102.3 RTG · 65.3%   │ ││
│            │ │ │ Season MVP odds: 8% · Pro Bowl track: ON                    │ ││
│            │ │ └─────────────────────────────────────────────────────────────┘ ││
│            │ │                                                                  ││
│            │ │ ┌─ SATISFACTION: HEALTHY ─────────────────────────────────────┐ ││
│            │ │ │ No active warnings · Last intervention: never                │ ││
│            │ │ └─────────────────────────────────────────────────────────────┘ ││
│            │ │                                                                  ││
│            │ │ [Add to Trade Block] [Restructure] [Cut Player]                  ││
│            │ └──────────────────────────────────────────────────────────────────┘│
└────────────┴───────────────────────────────────────────────────────────────────────┘
```

**Pattern rules extracted:**

- **Header zone**: photo + identity line + headline ratings. Compact, never scrolls away.
- **Tab nav** for facets of the same record (Overview / Stats / Contract / Satisfaction / History).
- **Action buttons at bottom** of Overview tab — primary actions visible without hunting.
- **Cap hit per year visible** in contract snapshot — don't make players drill to T-06 for the year-by-year.
- **Status callouts** (Satisfaction: HEALTHY) use color + label, never color alone.

---

## Wireframe 4 — Schedule (S-01)

Single-purpose screen. No sub-nav rail — full-width schedule grid.

```
┌─ Context Bar · Tabs: Schedule active ─────────────────────────────────────────────┐
├───────────────────────────────────────────────────────────────────────────────────┤
│  CHICAGO BEARS · 2026 REGULAR SEASON                                               │
│  Record: 5-3 · Streak: W2 · Remaining strength of schedule: .523                   │
│                                                                                     │
│  WK   DATE     OPP            LOC    RESULT     SCORE      STATUS                  │
│  ───  ───────  ─────────────  ─────  ─────────  ─────────  ──────                  │
│   1   Sep 7    @ DET          Away   W           24-17      [Recap]                │
│   2   Sep 14   GB             Home   L           20-23 OT   [Recap]                │
│   3   Sep 21   @ MIN          Away   W           28-14      [Recap]                │
│   4   Sep 28   ATL            Home   L           17-21      [Recap]                │
│   5   Oct 5    @ NYG          Away   W           31-10      [Recap]                │
│   6   Oct 12   BYE            ──     ──          ──         ──                     │
│   7   Oct 19   PHI            Home   W           24-20      [Recap]                │
│   8   Oct 26   @ NE           Away   W           27-17      [Recap]                │
│   9   Nov 2    GB             Home   ──          ──         [Game Preview ▶]       │  ← bold
│  10   Nov 9    @ DET          Away   ──          ──         Upcoming               │
│  11   Nov 16   MIN            Home   ──          ──         Upcoming               │
│  ... 6 more weeks ...                                                              │
│                                                                                     │
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Behavior:**

- Past games: result + clickable Recap link (S-05).
- Current week: bold row, primary CTA "Game Preview" (S-02).
- Future games: muted, no actions yet.
- BYE week shown as a row, not skipped.

---

## Wireframe 5 — Game Recap (S-05) · RECAP MOMENT

Read-only emotional payoff. Higher polish budget than utility screens (per Step 1 classification, this is a "recap moment").

```
┌─ Context Bar · Tabs: Schedule active ─────────────────────────────────────────────┐
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│         CHICAGO BEARS  27   ·  NEW ENGLAND PATRIOTS  17                             │
│                  Wk 8 · Oct 26, 2026 · Foxborough · 41°F, clear                    │
│                                                                                     │
│  ┌─ HEADLINE ─────────────────────────────────────────────────────────────────┐   │
│  │  Carter rumbles for 142, Bears spoil Patriots' homecoming                   │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─ KEY PLAYS (8) ────────────────────────────────────────────────────────────┐   │
│  │ Q1 12:08 · CHI 24yd TD pass Kim → Lopez ······························ 7-0 │   │
│  │ Q2 04:33 · NE  39yd FG  Garcia ······································· 7-3 │   │
│  │ Q2 00:41 · CHI 3yd TD run Carter ···································· 14-3 │   │
│  │ Q3 09:12 · NE  62yd TD pass Hill → Mason ··························· 14-10 │   │
│  │ Q3 02:55 · CHI 47yd FG Petersen ····································· 17-10 │   │
│  │ Q4 11:20 · CHI 18yd TD run Carter ··································· 24-10 │   │
│  │ Q4 06:08 · NE  4yd TD pass Hill → Adams ···························· 24-17 │   │
│  │ Q4 02:14 · CHI 39yd FG Petersen ····································· 27-17 │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─ TOP PERFORMERS ────────────┬─ BOX SCORE PREVIEW ──────────────────────────┐   │
│  │ M. Carter · 24 car, 142 yd │  CHI: 412 total, 28:14 TOP, 4-12 3rd-down    │   │
│  │ J. Kim · 24/34, 248, 1 TD  │  NE:  308 total, 31:46 TOP, 5-13 3rd-down    │   │
│  │ A. Williams · 2.5 sacks    │                       [Full Box Score ▶]      │   │
│  └────────────────────────────┴───────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─ INJURIES ─────────────────────────────────────────────────────────────────┐   │
│  │ CHI: TE Olsen — high ankle sprain, OUT 2-3 weeks                            │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  [Box Score]  [Full Play-by-Play]  [Continue ▶]                                    │
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Why higher polish:**

- This is the screen players will share screenshots of. It earns layout effort.
- The headline is generated narrative — not just a stat dump.
- Key plays use ASCII dot-leader to show progression of the score.
- Continue button at bottom returns to schedule and increments week.

---

## Wireframe 6 — Standings (L-02)

Tight, scannable. The single most-checked screen across a full season.

```
┌─ Context Bar · Tabs: League active ───────────────────────────────────────────────┐
├─ Sub-nav ──┬─ Content ─────────────────────────────────────────────────────────┤
│[Standings] │  View: [Division ▼] · Season: [2026 ▼]                             │
│ Leaders    │                                                                       │
│ Stat Brws  │  ═══ NFC NORTH ═══                                                    │
│ Trans Log  │  RNK  TEAM             W-L    PCT    DIV    CONF   PF    PA   STRK   │
│ News       │  ──── ────────────────  ─────  ────  ─────  ────   ───   ───  ────   │
│ Power Rks  │  1    Detroit Lions     6-2    .750  3-0    4-1    218   161   W3    │
│ All Teams  │  2    Chicago Bears     5-3    .625  2-1    3-2    189   172   W2    │
│            │  3    Green Bay Packers 4-4    .500  2-1    3-3    201   197   L1    │
│            │  4    Minnesota Vikings 3-5    .375  1-2    2-4    158   192   L2    │
│            │                                                                       │
│            │  ═══ NFC SOUTH ═══                                                    │
│            │  ... etc ...                                                          │
│            │                                                                       │
│            │  PLAYOFF PICTURE (live):                                              │
│            │  NFC: #1 SF · #2 PHI · #3 DET · #4 NO · #5 DAL · #6 LAR · #7 CHI     │
│            │  IN HUNT (8-10): GB, ATL, TB                                          │
│            │                                                                       │
└────────────┴────────────────────────────────────────────────────────────────────┘
```

**Behavior:**

- View toggle: Division / Conference / League / Playoff Picture.
- Each team name is clickable → opens that team's roster (L-10).
- Playoff picture is computed live from current standings — only visible from week 10 onwards.

---

## Wireframe 7 — Front Office Hub (F-01) · OFFSEASON MODE: FREE AGENCY

Most important wireframe in the doc — validates the mode-aware behavior locked in Step 1. Same screen ID renders different cards based on `offseason_state.current_phase`.

```
┌─ Context Bar · Phase badge: [FA] · Continue: "Continue ▶" ────────────────────────┐
├─ Tabs: Front Office active ──────────────────────────────────────────────────────┤
├─ Sub-nav ──┬─ Content ─────────────────────────────────────────────────────────┤
│ FO Hub     │  OFFSEASON · Free Agency Phase · Day 4 of 14                        │
│ Satisfact. │                                                                       │
│ ─────────  │  ┌─ FA HUB ──────────────────────────────────────────────────────┐  │
│ Tags       │  │ Your team needs (auto-detected):                                │  │
│ Scouting   │  │  • LB depth (1 starter, no quality backups)                     │  │
│[Free Agency]│ │  • CB2 (current C+ projects to free agency)                     │  │
│ Trades     │  │  • Backup QB (current B- aging out)                             │  │
│ Draft      │  │                                                                  │  │
│ Camp       │  │ Cap available for FA: $23.4M · After tags: $16.8M                │  │
│            │  │                                                                  │  │
│            │  │ [Browse FA Market ▶]  [Watchlist (4)]                            │  │
│            │  └────────────────────────────────────────────────────────────────┘  │
│            │                                                                       │
│            │  ┌─ ACTIVE NEGOTIATIONS (2) ─────────────────────────────────────┐  │
│            │  │ LB D. Reyes  · Pitch sent · Awaiting response · Day 2/3       │  │
│            │  │ CB T. Wallace · Counter received · $8M/yr (offered $6M/yr)    │  │
│            │  │                                            [Resolve Both]      │  │
│            │  └────────────────────────────────────────────────────────────────┘  │
│            │                                                                       │
│            │  ┌─ RECENT SIGNINGS (your team) ───┬─ LEAGUE SIGNINGS ──────────┐  │
│            │  │ K. Mason · 2yr · $4M  · Day 1   │ DAL signs WR L. Kane $14M │  │
│            │  │ M. Olsen · 1yr · $2M  · Day 3   │ NE signs S J. Cole $11M    │  │
│            │  │                                  │ ... 14 more ...           │  │
│            │  └─────────────────────────────────┴───────────────────────────┘  │
│            │                                                                       │
└────────────┴────────────────────────────────────────────────────────────────────┘
```

**Mode-aware behavior:**

- Sub-nav rail shows offseason phases. Current phase ("Free Agency") is highlighted.
- Phases above current (Tags) are completed; phases below (Trades, Draft, Camp) are upcoming.
- Sub-nav prevents skipping forward — you can revisit completed phases (read-only) but not jump ahead.
- During regular season, this same screen ID renders different cards (Satisfaction Dashboard, Trade Block, Roster Status) — sub-nav rail collapses to just Satisfaction.

---

## Wireframe 8 — Draft Room (F-60) · COMPLEX RECAP MOMENT

The most complex screen in the game. Combines real-time event feed, your draft board, decision modal, and league status.

```
┌─ Context Bar (franchise) ─────────────────────────────────────────────────────────┐
├─ Draft state bar (secondary) ────────────────────────────────────────────────────┤
│ Round 2 · Pick 47 of 256 · ON CLOCK: BAL · Your next pick: R2 #51 (in 4 picks)    │
├───────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ LIVE FEED (left) ──────────┬─ YOUR BOARD (center) ────┬─ LEAGUE (right) ──┐  │
│ │ R2 #46 · IND               │ Available · Your rank      │ Pick clock         │  │
│ │   selects WR M. Lewis       │  1. RB J. Powers   (A-)    │ BAL: 2:14 left    │  │
│ │   ────────────────         │  2. LB R. Singh    (B+)    │                    │  │
│ │ R2 #45 · KC                │  3. CB T. Mehra    (B+)    │ Recent picks       │  │
│ │   selects DT A. Boyd        │  4. WR G. Patel    (B+)    │ #46 IND · WR Lewis │  │
│ │ R2 #44 · DET               │  5. OG K. Adler    (B)     │ #45 KC  · DT Boyd  │  │
│ │   TRADED #44 to JAX         │  6. ...                    │ #44 JAX · TRADE    │  │
│ │ R2 #43 · MIA               │                            │                    │  │
│ │ ... scroll for more ...    │  [Filter ▼] [Sort: rank ▼] │ [Trade Picks]     │  │
│ └────────────────────────────┴────────────────────────────┴───────────────────┘  │
│                                                                                     │
│  At your pick (R2 #51), modal opens:                                                │
│  ┌─ DRAFT DECISION ────────────────────────────────────────────────────────────┐  │
│  │  ON THE CLOCK · Chicago Bears · R2 #51 · 5:00                              │  │
│  │  Top of your board: RB J. Powers (rank 1, A-)                              │  │
│  │  ──────────────────────────────────────────────────────────────────────    │  │
│  │  Your needs: LB, CB2, RB depth     │  Coach recommendation: Powers        │  │
│  │  Cap room post-rookie deal: $21.2M │  GM recommendation: Singh (LB)       │  │
│  │                                                                              │  │
│  │  [Pick Powers] [Pick Singh] [Other Player...] [Trade Pick] [Pass Auto-Pick]│  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Why this screen earns its complexity:**

- Three-column layout because the player needs to track three things simultaneously: who's been picked, what's left on their board, and the league context. Hiding any of the three breaks the experience.
- The decision modal opens *only* on your pick — it never blocks you from watching other teams' picks.
- The secondary "draft state" bar lives between the franchise context bar and the content (per Step 2 edge case).
- Live feed, board, and league pane all share the same scroll-on-update behavior — newest event on top.

**Implementation note for Phase 5**: this is the screen that will most stress-test the HTML+pywebview event loop. Step 8 (data volume testing) will validate.

---

## Extracted Layout Patterns

These five patterns cover ~85% of all screens. Locking them here lets Claude Code build reusable templates instead of one-off screens.

### Pattern A — List Screen
Used by: Roster, FA Market, Draft Class, Stat Browser, Standings, Transactions, All Teams.
Components: filter row → sortable table → optional detail panel on row click.

### Pattern B — Detail Screen with Tabs
Used by: Player Card, FA Player, Prospect Card, Coach Card, Other-Team Player.
Components: header zone (identity + headline ratings) → tab nav → tab content → action button row.

### Pattern C — Hub Screen
Used by: Team Dashboard, FO Hub, League Hub, Dynasty Hub, Scouting Hub.
Components: card grid (2-3 columns), each card representing a sub-system or alert. Cards are clickable to drill into the relevant screen.

### Pattern D — Recap Moment
Used by: Game Recap, Season Review, Conference Championship, Super Bowl Recap, Draft Class Reveal, Career Retirement.
Components: hero zone (final score / outcome / headline) → narrative summary → key facts grid → continue/share row. Higher polish budget per Step 1.

### Pattern E — Live Event Screen
Used by: Game View, Draft Room.
Components: dedicated event-context bar (replaces or stacks with franchise bar) → multi-pane live feed → modal-based decision points.

---

## Open Questions for Step 4

1. **Color palette** — currently using placeholder hex values. Step 4 needs the locked palette including team accent handling (each franchise gets the user's team colors as accent).
2. **Typography scale** — body text size, header sizes, monospace for numerics?
3. **Letter grade rendering** — colored badge, plain text, gradient? (Important: A+ should look distinctly different from F at a glance.)
4. **Currency formatting** — `$23.4M` vs `$23,400,000` vs `$23.4m` — pick one canonical form.
5. **Date formatting in lists** — `Sep 7` vs `9/7` vs `Sep 7, 2026`?
6. **Empty state design** — "No notifications", "No active trades", etc.
7. **Loading states** — spinner vs skeleton vs progress bar.

---

## Action Items Before Step 4

- [ ] David reviews each wireframe and flags layout issues.
- [ ] Confirm hybrid nav (top tabs + contextual left rail) — vs alternative (full sidebar, full top nav).
- [ ] Confirm Draft Room three-column layout fits his mental model (or prefer two columns + collapsible league pane).
- [ ] Confirm Game Recap polish level — content density and presence of generated headline.
- [ ] Confirm Pattern D recap moments deserve their own template (impacts Step 9 budget).
