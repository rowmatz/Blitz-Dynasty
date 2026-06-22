# Blitz Dynasty

A multiplayer dynasty fantasy football game built on a fully simulated NFL. Ten friends each own a franchise, draft made-up players, and compete across a compressed season — while the commissioner triggers weekly NFL simulations to generate real stats and scores.

The long-term vision is a living league: rookies age in, veterans retire, beat reporters file weekly stories, and one day you'll watch condensed game highlights in a visualisation engine.

---

## What's Been Built (Phase 1)

### Tech Stack
- **Backend:** Python 3.9 / Flask 3.x / SQLAlchemy 2.0
- **Database:** SQLite (`blitz.db`)
- **Auth:** Flask-Login with invite-code registration
- **Frontend:** Bootstrap 5, dark theme, vanilla JS (no framework)

### Core Loop
1. Commissioner creates the league and shares 9 invite codes with friends
2. All 10 owners register and name their franchise
3. Commissioner opens the draft — a live snake draft with a 90-second timer and auto-pick on expiry
4. Commissioner simulates NFL weeks; players accrue stats; fantasy scores are calculated automatically
5. Owners manage rosters via the waiver wire and trade hub between simulations
6. After 14 regular-season weeks, the league transitions to playoffs

### League Format
- **Roster:** 17 spots — QB×1, RB×2, WR×2, TE×1, FLEX (RB/WR/TE), SUPERFLEX (QB/RB/WR/TE), BN×9
- **Scoring:** PPR — 0.04/pass yd, 4/pass TD, −2/INT, 0.1/rush yd, 6/rush TD, 0.1/rec yd, 6/rec TD, 1/rec
- **Schedule:** 14-week regular season (round-robin, weeks 1–5 repeated for balance), then playoffs
- **Waivers:** Instant free agent claims, first-come-first-served
- **Draft:** 17-round snake, randomised order, 90s timer with auto-pick fallback

### Simulated NFL
- 32 teams, ~384 skill players (QB/RB/WR/TE) + 32 DEF units
- Each player has an archetype, age, potential rating (A–D), and skill bonus that drives sim output
- 18-week NFL regular season schedule (all 32 teams play exactly 18 games)
- DEF units exist in the sim engine but are not draftable in fantasy

### Pages
| Route | Description |
|---|---|
| `/team` | My Team — lineup management, current matchup, season leaders |
| `/league` | Fantasy standings — W/L, PF, PA, top players per team |
| `/nfl` | NFL standings — all 32 teams sorted by wins |
| `/players` | Player browser — filter by position, NFL team, name search |
| `/waiver` | Waiver wire — add/drop free agents |
| `/trades` | Trade hub — propose, accept, reject trades |
| `/draft` | Live draft room — snake draft with timer |
| `/commissioner` | Commissioner panel — invite codes, open draft, simulate weeks |

### Key Files
| File | Purpose |
|---|---|
| `models.py` | All SQLAlchemy models and lineup slot constants |
| `app.py` | All Flask routes and business logic |
| `sim.py` | Bridge between engine and DB — runs simulations, scores fantasy, sets lineups |
| `engine.py` | Core NFL game simulation engine (stateless, in-memory) |
| `seed.py` | Seeds the DB from `rosters.csv` — 32 teams, players, NFL schedule |
| `rosters.csv` | Source of truth for all NFL teams and players |

### Running Locally
```bash
# First run — seed the database
python3 seed.py

# Start the server
python3 -m flask run --port 5050
```
Then open `http://localhost:5050/setup` to create the commissioner account.

### Fresh Start
```bash
rm blitz.db
python3 seed.py
python3 -m flask run --port 5050
```

---

## Roadmap

### Phase 2 — Dynasty Layer
The game becomes a true dynasty when the off-season matters as much as the season.

- **End-of-season offseason flow** — season wraps, standings lock, rosters carry over
- **Rookie draft class** — each off-season generates a new cohort of young players with randomised archetypes and potential ratings; teams draft them in reverse standings order
- **Player aging** — players age each season; peak years vary by position; decline curves affect skill bonus
- **Keeper/contract system** — owners decide which players to retain vs release before each rookie draft
- **Free agent pool** — released veterans and undrafted rookies become available to sign

### Phase 3 — Flavor & Immersion
- **Beat reporter** — an AI-generated weekly news feed covering top performances, injuries, trades, and storylines from the simulated NFL and fantasy league
- **Injury system** — players can miss games; injury risk tied to age and archetype; owners get a waiver window before lineup lock
- **Game visualisation** — a condensed animated match summary showing key plays from the simulated NFL games
- **Player profiles** — individual stats page per player with season history, career arc, and ownership history
- **Trade history / activity log** — full audit trail of all roster moves visible to the league

### Phase 4 — Polish & Scale
- **Mobile-optimised UI** — the current layout works on mobile but wasn't designed for it
- **Push notifications** — alert owners when it's their draft turn, a trade comes in, or a sim has run
- **Multiple concurrent leagues** — multi-tenancy so different groups of friends can run separate leagues
- **Commissioner tools** — veto trades, manually override sim results, manage injured reserve slots

---

## Design Decisions & Principles

- **No DEF in fantasy** — DEF units exist in the sim engine for realistic game outcomes but are excluded from fantasy to keep roster management clean
- **Superflex format** — QB is eligible in the SUPERFLEX slot, which creates genuine QB scarcity and makes the position valuable at all draft spots
- **Instant waivers** — no waiver priority queue; first owner to claim wins. Keeps things simple for a friend group playing asynchronously
- **Auto-lineup** — if an owner hasn't set their lineup before simulation, the system auto-sets the optimal lineup by slot eligibility and player value. No punishing absent players
- **Commissioner sim trigger** — the NFL simulation is a deliberate action by the commissioner, not automated. This gives the group control over the pace of the season
- **Compressed season** — designed to complete a full dynasty season over weeks, not months, so friends stay engaged

---

## Known Gaps / Bugs to Track

- Playoffs are currently just continued weekly simulations with no bracket or seeding logic
- No end-of-season state — the game doesn't formally close out a season yet
- Browser-only tested in development; no production deployment setup
- No lineup lock before simulation — owners can change lineups after seeing early results

---

*Last updated: May 2026*
