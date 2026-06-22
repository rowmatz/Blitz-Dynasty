import pandas as pd
import os

ROSTER_FILE = 'rosters.csv'
FANTASY_FILE = 'fantasy_teams.csv'
RIVAL_NAME = "The Machine"

def fill_rival():
    if not os.path.exists(ROSTER_FILE): return
    
    # 1. Load Data
    r_df = pd.read_csv(ROSTER_FILE)
    
    # Load or Create Fantasy File
    if os.path.exists(FANTASY_FILE):
        f_df = pd.read_csv(FANTASY_FILE)
    else:
        f_df = pd.DataFrame(columns=["Fantasy_Team", "Owner", "Player_Name", "Sim_Team", "Position"])

    # 2. Clear previous Rival team (to ensure a fresh competitive squad)
    f_df = f_df[f_df['Owner'] != RIVAL_NAME]
    
    # 3. Define Needs (Starting Lineup)
    # We sort by Skill_Bonus to give them the best available players
    # Exclude players already owned by YOU
    owned_players = f_df['Player_Name'].tolist()
    available = r_df[~r_df['Player_Name'].isin(owned_players)].sort_values(by='Skill_Bonus', ascending=False)
    
    roster_slots = [("QB", 1), ("RB", 2), ("WR", 2), ("TE", 1), ("DEF", 1)]
    
    new_picks = []
    
    print(f"🤖 {RIVAL_NAME} is drafting...")
    
    for pos, count in roster_slots:
        # Get top available for this position
        candidates = available[available['Position'] == pos]
        
        # Take top N
        picks = candidates.head(count)
        
        for _, p in picks.iterrows():
            new_picks.append({
                "Fantasy_Team": "Skynet United",
                "Owner": RIVAL_NAME,
                "Player_Name": p['Player_Name'],
                "Sim_Team": p['Team_Name'],
                "Position": pos
            })
            print(f"   + Drafted {pos} {p['Player_Name']}")
            
            # Remove from available so we don't pick same guy twice (edge case)
            available = available[available['Player_Name'] != p['Player_Name']]

    # 4. Save
    if new_picks:
        f_df = pd.concat([f_df, pd.DataFrame(new_picks)], ignore_index=True)
        f_df.to_csv(FANTASY_FILE, index=False)
        print("✅ Rival Roster Set.")
    else:
        print("⚠️ Could not find players to draft.")

if __name__ == "__main__":
    fill_rival()