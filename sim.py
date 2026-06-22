"""
sim.py — bridges engine.py simulation with the SQLAlchemy DB.

Responsibilities:
  - Convert DB models → engine Player/Team objects
  - Run simulate_game() and write results back to DB
  - Generate fantasy schedule at season start
  - Auto-set lineups for teams that haven't set one
  - Calculate fantasy scores from week's player stats
"""
import json
import random

from models import (
    db, NflTeam, Player, NflSchedule, NflGame, PlayerGameStat,
    FantasyTeam, FantasyRoster, FantasySchedule, FantasyResult,
    FantasyLineup, LeagueState,
    STARTER_SLOTS, SLOT_ELIGIBILITY, LINEUP_SLOTS,
)
from engine import (
    Player as EngPlayer,
    Team   as EngTeam,
    simulate_game,
    calculate_fantasy_points,
)

FANTASY_REGULAR_SEASON_WEEKS = 14


# ==============================================================================
# ENGINE BRIDGE
# ==============================================================================

def _db_player_to_eng(p: Player) -> EngPlayer:
    return EngPlayer(p.name, p.position, p.archetype, p.age, p.potential, p.skill_bonus)


def _db_team_to_eng(nfl_team: NflTeam) -> EngTeam:
    eng = EngTeam(nfl_team.name, nfl_team.abbr)
    for p in nfl_team.players:
        if p.status != 'active':
            continue
        ep = _db_player_to_eng(p)
        if   p.position == 'QB':  eng.qbs.append(ep)
        elif p.position == 'RB':  eng.rbs.append(ep)
        elif p.position == 'WR':  eng.wrs.append(ep)
        elif p.position == 'TE':  eng.tes.append(ep)
        elif p.position == 'DEF': eng.defs.append(ep)

    if not eng.defs: eng.defs.append(EngPlayer(f"{nfl_team.name} Defense", "DEF", "Balanced"))
    if not eng.qbs:  eng.qbs.append(EngPlayer("Scrub QB",  "QB",  "Game Manager"))
    if not eng.rbs:  eng.rbs.append(EngPlayer("Scrub RB",  "RB",  "Bell Cow RB"))
    if not eng.wrs:  eng.wrs.append(EngPlayer("Scrub WR",  "WR",  "Slot Machine"))
    if not eng.tes:  eng.tes.append(EngPlayer("Scrub TE",  "TE",  "Security TE"))
    return eng


# ==============================================================================
# FANTASY SCHEDULE GENERATION
# ==============================================================================

def generate_fantasy_schedule(season_year: int):
    """
    Round-robin schedule for 10 fantasy teams over 14 weeks.
    Weeks 1-9: full round-robin (every team plays every other once).
    Weeks 10-14: repeat weeks 1-5 for balance.
    """
    teams = FantasyTeam.query.all()
    n = len(teams)
    if n < 2:
        return

    ids = [t.id for t in teams]
    if n % 2 == 1:
        ids.append(None)  # bye placeholder

    half = len(ids) // 2
    rounds = []

    for r in range(len(ids) - 1):
        pairs = []
        for i in range(half):
            h = ids[i]
            a = ids[len(ids) - 1 - i]
            if h is not None and a is not None:
                if random.random() < 0.5:
                    h, a = a, h
                pairs.append((h, a))
        rounds.append(pairs)
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]   # rotate keeping ids[0] fixed

    # 14 regular-season weeks: 9 round-robin + repeat weeks 0-4
    schedule_rounds = rounds[:9] + rounds[:5]

    for week_idx, pairs in enumerate(schedule_rounds):
        week = week_idx + 1
        for home_id, away_id in pairs:
            db.session.add(FantasySchedule(
                season_year=season_year,
                week=week,
                home_team_id=home_id,
                away_team_id=away_id,
            ))

    db.session.flush()


# ==============================================================================
# LINEUP MANAGEMENT
# ==============================================================================

def _player_value(p: Player, week: int, season_year: int) -> float:
    """Score to rank players for auto-lineup. Use season avg; fall back to skill_bonus."""
    if p.games_played > 0:
        return p.season_pts / p.games_played
    return p.skill_bonus * 10


