# Football Simulator — Game Design Document
## Layer 4: Feature Roadmap

**Version:** 0.1 (Draft)
**Author:** David Dong
**Date:** May 9, 2026
**Status:** Working Draft
**Depends on:** GDD_Layer1 through GDD_Layer3

---

## Roadmap Philosophy

The roadmap is built around one principle: **always have a playable game.**

Every phase ends with something that runs — not a partial system waiting for another system to be complete, but an actual playable loop you can test, feel, and tune. This matters especially when building with AI assistance, because the fastest way to discover design problems is to play the thing, not read about it.

The build order is **engine-in, UI-out.** The simulation engine comes first because everything else in the game is either feeding it data or displaying its results. A beautiful draft interface built on top of a broken simulation engine is worthless. A plain-text simulation engine that produces realistic, compelling game outputs is the foundation everything else stands on.

### Honest Timeline Assessment

Three full playable seasons in 3–6 months is **achievable but aggressive** for a solo developer, even with Claude Code assistance. The schedule below maps to that window with no slack. What makes it possible:

- Python prototypes fast — you won't write boilerplate
- Claude Code handles mechanical implementation of well-specified systems
- The GDD layers you've already written are unusually detailed — no design ambiguity to resolve mid-build
- A text-based game has no asset pipeline (no 3D models, no sprites, no audio to produce)

What will hurt the timeline: UI polish, edge case debugging, and simulation tuning. The schedule defers all three until after the core loop works.

---

## Development Phases

---

### Phase 0 — Foundation
**Target Duration:** Weeks 1–3
**Goal:** The database exists, rosters are populated, and you can query player data from the command line.

This phase produces no visible gameplay. It's infrastructure. Skip or rush it and you'll rebuild it twice.

#### Features:

**Database Setup**
- [ ] Create SQLite schema from Layer 3 (all tables, indexes, foreign keys)
- [ ] Write Python database connection module with basic CRUD helpers
- [ ] Implement `recalculate_cap_space()` utility function
- [ ] Implement `transaction_log` writer (called by every roster action)

**League & Team Generation**
- [ ] Generate 32 fictional teams with city, nickname, division, conference
- [ ] Assign GM personality archetype to each AI team
- [ ] Set initial team prestige, market size, and fan sentiment values

**Player Generation**
- [ ] Build player generator: position-specific attribute distributions
- [ ] Generate 53-man roster for all 32 teams (1,696 players total)
- [ ] Assign age distributions that mirror a realistic NFL roster
- [ ] Set development traits (superstar / star / normal / slow) by rarity
- [ ] Generate and assign rookie contracts and veteran contracts
- [ ] Verify cap space is valid for all 32 teams at generation

**Staff Generation**
- [ ] Generate coaching staff for all 32 teams (OC, DC, position coaches)
- [ ] Generate scouting department for all 32 teams (head scout + 3 regional scouts)
- [ ] Assign staff ratings and personalities

**Schedule Generation**
- [ ] Generate 17-game regular season schedule (home/away balance, division games)
- [ ] Seed playoff bracket structure

**Phase 0 Exit Criteria:**
```
python query_roster.py --team CHI
→ Prints 53-player roster with positions, ages, overall grades, and cap hits
→ Team cap space is correct
→ All 32 teams have valid rosters
```

---

### Phase 1 — The Simulation Engine
**Target Duration:** Weeks 4–10
**Goal:** One fully simulated, fully narrated game works end-to-end.

This is the hardest phase and the most important. Budget time for iteration — the first simulation outputs will not feel right, and tuning them to feel realistic requires running hundreds of test games.

#### Features:

**Game State Machine**
- [ ] Implement `GameState` object (all fields from Layer 3 §3.5)
- [ ] Implement quarter/time management, possession tracking, down/distance logic
- [ ] Implement drive logic (first downs, punts, turnovers, scores, end of half)
- [ ] Implement overtime rules

