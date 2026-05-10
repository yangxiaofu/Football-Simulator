# Football Simulator — Game Design Document
## Layer 2B: Transaction & Offseason System Specification

**Version:** 0.1 (Draft)
**Author:** David Dong
**Date:** May 9, 2026
**Status:** Working Draft
**Depends on:** GDD_Layer1_CoreDesign.md, GDD_Layer2_SimulationSpec.md

---

## Overview

The transaction and offseason system is the GM half of the GM + Head Coach role. While Layer 2 defines how games are *played*, this layer defines how rosters are *built* — the decisions made between snaps, between games, and between seasons that determine whether your franchise becomes a dynasty or a cautionary tale.

The offseason is not a menu screen you click through to get back to football. It's a season of its own — with its own tension, its own deadlines, and its own ways to win or lose before Week 1 kicks off.

> **Core design principle:** Every transaction decision carries risk that isn't fully visible at the time you make it. Cap consequences, player satisfaction, team chemistry, and competitive balance all shift with each move.

---

## 1. The Offseason Calendar

The offseason runs from the day after the Super Bowl through the start of training camp. The player advances through each phase **at their own pace** — no phase auto-advances. You move forward when you're ready.

### Full Calendar:

| Phase | Timing (Real NFL Equivalent) | Key Actions |
|---|---|---|
| **End-of-Season Review** | Super Bowl + 1 day | Legacy score update, staff performance review, owner meeting |
| **Staff Evaluation Window** | 1 week | Fire/retain coordinators and position coaches; negotiate extensions |
| **Senior Bowl & Pre-Combine Scouting** | Jan–Feb | Assign scouts to prospects; review early board (see Layer 1 §13) |
| **Franchise Tag Window** | Feb | Apply franchise or transition tags to impending free agents |
| **NFL Combine** | Feb | Combine events; prospect grades update; competitor interest signals emerge |
| **Pre-Draft Free Agency** | Mar | Trade window opens; pre-draft FA signings; contract extensions for your own players |
| **Free Agency Opening (Legal Tampering)** | Mar Day 1 | Contact agents; gauge player interest; assemble offer packages |
| **Free Agency Signing Period** | Mar–Apr | Sign free agents; release cap casualties; restructure contracts |
| **NFL Draft** | Apr | 7 rounds; live trading; picks and players both tradeable |
| **Post-Draft Rookie Signings** | Apr–May | Sign all drafted players to rookie contracts |
| **OTAs / Minicamp** | May–Jun | Voluntary workouts; depth chart previews; injury risk (minor) |
| **Training Camp** | Jul–Aug | Roster battles; preseason injury risk; final 53-man cuts |
| **Preseason Games** | Aug | 3 games; evaluate bubble players; minimal consequence |
| **Final Roster Cuts (53-man)** | Aug | Cut to 53; waiver claims; practice squad assembly |
| **Regular Season** | Sep–Jan | In-season transactions run parallel (see §6) |

---

## 2. Free Agency System

### 2.1 The Interest Tier Model

Every free agent enters the market with a **Destination Preference List** — a ranked set of teams he's willing to sign with, generated before money is discussed. This list is influenced by:

- **Winning culture** (your team's recent win record and playoff appearances)
- **Scheme fit** (does your OC/DC run a system that matches his strengths?)
- **Market size** (larger markets attract players who prioritize exposure and endorsement value)
- **Role clarity** (is he clearly your starter, or competing for a job?)
- **Coach relationship** (did he play for your staff before? Personal history matters)
- **Money proximity** (if your offer is significantly below market, it overcomes preference — downward only)

Players are sorted into **three interest tiers** relative to your franchise:

| Tier | Meaning | Signing Mechanic |
|---|---|---|
| **Tier 1 — High Interest** | Your team is in his top 3 destinations | Full negotiation access; he'll return calls; money is the primary lever |
| **Tier 2 — Neutral** | Your team isn't preferred but isn't ruled out | Requires a competitive offer + a pitch meeting; scheme fit or role can elevate to Tier 1 |
| **Tier 3 — Low Interest** | He doesn't want to play for you | You can still make an offer, but must massively overpay (20%+ above market) or wait until the market cools |

**You don't see tier labels directly.** Instead, your scouts and front office staff give you qualitative intelligence: *"His agent has been returning our calls quickly"* (Tier 1) or *"Word is he'd prefer to stay in the NFC East"* (Tier 3). Your Head Scout's Character Read rating determines how accurate this intelligence is.

### 2.2 The Pitch Meeting

For Tier 2 targets, you can request a **pitch meeting** before making a formal offer. In the pitch meeting, you make the case for your franchise through a short series of choices:

- **Emphasize winning:** Show your team's trajectory and playoff window — effective if you have recent success
- **Emphasize scheme fit:** Highlight how your system is built for his skill set — effective if his stats match your scheme
- **Emphasize role:** Promise him a starter role or a featured usage plan — effective if he's coming off a backup situation
- **Offer money first:** Skip the pitch and lead with the contract — signals desperation; effective for Tier 3 only if the number is extreme

A successful pitch meeting moves the player from Tier 2 to Tier 1. A failed pitch (wrong emphasis for his motivations) keeps him at Tier 2 or moves him to Tier 3.

### 2.3 The Negotiation

Once a player is Tier 1, formal negotiation opens. Negotiation runs in **rounds:**

**Round 1 — Your Opening Offer**
You structure a contract (see §3 for contract mechanics) and submit it.

**Round 2 — Agent Counter**
The agent responds with one of:
- **Accept** — deal is done
- **Counter** — new terms (usually higher AAV, more guarantees, or restructured bonus)
- **Shop** — agent takes your offer to the open market; other teams now know your number and can beat it
- **Walk** — player removes your team from consideration (usually only if you lowballed a Tier 1 player badly)

**Round 3 — Your Response**
Match, counter, or walk away. Most deals close in 2–3 rounds for Tier 1 targets.

### 2.4 Market Dynamics

The free agent market is not static. Signing periods create **market timing decisions:**

- **Early signers** (Legal Tampering / Day 1) cost a premium — teams overpay for certainty
- **Mid-market signers** (Week 2–3 of FA) represent fair value — the market has cleared enough to know true price
- **Late signers** (post-draft, training camp) are bargains — leverage is gone, players sign to secure a roster spot

AI teams also compete in the market with their own budgets and needs. A team with a desperate need at OT will overpay for an OT even if you bid fairly — understanding the AI landscape (fed by your scout intelligence) helps you time your moves.

---

## 3. Contract System — Full NFL Complexity

### 3.1 Contract Components

Every player contract consists of:

| Component | Description |
|---|---|
| **Years** | Contract length (1–5 years for standard deals; up to 6 for franchise cornerstones) |
| **AAV** | Annual Average Value — total value ÷ years. The headline number. |
| **Base Salary** | Cash paid that year; must fit under the cap hit |
| **Signing Bonus** | Paid upfront; prorated across all years as a cap charge |
| **Guaranteed Money** | Amount owed regardless of release or injury; creates dead cap if cut |
| **Roster Bonuses** | Annual bonuses that trigger if the player is on the roster on a specific date |
| **Performance Escalators** | Salary increases triggered by statistical thresholds (e.g., 1,000 rushing yards) |
| **Void Years** | Fake contract years added to push prorated bonus charges into the future |

### 3.2 The Salary Cap

Each season opens with a **hard salary cap** (set to a realistic NFL equivalent and inflating ~5% per year in-game). All 53 players' cap hits must fit under the cap. Practice squad players don't count against the cap.

**Cap hit per player per year:**
```
Cap Hit = Base Salary + (Signing Bonus ÷ Contract Years) + Roster Bonus (if triggered)
```

### 3.3 Dead Cap — The Cost of Mistakes

When you cut or trade a player before their contract expires, **dead cap** remains on your books — the unearned prorated signing bonus charges that accelerate into the current year.

```
Dead Cap = Remaining Prorated Bonus + Remaining Guaranteed Money
```

**Example:**
- You sign a player to a 4-year deal with a $20M signing bonus
- His prorated bonus charge is $5M/year
- You cut him after Year 1 → $15M in dead cap hits your books immediately

Dead cap is the primary consequence of bad contracts. A GM who overpays in Year 1 of a rebuild, then tries to pivot after a losing season, can be crippled by dead money for 2–3 seasons.

### 3.4 Contract Restructuring

At any point, you can offer a player a **contract restructure** — converting base salary into signing bonus to free up immediate cap space:

- Reduces the current year's cap hit by the amount converted
- Spreads the converted amount as prorated charges across remaining years
- Increases dead cap risk if the player is cut before the deal expires

Restructuring is a short-term cap fix with long-term consequences. Overuse creates "cap hell" — a well-known NFL franchise management failure mode that your game should be able to recreate authentically.

### 3.5 Void Years

You can add **void years** to a contract that automatically void (and never play out) on a specific date. Their purpose is purely to spread prorated bonus charges further into the future:

- Adds fake years to a contract that never get played
- Signing bonus is prorated across all years including void years (lower annual charge)
- When void years trigger, ALL remaining prorated charges accelerate into dead cap simultaneously

**Example:** 3-year deal with 2 void years → bonus prorated over 5 years. When the voids trigger after Year 3, Years 4 and 5's prorated charges become dead cap instantly.

Void years are powerful but dangerous — they're a bet that you'll either extend the player before the void triggers or absorb the dead cap hit later.

### 3.6 Performance Escalators

Escalators allow you to offer a player a lower guaranteed salary while providing upside if they perform:

- **Likely escalators:** Trigger if the player achieves stats he hit the previous season (low risk for him; modest cost for you)
- **Unlikely escalators:** Trigger only if he significantly outperforms his history (high upside for him; potentially expensive for you)

Escalators are useful for signing players coming off injuries, down years, or position changes — you manage risk while they prove their value.

### 3.7 The Franchise Tag

Once per offseason, you can apply a **franchise tag** to one impending free agent, retaining them for one year at the position's average top-5 salary (non-negotiable cap hit):

- **Exclusive franchise tag:** Player can only negotiate with you — no other teams
- **Transition tag:** Player can negotiate with other teams; you have right of first refusal
- A player franchise-tagged twice in a row receives a 20% salary increase; three times is extremely rare and creates significant relationship tension

Franchise-tagging a player who wanted long-term security creates immediate **satisfaction damage** (see §7).

---

## 4. The Trade System

### 4.1 Trade Assets

The following assets are tradeable in any combination:

- Current or future draft picks (up to 3 years forward)
- Player contracts (recipient must have cap space to absorb)
- Conditional picks (pick round adjusts based on performance triggers)

### 4.2 Trade Value System — The Point Floor

Every tradeable asset has a **base trade value** in points. The AI will not accept a trade where it receives fewer points than it gives — this is the non-negotiable floor.

**Pick value reference (approximate):**

| Pick | Value |
|---|---|
| #1 overall | 3,000 |
| Top 5 | 1,500–2,500 |
| Late 1st | 800–1,200 |
| Early 2nd | 500–700 |
| Mid 2nd | 350–500 |
| 3rd round | 200–300 |
| 4th round | 100–150 |
| 5th–7th | 25–80 |

**Player value** is calculated from their SAR (Scheme-Adjusted Rating from Layer 2), age, contract length remaining, and dead cap cost to trade:

```
Player Trade Value = (SAR × Age Modifier × Years Remaining Modifier) − Dead Cap Penalty
```

Age Modifier: peaks at age 24–27, declines to near zero by age 34+
Years Remaining Modifier: more years under contract = more value (predictable cost)
Dead Cap Penalty: reduces value by the dead cap the receiving team absorbs

### 4.3 Need Modifier — How Desperation Changes the Math

Once the value floor is met, **team need** determines whether the AI accepts and how much they're willing to overpay:

Each AI team has a **Positional Need Score** for every position (0–100, where 100 = critical need). If the asset you're offering fills a critical need:

```
Adjusted Acceptance Threshold = Base Value × (1 − (Need Score / 200))
```

A team with Need Score 80 at QB will accept a QB trade at 40% below fair market value — because they need him more than they need the picks.

This means you can exploit AI team needs by:
- Identifying which teams are desperate at which positions (your front office intelligence helps here)
- Timing offers after their starter gets injured (need spikes temporarily)
- Packaging players with positions that match multiple teams' needs to create bidding competition

### 4.4 Sending Trade Offers

You can initiate trades with any of the 31 AI teams at any time during open trade windows. The AI responds within the same simulated day with one of:

- **Accept** — deal is done
- **Counter** — AI proposes adjusted terms (usually asks for more value)
- **Decline** — AI explains why (player not in their need set, value gap too large, GM personality mismatch)
- **Not Interested** — hard no; typically means your offer was far below value or the GM archetype won't trade (see §8)

You can also **receive unsolicited trade offers** from AI teams throughout the season and offseason. These are generated when an AI team identifies a player on your roster that fills their critical need — they may offer you more than fair value.

### 4.5 Conditional Picks

You can structure **conditional picks** where the round adjusts based on performance:

*"A 2nd round pick that becomes a 1st if your team makes the playoffs next season."*

AI teams will accept conditionals if the base value (worst case) meets the value floor. Conditionals let you bet on outcomes — useful for recouping value on risky players you're trading away.

---

## 5. Draft-Day Transaction System

### 5.1 Pre-Draft Trade Window

From Free Agency through the night before the draft, picks are freely tradeable. This is the primary window for:

- Trading up into the top 5 (costs multiple future 1sts)
- Trading back to accumulate picks (accept a lower grade player, gain future capital)
- Packaging players + picks to move into a specific range

### 5.2 Live Draft Trading — On the Clock

Once the draft begins, the trade system remains active. This is where draft day becomes genuinely dramatic.

**When your pick comes up, you may simultaneously receive:**
- An AI team's offer to buy your pick (they want to move up)
- A lower-team's offer to trade down (they offer future value to get your pick)
- A player + pick package from a team that wants your pick position

You have **a time limit** to decide (configurable: 2–5 minutes real time, or unlimited). Choosing to trade resets the clock for the new pick position.

**AI teams also call you between picks**, not just when you're on the clock:
- *"The Wolves are offering their 2nd round pick for you to move from #14 to #17."*
- *"Three teams have expressed interest in trading up to #5 if you're willing to slide."*

**Unexpected board movement triggers live offers:**
If a player you've been targeting drops unexpectedly (AI teams passed on him), rival teams who also wanted him may offer to trade up to your position — creating urgency for you to decide whether to take him yourself or cash in.

### 5.3 Pick Trading Restrictions

- Future picks cannot be traded more than 3 years forward (Stepien Rule equivalent)
- A team cannot trade away both its 1st and 2nd round picks in the same future year simultaneously
- Conditional picks must resolve within 2 seasons of the trade

---

## 6. In-Season Transactions

The transaction system doesn't pause during the regular season. Each week, a transaction window runs alongside your game preparation.

### 6.1 Weekly Waiver Wire

**How waivers work:**

Every player released by any team goes to **waivers** for 24 simulated hours before becoming a free agent. During the waiver window:

- All 32 teams can submit a claim
- Claims are awarded by **waiver priority order** (inverse of current standings — worst record gets first priority)
- If claimed, the player's contract transfers to the claiming team; releasing team gets nothing
- Waiver priority is consumed when a successful claim is made (your priority drops to last for the rest of the season after a successful claim)

After waivers clear, unclaimed players become **free agents** — signable by any team at any time.

**Waiver priority resets:** Priority order resets at the start of each season based on the inverse of final standings.

### 6.2 Practice Squad — Full Rules

After the 53-man roster is set, you assemble a **16-man practice squad** from released players and undrafted rookies.

**Practice squad rules:**
- Any team can **poach** your practice squad players by offering them an active roster contract — you cannot block this
- You receive 24-hour notice of a poaching attempt (during which you can elevate the player to your active 53)
- **Practice squad elevations:** You can elevate up to 2 practice squad players to the active roster per week (for that week's game only); they return to the practice squad after the game
- Practice squad players receive a minimum salary but do not count against the active cap

**Protecting your practice squad:**
To deter poaching, you can sign a practice squad player to a **protected futures contract** — a guaranteed contract offer for next season in exchange for them staying on your practice squad. They can still be poached, but they have less incentive to accept the offer.

### 6.3 In-Season Trade Deadline

The **trade deadline** falls at Week 8 of the regular season (NFL equivalent). After the deadline:

- No player trades until the following offseason
- Draft picks can still be traded year-round
- Waiver claims and free agent signings continue through the season

The trade deadline creates a distinct mid-season moment: are you a buyer (adding for a playoff push) or a seller (trading veterans for future picks)?

### 6.4 Injured Reserve & Roster Exceptions

- Players placed on **IR** are removed from the active 53 and don't count against the cap (they still draw salary)
- Up to **4 players** can return from IR during the season (must have been on IR for at least 4 weeks)
- The **emergency QB exception** allows signing a third QB to the roster without counting against the 53 if both active QBs are injured

---

## 7. Player Satisfaction & Event System

### 7.1 The Satisfaction Rating

Every player has a hidden **Satisfaction Rating (0–100)** that tracks how happy they are with their situation. It's never shown directly — instead, your coaching staff and front office provide qualitative signals.

**Satisfaction is influenced by:**

| Factor | Effect |
|---|---|
| Contract relative to market value | Underpaid players lose satisfaction quickly |
| Playing time vs. expected role | Benched starters drop sharply |
| Team winning percentage | Losing cultures erode satisfaction over time |
| Franchise tag usage | Significant one-time drop (player wanted security) |
| Public criticism from coaching staff | Moderate drop |
| Public praise from coaching staff | Modest gain |
| Extension offer (fair market) | Significant gain |
| Playoff appearances | Gain |
| Coach relationship quality | Slow drift up or down based on communication events |

### 7.2 Warning Signals — The Early Warning System

Before a player takes a drastic action (holdout, trade demand, retirement), their declining satisfaction generates **warning signals** that appear in your weekly front office briefing:

**Signal Escalation Ladder:**

| Satisfaction Level | Signal Shown |
|---|---|
| 70–100 | No signal (healthy) |
| 55–69 | *"[Player] seemed distracted in practice this week."* |
| 40–54 | *"[Player]'s agent has been making calls around the league."* |
| 25–39 | *"[Player] declined a meeting with the coaching staff."* / Media reports surface |
| 10–24 | *"[Player] has formally requested a trade through his agent."* |
| 0–9 | Trade demand escalates to public holdout or retirement announcement |

The signal system gives you a window to intervene. A player at 45 satisfaction can be brought back — but you have to act before he slides further.

### 7.3 Intervention Options

When a warning signal fires, you can respond:

- **Schedule a private meeting:** A dialogue event where you choose your message. The right message (matched to the player's motivation) restores 10–20 satisfaction points. The wrong message does nothing or accelerates decline.
- **Make a contract extension offer:** A fair market offer restores significant satisfaction. A lowball offer damages the relationship further.
- **Adjust his role:** Change his depth chart position, usage plan, or responsibilities — effective if his dissatisfaction is role-based.
- **Trade him proactively:** Accept the situation and trade him while his value is high — better than waiting for a public holdout that destroys trade leverage.
- **Do nothing:** Satisfaction continues to drift. Sometimes players stabilize on their own; usually they don't.

### 7.4 Player-Driven Events

These events are generated automatically when satisfaction thresholds are crossed or specific conditions are met:

- **Holdout:** Player refuses to report to training camp or practice. He can't be forced to play. Each week of holdout costs him a game check (no sympathy from other players) but also costs you his absence. Holdouts resolve when either side concedes.
- **Trade Demand:** Player formally requests a trade through his agent. Failing to honor the request within 4 weeks causes a permanent relationship break (he won't sign an extension with you regardless of offer).
- **Retirement:** Age 30+ players with declining ratings and low satisfaction may retire unexpectedly. Your Free Agent Scout's Character Read rating improves how early you detect retirement risk.
- **Surprise retirement:** A high-satisfaction player in their prime retires suddenly (rare — 1–2% probability at age 28+ for position groups prone to it). The game doesn't telegraph these — they're the genuine shocks.
- **Locker room influence events:** A highly dissatisfied veteran can affect younger players' satisfaction scores — the "cancer in the locker room" mechanic. Your HC's Motivation rating determines how quickly you detect and contain it.

---

## 8. AI GM Personalities & Offseason Behavior

### 8.1 The Personality Archetypes

Every AI-controlled team is managed by a GM with one of five **personality archetypes**. The archetype determines how they behave throughout the offseason — their spending priorities, draft philosophy, trade willingness, and rebuild triggers.

| Archetype | Free Agency | Draft | Trades | Rebuild Threshold |
|---|---|---|---|---|
| **Draft Purist** | Spends minimally; fills gaps only | Prioritizes picks above all else; never trades 1sts | Reluctant to trade; hoards picks | Patient — will endure 3–4 losing seasons |
| **Win-Now Spender** | Aggressive; pursues top FA targets early | Trades picks for veterans; short-term focus | Very willing; often overpays to move up | Impatient — rebuilds only after 2 losing seasons |
| **Analytics-Driven** | Patient; targets value signings in mid-FA | Values scheme fit over raw rating | Trades based purely on value model; rejects emotional deals | Methodical — rebuilds early if data signals decline |
| **Loyalty-First** | Re-signs own players first; reluctant to cut veterans | Develops internal talent; avoids splashy picks | Trades only when approached; rarely initiates | Very patient — reluctant to admit a rebuild is needed |
| **Opportunist** | Inconsistent; reacts to the market | No clear philosophy; makes surprising picks | Very active trader; sometimes irrational | Unpredictable — might rebuild mid-winning-season |

### 8.2 How Personality Shapes Behavior

**Draft Purist example behaviors:**
- Will never trade a 1st round pick, even for an elite player
- Aggressively trades down if offered an extra 2nd round pick
- Passes on aging free agents even with obvious positional need

**Win-Now Spender example behaviors:**
- Submits Day 1 free agency offers before legal tampering period formally opens (penalized if caught)
- Trades future 1sts for proven veterans on the wrong side of 30
- Franchise-tags players liberally to avoid rebuilding

**Analytics-Driven example behaviors:**
- Correctly identifies and avoids overpriced positions in free agency
- Targets scheme-fit mismatches that other teams overlook
- Will trade a popular player for pure value reasons with no emotional hesitation

### 8.3 Personality Visibility

You don't see GM personality labels directly. Instead, you observe behavior over time and your **Head Scout's intelligence reports** surface patterns:

*"The Crushers have traded away two 1st round picks in the past 18 months. Classic win-now approach."*
*"The Wolves haven't signed a free agent over $10M AAV in four years. Draft-and-develop culture."*

Understanding opponent GM personalities helps you structure better trade offers — a Draft Purist will never give you a 1st, so don't structure your offer around it.

---

## 9. Roster Construction Rules

### 9.1 Active Roster Limits

| Roster | Size |
|---|---|
| Active 53-man roster | 53 players |
| Practice squad | 16 players |
| Reserve / IR | Unlimited (removed from cap) |
| Reserve / PUP (physically unable to perform) | Unlimited |

### 9.2 Positional Minimums

The 53-man roster must include:
- Minimum 2 QBs (recommended 3)
- Minimum 2 kickers (K + P)
- No formal minimum at other positions — depth decisions are yours

### 9.3 The 53-Man Cut Process

At the end of training camp, you cut from your full training camp roster (typically 75–80 players) to 53. This is a structured event:

1. Review your depth chart and injury report
2. Evaluate bubble players (players competing for the final roster spots)
3. Submit your 53-man list
4. Cut players immediately go to waivers
5. After waivers clear, assemble your 16-man practice squad from remaining cuts + undrafted free agents

Bubble player evaluation is one of the richest moments in the offseason — a 7th round pick outperforming a veteran on a cap-unfriendly deal creates genuine decision tension.

---

## 10. Key Transaction System Design Rules

1. **Every transaction has a hidden cost.** Salary cap consequences, satisfaction impacts, and draft capital spent all compound over time. The game should reward GMs who think 2–3 years ahead.

2. **Information asymmetry is intentional.** You never know a free agent's exact satisfaction with your offer, an AI team's true trade valuation, or a player's retirement probability. The fog of the transaction market mirrors the fog of the scouting system.

3. **The offseason is not a loading screen.** Each phase should feel like a meaningful decision set — not a series of confirmations to click through. Player-controlled pacing respects this by letting you spend time where you care most.

4. **AI teams should make realistic mistakes.** A Win-Now GM should sometimes overpay for aging veterans. A Draft Purist should occasionally miss an obvious need in free agency. Flawed AI creates a realistic league that feels alive — not a perfectly optimized opponent.

5. **Player satisfaction is the long game.** A franchise that wins and treats players fairly maintains a culture that attracts free agents and retains stars. A franchise that franchise-tags everyone, lowballs extensions, and ignores warning signals becomes a destination nobody wants to join. Both paths should be playable — but the consequences should be real.

---

*Next: Layer 3 — Data Model (entities, attributes, relationships, and schema design)*