def auto_set_lineup(fantasy_team: FantasyTeam, week: int, season_year: int):
    """Fill lineup slots for a team that hasn't set one yet."""
    existing = FantasyLineup.query.filter_by(
        fantasy_team_id=fantasy_team.id, week=week, season_year=season_year
    ).count()
    if existing > 0:
        return  # already set

    roster_entries = FantasyRoster.query.filter_by(fantasy_team_id=fantasy_team.id).all()
    players = [r.player for r in roster_entries]

    # Sort by value descending
    players.sort(key=lambda p: _player_value(p, week, season_year), reverse=True)

    assigned = {}   # slot → player
    used_ids = set()

    def best_for_slot(slot):
        eligible = SLOT_ELIGIBILITY.get(slot, [])
        for p in players:
            if p.id not in used_ids and p.position in eligible:
                return p
        return None

    # Fill starter slots in order
    for slot in STARTER_SLOTS:
        p = best_for_slot(slot)
        if p:
            assigned[slot] = p
            used_ids.add(p.id)

    # Remaining players on bench
    bench_slots = [s for s in LINEUP_SLOTS if s not in STARTER_SLOTS]
    for slot in bench_slots:
        for p in players:
            if p.id not in used_ids:
                assigned[slot] = p
                used_ids.add(p.id)
                break

    for slot, p in assigned.items():
        db.session.add(FantasyLineup(
            fantasy_team_id=fantasy_team.id,
            player_id=p.id,
            season_year=season_year,
            week=week,
            slot=slot,
        ))

    db.session.flush()


# ==============================================================================
# WEEKLY SIM
# ==============================================================================