**Matchup Resolution Engine**
- [ ] Implement logistic probability function `P(attacker wins)` with k=0.07
- [ ] Implement Scheme-Adjusted Rating (SAR) calculator
  - Pull true ratings from player table
  - Apply scheme fit modifier based on coordinator scheme_expertise
- [ ] Implement pass play resolution tree (Steps 1–5 from Layer 2 §2.3)
- [ ] Implement run play resolution tree (Steps 1–3 from Layer 2 §2.3)

**Play Type Logic**
- [ ] Implement offensive play selection (based on game plan tendency sliders)
- [ ] Implement defensive play selection (DC disguise and coverage scheme)
- [ ] Implement 3rd down and red zone situation logic
- [ ] Implement 2-minute drill awareness (tempo change, clock management)
- [ ] Implement 4th down decision logic (AI and player override prompt)

**Special Teams**
- [ ] Implement field goal resolution (accuracy + distance + weather)
- [ ] Implement punt resolution (power + directional accuracy + return)
- [ ] Implement kickoff resolution (touchback probability + return)
- [ ] Implement blocked kick probability
- [ ] Implement STC rating as global special teams modifier

**Injury System**
- [ ] Implement per-play base injury probability formula
- [ ] Implement high-contact situation multipliers (sack, goal-line, etc.)
- [ ] Implement injury severity roll and classification
- [ ] Update player `injury_status` and `roster_status` when injury fires

**Fatigue System**
- [ ] Implement weekly stamina drain per snap (position-specific rates)
- [ ] Implement in-game stamina effect on SAR (penalties at <60%, <40%, <20%)
- [ ] Implement season wear accumulation (from Week 10, position-specific rates)

**Weather System**
- [ ] Implement weather generation per game (city + time of year)
- [ ] Apply weather modifiers to accuracy, speed, fumble rate, kicking

**Narration Engine**
- [ ] Build narration template library for each play result type
  - Pass: complete / incomplete / sack / scramble / interception / TD
  - Run: short gain / standard / chunk / breakaway / fumble / TD
  - Special teams: FG good / FG miss / punt / return / blocked kick / TD
- [ ] Implement context-aware narration (score, time, down/distance woven in)
- [ ] Implement key play flagging (`is_big_play`, momentum moments)

**Box Score Generation**
- [ ] Accumulate per-player stats during simulation
- [ ] Write box_score records at game completion
- [ ] Write flagged key_plays at game completion
- [ ] Write all play records to play table (current season)

**Override System**
- [ ] Implement override trigger detection (3rd & short, 4th down, red zone, 2-min)
- [ ] Present player with play options and risk/reward indicators
- [ ] Process player choice and route into resolution engine

**Phase 1 Exit Criteria:**
```
python simulate_game.py --home CHI --away GB --week 1
→ Full play-by-play log prints to terminal
→ Realistic score (both teams score, no 0-0 games, no 70-0 blowouts)
→ Box score stats are plausible (QB: 250 yds, RB: 80 yds, etc.)
→ At least 1 injury fires per 3-4 games on average
→ Weather affects outcomes visibly in cold/wind conditions
```

*Plan a 1-week tuning sprint here before moving to Phase 2. Run 500 simulated games, check stat distributions against real NFL averages, and adjust tuning constants.*

---

### Phase 2 — The Full Season
**Target Duration:** Weeks 11–14
**Goal:** Simulate an entire 17-game regular season and playoffs with standings, stats, and a champion.

#### Features:

**Season Loop**
- [ ] Implement week advancement (user triggers "advance to next week")
- [ ] Simulate all 32 teams' games each week (AI vs AI games auto-resolve to box score only — no full play log for games you're not involved in)
- [ ] Implement bye weeks

**Standings & Tiebreakers**
- [ ] Track win/loss/tie records, points for/against per team
- [ ] Implement division standings with tiebreaker logic (head-to-head, division record, conference record, point differential)
- [ ] Generate playoff seeding (7 teams per conference)

