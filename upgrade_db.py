import pandas as pd
import os

FILENAME = 'rosters.csv'

def upgrade_database():
    if not os.path.exists(FILENAME): return
    
    df = pd.read_csv(FILENAME)
    print(f"🔧 Upgrading {FILENAME}...")
    
    # List of new columns to track
    new_cols = [
        'Pass_Yds', 'Pass_TD', 'Int',
        'Rush_Yds', 'Rush_TD',
        'Rec_Yds', 'Rec_TD', 'Rec', 'Targets'
    ]
    
    for col in new_cols:
        if col not in df.columns:
            print(f"   + Adding {col}")
            df[col] = 0
            
    df.to_csv(FILENAME, index=False)
    print("✅ Database upgraded with Stat Tracking columns.")

if __name__ == "__main__":
    upgrade_database()