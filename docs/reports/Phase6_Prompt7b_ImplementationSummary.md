# Phase 6 Prompt 7b — Implementation Summary

**Milestone 5.7b — FA Modals + 3 Contract Mutations.** Ships the GUI's first
modal framework, the F-43→F-44→F-45 modal stack, three contract mutations,
the watchlist toggle, and wires four previously-disabled buttons.

## Files

### Created
- `src/ui/static/js/modal.js` — generic stacked modal framework.
- `src/ui/static/js/screens/modal_pitch.js` — F-43 Pitch Meeting.
- `src/ui/static/js/screens/modal_offer.js` — F-44 Offer Builder (modal-over-modal).
- `src/ui/static/js/screens/modal_negotiation_result.js` — F-45 Result.
- `src/ui/static/js/screens/modal_cut_confirm.js` — Cut confirmation.
- `src/ui/static/js/screens/modal_restructure.js` — Restructure.
- `src/ui/presenters/tests/test_fa_mutations.py` — 8 mutation tests.
- `src/ui/presenters/tests/test_modal_views.py` — 5 view-model shape tests.

### Modified
- `src/utils/constants.py` — z-index tiers, fade ms, watchlist col name,
  enabled-button tooltips, offer-range estimate consts, message templates.
- `src/db/schema.sql` — `player.is_watchlisted INTEGER NOT NULL DEFAULT 0`.
- `src/db/connection.py` — `ensure_player_watchlist_column` migration (wired
  into the forward-migration sequence).
- `src/db/queries.py` — `set_player_watchlist`, `count_watchlisted_players`.
- `src/ui/api.py` — `_MUTATION_LOCK` + `get_pitch_meeting`,
  `get_offer_builder`, `do_add_to_watchlist`, `do_sign_free_agent`,
  `do_cut_player`, `do_restructure_contract`.
- `src/ui/presenters/free_agency.py` — `build_pitch_meeting`,
  `build_offer_builder`, `build_negotiation_result`; `is_watchlisted` surfaced;
  FA actions enabled + `action_key`.
- `src/ui/presenters/player.py` — Cut/Restructure enabled when on user team
  with active contract; `cut`/`restructure` sub-views attached to the
  `contract` dict (PlayerView top-level key set unchanged).
- `src/ui/presenters/types.py` — `MarketRange`, `PitchMeetingView`,
  `OfferBuilderView`, `NegotiationResultView`, `CutConfirmView`,
  `RestructureView`.
- `src/ui/static/index.html` — `#modal-root` mount point.
- `src/ui/static/js/api.js` — 6 bridge wrappers (immediate, no polling).
- `src/ui/static/js/screens/detail.js` — respects `enabled`, emits
  `onAction(actionKey)` for enabled buttons.
- `src/ui/static/js/screens/fa_player.js`, `player.js` — `onAction` wiring.
- `src/ui/static/js/shell.js` — `window.reloadRoute` (post-mutation re-render).
- `src/ui/static/css/components.css`, `screens.css` — modal stack/fade/close
  button + modal content layout.
- `src/ui/presenters/tests/test_player.py`, `test_free_agency.py` — updated
  to assert the new (wired) action state instead of the old read-only state.
- `jobs.py` — **untouched** (synchronous model).

## Modal framework architecture

- **Component pattern:** `openModal(cfg)` injects a `.modal-scrim` + `.modal`
  (header/title/✕ + body) into `#modal-root`. Content modules supply
  `contentHTML` and bind handlers in `onMount(dialogEl)`. Generic — no
  FA-specific code; P8 (Trade) / P9 (Draft) reuse it as-is.
- **Stack management:** internal `_stack` array; each level's scrim gets
  `z-index = UI_ZINDEX_MODAL_BASE + level*STEP` (1000, 1010, …; below the
  z-2000 toast layer). F-43 → F-44 → F-45 stack literally as three modals.
- **Focus trap:** document-level `keydown`; Tab/Shift-Tab cycle within the
  **top** modal only. Opener element captured on open, focus restored on
  close (or moved to the new top modal).
- **ESC / backdrop:** ESC closes the **top** modal only (per-modal
  `closeOnEsc`). Backdrop mousedown closes the top modal iff
  `backdropDismissable` (F-45 sets it false so the result must be
  acknowledged). `closeAllModals()` unwinds the whole stack.
