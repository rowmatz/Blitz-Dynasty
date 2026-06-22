import pandas as pd
import random
import os

ROSTER_FILE = 'rosters.csv'
FANTASY_FILE = 'fantasy_teams.csv'

# Expanded Name Database for retro-active fixing
FIRST_NAMES = ["Caleb", "Drake", "Jayden", "Bo", "Rome", "Brock", "Ty", "Zay", "Ashton", "Quinn", "Spencer", "Jordan", "Jja", "Kool", "Tank", "Bucky", "Xavier", "Keon", "Ladd", "Ricky", "Malik", "Troy", "Audric", "Blake", "Trey", "Marvin"]
LAST_NAMES = ["Williams", "Maye", "Daniels", "Nix", "Odunze", "Bowers", "Harrison", "Worthy", "Ewers", "Jeanty", "Rattler", "Travis", "McCarthy", "Corum", "Brooks", "Pearsall", "Coleman", "McConkey", "Pearsall", "Nabers", "Franklin", "Benson", "Estime", "Corum"]

def rename_rookies():
    if not os.path.exists(ROSTER_FILE):
        print("❌ No roster file found.")
        return

    print("🔄 Renaming generic rookies...")
    
    # Load files
    df_roster = pd.read_csv(ROSTER_FILE)
    df_fantasy = pd.DataFrame()
    if os.path.exists(FANTASY_FILE):
        df_fantasy = pd.read_csv(FANTASY_FILE)

    # Track name changes mapping {OldName: NewName}
    name_map = {}
    
    # 1. GENERATE NEW NAMES
    for index, row in df_roster.iterrows():
        old_name = row['Player_Name']
        
        # Only target "Rookie ..." names
        if str(old_name).startswith("Rookie "):
            
            # Generate unique new name
            while True:
                fname = random.choice(FIRST_NAMES)
                lname = random.choice(LAST_NAMES)
                new_name = f"{fname} {lname}"
                
                # Make sure it doesn't exist in the league AND we haven't just assigned it
                if new_name not in df_roster['Player_Name'].values and new_name not in name_map.values():
                    break
            
            # Store the change
            name_map[old_name] = new_name
            
            # Update Roster DataFrame immediately
            df_roster.at[index, 'Player_Name'] = new_name

    # 2. UPDATE FANTASY TEAMS
    if not df_fantasy.empty:
        # Apply the map to the fantasy file
        # If the player is in the map, use new name, else keep old
        df_fantasy['Player_Name'] = df_fantasy['Player_Name'].apply(lambda x: name_map.get(x, x))
        df_fantasy.to_csv(FANTASY_FILE, index=False)
        print("✅ Fantasy Roster names updated.")

    # 3. SAVE ROSTER
    df_roster.to_csv(ROSTER_FILE, index=False)
    
    print(f"✅ Success! Renamed {len(name_map)} players.")
    if len(name_map) > 0:
        print(f"   Example: '{list(name_map.keys())[0]}' is now '{list(name_map.values())[0]}'")

if __name__ == "__main__":
    rename_rookies()