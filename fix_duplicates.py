import pandas as pd

def fix_duplicates(filename='rosters.csv'):
    df = pd.read_csv(filename)
    
    # Check for duplicates
    # keep='first' marks the second occurrence as True
    duplicates = df[df.duplicated('Player_Name', keep=False)]
    
    if duplicates.empty:
        print("✅ No duplicates found.")
        return

    print(f"⚠️ Found {len(duplicates)} collision(s). Fixing...")
    
    # Logic: If name matches, append " Jr." or " II" to the younger one
    # Sort by Age so we rename the young one
    df = df.sort_values(by=['Player_Name', 'Age'], ascending=[True, False])
    
    # Identify duplicates again after sort
    mask = df.duplicated('Player_Name', keep='first') # Mark the 2nd/younger ones
    
    # Rename them
    df.loc[mask, 'Player_Name'] = df.loc[mask, 'Player_Name'] + " II"
    
    df.to_csv(filename, index=False)
    print("✅ Fixed! Duplicate rookies have been renamed (e.g. 'Rookie 938 II').")

if __name__ == "__main__":
    fix_duplicates()