import pandas as pd
import os

FILENAME = 'rosters.csv'

def repair_stats():
    if not os.path.exists(FILENAME):
        print("❌ rosters.csv not found!")
        return

    print(f"🔧 Repairing {FILENAME} stats columns...")
    df = pd.read_csv(FILENAME)
    
    # Check and Add 'Season_Pts'
    if 'Season_Pts' not in df.columns:
        print("   + Adding Season_Pts column")
        df['Season_Pts'] = 0.0
    
    # Check and Add 'Games_Played'
    if 'Games_Played' not in df.columns:
        print("   + Adding Games_Played column")
        df['Games_Played'] = 0

    # Fill any NaNs with 0 just in case
    df['Season_Pts'] = df['Season_Pts'].fillna(0.0)
    df['Games_Played'] = df['Games_Played'].fillna(0)

    df.to_csv(FILENAME, index=False)
    print("✅ Repair Complete. You can now use the My Team page!")

if __name__ == "__main__":
    repair_stats()