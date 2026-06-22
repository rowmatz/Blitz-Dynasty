import pandas as pd
import os
import random

FILENAME = 'rosters.csv'

# Archetypes from engine.py
DEF_ARCHS = ["Steel Curtain", "No Fly Zone", "Blitz Heavy", "Balanced"]

def add_defenses():
    if not os.path.exists(FILENAME): return
    print("🛡️  Adding Defensive Units to the League...")
    
    df = pd.read_csv(FILENAME)
    
    # Get List of Teams
    teams = [t for t in df['Team_Name'].unique() if t != "FA"]
    
    new_rows = []
    
    for team in teams:
        # Check if they already have a DEF
        has_def = df[(df['Team_Name'] == team) & (df['Position'] == 'DEF')]
        if not has_def.empty:
            continue
            
        print(f"   + Commissioning Defense for {team}")
        
        # Get Abbreviation from another player on the team
        abbr = df[df['Team_Name'] == team].iloc[0]['Abbr']
        
        # Create Defense Row
        new_rows.append({
            "Team_Name": team,
            "Abbr": abbr,
            "Player_Name": f"{team} Defense", # e.g. "Chicago Bears Defense"
            "Position": "DEF",
            "Archetype": random.choice(DEF_ARCHS),
            "Age": 0, # Defenses don't age like humans
            "Potential": "C",
            "Skill_Bonus": 0.0,
            "Season_Pts": 0.0,
            "Games_Played": 0
        })
        
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df.to_csv(FILENAME, index=False)
        print(f"✅ Added {len(new_rows)} defenses.")
    else:
        print("✅ All teams already have defenses.")

if __name__ == "__main__":
    add_defenses()