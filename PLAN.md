# Blitz Dynasty — Development Plan (Phase 2 → Phase 3)

This plan was created in a separate Claude Code session. Steps 1 and 2 are already complete.
Each step is sized for a 30–45 minute window. Commit and push after each step.

---

## ✅ Step 1 — Git init + GitHub repo (DONE)
Repo live at https://github.com/rowmatz/Blitz-Dynasty

## ✅ Step 2 — Bug fixes (DONE)
- Fantasy ties now record as draws (not double-wins) — `sim.py` + `FantasyTeam.draws` column added to `models.py`
- `/results` historical page now builds real NFL + fantasy data from DB — `app.py`
- `best_available` auto-pick fixed broken filter when drafted set was empty — `app.py`

---

## Part 1 — Phase 2: Dynasty Layer

### Step 3 — End-of-season flow
Add an `offseason` phase transition. When week 18 is simulated, the league locks standings
and the phase moves to `offseason`. Commissioner panel shows final standings and an
"Advance to Off-Season" button. No roster or stat changes yet — just the state machine.

### Step 4 — Player aging
Add an "Advance Season" commissioner action that:
- Increments every player's `age` by 1
- Applies position-based decline curves to `skill_bonus` (QBs peak ~28, RBs ~26, WRs ~27, TEs ~29)
- Triggers retirement for players past their prime with low potential (D/C)

### Step 5 — Keeper system (backend)
- Add a `KeeperTag` model (player_id, fantasy_team_id, season_year)
- Add `keeper_window` as a sub-phase inside `offseason`
- Add `/api/keeper/tag` and `/api/keeper/drop` endpoints
- Enforce a 3-keeper limit per team

### Step 6 — Keeper system (UI)
- Add a keeper selection screen on the My Team page during `keeper_window` phase
- Shows roster, lets owner tag up to 3 keepers
- Shows all other teams' kept players once the window closes

### Step 7 — Rookie class generation
- Add `generate_rookie_class()` that creates 40–50 new Player rows
- Randomised names, archetypes, potential (A–D weighted toward C/D), ages 19–22, zero stats
- Triggered by the commissioner at the start of the rookie draft

### Step 8 — Rookie draft room
- Reuse the existing snake draft UI and `Draft` model
- Add "Open Rookie Draft" commissioner action — creates a new Draft in reverse-standings order
- Rookies not drafted go to the free-agent pool (`nfl_team_id = null`)

### Step 9 — Off-season free agent pool
- Released veterans (non-keepers) and undrafted rookies appear in waiver wire during `offseason`
- Add sign/cut flow so teams can adjust rosters before the new season opens
- "Start New Season" commissioner action: resets week to 1, seeds new NFL schedule, moves to `regular_season`

---

## Part 2 — Phase 3: Flavor & Immersion

### Step 10 — Injury system (sim engine)
- Add `injury_risk` per archetype in `engine.py`
- During `simulate_game()`, players have a small chance of going `questionable` or `out`
- Store as `status` on the Player model with a `weeks_out` counter
- Add a `NflInjury` model to track injury history

### Step 11 — Injury system (roster management)
- Add an IR slot to rosters (17 → 18 spots)
- Injured players flag on the My Team page
- Commissioner panel shows current injury report

### Step 12 — Player profiles page
- New route `/player/<id>`
- Shows: player card (name, team, position, archetype, age, potential), season stats table,
  career history by year, ownership history (drafted by / traded to / waiver claimed)
- Linked from the player browser and roster views

### Step 13 — Trade history & activity log
- New route `/activity`
- Reverse-chronological feed of all league moves: trades accepted, waiver claims, draft picks
- Add a `LeagueActivity` model (event_type, description, week, created_at)
- Write to it whenever a trade is accepted, a waiver claim completes, or a pick is made

### Step 14 — Beat reporter (Claude API integration)
- Add `generate_news_report(week, year)` in a new `reporter.py`
- Pulls top performances, injury news, trade activity, and standings shifts for the week
- Calls the Claude API (claude-sonnet-4-6) to generate a 4–6 paragraph weekly dispatch
- Store result in a `NewsReport` model (week, season_year, body_html)
- Requires `ANTHROPIC_API_KEY` env var

### Step 15 — Beat reporter (news feed UI)
- New `/news` route and template listing all weekly dispatches, newest first
- Commissioner panel gets a "Generate This Week's Report" button
- Reports readable by all league members
- Tease the latest headline on the league standings page

---

## Key files
| File | Purpose |
|---|---|
| `models.py` | All SQLAlchemy models — add new models here |
| `app.py` | All Flask routes and business logic |
| `sim.py` | Weekly sim bridge — engine ↔ DB, fantasy scoring |
| `engine.py` | Stateless NFL game simulation engine |
| `seed.py` | Seeds DB from `rosters.csv` |
| `templates/` | Jinja2 templates, extends `base.html` |

## Running locally
```bash
python3 seed.py        # first run only
python3 -m flask run --port 5050
# then open http://localhost:5050/setup
```