def simulate_week(state: LeagueState) -> dict:
    """
    Simulate all NFL games for the current week, calculate fantasy scores,
    advance the week counter. Returns a summary dict for the UI.

    Must be called inside an app_context with an active DB session.
    """
    week       = state.week
    year       = state.season_year
    is_fantasy = week <= FANTASY_REGULAR_SEASON_WEEKS

    # ── 1. LOAD NFL TEAMS ─────────────────────────────────────────────────────
    nfl_teams_db = NflTeam.query.all()
    eng_teams    = {t.name: _db_team_to_eng(t) for t in nfl_teams_db}
    team_db_map  = {t.name: t for t in nfl_teams_db}

    # Name → DB player lookup (skill positions only)
    player_db_map = {p.name: p for p in Player.query.filter(Player.position != 'DEF').all()}

    # ── 2. SIMULATE NFL GAMES ─────────────────────────────────────────────────
    scheduled_games = NflSchedule.query.filter_by(
        week=week, season_year=year, simulated=False
    ).all()

    if not scheduled_games:
        return {'error': f'No unplayed games for week {week}'}

    nfl_results = []

    for sched in scheduled_games:
        home_eng = eng_teams[sched.home_team.name]
        away_eng = eng_teams[sched.away_team.name]

        scores, drives, game_stats = simulate_game(home_eng, away_eng)

        home_score = scores[sched.home_team.name]
        away_score = scores[sched.away_team.name]

        # Save game record
        game = NflGame(
            nfl_schedule_id=sched.id,
            home_score=home_score,
            away_score=away_score,
            game_log=json.dumps(drives),
        )
        db.session.add(game)
        db.session.flush()   # get game.id

        # Mark schedule as simulated + update standings
        sched.simulated = True
        ht = team_db_map[sched.home_team.name]
        at = team_db_map[sched.away_team.name]
        ht.points_for    += home_score;  ht.points_against += away_score
        at.points_for    += away_score;  at.points_against += home_score
        if   home_score > away_score: ht.wins  += 1; at.losses += 1
        elif away_score > home_score: at.wins  += 1; ht.losses += 1
        else:                         ht.draws += 1; at.draws  += 1

        # Save per-player stats
        for pname, stats in game_stats.items():
            db_p = player_db_map.get(pname)
            if not db_p:
                continue
            pts = calculate_fantasy_points(stats)
            db.session.add(PlayerGameStat(
                player_id  = db_p.id,
                game_id    = game.id,
                week       = week,
                season_year= year,
                pass_yds   = stats.get('pass_yds', 0),
                pass_td    = stats.get('pass_td',  0),
                ints       = stats.get('int',      0),
                rush_yds   = stats.get('rush_yds', 0),
                rush_td    = stats.get('rush_td',  0),
                rec_yds    = stats.get('rec_yds',  0),
                rec_td     = stats.get('rec_td',   0),
                rec        = stats.get('rec',      0),
                targets    = stats.get('targets',  0),
                sacks      = stats.get('sacks',    0),
                fantasy_pts= pts,
            ))
            # Accumulate season totals
            db_p.season_pts    += pts
            db_p.games_played  += 1
            db_p.pass_yds      += stats.get('pass_yds', 0)
            db_p.pass_td       += stats.get('pass_td',  0)
            db_p.ints          += stats.get('int',      0)
            db_p.rush_yds      += stats.get('rush_yds', 0)
            db_p.rush_td       += stats.get('rush_td',  0)
            db_p.rec_yds       += stats.get('rec_yds',  0)
            db_p.rec_td        += stats.get('rec_td',   0)
            db_p.rec           += stats.get('rec',      0)
            db_p.targets       += stats.get('targets',  0)

        nfl_results.append({
            'home': sched.home_team.abbr, 'home_score': home_score,
            'away': sched.away_team.abbr, 'away_score': away_score,
        })

    db.session.flush()

    # ── 3. FANTASY SCORING ────────────────────────────────────────────────────
    fantasy_results = []

    if is_fantasy:
        fantasy_teams = FantasyTeam.query.all()

        # Auto-set lineups for any team that hasn't set one
        for ft in fantasy_teams:
            auto_set_lineup(ft, week, year)

        db.session.flush()

        # Build player_id → fantasy_pts for this week
        week_stats = PlayerGameStat.query.filter_by(week=week, season_year=year).all()
        pts_map = {}   # player_id → total pts this week (could play in 1 game)
        for pgs in week_stats:
            pts_map[pgs.player_id] = pts_map.get(pgs.player_id, 0.0) + pgs.fantasy_pts

        # Score each fantasy team's starting lineup
        def score_lineup(ft_id):
            starters = FantasyLineup.query.filter(
                FantasyLineup.fantasy_team_id == ft_id,
                FantasyLineup.week == week,
                FantasyLineup.season_year == year,
                FantasyLineup.slot.in_(STARTER_SLOTS),
            ).all()
            return round(sum(pts_map.get(s.player_id, 0.0) for s in starters), 2)

        matchups = FantasySchedule.query.filter_by(week=week, season_year=year).all()

        for matchup in matchups:
            home_pts = score_lineup(matchup.home_team_id)
            away_pts = score_lineup(matchup.away_team_id)
            winner_id = matchup.home_team_id if home_pts >= away_pts else matchup.away_team_id

            result = FantasyResult(
                fantasy_schedule_id=matchup.id,
                home_score=home_pts,
                away_score=away_pts,
                winner_id=winner_id,
            )
            db.session.add(result)

            # Update W/L/PF/PA
            ht = db.session.get(FantasyTeam, matchup.home_team_id)
            at = db.session.get(FantasyTeam, matchup.away_team_id)
            ht.points_for    += home_pts;  ht.points_against += away_pts
            at.points_for    += away_pts;  at.points_against += home_pts
            if home_pts > away_pts:  ht.wins  += 1; at.losses += 1
            elif away_pts > home_pts: at.wins  += 1; ht.losses += 1
            else:                    ht.wins  += 1; at.wins   += 1  # tie = both win (rare)

            fantasy_results.append({
                'home': ht.name, 'home_score': home_pts,
                'away': at.name, 'away_score': away_pts,
                'winner': ht.name if winner_id == ht.id else at.name,
            })

    # ── 4. ADVANCE WEEK ───────────────────────────────────────────────────────
    state.week += 1
    if state.week > FANTASY_REGULAR_SEASON_WEEKS and state.phase == 'regular_season':
        state.phase = 'playoffs'

    db.session.commit()

    return {
        'week_simmed': week,
        'nfl_games': len(nfl_results),
        'nfl_results': nfl_results,
        'fantasy_results': fantasy_results,
    }