**Playoff Bracket**
- [ ] Generate wildcard, divisional, conference, and Super Bowl matchups
- [ ] Implement home field advantage correctly through bracket
- [ ] Simulate or play each playoff game through the normal game engine
- [ ] Crown champion, update `team_season_record`

**Season-End Processing**
- [ ] Run season archive job (Layer 3 §5)
  - Compute `player_season_stats` from box scores
  - Update `player_career_stats`
  - Select and store `key_play` records
  - Delete current season `play` records
  - Compute team season records
- [ ] Run player development pass (age 22–26: most growth; 27–29: plateau; 30+: decline)
- [ ] Run aging decay pass (position-specific attribute reduction)
- [ ] Update legacy score

**Awards**
- [ ] Compute season awards from stats: MVP, Offensive/Defensive Player of Year, Rookie of Year
- [ ] Assign Pro Bowl and All-Pro designations (top N players per position by stats + ratings)

**Basic UI — Terminal / Text Interface**
- [ ] Weekly summary screen (your record, division standings, upcoming opponent)
- [ ] Roster screen (53-man roster with grades and contract status)
- [ ] Box score display (post-game stat lines)
- [ ] Season stats leaderboard (top 10 passers, rushers, receivers, sackers)

**Phase 2 Exit Criteria:**
```
→ Can simulate a full 17-week season + playoffs from start to finish
→ Champion is crowned with a narrative summary
→ Season stats are plausible across all 32 teams
→ Player development moves ratings in the right direction between seasons
→ Legacy score updates correctly
```

---

### Phase 3 — The Offseason Loop
**Target Duration:** Weeks 15–20
**Goal:** Full franchise year is playable: season → offseason → draft → back to Week 1.

This is where the game becomes a franchise simulator rather than a season simulator. It's also the phase with the most distinct sub-systems.

#### Features:

**Offseason Calendar**
- [ ] Implement phase advancement (user manually advances through each offseason phase)
- [ ] Display current phase, available actions, and upcoming deadlines

**Staff Management**
- [ ] Implement staff firing and hiring market
- [ ] Generate staff free agent pool (available coaches and scouts)
- [ ] Implement staff contract negotiation (simple: years + salary)
- [ ] Apply coordinator rating changes to SAR calculations for next season
- [ ] Implement AI team staff changes (GMs fire/hire based on performance)

**Contract Management**
- [ ] Implement contract expiration (players whose deals end become free agents)
- [ ] Implement player releases (with dead cap calculation)
- [ ] Implement contract restructuring (convert base to bonus, recalculate cap years)
- [ ] Implement void year addition
- [ ] Implement franchise tag (once per team per year)
- [ ] Implement performance escalator tracking and triggering

**Free Agency**
- [ ] Generate free agent pool from all expired contracts + released players
- [ ] Compute interest tier (1/2/3) for each free agent relative to each team
- [ ] Implement pitch meeting system (user-facing dialogue event)
- [ ] Implement offer/counter/accept/reject negotiation loop
- [ ] Implement market dynamics (early signers cost more; late signers cost less)
- [ ] Implement AI team free agency behavior (governed by GM personality)
- [ ] Implement front office intelligence signals ("his agent is returning calls...")

**Trade System**
- [ ] Implement trade value point system (player and pick values)
- [ ] Implement positional need score per AI team
- [ ] Implement trade offer UI (you → AI team)
- [ ] Implement AI evaluation logic (value floor + need modifier)
- [ ] Implement unsolicited trade offers (AI → you)
- [ ] Implement conditional pick structure
- [ ] Implement in-season trade deadline (Week 8 lock)

