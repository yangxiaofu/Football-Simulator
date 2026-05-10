# Football Simulator — Game Design Document
## Layer 2: Simulation Specification

**Version:** 0.1 (Draft)
**Author:** David Dong
**Date:** May 9, 2026
**Status:** Working Draft
**Depends on:** GDD_Layer1_CoreDesign.md

---

## Overview

Layer 2 defines the actual rules of the simulation engine — the math, logic, and decision trees that turn player attributes into play outcomes, plays into games, and games into seasons. This document is the bridge between design vision (Layer 1) and data architecture (Layer 3).

Every design decision in this layer was made to serve one principle: **the simulation should reward smart roster and scheme decisions, not just roll dice.**

---

## 1. The Rating System

### 1.1 External Representation — Letter Grades

Players are displayed to the user using a **letter grade scale (A+ to F)**. This is the only representation the player sees in the UI. Grades communicate quality intuitively and preserve scouting uncertainty (a scout's grade is an estimate; the grade doesn't pretend to be a precise number).

| Grade | Numeric Equivalent | Description |
|---|---|---|
| A+ | 97–99 | Generational / All-Pro |
| A | 93–96 | Elite starter |
| A- | 90–92 | Pro Bowl level |
| B+ | 87–89 | Solid starter, above average |
| B | 83–86 | League-average starter |
| B- | 80–82 | Below-average starter |
| C+ | 77–79 | Fringe starter / strong backup |
| C | 73–76 | Backup / depth player |
| C- | 70–72 | Practice squad level |
| D+ | 67–69 | Replacement level |
| D | 60–66 | Camp body |
| F | Below 60 | Not NFL-caliber |

### 1.2 Internal Representation — Numeric Values

The simulation engine operates exclusively on **integer values (1–99)**. Letter grades are a UI translation layer only. All probability calculations, matchup resolutions, and outcome generation use the raw numeric values.

