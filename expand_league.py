import pandas as pd
import random
import os

FILENAME = 'rosters.csv'

# 28 FICTIONAL TEAMS (Updated)
NEW_TEAMS = [
    # West Coast & Mountain
    ("Los Angeles Leos", "LAL"), ("San Diego Surfers", "SD"), ("Portland Pioneers", "POR"), 
    ("Seattle Sasquatch", "SEA"), ("Vegas Vipers", "LV"), ("Salt Lake Stags", "SLC"),
    ("Phoenix Firebirds", "PHX"), ("Denver Peaks", "DEN"),
    
    # Central & South
    ("Austin Outlaws", "AUS"), ("San Antonio Sheriffs", "SAS"), ("Oklahoma Bisons", "OKC"),
    ("New Orleans Voodoo", "NOLA"), ("Memphis Kings", "MEM"), ("Nashville Notes", "NSH"),
    ("Texas Rattlers", "TEX"), ("Louisville Legion", "LOU"),
    
    # Midwest & North
    ("Chicago Wind", "CHI"), ("Detroit Diesels", "DET"), 
    ("Milwaukee Maulers", "MIL"), # <--- RENAMED to avoid clash with Miami Machines
    ("Toronto Thunder", "TOR"), ("Montreal Mounties", "MTL"), ("Philadelphia Cannons", "PHI"),
    
    # East Coast
    ("Washington Warriors", "WAS"), ("Carolina Cobras", "CAR"), ("Florida Gators", "FLA"),
    ("Atlanta Swarm", "ATL"), ("Orlando Orbit", "ORL"),
    
    # International / Misc
    ("Mexico City Diablos", "MEX"), ("Paris Musketeers", "PAR")
]

# Config from Engine
VALID_ARCHETYPES = {
    "QB": ["Gunslinger", "Game Manager", "Konami Code"],
    "RB": ["Bell Cow RB", "Home Run RB"],
    "WR": ["Alpha WR", "Deep Threat", "Slot Machine"],
    "TE": ["Security TE", "Unicorn TE"],
    "DEF": ["Steel Curtain", "No Fly Zone", "Blitz Heavy", "Balanced"]
}

# Name Generators
FIRST_NAMES = ["Jalen", "Trevor", "Justin", "Patrick", "Joe", "Lamar", "Dak", "Josh", "Brock", "Tua", "Jared", "Kirk", "Geno", "Derek", "Baker", "Matthew", "Russell", "Aaron", "Kyler", "Deshaun", "Bryce", "CJ", "Anthony", "Will", "Sam", "Kenny", "Mac", "Jimmy", "Ryan", "Gardner", "Tyson", "Kobe", "LeBron", "Zion", "Luka"]
LAST_NAMES = ["Hurts", "Lawrence", "Herbert", "Mahomes", "Burrow", "Jackson", "Prescott", "Allen", "Purdy", "Tagovailoa", "Goff", "Cousins", "Smith", "Carr", "Mayfield", "Stafford", "Wilson", "Rodgers", "Murray", "Watson", "Young", "Stroud", "Richardson", "Levis", "Howell", "Pickett", "Jones", "Garoppolo", "Tannehill", "Minshew", "Bolt", "Strong", "Fast", "Wise"]

def expand_league_custom():
    if not os.path.exists(FILENAME):
        print("❌ No roster file found.")
        return

    df = pd.read_csv(FILENAME)
    existing_teams = df['Team_Name'].unique().tolist()
    print(f"📉 Current League Size: {len(existing_teams)-1} Teams")
    
    new_players = []
    
    for team_name, abbr in NEW_TEAMS:
        if team_name in existing_teams:
            continue 
            
        print(f"   + Franchising {team_name}...")
        
        # Roster Needs
        roster_needs = [("QB", 1), ("RB", 3), ("WR", 5), ("TE", 2), ("DEF", 1)]
        
        for pos, count in roster_needs:
            for i in range(count):
                arch = random.choice(VALID_ARCHETYPES[pos])
                age = random.randint(21, 35)
                pot = random.choice(['A', 'B', 'C', 'C', 'D'])
                bonus = random.uniform(-0.05, 0.15)
                
                if pos == "DEF":
                    p_name = f"{team_name} Defense"
                    age = 0
                else:
                    p_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                    if any(p['Player_Name'] == p_name for p in new_players):
                        p_name = f"{p_name} Jr."

                new_players.append({
                    "Team_Name": team_name, "Abbr": abbr, "Player_Name": p_name,
                    "Position": pos, "Archetype": arch, "Age": age,
                    "Potential": pot, "Skill_Bonus": bonus,
                    "Season_Pts": 0, "Games_Played": 0,
                    "Pass_Yds":0, "Pass_TD":0, "Int":0, "Rush_Yds":0, "Rush_TD":0, 
                    "Rec_Yds":0, "Rec_TD":0, "Rec":0, "Targets":0
                })

    if new_players:
        df_new = pd.DataFrame(new_players)
        df_final = pd.concat([df, df_new], ignore_index=True)
        df_final.to_csv(FILENAME, index=False)
        print(f"✅ Custom Expansion Complete! League now has 32 teams.")
    else:
        print("✅ No new teams added.")

if __name__ == "__main__":
    expand_league_custom()