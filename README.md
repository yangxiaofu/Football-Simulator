# Football Simulator

A deep, text-based NFL franchise simulator inspired by Out of the Park Baseball. Act as both General Manager and Head Coach of a fictional NFL franchise, building a dynasty across multiple seasons through smart drafting, cap management, and scheme decisions.

**Target Platform:** Steam (Windows)
**Tech Stack:** Python 3.11+ / SQLite
**Status:** Phase 0 Complete ✅

---

## Quick Start

### 1. Generate a New Franchise

```bash
python generate.py saves/my_franchise.db --season 2024
```

This creates:
- 32 teams with divisions and conferences
- 1,696 players (53-man rosters for all teams)
- 352 staff members (coordinators, coaches, scouts)
- 272 games across a 17-week regular season

### 2. Query a Team Roster

```bash
python query_roster.py saves/my_franchise.db --team CHI
python query_roster.py saves/my_franchise.db --team "Green Bay"
```

Displays the complete 53-man roster with:
- Player names, positions, ages
- Overall ratings (as letter grades: A+ through F)
- Years of experience
- College attended
- Current cap hit

---

## Project Structure

```
/Football Simulator/
├── generate.py           # Create a new franchise
├── query_roster.py       # Query team rosters
├── docs/                 # Complete Game Design Documents
├── src/
│   ├── db/               # Database layer (schema, queries, cap logic)
│   ├── generation/       # Team, player, staff, schedule generation
│   ├── utils/            # Shared constants and helpers
│   └── [future phases]/  # engine, league, transactions, scouting, ui
└── saves/                # Generated franchise .db files
```

---

## Development Status

### ✅ Phase 0 — Foundation (Complete)
- SQLite schema with 30+ tables
- Database connection and query layer
- Salary cap calculation and validation
- Transaction logging system
- Team, player, and staff generation
- 17-game schedule generation

### 🔜 Phase 1 — Simulation Engine (Next)
- Play-by-play game simulation
- Matchup resolution with Scheme-Adjusted Ratings
- Injury and fatigue systems
- Weather effects
- Narration engine

### 🔜 Phase 2 — Full Season
- Complete season loop with standings
- Playoff bracket and Super Bowl
- Player development and aging
- Season archival and statistics

### 🔜 Phase 3 — Offseason Loop
- Free agency and contract negotiations
- Trade system
- Scouting and draft system
- Player satisfaction

### 🔜 Phase 4 — Dynasty
- Multi-season stability
- Legacy scoring system
- Media and pressure mechanics
- Hall of Fame

---

## Documentation

- **`CLAUDE.md`** — Developer and AI assistant guide (coding conventions, design decisions, architecture)
- **`docs/`** — Complete Game Design Documents:
  - `GDD_Layer1_CoreDesign.md` — Vision, core loop, game systems
  - `GDD_Layer2_SimulationSpec.md` — Play resolution engine, ratings, simulation
  - `GDD_Layer2B_TransactionOffseason.md` — Contracts, trades, free agency, draft
  - `GDD_Layer3_DataModel.md` — Complete SQLite schema documentation
  - `GDD_Layer4_FeatureRoadmap.md` — Development phases and timeline

---

## Requirements

- **Python 3.11+** (uses standard library only)
- No external dependencies for Phase 0

---

## Design Philosophy

**Engine-In, UI-Out**
The simulation engine comes first. Every phase ends with a working, testable system — not a demo or mockup, but real functionality you can run and evaluate.

**Never Build UI for a System That Isn't Working**
Polish comes after the core systems are solid. A plain-text simulation that produces realistic results is more valuable than a beautiful interface on top of broken logic.

**Information Fog**
Players never see true ratings (1-99 numeric values). The UI always displays letter grades (A+ through F). Scouting reports have confidence ranges based on scout quality.

---

## License

[To be determined]

---

## Acknowledgments

Inspired by Out of the Park Baseball's depth and franchise management systems.
