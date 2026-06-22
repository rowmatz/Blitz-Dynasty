import pandas as pd
import os

FILENAME = 'rosters.csv'

def force_reset():
    if not os.path.exists(FILENAME):
        print("❌ rosters.csv not found")
        return

    print(f"🧹 Scrubbing stats from {FILENAME}...")
    df = pd.read_csv(FILENAME)
    
    # Force reset all tracking columns
    df['Season_Pts'] = 0.0
    df['Games_Played'] = 0
    df['Skill_Bonus'] = df['Skill_Bonus'].fillna(0.0) # Ensure bonuses exist
    
    df.to_csv(FILENAME, index=False)
    print("✅ Stats reset to 0.0. Your 'My Team' page should now be clean.")

if __name__ == "__main__":
    force_reset()