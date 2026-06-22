"""
Seed the database from rosters.csv.
Run once after setup, or any time you need to reset NFL data.

Creates:
  - 32 NFL teams
  - All skill position players (draftable)
  - 1 DEF unit per team (sim engine only, not draftable)
  - 18-week NFL schedule
"""
import random
import pandas as pd
from app import app, db
from models import NflTeam, Player, NflSchedule

ROSTER_FILE = 'rosters.csv'
SEASON_YEAR = 2025
WEEKS = 18


def generate_schedule(team_ids, season_year, weeks):
    """
    Pair all 32 teams each week. Uses a rotating round-robin so every team
    faces a variety of opponents across the season.
    """
    n = len(team_ids)
    # Fix team[0], rotate the rest — standard round-robin algorithm
    fixed = team_ids[0]
    rotating = team_ids[1:]
    schedules = []

    for week in range(1, weeks + 1):
        pairs = [(fixed, rotating[0])]
        for i in range(1, n // 2):
            pairs.append((rotating[i], rotating[n - 1 - i]))

        for home_id, away_id in pairs:
            # Randomly assign home/away each week
            if random.random() < 0.5:
                home_id, away_id = away_id, home_id
            schedules.append(NflSchedule(
                season_year=season_year,
                week=week,
                home_team_id=home_id,
                away_team_id=away_id,
                simulated=False,
            ))

        # Rotate
        rotating = [rotating[-1]] + rotating[:-1]

    return schedules


def main():
    with app.app_context():
        print("Clearing existing NFL data...")
        NflSchedule.query.delete()
        Player.query.delete()
        NflTeam.query.delete()
        db.session.commit()

        df = pd.read_csv(ROSTER_FILE)
        df['Skill_Bonus'] = pd.to_numeric(df['Skill_Bonus'], errors='coerce').fillna(0.0)
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(21).astype(int)
        df['Potential'] = df['Potential'].fillna('C').astype(str)

        # ── 1. NFL TEAMS ────────────────────────────────────────────────────────
        teams_df = (
            df[df['Team_Name'] != 'FA'][['Team_Name', 'Abbr']]
            .drop_duplicates(subset='Team_Name')
            .sort_values('Team_Name')
        )

        team_map = {}  # name → NflTeam
        for _, row in teams_df.iterrows():
            team = NflTeam(name=row['Team_Name'], abbr=row['Abbr'])
            db.session.add(team)
            team_map[row['Team_Name']] = team

        db.session.flush()
        print(f"  Created {len(team_map)} NFL teams")

        # ── 2. SKILL POSITION PLAYERS ───────────────────────────────────────────
        skill_df = df[df['Position'] != 'DEF'].copy()
        player_count = 0

        for _, row in skill_df.iterrows():
            team_name = row['Team_Name']
            nfl_team_id = team_map[team_name].id if team_name in team_map else None

            player = Player(
                nfl_team_id=nfl_team_id,
                name=row['Player_Name'],
                position=row['Position'],
                archetype=row['Archetype'],
                age=int(row['Age']),
                potential=row['Potential'],
                skill_bonus=float(row['Skill_Bonus']),
                status='active',
            )
            db.session.add(player)
            player_count += 1

        db.session.flush()
        print(f"  Created {player_count} skill players")

        # ── 3. DEF UNITS (one per team, engine-only) ────────────────────────────
        def_df = df[(df['Position'] == 'DEF') & (df['Team_Name'] != 'FA')]
        teams_with_def = set(def_df['Team_Name'].values)
        def_count = 0

        for _, row in def_df.iterrows():
            team_name = row['Team_Name']
            if team_name not in team_map:
                continue
            player = Player(
                nfl_team_id=team_map[team_name].id,
                name=row['Player_Name'],
                position='DEF',
                archetype=row['Archetype'],
                age=0,
                potential='C',
                skill_bonus=float(row['Skill_Bonus']),
                status='active',
            )
            db.session.add(player)
            def_count += 1

        # Any team missing a DEF in the CSV gets a default Balanced unit
        for team_name, team in team_map.items():
            if team_name not in teams_with_def:
                player = Player(
                    nfl_team_id=team.id,
                    name=f"{team_name} Defense",
                    position='DEF',
                    archetype='Balanced',
                    age=0,
                    potential='C',
                    skill_bonus=0.0,
                    status='active',
                )
                db.session.add(player)
                def_count += 1

        db.session.flush()
        print(f"  Created {def_count} DEF units")

        # ── 4. NFL SCHEDULE ─────────────────────────────────────────────────────
        team_ids = [t.id for t in team_map.values()]
        random.shuffle(team_ids)  # randomise starting rotation

        schedules = generate_schedule(team_ids, SEASON_YEAR, WEEKS)
        for s in schedules:
            db.session.add(s)

        db.session.commit()
        print(f"  Generated {len(schedules)} games ({WEEKS} weeks × {len(schedules)//WEEKS} games/week)")

        # ── 5. VERIFY ───────────────────────────────────────────────────────────
        print("\n=== SEED COMPLETE ===")
        print(f"NFL Teams    : {NflTeam.query.count()}")
        print(f"Skill Players: {Player.query.filter(Player.position != 'DEF').count()}")
        print(f"DEF Units    : {Player.query.filter_by(position='DEF').count()}")
        print(f"Schedule     : {NflSchedule.query.count()} games, {WEEKS} weeks")

        # Spot-check: each team should have exactly 18 games
        from sqlalchemy import or_
        issues = []
        for team in NflTeam.query.all():
            games = NflSchedule.query.filter(
                or_(NflSchedule.home_team_id == team.id,
                    NflSchedule.away_team_id == team.id)
            ).count()
            if games != WEEKS:
                issues.append(f"  ! {team.name}: {games} games")

        if issues:
            print("Schedule issues:")
            for i in issues: print(i)
        else:
            print(f"Schedule check: all 32 teams have exactly {WEEKS} games ✓")


if __name__ == '__main__':
    main()