This separation matters for two reasons:
- It keeps the UI clean and accessible
- It allows scouting inaccuracy to be modeled precisely (a scout might show you "B+" when the true value is 79 — both display as B+, but they're different numbers)

### 1.3 Player Overall Rating

Every player has a **composite Overall rating** — a weighted average of their relevant position attributes. The weighting is position-specific.

**Example — QB Overall Weighting:**
| Attribute | Weight |
|---|---|
| Accuracy (Short) | 20% |
| Accuracy (Medium) | 20% |
| Accuracy (Deep) | 10% |
| Pocket Presence | 15% |
| Football IQ | 20% |
| Mobility | 5% |
| Arm Strength | 10% |

**Example — CB Overall Weighting:**
| Attribute | Weight |
|---|---|
| Man Coverage | 25% |
| Zone Coverage | 20% |
| Press Coverage | 15% |
| Ball Hawk | 15% |
| Speed | 15% |
| Tackling | 10% |

The Overall is recalculated whenever an individual attribute changes (development, injury, age decline). It is the number shown when "Overall" is referenced in the UI — translated to a letter grade.

### 1.4 Scheme Fit Modifier

Raw Overall rating is **not** what the simulation engine uses. The engine uses a **Scheme-Adjusted Rating (SAR)** calculated as:

```
SAR = Overall + (Scheme Fit Bonus × Fit Multiplier)
```

Scheme fit is assessed by matching a player's attribute profile to your current offensive or defensive scheme. The fit multiplier is set by your coordinator's Scheme Expertise rating.

**Example:**
- A zone-coverage CB (Man: B-, Zone: A) in a man-heavy scheme: SAR penalty of −6
- Same CB in a zone scheme with a DC who has elite Zone expertise: SAR bonus of +8
- Net swing: 14 points — the difference between a solid starter and a liability

Scheme fit is one of the primary reasons player trades and free agent signings require more thought than just sorting by Overall.

---

## 2. The Play Resolution Model

### 2.1 Core Architecture — Matchup-Based Resolution

Every play is resolved as a series of **1v1 matchup battles**. The result of the play emerges from the combined outcomes of those individual battles, not from a single team-vs-team calculation.

This means the simulation is inherently granular: a great WR can win a game against a poor secondary even on a weak team. A dominant pass rusher can wreck a QB behind a bad OL. Individual excellence matters — but depth determines consistency.

### 2.2 The Matchup Probability Function

When two players contest a matchup, the probability of the attacking player winning is calculated using a **logistic (sigmoid) function**:

```
P(attacker wins) = 1 / (1 + e^(-k × (SAR_attacker - SAR_defender)))
```

Where **k = 0.07** (a tuning constant that controls curve steepness).

**Reference table (attacker win probability by rating differential):**

| Rating Differential | Win Probability |
|---|---|
| +30 (attacker far superior) | ~88% |
| +20 | ~80% |
| +10 | ~68% |
| 0 (even matchup) | 50% |
| −10 | ~32% |
| −20 | ~20% |
| −30 | ~12% |

This ensures that upsets are possible but not fluky — a C+ WR won't consistently beat an A CB, but they'll win occasionally, which is realistic. An A+ pass rusher against a D+ tackle will win almost every time but not literally every snap.

### 2.3 Play Type Resolution Trees

#### PASS PLAY — Resolution Sequence:

**Step 1 — Pre-Snap Read (QB Football IQ vs. DC Disguise Rating)**
- QB reads the defensive alignment
- If QB IQ beats the DC's disguise rating: QB identifies the coverage pre-snap → bonus to the correct route concept
- If DC disguise beats QB IQ: QB operates on an incorrect coverage assumption → possible misread, late throw, or scramble

**Step 2 — Pass Rush (OL Pass Block vs. DL Pass Rush)**
- Resolve each OL–DL matchup individually (up to 5 on the line + blitzers)
- Blitz decisions come from the DC's tendency settings and down/distance situation
- Count of wins vs. losses determines **Pocket Time Generated:**
  - 4–5 OL wins → clean pocket (full accuracy rating applied)
  - 2–3 OL wins → disrupted pocket (accuracy penalty −5 to −15)
  - 0–1 OL wins → collapsed pocket (QB must scramble or force throw; sack probability spike)

**Step 3 — Route vs. Coverage (WR Route Running vs. CB Coverage Type)**
- Resolve the targeted receiver's matchup against their assigned defender
- Separation generated is a continuous value (yards of separation at the throw point)
- Safety help (zone coverage rating) applies a modifier if coverage scheme provides over-the-top help

**Step 4 — The Throw (QB Accuracy + Pocket Time + Separation)**
- Completion probability calculated from:
  - QB Accuracy (zone-specific: short/medium/deep based on throw distance)
  - Pocket time modifier from Step 2
  - Separation value from Step 3
  - Target's Catch rating vs. defender's Pass Breakup rating

**Step 5 — After the Catch (YAC)**
- If caught: receiver's Yards After Catch rating determines additional gain
- Tackle probability: tackler Tackle rating vs. ball carrier Elusiveness + YAC rating

**Possible outcomes:** Completion + gain, incomplete (coverage), incomplete (drop), sack, scramble + gain, scramble + out of bounds, interception

---

#### RUN PLAY — Resolution Sequence:

**Step 1 — Gap Assignment (OC Run Scheme + OL Zone/Power Rating)**
- The called run type (inside zone, outside zone, power, counter, etc.) is matched against OL's scheme-specific run blocking rating
- Each OL blocks their assigned gap — resolve 1v1 vs. the DL defender in that gap
- Results map to: sealed (great block), pushed (neutral), beaten (immediate penetration)

**Step 2 — Second Level (LB Fill + RB Vision)**
- RB Vision rating determines how quickly they identify the correct gap from the OL resolution
- High Vision: RB finds the best available lane even if initial gap is closed
- Low Vision: RB commits to the called gap regardless — runs into sealed blocks
- LB Rating determines how quickly linebackers fill and shed blocks from the second level

**Step 3 — Ball Carrier vs. Open Field Tackler**
- If the RB reaches the open field: RB Elusiveness + Speed vs. DB Pursuit + Tackle rating
- Result: tackle, broken tackle, or open field run

**Possible outcomes:** Loss, short gain (0–2), standard gain (3–5), chunk gain (6–10), breakaway run (11+), fumble

---

#### Special Teams — see Section 6

---

### 2.4 Coordinator Influence on Resolution

Your coaching staff does not play the game — they shape the probability environment the players perform in.

| Staff Role | Mechanic Influenced | How |
|---|---|---|
| OC | Play selection efficiency | Better OC → called plays match the defensive look more often; fewer wasted snaps |
| DC | Disguise rating | DC Scheme Expertise sets the pre-snap disguise value in Step 1 of pass resolution |
| OL Coach | OL technique bonus | Adds a flat bonus to all OL matchup ratings in Steps 2 (pass) and 1 (run) |
| WR Coach | Route running efficiency | Adds a bonus to WR route running in high-leverage situations (3rd down, red zone) |
| QB Coach | Accuracy under pressure modifier | Reduces the pocket-disruption accuracy penalty in Step 4 |
| RB Coach | Vision modifier | Adds to RB Vision in Step 2 of run resolution |
| DB Coach | Coverage technique bonus | Adds to CB Zone/Man coverage rating in pass coverage step |
| ST Coordinator | All special teams probability adjustments | See Section 6 |

These bonuses are **not cosmetic** — they're real numeric modifiers applied inside the resolution calculations. A great OL Coach on a mediocre OL can meaningfully change the pocket time distribution. This is the mechanical reason staff hiring matters.

---

## 3. The Randomness Model

### 3.1 Weighted Probability — Not Pure RNG

The engine uses **weighted probability**: outcomes are never deterministic, but the probability distribution is always anchored to player quality and matchup results. The goal is that over a full game (60–80 plays), quality wins — but individual plays can surprise.

A 90-rated CB holds a 75-rated WR to 2 catches in most simulations. But occasionally that WR has a 6-catch game. That variance is intentional — it mirrors real NFL outcomes and prevents the game from feeling scripted.

### 3.2 Variance Tuning Parameters

The engine exposes several **tuning constants** that control how "swingy" the simulation feels. These are adjustable during development to dial in the right feel:

| Parameter | Default | Effect |
|---|---|---|
| `k` (matchup curve steepness) | 0.07 | Lower = more upsets; higher = more dominant favorites |
| `variance_cap` | ±15 | Max random modifier applied to any single play outcome |
| `big_play_rate` | 0.08 | Probability any completion results in a 20+ yard gain |
| `turnover_base_rate` | 0.012 | Base per-play fumble/INT probability before modifiers |

These constants are not exposed to the player — they're developer levers that will need tuning once a working prototype exists.

### 3.3 Clutch Modifier (Situational Pressure)

While the primary randomness model is weighted probability, **Clutch** is handled as a situational modifier rather than a standalone system.

Every player has a hidden **Clutch rating (1–99)**. It activates in defined high-pressure situations:
- 4th quarter with score within 7 points
- 2-minute drill (under 2:00, trailing)
- 3rd & 5+ (conversion attempt)
- Playoff games (flat +5 modifier to Clutch activation frequency)

When Clutch activates, the player's relevant attribute ratings are modified by:
```
Clutch modifier = (Clutch_rating - 50) / 10
```
A player with Clutch 80 gets +3 to their relevant ratings in clutch moments.
A player with Clutch 30 gets −2.

This creates star players who rise in big moments and role players who wilt — without making clutch feel like a separate game mechanic.

---

## 4. Play Calling — Game Plan + Override

### 4.1 The Weekly Game Plan

Before each game, you set your **offensive and defensive tendency sliders.** These are percentage allocations that define how the AI selects plays throughout the game:

**Offensive Tendencies:**
- Run / Pass split (e.g., 40% run / 60% pass)
- Short / Medium / Deep pass distribution
- Aggressiveness on 3rd down (go for it on 4th & short: always / situational / never)
- Red zone preference (run-heavy / balanced / pass-heavy)
- Two-minute drill style (quick throws / scramble-friendly / conservative clock management)

**Defensive Tendencies:**
- Base coverage (man / zone / mixed)
- Blitz frequency (conservative / moderate / aggressive)
- Run stop priority (load the box vs. play the pass)
- Late-game coverage mode (prevent / normal / press)

These tendencies interact with your OC and DC's Scheme Expertise — a DC with high Blitz Package rating executing an aggressive blitz tendency is more effective than a poor DC running the same tendency.

### 4.2 In-Game Overrides

The AI runs your tendency-based game plan for the majority of the game. However, on **critical downs**, the game pauses and offers you a manual override opportunity:

**Override trigger situations:**
- 3rd & 4 or less (short conversion)
- 4th down decisions (punt / kick / go for it)
- Red zone (inside the 10-yard line)
- 2-minute drill (trailing or protecting a lead under 2:00)
- Overtime possession decisions

When an override triggers, you see:
- Current down, distance, score, time
- 3–4 play options with brief descriptions
- A risk/reward indicator for each option
- Your OC's recommendation (based on their rating — a great OC recommends the right play more often)

You can accept the AI's recommendation or override it. Overriding against the OC's recommendation is always your right — but a great OC being ignored consistently creates a staff relationship tension event (see Media & Pressure system in Layer 1).

### 4.3 Halftime Adjustments

At halftime, you make **scheme adjustments** that modify your tendency sliders for the second half:

- React to what the defense is showing (your DC identifies tendencies your opponent exploited in Q1/Q2)
- Shift the run/pass split based on what's working
- Change coverage scheme if your secondary is getting beaten

Halftime adjustment quality is influenced by your HC Football IQ rating (you) — a mechanic that represents your ability to make good mid-game reads. This is one of the few places where your own hidden rating matters.

---

## 5. The Injury System

### 5.1 Per-Play Injury Probability

Every snap carries a **base injury probability** determined by three factors:

```
P(injury) = Base_Rate × Durability_Modifier × Fatigue_Modifier
```

- **Base_Rate:** 0.004 (0.4% per play — roughly 2–3 injuries per game across all players, matching real NFL rates)
- **Durability_Modifier:** Player's Durability rating scales this. A Durability A player has 0.6× the base rate. A Durability D player has 1.8×.
- **Fatigue_Modifier:** Fatigued players (stamina below 40%) have 1.3× injury probability

### 5.2 High-Contact Situation Multipliers

Specific play types apply a multiplier to the base injury probability for players involved in that play:

| Situation | Affected Player | Multiplier |
|---|---|---|
| Sack taken | QB | 3.5× |
| High-speed collision (open field) | Ball carrier, tackler | 2.0× |
| Jump ball contested catch | WR, CB | 2.2× |
| Goal-line pile (inside the 2) | OL, DL, RB | 2.5× |
| Scramble (QB runs) | QB | 2.8× |
| Punt coverage | Coverage team | 1.8× |
| Kickoff return | Returner | 2.0× |

### 5.3 Injury Severity Classification

When an injury triggers, severity is rolled from a weighted distribution:

| Severity | Duration | Probability |
|---|---|---|
| Questionable (minor) | Miss 0–1 games | 50% |
| Week-to-week | Miss 2–4 games | 25% |
| IR — Short | Miss 5–8 games | 12% |
| IR — Season-ending | Miss remainder of season | 8% |
| Career-altering | Permanent attribute reduction (−5 to −15) | 4% |
| Career-ending | Player retires immediately | 1% |

Career-altering injuries permanently modify the affected attribute (e.g., ACL tear reduces Speed and Elusiveness; shoulder injury reduces QB Arm Strength). These are rare but consequential — and they're one of the reasons depth management matters.

### 5.4 The Injury Report

Each week, an **injury report** is generated for your roster and all 31 opponents:

- **Confirmed Out:** Will not play this game
- **Doubtful:** 25% chance of playing
- **Questionable:** 50% chance of playing
- **Probable:** 85% chance of playing

Opponent injury status is partially obscured — teams can list players as Questionable to hide true availability. Your Free Agent Scout's Medical Eye rating improves your ability to read through the deception.

---

## 6. The Fatigue System

### 6.1 Weekly Stamina (Game-to-Game Management)

Every player has a **Stamina Pool (0–100)** that resets partially each week based on rest and practice load.

**Stamina drains during a game:**
- Each snap played draws from the stamina pool based on position (linemen drain faster than kickers)
- High-effort plays (sacks, explosive runs, contested catches) drain additional stamina

**In-game stamina effects:**
- Stamina 80–100: Full ratings applied
- Stamina 60–79: No effect (normal play)
- Stamina 40–59: −3 to relevant ratings (mild fatigue)
- Stamina 20–39: −8 to relevant ratings (visible fatigue)
- Stamina below 20: −15 to ratings + injury probability doubles (should be substituted)

**Weekly stamina recovery:**
Recovery per week depends on player's Stamina Recovery rating and practice intensity you set (light / normal / intense). Intense practice improves development speed but leaves players less recovered for game day.

### 6.2 Cumulative Season Wear (Week 10 Onward)

From **Week 10** of the regular season, high-contact position players accumulate **Season Wear** — a separate variable that degrades performance regardless of weekly recovery.

**Positions affected (wear rate per week):**
| Position | Wear Rate |
|---|---|
| RB | −1.5 points per week |
| OL / DL | −0.8 points per week |
| LB | −0.7 points per week |
| QB (if scrambler) | −0.5 per week |
| WR / TE (high-usage) | −0.4 per week |
| All others | Negligible |

Season Wear applies as a flat modifier to SAR from Week 10 through the Super Bowl. A RB who was an 85 in September is effectively an 80 by Week 17 — unless you managed their carries wisely.

**Managing wear:** Lower usage (carries per game) reduces the wear rate. Splitting carries between your RB1 and RB2 extends your starter's effectiveness into January. This creates meaningful roster depth decisions throughout the season.

---

## 7. Special Teams Simulation

Full play-by-play narration for all special teams plays. Your Special Teams Coordinator (STC) rating acts as a global modifier across all special teams categories.

### 7.1 Field Goal Attempts

**Resolution inputs:**
- Kicker Accuracy rating (short: <40 yards, medium: 40–49, long: 50+)
- Distance modifier (each yard beyond 40 reduces base probability by ~2%)
- Weather modifier (wind speed and direction; precipitation reduces accuracy)
- Pressure modifier (late-game, close score activates Clutch)
- OL Protection rating (affects snap + hold quality; blocked kick probability)
- STC rating (execution modifier ±5%)

**Narrated output:**
```
4th & 2 | NYG 31 | 0:08 | Q4
→ Flores lines up for 47 yards. Wind: 12 mph crosswind (left to right).
→ Snap is clean. Hold is down.
→ The kick is UP... and it's GOOD. 47 yards.
   [Flores: 3/3 FG today | Season: 22/26]
```

### 7.2 Punts

**Resolution inputs:**
- Punter Power rating → gross punt distance
- Punter Directional Accuracy rating → hang time and placement (pin inside 20)
- Coverage team ratings → coverage speed and tackle probability on returner
- Returner Elusiveness + Speed → return yardage

**Outcomes:** Touchback, fair catch, downed inside the 20, returned (with yardage), muffed punt (fumble probability: low)

### 7.3 Kickoffs

**Resolution inputs:**
- Kicker Power rating → depth of kick
- Coverage team Speed rating → time to the returner
- Returner Speed + Elusiveness → return success probability

**Outcomes:** Touchback (no return), returned with yardage, returned for TD (low probability)

### 7.4 Blocked Kicks

**Blocked kick probability** exists on every field goal and punt attempt. Influenced by:
- OL Protection rating (higher = better protection)
- Opponent STC rating (higher opponent STC = better block schemes)
- Snap and hold quality (small random variance)

Base blocked kick probability: ~1.5% per attempt (matching real NFL rates), modified by the above.

### 7.5 STC Rating as Global Modifier

Your Special Teams Coordinator's rating applies a **flat modifier** to all special teams probability calculations:

| STC Rating | Modifier |
|---|---|
| A / A+ | +8% to all favorable outcomes |
| B | +3% |
| C | No modifier (baseline) |
| D | −5% |
| F | −10% |

A great STC makes your kicker look better, your coverage units faster, and your return game more dangerous. A poor STC drags every unit down. Special teams is often the hidden difference between an 8-win team and a 10-win team — and it should feel that way.

---

## 8. The Season Simulation Model

### 8.1 One Season = 17 Game Weeks + Playoffs

Each regular season game is simulated as a full play-by-play event. The simulation engine generates approximately **130–160 plays per game** (both teams combined), narrating each one.

The player experiences each game one of two ways:
- **Active (default):** Watch the play-by-play log in real time, with the option to make override decisions on critical downs
- **Fast sim:** Skip to the final score with a highlight summary of 5–8 key plays

### 8.2 Game State Variables

The engine tracks a full game state at all times:

```
GameState {
  quarter: 1–4 (+ OT)
  time_remaining: seconds
  score: {home, away}
  possession: team_id
  field_position: yard_line
  down: 1–4
  distance: yards to first down
  timeout_remaining: {home, away}
  active_weather: {wind_speed, precipitation, temperature}
  player_stamina: {player_id: stamina_value}
  active_injuries: {player_id: severity}
}
```

### 8.3 Home Field Advantage

Home teams receive a **+3 SAR modifier** on all player ratings during home games — simulating crowd noise, familiarity, and travel disadvantage for the visiting team. Stadiums with high fan sentiment ratings (from Layer 1 Media system) amplify this to +5.

### 8.4 Weather System

Each game generates a **weather condition** based on city and time of year:

- Dome stadiums: No weather effect (always controlled conditions)
- Cold-weather cities (Green Bay, Buffalo, Chicago) in November–January: High probability of cold + wind
- Warm-weather cities (Miami, Tampa, LA): Rare weather impact

**Weather effects on simulation:**
| Condition | Effect |
|---|---|
| Wind > 15 mph | Deep pass accuracy −10, FG probability −8% beyond 45 yards |
| Rain / Snow | Ball carrier Fumble rate +0.3%, Kicker accuracy −5% |
| Cold < 25°F | All Speed ratings −3, Stamina drain rate +15% |
| Extreme cold < 10°F | Speed −6, all accuracy ratings −5 |

### 8.5 Overtime Rules

Follows NFL sudden-death overtime rules:
- Each team gets a possession in the first OT period
- If tied after both possessions: next score wins
- Playoff OT: Full 10-minute period; game continues until a winner is determined

---

## 9. Key Simulation Design Rules

These are non-negotiable principles that must hold true in every version of the engine:

1. **Individual excellence is visible but not invincible.** An A+ pass rusher creates pressure most snaps — but a great OL or quick-release QB neutralizes them.

2. **Depth is rewarded across 17 games.** A team with a great starting 11 but poor depth will visibly decline from Week 13 onward as injuries and wear accumulate.

3. **Scheme fit is a real multiplier.** Two teams with identical Overall ratings but different scheme alignment will perform differently — consistently enough that players notice and care.

4. **Staff quality is visible over a season, not a game.** A great OC doesn't guarantee a win. A great OC over 17 games produces measurably better play selection efficiency and QB performance.

5. **Special teams are not an afterthought.** A blocked kick, a 30-yard punt return, or a missed FG should feel like a real momentum swing — because the simulation treats it as one.

6. **Randomness serves drama, not frustration.** Upsets happen within realistic probability bands. An 85-overall team losing to a 70-overall team is possible — it should feel unlikely, not broken.

---

*Next: Layer 3 — Data Model (entities, attributes, relationships, and database schema design)*