- **ARIA:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby` → title.

## Mutation architecture

All three mutations are **synchronous** under a process-global
`threading.Lock` (`src.ui.api._MUTATION_LOCK`, non-blocking acquire → second
concurrent call returns the busy error). Justification: market valuation is
O(1) and `resolve_offer` is single-pass — sub-1s, so JobManager indirection +
polling was unnecessary (`jobs.py` left untouched).

**Cap recalc placement:** `offer_contract` (via `resolve_offer`),
`release_player`, and `restructure_contract` each open their **own**
`with conn:` and call `recalculate_cap_space()` internally. The UI wrappers
are thin and deliberately do **not** add an outer transaction or re-call
recalc — the CLAUDE.md cap-cache rule is satisfied at the business layer.
After a successful mutation the wrapper calls `_invalidate_conn()` so the next
`get_*` reopens and sees committed writes.

- `do_sign_free_agent` → `submit_offer` then `resolve_offer`. `accepted` →
  signed; `countered`/`shopped`/`walked` → `{accepted: False}` with
  "Rejected: <reason>" (counter-offer flow deferred). Cap impact = cached
  `team.cap_space` delta around the call.
- `do_cut_player` → `release_player`. `post_june_1` accepted but **not
  honored** (standard pre-June-1 release only this prompt).
- `do_restructure_contract` → `restructure_contract(amount_to_convert)`.

## Save-file safety (verified per mutation)

Each business function wraps its writes in `with conn:`. On any exception the
SQLite transaction auto-rolls back and the UI wrapper returns
`{"ok": False, "error": ...}`. Verified by
`test_rollback_on_exception_leaves_db_unchanged`: an over-limit restructure
raises `ValueError`; `contract_year` rows and `team.cap_space` are byte-for-
byte unchanged afterward.

## Test results

`python -m pytest src/ui/presenters/tests/ -v` → **79 passed, 1 skipped**
(up from 67). The skip is `test_fa_market_real_save` — its optional sample
save (`saves/phase6_p7a_test.db`) is absent; environmental, pre-existing.

New coverage:
- `test_fa_mutations.py` (8): cut releases + recalcs cap; restructure rewrites
  schedule + recalcs cap; sign creates contract+years+sets team_id; every
  mutation changes `cap_space` (regression guard); rollback-on-exception;
  single-flight busy; watchlist toggle. Fixture bootstraps a real franchise
  via `generate.py` then creates contracts through real `offer_contract`
  (a fresh generate has 0 contracts — the documented Phase 0/3 gap).
- `test_modal_views.py` (5): shape of Pitch/Offer/Negotiation-Result views.

## Manual checks — what was / wasn't verified

`test_franchise.db`: 20 contracts (17 active), `user_team_id=1`,
phase=`playoffs`, **1 teamless player**, and **no `contract_year` row aligned
to current_season 2024**.

- **Verifiable & exercised programmatically:** `do_cut_player` (succeeds,
  player off roster, contract `expired`, cap recalced), single-flight busy
  guard, watchlist toggle.
- **NOT manually verifiable on `test_franchise.db` (data state, not a code
  defect):**
  - FA signing end-to-end (checks #6–14): no FA pool + phase=playoffs. Covered
    instead by `test_fa_mutations.py` (real `submit_offer`/`resolve_offer`,
    Tier-1 forced-accept fixture).
  - Restructure on this save: no `contract_year` row for season 2024 →
    `restructure_contract` correctly raises; covered by the generated-fixture
    test where the contract aligns to the current season.
  - `p7a_check.db` unusable (0 contracts) as flagged in the prompt.
- **Interactive GUI checks (#1–5, 15–23):** require a human-driven pywebview
  window session; cannot be exercised headlessly in this environment. JS was
  validated with `node --check` (all modules parse) and the Python bridge
  surface confirmed (all 6 methods exposed on `Api`). The modal stack /
  focus-trap / ESC / backdrop logic in `modal.js` is implemented to the
  Step-4 spec but its on-screen behavior is **not** machine-verified here.

## Deferred (unchanged scope)

Counter-offer flow, June-1 dead-cap split, Trade Block wiring (5.8),
Intervention dialog, Phase 0 contract-generation gap.
