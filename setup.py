import pandas as pd
import csv

def create_initial_rosters(filename='rosters.csv'):
    # The 4 MVP Teams
    data = [
        # Columns
        ["Team_Name", "Abbr", "Player_Name", "Position", "Archetype", "Age", "Potential", "Skill_Bonus", "Season_Pts", "Games_Played"],
        
        # NY Nightmares (Risk Takers)
        ["NY Nightmares", "NYN", "Gunslinger Gary", "QB", "Gunslinger", 24, "A", 0.05, 0.0, 0],
        ["NY Nightmares", "NYN", "Speedy Gonzalez", "RB", "Home Run RB", 22, "B", 0.02, 0.0, 0],
        ["NY Nightmares", "NYN", "Deep Threat Danny", "WR", "Deep Threat", 25, "C", 0.0, 0.0, 0],
        ["NY Nightmares", "NYN", "Alpha Adam", "WR", "Alpha WR", 27, "A", 0.10, 0.0, 0],
        ["NY Nightmares", "NYN", "Safety Sam", "TE", "Security TE", 29, "C", -0.01, 0.0, 0],

        # Boston Bricklayers (Safe)
        ["Boston Bricklayers", "BOS", "Manager Mike", "QB", "Game Manager", 30, "C", 0.0, 0.0, 0],
        ["Boston Bricklayers", "BOS", "Grinder Greg", "RB", "Bell Cow RB", 26, "B", 0.03, 0.0, 0],
        ["Boston Bricklayers", "BOS", "Slot Steve", "WR", "Slot Machine", 24, "B", 0.01, 0.0, 0],
        ["Boston Bricklayers", "BOS", "Possession Paul", "WR", "Alpha WR", 28, "B", 0.05, 0.0, 0],
        ["Boston Bricklayers", "BOS", "Blocking Bob", "TE", "Security TE", 31, "D", -0.05, 0.0, 0],

        # Miami Machines (Balanced)
        ["Miami Machines", "MIA", "Balanced Bill", "QB", "Game Manager", 23, "B", 0.02, 0.0, 0],
        ["Miami Machines", "MIA", "All-Round Al", "RB", "Bell Cow RB", 25, "A", 0.08, 0.0, 0],
        ["Miami Machines", "MIA", "Star Stu", "WR", "Alpha WR", 22, "A", 0.04, 0.0, 0],
        ["Miami Machines", "MIA", "Speedy Steve", "WR", "Deep Threat", 24, "C", 0.01, 0.0, 0],
        ["Miami Machines", "MIA", "Reliable Rob", "TE", "Security TE", 27, "C", 0.0, 0.0, 0],

        # Chicago Crushers (Run Heavy)
        ["Chicago Crushers", "CHI", "Konami Karl", "QB", "Konami Code", 21, "A", 0.0, 0.0, 0],
        ["Chicago Crushers", "CHI", "Power Pete", "RB", "Bell Cow RB", 24, "B", 0.03, 0.0, 0],
        ["Chicago Crushers", "CHI", "Blocker Ben", "WR", "Slot Machine", 29, "C", -0.02, 0.0, 0],
        ["Chicago Crushers", "CHI", "Fast Fred", "WR", "Deep Threat", 22, "B", 0.01, 0.0, 0],
        ["Chicago Crushers", "CHI", "Big Barry", "TE", "Unicorn TE", 26, "A", 0.09, 0.0, 0]
    ]

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    print(f"✅ Successfully created {filename} with 4 teams.")

if __name__ == "__main__":
    create_initial_rosters()