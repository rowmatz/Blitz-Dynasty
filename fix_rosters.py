"""
One-off script: remove Chicago Wind, fill thin rosters to standard depth.
Standard depth: QB=1, RB=3, WR=5, TE=2
"""
import random
import pandas as pd

ROSTER_FILE = 'rosters.csv'

ARCHETYPES = {
    'QB': ['Gunslinger', 'Game Manager', 'Konami Code'],
    'RB': ['Bell Cow RB', 'Home Run RB'],
    'WR': ['Alpha WR', 'Deep Threat', 'Slot Machine'],
    'TE': ['Security TE', 'Unicorn TE'],
}

FIRST_NAMES = [
    'Marcus', 'DeShawn', 'Tyrell', 'Brandon', 'Corey', 'Damon', 'Elijah',
    'Freddie', 'Gerald', 'Hassan', 'Isaiah', 'Jerome', 'Kendall', 'Lamar',
    'Malik', 'Nate', 'Omar', 'Preston', 'Quentin', 'Rashad', 'Stevie',
    'Terrence', 'Ulysses', 'Vernon', 'Willie', 'Xavier', 'Yannick', 'Zach',
    'Andre', 'Byron', 'Calvin', 'Dante', 'Eddie', 'Floyd', 'Grant',
]
LAST_NAMES = [
    'Adams', 'Brooks', 'Carter', 'Dixon', 'Evans', 'Ford', 'Grant',
    'Hayes', 'Irving', 'Jackson', 'King', 'Lewis', 'Moore', 'Nash',
    'Owens', 'Parker', 'Quinn', 'Reed', 'Scott', 'Thomas', 'Underwood',
    'Vance', 'Walker', 'Xavier', 'Young', 'Zimmerman', 'Bell', 'Cox',
    'Dean', 'Ellis', 'Flynn', 'Gray', 'Hunt', 'Ingram', 'James',
]

TARGETS = {'QB': 1, 'RB': 3, 'WR': 5, 'TE': 2}


def unique_name(existing_names):
    for _ in range(1000):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name not in existing_names:
            return name
    raise RuntimeError("Could not generate a unique player name")


def main():
    df = pd.read_csv(ROSTER_FILE)
    print(f"Loaded {len(df)} rows")

    # 1. Drop Chicago Wind
    before = len(df)
    df = df[df['Team_Name'] != 'Chicago Wind']
    print(f"Removed Chicago Wind: {before - len(df)} rows dropped")

    existing_names = set(df['Player_Name'].values)

    # 2. Fill thin rosters
    thin_teams = ['Boston Bricklayers', 'Chicago Crushers', 'Miami Machines', 'NY Nightmares']
    new_rows = []

    for team_name in thin_teams:
        team_rows = df[df['Team_Name'] == team_name]
        abbr = team_rows.iloc[0]['Abbr']

        for pos, target_count in TARGETS.items():
            have = len(team_rows[team_rows['Position'] == pos])
            needed = target_count - have
            if needed <= 0:
                continue

            for _ in range(needed):
                name = unique_name(existing_names)
                existing_names.add(name)
                archetype = random.choice(ARCHETYPES[pos])
                age = random.randint(22, 27)
                potential = random.choices(['A', 'B', 'C', 'D'], weights=[10, 25, 45, 20])[0]
                skill_bonus = round(random.uniform(0.0, 0.08), 3)

                new_rows.append({
                    'Team_Name': team_name, 'Abbr': abbr,
                    'Player_Name': name, 'Position': pos,
                    'Archetype': archetype, 'Age': age,
                    'Potential': potential, 'Skill_Bonus': skill_bonus,
                    'Season_Pts': 0, 'Games_Played': 0,
                    'Pass_Yds': 0, 'Pass_TD': 0, 'Int': 0,
                    'Rush_Yds': 0, 'Rush_TD': 0,
                    'Rec_Yds': 0, 'Rec_TD': 0, 'Rec': 0, 'Targets': 0,
                })
                print(f"  + {team_name} | {pos} {archetype} | {name} (age {age}, pot {potential})")

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    df.to_csv(ROSTER_FILE, index=False)
    print(f"\nSaved {len(df)} rows to {ROSTER_FILE}")

    # 3. Verify
    print("\n=== FINAL VERIFICATION ===")
    skill = df[(df['Team_Name'] != 'FA') & (df['Position'] != 'DEF')]
    for team, grp in skill.groupby('Team_Name'):
        counts = grp.groupby('Position').size().to_dict()
        status = '✓' if counts.get('QB',0)==1 and counts.get('RB',0)==3 and counts.get('WR',0)==5 and counts.get('TE',0)==2 else '!'
        print(f"  {status} {team}: QB={counts.get('QB',0)} RB={counts.get('RB',0)} WR={counts.get('WR',0)} TE={counts.get('TE',0)}")

    total = len(skill)
    print(f"\nTotal draftable skill players: {total}")
    print(f"Draft needs: 170  |  Waiver pool: {total - 170}")
    teams = df[df['Team_Name'] != 'FA']['Team_Name'].nunique()
    print(f"NFL teams: {teams}")


if __name__ == '__main__':
    main()