**Scouting System**
- [ ] Generate draft class (300–400 prospects with true ratings + flags)
- [ ] Implement scouting assignment (assign scouts to prospects per week)
- [ ] Implement scouting report generation (estimate + confidence range)
- [ ] Implement report accuracy as function of scout's Talent Evaluation rating
- [ ] Implement Phase 1–4 scouting calendar (Early Season → Film → Combine → Pre-Draft)
- [ ] Implement combine events (40 time, bench, vertical, Wonderlic)
- [ ] Implement mock draft publication (weekly during pre-draft)
- [ ] Implement competitor interest signals (visit reports, workout intel)

**The Draft**
- [ ] Display draft board (your scouted grades, flags, confidence ranges)
- [ ] Implement AI team picks (governed by GM personality and positional needs)
- [ ] Implement live trade offers (AI calls you while on the clock)
- [ ] Implement pre-draft pick trading
- [ ] Implement player-to-team promotion after selection (prospect → player record)
- [ ] Implement rookie contract generation (4-year deals, scale by round)
- [ ] Implement post-draft revelation (scouts compare picks to early camp grades)

**Player Satisfaction System**
- [ ] Implement satisfaction rating updates (weekly tick based on role, wins, contract)
- [ ] Implement warning signal generation and display in weekly briefing
- [ ] Implement intervention options (meeting, offer extension, adjust role)
- [ ] Implement holdout, trade demand, and retirement events

**Phase 3 Exit Criteria:**
```
→ Complete franchise year loop works: Season → Staff eval → FA → Draft → next Season
→ Draft feels like an event — board builds over the scouting season, mock drafts shift, competitor interest creates pressure
→ Cap management is consequential — dead cap from a bad cut hurts next season
→ Player satisfaction creates at least one event per offseason (holdout, demand, or surprise retirement)
```

---

### Phase 4 — The Dynasty
**Target Duration:** Weeks 21–26
**Goal:** Three full seasons are playable with a functioning legacy system. This is the internal MVP.

#### Features:

**Multi-Season Stability**
- [ ] Validate database integrity after 3 full season archive cycles
- [ ] Validate player development arcs look realistic over 3 seasons (rookies improve, veterans decline)
- [ ] Validate cap space remains valid across seasons (no phantom cap hits)
- [ ] Validate AI teams make coherent decisions across multiple seasons

**Legacy Score System**
- [ ] Implement full legacy score calculation (all six weighted categories)
- [ ] Display legacy score summary at end of each season
- [ ] Implement dynasty flag (3+ SBs in 10-season window)
- [ ] Implement Hall of Fame eligibility check (career legacy threshold)
- [ ] Write Hall of Fame induction narrative (generated summary of career)

**Media & Pressure System**
- [ ] Implement owner expectation setting at season start (playoff / division / SB)
- [ ] Implement fan sentiment tracking (wins/losses, draft results, transactions)
- [ ] Implement hot seat escalation (2 losing seasons → contract discussion → fired)
- [ ] Implement media event generation (press conference questions, locker room leaks, controversies)
- [ ] Implement response choices and consequence resolution

**AI GM Behavior — Full Implementation**
- [ ] Implement rebuild trigger logic (each archetype has different patience threshold)
- [ ] Implement win-now vs. rebuild behavioral switch
- [ ] Validate AI teams produce believable rosters and records over 3 seasons
- [ ] Implement league parity logic (prevent same team winning 3 SBs in a row without user involvement)

**Historical Records**
- [ ] Implement league record tracking (single-season passing yards record, etc.)
- [ ] Display historical champion list
- [ ] Display franchise all-time stats leaders

**Phase 4 Exit Criteria:**
```
→ Three full seasons complete without crashes or data corruption
→ Dynasty arc feels real: your team gets better or worse based on your decisions
→ Legacy score moves meaningfully based on performance
→ At least one Hall of Fame moment is generated by end of Season 3
→ You feel the urge to start Season 4
```

**This is your internal MVP. At this point, the game works.**

---

## Steam Early Access Target

**Target:** 6–12 months after Phase 4 completion
**What needs to happen between internal MVP and Steam EA:**

