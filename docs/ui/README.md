# UI Design Reference

This folder contains the UI design-of-record for the Football Simulator. Claude Code (terminal) reads from here when implementing UI work in Phase 5. Do not modify these without updating the corresponding Game Design Document where relevant.

## Walkthrough Sequence

| Step | Document | Status | Decision Locked |
|---|---|---|---|
| 0 | `00_framework_selection.md` | Locked 2026-05-09 | HTML + pywebview |
| 1 | `01_information_architecture.md` | Locked 2026-05-09 | Sitemap + screen IDs |
| 2 | `02_persistent_context_bar.md` | Locked 2026-05-09 | Bar contents + states |
| 3 | `03_wireframes.md` | Locked 2026-05-09 | 5 layout patterns + 8 wireframes |
| 4 | `04_component_vocabulary.md` | Locked 2026-05-09 | Design system + tokens |
| 5 | `05_framework_implementation_plan.md` | Locked 2026-05-09 | SPA + Alpine + 12 milestones |
| 6 | `06_read_only_first.md` | Locked 2026-05-09 | Render-disabled-then-wire discipline |
| 7 | `07_presenter_layer.md` | Locked 2026-05-09 | Contract + golden tests + no caching |
| 8 | `08_data_volume_testing.md` | Locked 2026-05-09 | Tiered budgets + Year-10 fixture |
| 9 | `09_recap_moments.md` | Locked 2026-05-09 | Pattern D ship-it + narrative module |

**Walkthrough complete — all 9 steps locked. Ready for Phase 5 implementation.**

## Phase 5 Kickoff

When ready to begin implementation, see `_phase5_kickoff_prompt.md` — a self-contained prompt for the first Claude Code session (Milestone 5.1: Window + Shell). Subsequent milestones follow the same template, referencing the relevant design docs.

**Note on phase numbering**: This walkthrough originally used "Phase 4" terminology. Renamed to "Phase 5" on 2026-05-09 to align with `CLAUDE.md`, where Phase 4 is Dynasty & Coach Identity (currently in progress). UI implementation is Phase 5 — runs *after* Phase 4 completes.

## How to Use This Folder

- **Cowork sessions**: design decisions are made and saved here.
- **Claude Code sessions**: terminal Claude reads these files as authoritative spec when implementing UI in `src/ui/`.
- **Updates**: if a design decision changes mid-implementation, update the relevant doc here first, then change code. Never let code drift from spec without updating spec.

## Source-of-Truth Rules

- This folder governs the UI layer only. Game logic, simulation, and data model decisions live in the GDDs (`docs/GDD_Layer*.md`).
- UI must remain a strict consumer of the data layer (per CLAUDE.md layer boundaries).
- All ratings displayed as letter grades, never raw numbers.
- All currency formatted consistently (decided in step 4).
- All dates formatted consistently (decided in step 4).
