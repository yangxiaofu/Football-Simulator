# Football Simulator — Game Design Document
## Layer 1: Core Design Vision

**Version:** 0.1 (Draft)
**Author:** David Dong
**Date:** May 9, 2026
**Status:** Working Draft

---

## 1. Elevator Pitch

A deep, text-based NFL franchise simulator that puts the player in dual control as both General Manager and Head Coach. Every snap is narrated. Every contract matters. Every hire shapes your roster's ceiling. Your goal isn't just to win a Super Bowl — it's to build something that lasts: a dynasty measured in rings, records, and a Hall of Fame legacy.

Think *Out of the Park Baseball*, but built from the ground up for American football — with a true play-by-play simulation engine, a coordinator and staff layer that actually influences outcomes, and a media and fan pressure system that makes every losing streak feel real.

---

## 2. Core Vision Statement

> "You didn't just win the Super Bowl. You built an organization that was supposed to lose — and turned it into a machine."

The emotional payoff of this game is **dynasty**. Not a lucky single-season run, but sustained excellence built from three equally weighted pillars:

- **The Draft** — finding gems late, developing unknowns into stars, and building your board better than 31 other GMs
- **Scheme Fit** — assembling a staff whose system extracts the most from the talent you have
- **Cap Management** — keeping your core together, avoiding dead money traps, and building the depth to survive injuries

A player who nails all three builds a dynasty. A player who ignores one eventually collapses. That tension is the game.

---

## 3. The Player's Role

The player holds two titles simultaneously: **General Manager** and **Head Coach**.

### As General Manager, you control:
- The draft (pre-draft scouting, board construction, day-of picks)
- Free agency (signing, releasing, restructuring contracts)
- Trades (player and pick-based)
- Salary cap management and contract negotiations
- Staff hiring (Head Coach is you — but you hire coordinators, position coaches, scouts, and front office staff)

### As Head Coach, you control:
- Offensive and defensive scheme selection
- Depth chart decisions and positional priorities
- Weekly game plan (tendencies, target distribution, defensive focus)
- In-game adjustments during simulated play-by-play
- Player usage and development priorities

### What the AI handles:
- Opposing team decisions (their draft picks, FA signings, game-planning)
- Officiating, weather, and game-day randomness
- League-wide events (injuries, suspensions, retirements)

---

## 4. The Game Loop

The game operates on a **franchise calendar** — a year-round NFL-style schedule broken into distinct phases. Each phase has its own decisions, pressures, and consequences.

### Franchise Calendar Overview

| Phase | Timing | Key Decisions |
|---|---|---|
| Scouting Season | Jan–Feb | Build draft board, assign scouts, attend combine |
| Free Agency | March | Sign, release, restructure — cap management pressure |
| NFL Draft | April | 7-round draft with your board vs. team needs |
| OTAs / Training Camp | May–Aug | Depth chart battles, injury risks, scheme installs |
| Preseason | Aug | Final roster cuts, evaluate bubble players |
| Regular Season | Sep–Jan | 17 weeks of games + weekly management decisions |
| Playoffs | Jan | Single-elimination bracket |
| Offseason Review | Feb | Legacy scoring update, staff evaluations, owner meeting |

Each week of the regular season, the player faces a **Weekly Decision Cycle:**
1. Review injury report and opponent tendencies
2. Set depth chart and game plan for the upcoming game
3. Simulate the game (play-by-play)
4. Handle post-game media and fan sentiment
5. Manage any mid-week transactions (waiver wire, practice squad)

---

## 5. Game Simulation — The Play-by-Play Engine

The beating heart of the game. When you simulate a game, you experience it as a **full play-by-play text log** — every snap narrated, every drive unfolding in real time.

### What the simulation engine resolves:

**Before the snap:**
- Down, distance, field position, score, time
- Offensive play call (influenced by your game plan tendencies)
- Defensive call (influenced by opponent tendencies and your DC's scheme)

**On the snap:**
- Player ratings interact with scheme fit and opponent matchups
- Randomness is applied within probability ranges (not pure RNG — elite players perform elite *more often*)
- Result is generated: gain/loss, completion/incompletion, penalty, turnover, score

**Narrated output example:**
```
Q2 | 2nd & 7 | OWN 34 | 10:42
→ Shotgun, 3-wide. Williams motions to the slot.
→ Play-action fake to Harrison. Coverage rotates.
→ Williams finds the seam — caught for 14 yards. FIRST DOWN.
   [Williams: 3 rec, 41 yds | Coverage bust by CB #24]
```

### Key design principles for the engine:
- **Scheme fit amplifies ratings** — a scheme-fit C+ player can outperform a scheme-misfit A player in specific situations
- **Coordinator quality affects play calling efficiency** — a poor OC wastes talented players; a great DC hides defensive weaknesses
- **Fatigue and depth matter** — a thin roster gets exposed in Q4 and in Week 15
- **Weather and field conditions** affect passing efficiency, kicking, and fumble rates

---

## 6. Player Development Philosophy

Player development follows **realistic NFL career curves** — grounded in how football careers actually unfold, with enough variance to generate surprises.

### Core Principles:

**Age-based trajectory:** Players have position-specific prime windows.
- QBs: Peak at 28–33 (reads, pocket presence improve with age)
- RBs: Peak at 24–27 (explosive decline begins early)
- WRs: Peak at 26–30 (route running matures, athleticism declines)
- OL/DL: Peak at 27–31 (technique-heavy, longer primes)
- DBs: Peak at 25–29 (athleticism-dependent, faster decline)

**Hidden potential with scouting variance:** Players have a true development ceiling, but your scouts only give you an estimate — with accuracy tied to scout quality and positional experience. A 4th-round pick might be a hidden gem. A 1st-round pick might bust.

**Development factors that move the needle:**
- Coaching quality (position coach rating affects skill progression)
- Scheme fit (players in their natural scheme develop faster)
- Injuries (significant injuries can permanently lower ceilings or accelerate decline)
- Workload (overworked players — especially RBs — decline faster)

**Late bloomers and early burnouts exist by design** — because the NFL has them, and they're some of the best stories.

---

## 7. The Staff & Coordinator Layer

This is one of the features that separates this game from anything currently on the market. Your coaching staff is not cosmetic — it directly influences simulation outcomes.

### Staff Positions That Matter:

| Role | Key Influence |
|---|---|
| Offensive Coordinator | Play-calling efficiency, QB development, red zone conversion |
| Defensive Coordinator | Scheme execution, blitz packaging, coverage disguise |
| QB Coach | QB progression speed, reading improvement, pocket awareness |
| OL Coach | Pass protection efficiency, run blocking scheme fit |
| WR Coach | Route running development, separation rates |
| RB Coach | Vision/contact balance ratings, pass protection ability |
| DB Coach | Coverage ratings, ball hawk development |
| Special Teams Coordinator | Kicking accuracy, return game, coverage units |
| Head Scout | Draft board accuracy, regional scout management |

### Staff ratings include:
- **Teaching ability** — how fast they develop young players
- **Scheme expertise** — how well they execute specific systems (4-3 vs 3-4, zone vs man, spread vs pro-style)
- **Motivation** — clutch performance lift in high-stakes games
- **Loyalty** — likelihood of leaving for a better opportunity

Hire the wrong OC and your QB's development stalls. Fire a great position coach mid-season and watch your unit regress. The staff layer creates a management meta-game within the franchise.

---

## 8. The Media & Pressure System

The third differentiating feature. You are not simulating in a vacuum — you are a public figure running a franchise under scrutiny.

### Pressure Sources:

**Owner Expectations:** At the start of each season, your owner sets a minimum bar (make playoffs / win division / Super Bowl or else). Fall short and face a contract discussion. Fall short twice and you're fired.

**Fan Sentiment:** A rolling approval rating influenced by wins, losses, draft results, and how you handle the media. Low fan sentiment reduces revenue (affects owner patience). High sentiment gives you more rope to rebuild.

**Media Events:** Several times per season, you face a media moment — a press conference question, a locker room leak, a trade demand, a player controversy. Your response choice affects morale, fan sentiment, and player relationships.

**Hot Seat Mechanic:** Losing streaks, draft busts, or cap disasters trigger escalating pressure events. The game doesn't fire you instantly — it lets you feel the walls closing.

**Examples of media events:**
- "Your star WR skipped voluntary OTAs — what's your message to the team?"
- "A national reporter claims your locker room is divided. How do you respond?"
- "The owner is reportedly considering a rebuild. Do you address it publicly?"

Responses are multiple-choice, each with simulated consequences to morale, fan sentiment, or player loyalty.

---

## 9. League Structure (MVP Scope)

### Default Configuration:
- **32 teams** modeled after real NFL franchises (city, nickname, division, conference)
- **Fictional players** generated at game start to avoid licensing issues (real team structures, fictional rosters)
- **Real NFL schedule format:** 17-game regular season, 7-team playoff bracket, Super Bowl

### Player generation at game start:
- Each team's roster is procedurally generated to reflect their real-world competitive window (contenders start with higher-rated rosters; rebuilding teams start weaker)
- Age distribution mirrors a realistic NFL roster (mix of young, prime, and veteran players)
- Contracts are pre-assigned to create realistic cap situations across all 32 teams

### Licensing note:
Using real team names and cities without a license carries legal risk for Steam distribution. **The MVP will be built with fictional team names** (e.g., "Los Angeles Wolves" instead of "LA Rams") with a future planned feature for user-created data files that import real names — a common workaround used by OOTP and Football Manager.

---

## 10. Win Conditions & The Legacy Score

The game has no single "end state." A career can last 5 seasons or 40. What defines success is your **Legacy Score** — a composite rating calculated at the end of every season and tallied at career end.

### Legacy Score Components:

| Category | What it Measures | Weight |
|---|---|---|
| Championships | Super Bowl wins, conference titles | 35% |
| Win Record | Career winning percentage | 20% |
| Player Development | Stars developed from lower-rated prospects | 20% |
| Cap Stewardship | Avoiding dead money disasters, smart long-term deals | 10% |
| Longevity | Seasons coached, franchises rebuilt | 10% |
| Media Legacy | How the press covered your tenure | 5% |

### Hall of Fame Threshold:
A career Legacy Score above a defined threshold unlocks a **Hall of Fame induction ceremony** — a narrative end-game moment that summarizes your franchise's story. Multiple HOF careers in one save file are possible (if you cycle through franchises).

### Dynasty Recognition:
Three or more Super Bowl wins in a 10-season window triggers a **Dynasty Flag** on your franchise — a permanent marker in the league's historical record.

---

## 11. What This Game Is NOT (MVP Scope Boundaries)

To ship a focused, high-quality MVP, the following are explicitly out of scope for v1.0:

- **No real player names or likenesses** (fictional rosters only at launch)
- **No multiplayer or online leagues** (single-player career only)
- **No 3D or 2D match visualization** (pure text simulation)
- **No historical replay mode** (planned for a future update)
- **No player control** (you do not control individual players on the field)
- **No salary arbitration or player holdouts** (simplified contract system in MVP)
- **No international leagues or expansion teams** (fixed 32-team NFL structure)

---

## 12. The One-Sentence Design Test

Before adding any feature, ask: *"Does this make the dynasty feel more earned, or does it add noise?"*

If it doesn't deepen the draft-scheme-cap triangle, make the play-by-play more meaningful, or raise the stakes of the media/pressure system — it belongs in a future version.

---

---

## 13. The Scouting System

Scouting is the anticipation engine of the franchise. The draft is your most consequential day of the year — and the scouting system is designed so that what you know, and *how well* you know it, is entirely a function of the scouting department you've built.

> **Core design principle:** Your scouting information is only as good as your scouting team.

A well-funded department with experienced, specialized scouts gives you tighter estimates and earlier clarity. A thin, underfunded department leaves you guessing — and sometimes getting burned by a pick you thought was safe.

---

### 13.1 The Scouting Department

Your scouting staff is a sub-layer within your front office. The **Head Scout** manages the department and their rating determines overall department efficiency. Beneath them, you hire **Regional Scouts** and **Specialist Scouts** who cover specific areas and positions.

#### Staff Roles:

| Role | Function |
|---|---|
| **Head Scout** | Sets department efficiency multiplier; oversees board accuracy |
| **Regional Scout (6 regions)** | Covers college programs in their region; number of programs they can track scales with their rating |
| **Specialist Scout** | Deep expertise in one position group; dramatically improves accuracy for their position |
| **Free Agent Scout** | Evaluates veterans; specializes in medical history and film review of older players |
| **International Scout** | (Future feature) Evaluates USFL, XFL, and Canadian players |

#### Scout Ratings (each scout has four attributes):

- **Talent Evaluation** — accuracy of their player grades against true ratings
- **Regional Coverage** — number of programs they can meaningfully track per season
- **Medical Eye** — ability to detect physical decline, injury risk, and recovery quality
- **Character Read** — ability to surface off-field risks, coachability, and locker room fit

A regional scout with high Talent Evaluation but low Medical Eye might rave about a player who is secretly carrying a nagging knee injury. A specialist scout with a high Character Read flags that your top-rated CB has a history of tuning out coaches — something no stat line reveals.

#### Scouting Budget:
Your owner allocates a **scouting budget** at the start of each offseason. Better coaches earn larger budgets. The budget determines how many scouts you can employ and at what salary (which loosely correlates to quality). You can overspend on a single elite Head Scout or build depth with a larger team of average scouts — both are viable strategies with different tradeoffs.

---

### 13.2 The College Draft Scouting Cycle

The college scouting season runs from **September through April** and unfolds in four phases. Each phase unlocks more information — but only if your scouts have been assigned to cover those players.

#### Phase 1 — Early Season Scouting (Sep–Oct)
- A pool of **300–400 college prospects** is generated at the start of each season (across all positions, all rounds)
- Each scout can meaningfully track a limited number of prospects based on their Regional Coverage rating
- **Untracked players** appear on your board as complete unknowns — no grade, no projection
- **Tracked players** receive an initial grade with a wide confidence interval that narrows over time

**Example of initial board entry:**
```
WR | Marcus Webb | Junior | Ohio State
Scout: J. Harrington (Midwest, B+)
Current Grade: B | Range: C+ to A-
Notes: "Elite separation at the line. Hasn't faced press coverage yet."
```

#### Phase 2 — Midseason Film Review (Nov–Dec)
- Scouts submit midseason updates after watching 6–8 games of film
- Grades shift as players face tougher competition (a WR shining against MAC defenses may look different against the Big Ten)
- **Boom/bust signals emerge:** a previously unknown player jumps into your top 50; a hyped prospect shows concerning tendencies under pressure
- Your Head Scout's rating determines how many prospect updates arrive per week

#### Phase 3 — Senior Bowl & Combine (Jan–Feb)
- **Invite-only events** your scouts attend in person
- Players can move significantly on boards based on combine performance (40 time, positional drills, Wonderlic-style interview)
- **Your scouts' assessments of combine performance** vary in accuracy — a scout with a low Talent Evaluation rating may misread a slow 40 time as a talent problem when it's a recovery injury
- You can request **private workouts** for players you're targeting — spending scouting resources for deeper one-on-one evaluation

**Combine surprise events** (procedurally generated each year):
- A mid-round RB runs a 4.28 — suddenly every team is calling about him
- A top-5 QB bombs the interview — character flags surface; teams drop him
- A fringe prospect impresses in positional drills — you might be the only team who noticed

#### Phase 4 — Pre-Draft Intelligence (Mar–Apr)
- Your scouts submit **final board recommendations** with confidence scores
- You can now see **which prospects other teams are visiting** — a leading indicator of draft interest (see §13.4)
- Last-chance private workouts and medical rechecks happen in this window
- Players with injury history get a **medical clearance rating** — a separate signal from their talent grade

---

### 13.3 The Information Fog Model

Every prospect on your board has three layers of information — and what you can see depends on your scouts.

#### Layer 1 — The True Rating (hidden from player)
Every generated prospect has a set of **true ratings** (Speed, Strength, Route Running, Football IQ, etc.) and a **true development ceiling**. These are never directly visible to the player.

#### Layer 2 — Your Scout's Estimate (what you see)
Your scouts translate their observations into a **grade estimate** with an **accuracy range**:

| Scout Quality | Accuracy Range |
|---|---|
| Elite (A-rated scout) | True rating ± 3–5 points |
| Good (B-rated scout) | True rating ± 8–12 points |
| Average (C-rated scout) | True rating ± 15–20 points |
| Poor (D-rated scout) | True rating ± 25+ points (essentially a guess) |

Grades are presented as letter grades (A+, A, A-, B+...) derived from the estimate. A C-rated scout might show you "B+" for a player whose true rating is a C — a costly bust if you use a high pick.

#### Layer 3 — Scouting Flags (qualitative signals)
Beyond the grade, scouts attach **flags** — written observations that hint at information the number doesn't capture:

- 🟢 **Green flags:** "Elite competitor," "Film junkie," "Position coach raves about his preparation"
- 🟡 **Caution flags:** "Inconsistent motor," "Struggles vs. physical corners," "Scheme-dependent production"
- 🔴 **Red flags:** "Multiple soft tissue injuries," "Attitude issues reported by two programs," "Agent known for holdouts"

Flag accuracy also scales with scout quality. A poor scout might miss a red flag entirely. An elite scout with a high Character Read might surface a locker room concern that no other team catches.

---

### 13.4 Other Teams' Interest — The Suspense Engine

This is the feature that turns draft preparation into genuine anticipation. You are not scouting in isolation — 31 other teams are building their boards simultaneously, and you get **partial visibility into their interest**.

#### Intelligence Signals:
Throughout the pre-draft process, your scouts report back on competitor activity:

- **Visits:** "Three teams visited WR Marcus Webb at Ohio State this week. One was confirmed as the Wolves (pick #4)."
- **Private workouts:** "The Crushers (pick #11) requested a private session with your top-rated CB. No other team had done so."
- **Combine attention:** "Webb drew the largest position group crowd at the combine. Buzz has him moving into the top 15."
- **Rumored trades:** "Intel suggests the Falcons are exploring a trade into the top 5. Unknown target."

#### The Mock Draft Feed:
A **league media mock draft** is published weekly from January through April. It aggregates public scouting information — not your private board. The mock draft may be wrong, outdated, or deliberately misleading by agents. But it creates a reference point that drives urgency:

- If your #1 target climbs the mock draft, you may need to trade up
- If a player you thought was a sleeper suddenly appears in the mock at pick #20, your competitive advantage is gone
- If a team trading up is rumored to be targeting your position of need, the pressure builds

#### Board Volatility Events (procedurally generated):
- "A national reporter releases a story claiming Team X will take QB first overall — changing every other team's strategy"
- "Webb's agent leaks that he won't sign with small-market teams — two franchises drop him from their boards"
- "A leaked draft board from an anonymous scout creates chaos — some of it is accurate, some isn't"

This creates a genuine sense that **the draft is a living event**, not a static spreadsheet you fill in at the start of the season.

---

### 13.5 Draft Day Experience

After months of scouting, draft day is a multi-round event with real tension.

#### The War Room:
You enter draft day with your **final board** — a ranked list of all prospects you've evaluated. The board shows:
- Your scout's grade and confidence range
- Flags (green/yellow/red)
- Your positional need weighting
- Any competitor intelligence on that player

#### On the Clock:
When your pick comes up, you see:
- Who is still available (players taken are grayed out with the team that took them)
- Any surprise picks that have already happened (and your scouts' reaction: "We had him rated 15 spots lower — either we missed something or the Crushers panicked")
- Trade offers from other teams for your pick

#### Post-Draft Revelation:
After all 7 rounds complete, your scouts conduct a **post-draft grade review** — comparing your picks' estimated grades against early camp observations. This is the first moment where the fog begins to lift, and you discover whether your scouting was sharp or flawed.

---

### 13.6 Free Agent Scouting — The Partial Fog

Free agents are known quantities on the surface — their career stats are public, their reputations are established, and their agents are actively selling them. But the fog doesn't disappear entirely.

#### What you know about a free agent:
- Career statistics and performance trends
- Historical injury log (public record)
- Previous contract details
- Public reputation (scheme fit, leadership, agent difficulty)
- Age and assumed career stage

#### What remains hidden:
- **True current physical condition** — A 31-year-old RB's career stats look fine, but is the explosion still there? Your Free Agent Scout's Medical Eye rating determines how accurately you assess current physical state vs. career prime.
- **True remaining prime** — A WR at 29 might have 4 good years left or 1. Age curves are probabilistic, not deterministic — and your scout's read influences how accurately you project.
- **Injury recurrence risk** — A player who "recovered" from a torn ACL may have a higher re-injury probability that only a medically skilled scout detects.
- **Locker room fit** — Is the veteran a mentor or a cancer? A scout with high Character Read surfaces this before you sign.

#### Medical Exam Events:
For high-value free agents (projected contracts over a threshold), you can request a **team medical exam** before signing. This spends scouting resources but reveals the player's true physical condition rating — removing the largest source of uncertainty. Skipping the exam is faster and cheaper but carries real risk.

#### Agent Tactics:
A free agent's **agent rating** (a hidden attribute) determines how aggressively they obscure or manage information. A high-rated agent will suppress injury reports, create false bidding wars, and push you toward signing before your medical eval is complete. Recognizing these tactics — and slowing down — is part of the GM meta-game.

---

### 13.7 Scouting as a Competitive Advantage

The scouting system is designed so that **two players with identical rosters but different scouting departments will draft very differently** — and over time, diverge dramatically in roster quality.

A GM who invests in elite scouts, assigns attention wisely, picks up on competitor signals early, and reads free agent fog correctly will consistently find value where others miss it. That is the dynasty engine underneath the dynasty.

---

*Next: Layer 2 — Simulation Specification (the engine rules: how a play is resolved, how ratings map to outcomes, how a season simulates)*
