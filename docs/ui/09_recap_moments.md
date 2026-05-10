# Step 9 — Recap Moments

**Status**: Drafted, pending review.
**Purpose**: Define how the screens classified as "recap moments" earn their extra polish budget. Lock the narrative architecture, animation philosophy, and ship-it definition for Pattern D, so Milestone 5.10's polish pass has a target instead of an aesthetic argument.
**Inputs to this step**: Step 1 screen classification (9 recap moments identified), Step 4 typography scale (display tier), Step 8 performance budgets.
**Output of this step**: Recap moment inventory, polish element checklist, generated-narrative architecture, animation rules, ship-it definition.

---

## Why Recap Moments Get Extra Effort

The hours-long sim experience runs on utility screens — rosters, standings, contracts, schedules. Those are functional and unmemorable, by design. They reward speed and density.

Recap moments are different. They are **emotional payoff** — the screens players will:
- Sit and read instead of click through.
- Screenshot and share with friends.
- Remember from the season.
- Look back at in Year 10's history browser.

OOTP's "World Series Champion" screen and Football Manager's end-of-season reveal are why these games keep players for hundreds of hours. They are also why players forgive a clunky table six clicks deep.

If utility screens fail, the game feels broken. If recap moments fail, the game feels soulless. Both are project-killing — but recap moments earn deliberate attention because the failure mode (forgettable) is invisible during testing.

---

## Resolutions to Step 8 Open Questions

| Question | Resolution |
|---|---|
| Separate performance budget for recap moments? | **Yes — 200–300ms render budget instead of 100ms.** Plus an additional 200–500ms animation budget *after* first paint. Players are reading; the extra cost is invisible to perceived speed. |
| Where does generated narrative live? | **`src/league/recap_narrative.py`** — new module. Composes outcome data (game results, season stats) into prose strings. Sits alongside `src/league/season.py` and `src/league/playoffs.py`. UI receives finished strings via presenters. Reasoning in §3. |
| Ship-it definition for Pattern D | **Six-element checklist** (§5). Locked. |

---

## 1. The Nine Recap Moments

From Step 1 classification, restated with target polish weight:

| ID | Screen | Frequency | Polish Weight |
|---|---|---|---|
| **S-05** | Game Recap | 17–22 per season | High (most-encountered recap) |
| **S-08** | Playoff Bracket | Live during playoffs | Medium-High |
| **S-10** | Conference Championship Recap | 1 per season | High |
| **S-11** | Super Bowl Recap | 1 per season (if you make it) | **Maximum** — the screen of the year |
| **F-10** | Season Review (offseason kickoff) | 1 per season | High |
| **F-34** | Combine Results | 1 per offseason | Medium |
| **F-60** | Draft Room (also Pattern E) | 1 per offseason | High (different polish vector — "live event" feel) |
| **F-62** | Post-Draft Review | 1 per offseason | Medium-High |
| **D-04** | Past Season Summary (history) | On-demand | Medium |

Implied additions worth flagging:

| Screen | Notes |
|---|---|
| Awards Ceremony Reveal | Currently a sub-screen of F-10 / D-05; promote to its own recap moment if it deserves the budget |
| Career Retirement Tribute | When a star retires — fires once per career, max polish per fire |
| Hall of Fame Induction | v1.1, deferred but earmarked |

---

## 2. The Six Polish Elements

These are the components that distinguish a recap moment from a utility screen. The ship-it checklist (§5) requires all six.

### Element 1: Hero Zone
The opening visual. Not a tableof stats — a **single dominant element** that communicates the outcome at a glance.

| Recap | Hero Zone |
|---|---|
| Game Recap | Final score, oversized: `BEARS 27 — 17 PATRIOTS`, with date and venue underneath |
| Super Bowl Recap | Champion team logo + score + "SUPER BOWL CHAMPIONS" |
| Season Review | Final record + division finish + playoff outcome in display type |
| Draft Class Reveal | "2026 DRAFT CLASS" + class strength rating |
| Career Retirement | Player photo + name + career headline ("Six-time Pro Bowl QB") |

Renders in `--text-display` (32px, weight 700) or larger. Center-aligned. Generous vertical spacing (`--space-7`).

### Element 2: Generated Narrative Headline
A 1-3 sentence prose summary, generated from outcome data. Not a stat dump — a sentence that reads like a sportswriter wrote it. Examples:

| Outcome | Generated Headline |
|---|---|
| Big road win, RB monster game | `Carter rumbles for 142, Bears spoil Patriots' homecoming` |
| Last-second loss after blown lead | `Bears blow 14-point lead, fall to Packers in OT` |
| Playoff elimination | `Season ends in Foxborough — Bears fall short of Wild Card` |
| Super Bowl win | `Sixty years of waiting end in glory: Bears are champions` |

The tone is **understated, not breathless**. Sim-game narratives lose their charm fast when every game is a "stunning upset." See §3 for architecture.

### Element 3: Key Facts Grid
A small grid (typically 2–4 cards) with the **3–6 facts that mattered most**, not 30 stat lines. The Box Score lives one click away — this grid is for the player who's reading the recap, not researching the game.

