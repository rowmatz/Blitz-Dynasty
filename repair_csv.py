import pandas as pd
import random

FILENAME = 'rosters.csv'

def repair():
    print(f"🔧 Repairing {FILENAME}...")
    df = pd.read_csv(FILENAME)
    
    # 1. Fix Potential (Strings)
    # If the column doesn't exist, create it.
    if 'Potential' not in df.columns:
        df['Potential'] = 'C'
    
    # Fill actual NaN values with 'C'
    df['Potential'] = df['Potential'].fillna('C')

    # 2. Fix Skill_Bonus (Numbers)
    if 'Skill_Bonus' not in df.columns:
        df['Skill_Bonus'] = 0.0
    
    # Fill NaN numbers with 0.0
    df['Skill_Bonus'] = df['Skill_Bonus'].fillna(0.0)

    # 3. Fix Ages (Just in case)
    df['Age'] = df['Age'].fillna(21)

    # 4. Save back to CSV
    df.to_csv(FILENAME, index=False)
    print("✅ Repair Complete. No more NaNs!")

if __name__ == "__main__":
    repair()