### UI Overhaul
- [ ] Replace terminal interface with a proper windowed UI
- [ ] Build roster management screen with sortable columns, filters, grade display
- [ ] Build game viewer (play-by-play log with scroll, key play highlights)
- [ ] Build depth chart editor (drag-and-drop or click-to-set)
- [ ] Build draft room interface (board, available players, pick timer, trade popup)
- [ ] Build contract negotiation interface
- [ ] Build franchise dashboard (standings, cap, upcoming schedule, news feed)

### Polish & Tuning
- [ ] Simulation tuning sprint: 10,000 auto-simulated games, validate all stat distributions
- [ ] Narration expansion: 500+ play narration templates (variety prevents repetition)
- [ ] Edge case hardening: weird cap situations, draft edge cases, playoff tiebreakers

### Steam Integration
- [ ] Package game with PyInstaller (Windows executable)
- [ ] Implement Steam save file location (AppData)
- [ ] Implement multiple franchise slots (player can run multiple saves)
- [ ] Create Steam store page assets (screenshots, description, tags)
- [ ] Write Early Access disclaimer (features planned, known limitations)

### Content
- [ ] Expand to multiple save slots
- [ ] Add "Historical Mode" toggle (import real NFL-style team structures and rosters via community data files — avoids licensing by making it a user-generated import, not a shipped asset)

---

## Post-Launch Backlog (v1.1 and Beyond)

These features are explicitly deferred. They are not forgotten — they're documented here so the data model (Layer 3) was designed to support them.

| Feature | Why Deferred | Target Version |
|---|---|---|
| Practice squad & full waiver wire rules | Complex to implement correctly; core game works without it | v1.1 |
| Locker room chemistry system | Adds depth but requires testing; satisfaction system covers the basics | v1.1 |
| Financial system (ticket prices, jersey sales) | Scope risk; owner budget abstraction covers what's needed | v1.2 |
| Multiplayer / online leagues | Architecture change; single-player must be solid first | v2.0 |
| Historical replay mode (real seasons) | Licensing complexity; needs community data import system | v1.2 |
| International players / USFL/XFL pipeline | Nice to have; core NFL draft system first | v1.2 |
| 2D match visualizer | Significant engineering investment; text sim ships first | v2.0 |
| Expansion teams / relocation | Requires league structure changes | v1.3 |
| Commissioner mode (edit everything) | Community request likely; low complexity to add post-launch | v1.1 |
| Modding support | Community data files for real rosters | v1.2 |

---

## Build Sequence Summary

```
Week 1–3   │ Phase 0: Foundation
            │ Database schema, team/player generation, schedule
            │
Week 4–10  │ Phase 1: Simulation Engine           ← START HERE
            │ Play resolution, narration, weather, injury, fatigue
            │ [1-week tuning sprint at end of Phase 1]
            │
Week 11–14 │ Phase 2: Full Season
            │ Season loop, standings, playoffs, archive, development
            │
Week 15–20 │ Phase 3: Offseason Loop
            │ FA, contracts, trades, scouting, draft, satisfaction
            │
Week 21–26 │ Phase 4: Dynasty
            │ 3-season stability, legacy score, media/pressure, AI GM
            │
            │ ← INTERNAL MVP ←
            │
Month 7–18 │ Steam Early Access Prep
            │ UI, polish, tuning, Steam integration
```

---

## The One Rule

**Never build a UI for a system that isn't working.**

The most common indie game development failure is spending months on interface design before the simulation underneath it is solid. A beautiful draft board on top of a broken engine ships broken. An ugly but accurate engine gives you something real to build on.

Every phase in this roadmap ends with a playable system test — not a mockup, not a demo, but a real query or simulation you can run and evaluate. If the output doesn't feel right, fix it before moving to the next phase.

---

*The GDD is complete. Next step: begin Phase 0 implementation.*