For Game Recap: top performers (3–4 lines) + box score preview (totals, TOP, third-down rate) + injuries (only if any) + headline storyline ("Pro Bowl track now ON for Carter").

For Season Review: final standings, awards your team won, draft picks acquired, top performers, satisfaction concerns.

### Element 4: Narrative Detail Block
Below the hero, optional but recommended for the largest recaps (Super Bowl, Season Review). 2–3 short paragraphs of generated prose covering: how the season unfolded, key inflection points, what to watch next year. Replaces and exceeds what the headline can convey.

### Element 5: Typography Rhythm
Recap moments use the full typography scale, not just body text:

- Display (32px+) for the hero result.
- H1 (24px) for section headers within the recap.
- Body (14px) for narrative.
- Tabular-nums (monospace) for any inline stats.
- Generous line-height (1.5–1.6) for readability.

This is the only place in the game where body text routinely sits at 16–18px instead of 14px. Recaps are read, not scanned.

### Element 6: Subtle Motion
First-paint animation that sells the moment without demanding attention. Rules in §4.

---

## 3. Generated Narrative Architecture

### Where It Lives

A new module: `src/league/recap_narrative.py`.

Sits alongside existing `season.py`, `playoffs.py`, `archive.py`. Reads from the same league-level data sources. Outputs strings.

CLAUDE.md layer rule check:
- Engine produces stats; engine doesn't write narrative beyond per-play templates (already in `src/engine/narration.py`).
- League composes outcomes; recap narrative is league-level composition.
- UI displays; presenters call into `recap_narrative` to fetch already-composed strings.

This is the right home.

### Architecture: Templated with Stat-Driven Slots

Three options were considered:

| Option | Verdict |
|---|---|
| Hard-coded templates per outcome class | ✗ Goes stale fast — every game reads the same |
| Random selection from a library | ✗ Better, but still feels canned |
| AI-generated (LLM call at recap time) | ✗ Out of scope for v1; adds infra and unpredictability |
| **Templated with stat-driven slots + variant pools** | ✓ Chosen |

The chosen pattern, similar to how `src/engine/narration.py` already handles per-play text:

```python
# src/league/recap_narrative.py
def game_headline(game_result: GameResult) -> str:
    """Generate a 1-sentence headline from a completed game."""
    template = _select_template(game_result)
    slots = _extract_slots(game_result)  # leading_rusher, blowout_margin, etc.
    return template.format(**slots)


_TEMPLATES_BIG_WIN = [
    "{leader_name} {leader_verb} for {leader_stat}, {winner_short} {win_verb} {loser_short}",
    "{winner_short} cruise past {loser_short} behind {leader_name}'s {leader_stat}",
    "{winner_short} dominate {loser_short} as {leader_name} {leader_verb}",
]

_TEMPLATES_OT_LOSS_AFTER_LEAD = [
    "{loser_short} blow {blown_lead}-point lead, fall to {winner_short} in OT",
    "{loser_short} squander late lead, drop heartbreaker to {winner_short}",
]

# ... 8-12 outcome categories, each with 3-5 variants
```

Variant selection is **deterministic per game** (seeded by `game_id`) — re-reading a recap shows the same headline. This matters: a player who screenshots a recap and revisits it should see the same story.

### Outcome Categories to Cover (v1)

For game recaps:
- Big win (margin > 14 + offensive leader)
- Tight win (margin ≤ 7)
- OT win
- Big loss
- OT loss
- Loss after blown lead (≥ 10-point fourth quarter lead)
- Defensive struggle (combined points < 30)
- Shootout (combined points > 60)
- Upset (loser was favored)
- Trap game (looked easy, was close)

For season recaps:
- Won Super Bowl
- Lost Super Bowl
- Lost in Conference Championship / Divisional / Wildcard
- Missed playoffs but improved
- Missed playoffs, regressed
- Rebuild season
- Surprise contender

A library of ~50 templates total covers v1. Expand post-launch based on what feels stale.

---

## 4. Animation Philosophy & Budget

### Rules

1. **Total budget after first paint: ≤ 500ms.** Animation cannot delay player interaction.
2. **CSS transitions only** — no JS animation libraries. Keep complexity low.
3. **Subtle, not theatrical.** Fade in, count up, slide up. No bouncing, spinning, parallax, particles.
4. **Respect `prefers-reduced-motion`.** Disable all animation when the OS setting is on. Locked accessibility floor.
5. **No animation on utility screens.** Recaps are the only place motion lives.

### Animation Types Used

| Type | Where | Duration | Easing |
|---|---|---|---|
| Hero fade-in + slight slide-up | Hero zone on first render | 300ms | `cubic-bezier(0.16, 1, 0.3, 1)` (eased-out) |
| Score count-up | Final score numbers | 600ms | linear |
| Stagger card fade-in | Key facts grid (cards appear sequentially) | 100ms each, 4 cards | ease-out |
| Subtle highlight pulse | Key plays as they list | 200ms per pulse | ease-in-out |

For Super Bowl Recap specifically: an extra 200ms reveal sequence on the championship logo. Once-per-season screen earns it.

### What NOT to Animate
- Tables and lists (utility-screen behavior even within recaps)
- The persistent context bar
- Any text that's being read (animating text-as-it-renders is a 2000s effect that aged badly)

---

## 5. Ship-It Definition for Pattern D

A recap moment screen is "done" only when **all six elements are present and tested**:

- [ ] **Hero zone** with display-type result, generous spacing, centered.
- [ ] **Generated narrative headline** sourced from `recap_narrative.py`, deterministic per-game/season.
- [ ] **Key facts grid** with 3–6 cards, no more.
- [ ] **Narrative detail block** (Super Bowl Recap and Season Review only — others optional).
- [ ] **Typography rhythm** uses display + h1 + body, line-height ≥ 1.5 for narrative.
- [ ] **Motion**: hero fade-in + at least one count-up or stagger, total ≤ 500ms, respects `prefers-reduced-motion`.

Plus:

- [ ] Render budget: cold ≤ 300ms (per Step 8).
- [ ] Looks good in a screenshot at 1440×900 — the social-share test.
- [ ] Works at minimum viewport 1280×720 without horizontal scroll.

---

## 6. Implementation Order Within Milestone 5.10

Milestone 5.10 (Recap Polish) builds in this order to compound gains:

1. **Game Recap (S-05) first.** Most-rendered, sets the Pattern D template. Validates the entire stack: presenter → narrative module → six elements → motion.
2. **Season Review (F-10) second.** Reuses the template. Tests narrative module's season-level outcomes.
3. **Playoff Bracket (S-08).** Different shape than other recaps (more visual diagram, less prose). May require its own sub-template.
4. **Conference Championship + Super Bowl Recaps (S-10, S-11).** Highest polish weight; reuse infrastructure built in 1–3.
5. **Combine Results (F-34) and Post-Draft Review (F-62).** Lower polish weight, mostly data-heavy with light narrative wrapper.
6. **Past Season Summary (D-04).** Read-only history view; reuses Season Review template.

Career Retirement Tribute and Awards Ceremony Reveal are deferred — implement in v1 only if Phase 5 timeline allows. Earmark for v1.1 if not.

---

## 7. What Recap Moments DO NOT Need

Cutting the over-build:

- **No video or 3D rendering.** Out of stack.
- **No sound effects.** v1 ships silent.
- **No multiplayer share buttons.** Local single-player only.
- **No rich-text editor for player notes.** Different feature.
- **No avatar/portrait generation.** Use placeholder photos in v1; real player portraits are a v2 art-asset project.
- **No infinite scroll narrative.** A recap is a screen, not a Wikipedia article. Cap at 3 paragraphs of detail.

---

## 8. Walkthrough Closure

This is the final step in the UI design walkthrough. With Step 9 locked, the design-of-record is complete.

### What's Locked
- **Step 0**: HTML + pywebview as the framework.
- **Step 1**: 64-screen sitemap with screen IDs.
- **Step 2**: Persistent context bar contents and behavior.
- **Step 3**: Universal shell + 8 wireframes + 5 layout patterns.
- **Step 4**: Design system — color palette, typography, components, formats.
- **Step 5**: SPA shell + Alpine.js + folder structure + 12-milestone build order.
- **Step 6**: Read-only-first discipline + viewer build checkpoint + action enablement order.
- **Step 7**: Presenter layer contract + golden-file testing + no caching at v1.
- **Step 8**: Tiered performance budgets + Year-10 fixture + pre-launch gate.
- **Step 9**: Recap moment polish elements + generated narrative module + ship-it checklist.

### What Phase 5 Implementation Inherits
- 9 design-of-record documents in `docs/ui/`.
- A clear, ordered, testable build sequence (12 milestones).
- A presenter contract that protects layer boundaries.
- A performance gate that protects user experience.
- A polish standard for the screens that earn it.

### What Comes Next
- David hands these documents to Claude Code in the terminal.
- Phase 5 begins with Milestone 5.1 (Window + Shell).
- Each milestone closes against its exit criterion (working test command), with the relevant doc(s) read at the start of the prompt.
- The viewer-build checkpoint at end of 5.4 is the single most valuable mid-Phase-5 review point.

The Cowork-side of UI design is now complete. The Claude Code-side begins on David's command.

---

## Action Items Before Phase 5 Starts

- [ ] David reviews Step 9 — confirms recap moment polish is the right level of effort.
- [ ] Confirm `src/league/recap_narrative.py` as the home for narrative composition.
- [ ] Confirm `prefers-reduced-motion` accessibility floor.
- [ ] Confirm Career Retirement Tribute and Awards Ceremony Reveal as v1.1 if 5.10 runs long.
- [ ] Update `docs/ui/README.md` to mark Step 9 as Locked once approved.
- [ ] Optional: produce a single `docs/ui/_phase4_kickoff_prompt.md` summarizing the 9 documents into a single hand-off prompt for Claude Code.
