import pandas as pd
import random
import os
import csv 
from datetime import datetime
import json
STATE_FILE = 'state.json'
GAME_LOG_FILE = 'game_log.json'

# ==============================================================================
# 1. CONFIG & STATS
# ==============================================================================
ARCHETYPE_STATS = {
    # --- OFFENSE ---
    "Gunslinger":   {"throw_deep_chance": 0.35, "int_chance": 0.045, "completion_mod": -0.05},
    "Game Manager": {"throw_deep_chance": 0.10, "int_chance": 0.015, "completion_mod": 0.10},
    "Konami Code":  {"throw_deep_chance": 0.20, "int_chance": 0.025, "scramble_chance": 0.15},
    "Alpha WR":     {"catch_mod": 0.05, "yards_mean": 14, "target_weight": 10},
    "Deep Threat":  {"catch_mod": -0.10,"yards_mean": 25, "target_weight": 6},
    "Slot Machine": {"catch_mod": 0.15, "yards_mean": 9,  "target_weight": 8},
    "Bell Cow RB":  {"catch_mod": -0.1, "yards_mean": 4,  "breakaway_chance": 0.02},
    "Home Run RB":  {"catch_mod": 0.0,  "yards_mean": 3,  "breakaway_chance": 0.08},
    "Security TE":  {"catch_mod": 0.20, "yards_mean": 7,  "target_weight": 5},
    "Unicorn TE":   {"catch_mod": 0.05, "yards_mean": 14, "target_weight": 9},
    
    # --- DEFENSE (Modifiers applied to OPPONENT) ---
    # pass_def: subtracts from QB completion %
    # run_def: subtracts from RB yards mean
    # pressure: increases INT chance
    "Steel Curtain": {"pass_def": 0.05, "run_def": 2.0, "pressure": 0.0},
    "No Fly Zone":   {"pass_def": 0.15, "run_def": 0.0, "pressure": 0.02},
    "Blitz Heavy":   {"pass_def": 0.10, "run_def": 0.5, "pressure": 0.05},
    "Balanced":      {"pass_def": 0.05, "run_def": 1.0, "pressure": 0.01}
}

VALID_ARCHETYPES = {
    "QB": ["Gunslinger", "Game Manager", "Konami Code"],
    "RB": ["Bell Cow RB", "Home Run RB"],
    "WR": ["Alpha WR", "Deep Threat", "Slot Machine"],
    "TE": ["Security TE", "Unicorn TE"],
    "DEF": ["Steel Curtain", "No Fly Zone", "Blitz Heavy", "Balanced"]
}

# ==============================================================================
# 2. CLASSES
# ==============================================================================
class Player:
    def __init__(self, name, position, archetype, age=21, potential='C', skill_bonus=0.0):
        self.name = name
        self.position = position
        self.archetype = archetype
        self.age = age
        self.potential = potential
        self.skill_bonus = skill_bonus
        
        # Load Stats
        default = ARCHETYPE_STATS["Balanced"] if position == "DEF" else ARCHETYPE_STATS["Bell Cow RB"]
        self.stats = ARCHETYPE_STATS.get(archetype, default).copy()
        
        # Apply Skill Bonus Logic
        if position == "DEF":
            # Better DEF = Higher suppression
            if 'pass_def' in self.stats: self.stats['pass_def'] += (skill_bonus * 0.5)
            if 'run_def' in self.stats: self.stats['run_def'] += (skill_bonus * 2)
            if 'pressure' in self.stats: self.stats['pressure'] += (skill_bonus * 0.2)
        else:
            if 'catch_mod' in self.stats: self.stats['catch_mod'] += skill_bonus
            if 'yards_mean' in self.stats: self.stats['yards_mean'] += (self.stats['yards_mean'] * skill_bonus)

class Team:
    def __init__(self, name, abbr):
        self.name = name
        self.abbr = abbr
        self.qbs = []; self.rbs = []; self.wrs = []; self.tes = []
        self.defs = [] # List of Defenses (Starter vs Bench)

# ==============================================================================
# 3. SIMULATION
# ==============================================================================
def add_stat(stats_dict, player_name, category, value):
    if player_name not in stats_dict:
        stats_dict[player_name] = {
            "pass_yds":0, "pass_td":0, "int":0, 
            "rush_yds":0, "rush_td":0, 
            "rec_yds":0, "rec_td":0, "rec":0, 
            "targets":0, "sacks":0
        }
    stats_dict[player_name][category] += value

def get_starter(players, weights):
    if not players: return None
    available_weights = weights[:len(players)]
    if sum(available_weights) == 0: return random.choice(players)
    return random.choices(players, weights=available_weights, k=1)[0]

def simulate_drive(offense, defense_team, scores, game_stats):
    """
    Simulates one possession.
    Returns: { "result": str, "yards": int, "plays": list }
    """
    curr = 20; to_go = 10; down = 1
    drive_yards = 0; drive_plays = []; drive_result = "PUNT"
    
    # 1. GET STARTERS
    qb = get_starter(offense.qbs, [98, 2, 0]) or Player("Scrub QB", "QB", "Game Manager")
    
    # Get Opponent Defense (Restoring the Defense Logic)
    defense = get_starter(defense_team.defs, [100]) or Player("Scrub DEF", "DEF", "Balanced")
    
    # 2. CALC MODIFIERS
    pass_suppression = defense.stats.get('pass_def', 0.05)
    run_suppression = defense.stats.get('run_def', 1.0)
    pressure_boost = defense.stats.get('pressure', 0.0)

    while True:
        # A. SCORING CHECKS
        if down > 4:
            if curr > 65: 
                scores[offense.name] += 3
                drive_result = "FIELD GOAL"
                drive_plays.append(f"👟 FIELD GOAL! {offense.abbr} kicks it through.")
            else: 
                drive_result = "DOWNS"
                drive_plays.append(f"🛑 Turnover on Downs.")
            break
        
        # B. PLAY LOGIC
        is_pass = random.random() > 0.45
        gained = 0
        play_desc = ""
        
        if is_pass:
            # Targets
            targets = []
            weights = []
            if len(offense.wrs) > 0: targets.append(offense.wrs[0]); weights.append(30)
            if len(offense.wrs) > 1: targets.append(offense.wrs[1]); weights.append(20)
            if len(offense.tes) > 0: targets.append(offense.tes[0]); weights.append(15)
            if len(offense.rbs) > 0: targets.append(offense.rbs[0]); weights.append(15)
            if len(offense.wrs) > 2: targets.append(offense.wrs[2]); weights.append(10)
            
            target = random.choices(targets, weights=weights, k=1)[0] if targets else qb
            
            # --- NEW: TRACK TARGETS ---
            add_stat(game_stats, target.name, "targets", 1)
            # --------------------------

            # Math: Skill - Defense
            chance = (0.65 + qb.stats.get('completion_mod',0) + target.stats.get('catch_mod',0)) - pass_suppression
            
            if random.random() < chance:
                mean = target.stats.get('yards_mean', 10)
                gained = int(random.gauss(mean, 5))
                if gained < 0: gained = 0
                
                add_stat(game_stats, qb.name, "pass_yds", gained)
                add_stat(game_stats, target.name, "rec_yds", gained)
                add_stat(game_stats, target.name, "rec", 1)
                
                play_desc = f"{qb.name} pass to {target.name} for {gained} yds"
                if gained > 20: play_desc += " (BIG PLAY!)"
                
                curr += gained; to_go -= gained; drive_yards += gained
                
                if curr >= 100:
                    add_stat(game_stats, qb.name, "pass_td", 1)
                    add_stat(game_stats, target.name, "rec_td", 1)
            else:
                # Int Logic
                int_chance = qb.stats.get('int_chance', 0.02) + pressure_boost
                if random.random() < int_chance:
                    add_stat(game_stats, qb.name, "int", 1)
                    add_stat(game_stats, defense.name, "int", 1) # Defense gets credit
                    drive_result = "TURNOVER"
                    drive_plays.append(f"💀 INTERCEPTION! {qb.name} picked off by {defense.name}!")
                    break 
                play_desc = f"{qb.name} incomplete. Pressure by {defense.name}."
        else:
            runner = get_starter(offense.rbs, [70, 25, 5]) or qb
            
            # Run Defense Math
            mean_run = runner.stats.get('yards_mean', 4) - run_suppression
            if mean_run < 1: mean_run = 1
            
            gained = int(random.gauss(mean_run, 3))
            if random.random() < runner.stats.get('breakaway_chance',0): gained += 20
            
            add_stat(game_stats, runner.name, "rush_yds", gained)
            play_desc = f"Run by {runner.name} for {gained} yds"
            
            curr += gained; to_go -= gained; drive_yards += gained
            if curr >= 100: add_stat(game_stats, runner.name, "rush_td", 1)

        # C. END OF PLAY
        if curr >= 100:
            scores[offense.name] += 7
            drive_result = "TOUCHDOWN"
            drive_plays.append(f"🚨 TOUCHDOWN! {play_desc}") 
            break

        if to_go <= 0:
            play_desc += " [1ST DOWN]"
            down = 1; to_go = 10
        else:
            down += 1
        
        drive_plays.append(play_desc)

    return { "team": offense.abbr, "result": drive_result, "yards": drive_yards, "plays": drive_plays }

def simulate_game(t1, t2):
    scores = {t1.name: 0, t2.name: 0}
    drives = []; stats = {}
    
    for i in range(12): 
        # Alternating Possessions
        if i % 2 == 0:
            offense = t1; defense = t2
        else:
            offense = t2; defense = t1
            
        # Pass the DEFENSE argument
        drive_data = simulate_drive(offense, defense, scores, stats)
        drive_data["id"] = i + 1
        drives.append(drive_data)
        
    return scores, drives, stats

# ==============================================================================
# 4. LEAGUE & FANTASY LOGIC
# ==============================================================================
import json

STATE_FILE = 'state.json'
SCHEDULE_FILE = 'schedule.json'
PLAYOFF_FILE = 'playoffs.json'

# --- HELPER FUNCTIONS (Must be at the far left margin) ---
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"year": 2025, "week": 1, "phase": "regular_season"}
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

# --- LEAGUE CLASS ---
def load_league(filename):
    if not os.path.exists(filename): return {}
    df = pd.read_csv(filename)
    
    if 'Potential' not in df.columns: df['Potential'] = 'C'
    if 'Skill_Bonus' not in df.columns: df['Skill_Bonus'] = 0.0
    if 'Season_Pts' not in df.columns: df['Season_Pts'] = 0.0
    if 'Games_Played' not in df.columns: df['Games_Played'] = 0
    df.fillna({'Potential':'C', 'Skill_Bonus':0.0, 'Age':21, 'Season_Pts':0.0, 'Games_Played':0}, inplace=True)
    
    df = df.sort_values(by=['Team_Name', 'Skill_Bonus'], ascending=[True, False])

    teams = {}
    for t_name, t_data in df.groupby("Team_Name"):
        if t_name == "FA": continue
        team = Team(t_name, t_data.iloc[0]["Abbr"])
        
        for _, row in t_data.iterrows():
            try: bonus = float(row['Skill_Bonus'])
            except: bonus = 0.0
            p = Player(row["Player_Name"], row["Position"], row["Archetype"], row.get("Age", 21), row.get("Potential", "C"), bonus)
            
            if row["Position"] == "QB": team.qbs.append(p)
            elif row["Position"] == "RB": team.rbs.append(p)
            elif row["Position"] == "TE": team.tes.append(p)
            elif row["Position"] == "WR": team.wrs.append(p)
            elif row["Position"] == "DEF": team.defs.append(p)
        
        if not team.defs: team.defs.append(Player(f"{team.name} Defense", "DEF", "Balanced"))
        if not team.qbs: team.qbs.append(Player("Scrub QB", "QB", "Game Manager"))
        if not team.rbs: team.rbs.append(Player("Scrub RB", "RB", "Bell Cow RB"))
        if not team.wrs: team.wrs.append(Player("Scrub WR", "WR", "Slot Machine"))
        if not team.tes: team.tes.append(Player("Scrub TE", "TE", "Security TE"))
        
        teams[t_name] = team
    return teams

def calculate_fantasy_points(stats_dict):
    pts = 0
    pts += stats_dict.get('pass_yds', 0) * 0.04
    pts += stats_dict.get('pass_td', 0) * 4
    pts += stats_dict.get('int', 0) * -2
    pts += stats_dict.get('rush_yds', 0) * 0.1
    pts += stats_dict.get('rush_td', 0) * 6
    pts += stats_dict.get('rec_yds', 0) * 0.1
    pts += stats_dict.get('rec_td', 0) * 6
    pts += stats_dict.get('rec', 0) * 1
    if 'pass_def' in stats_dict: pts += stats_dict.get('int', 0) * 2 
    return round(pts, 2)

class League:
    def __init__(self, filename):
        self.filename = filename
        self.teams = load_league(filename)
        self.standings = {t: {'W':0, 'L':0, 'D':0, 'PF':0, 'PA':0} for t in self.teams}
        self.state = load_state() 
        
        # Load Schedule OR Bracket depending on phase
        if self.state['phase'] == 'regular_season':
            self.schedule = self.load_schedule()
        else:
            self.bracket = self.load_bracket()

    def load_schedule(self):
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as f: return json.load(f)
        return self.generate_schedule()

    def load_bracket(self):
        if os.path.exists(PLAYOFF_FILE):
            with open(PLAYOFF_FILE, 'r') as f: return json.load(f)
        return [] # Return empty if not created yet

    def generate_schedule(self):
        names = list(self.teams.keys())
        random.shuffle(names)
        matchups = []
        while len(names) >= 2:
            matchups.append({"home": names.pop(), "away": names.pop()})
        with open(SCHEDULE_FILE, 'w') as f: json.dump(matchups, f)
        return matchups

    def start_playoffs(self):
        # 1. Sort teams by Wins, then Point Diff
        sorted_teams = sorted(
            self.standings.items(), 
            key=lambda item: (-item[1]['W'], -(item[1]['PF'] - item[1]['PA']))
        )
        
        num_teams = len(self.teams)
        bracket = []
        start_round = ""

        # --- SCENARIO A: 4-TEAM LEAGUE (Start at Semifinals) ---
        if num_teams < 8:
            seeds = [t[0] for t in sorted_teams[:4]]
            start_round = "Semifinals"
            bracket = [
                {"round": "Semifinals", "home": seeds[0], "away": seeds[3], "winner": None},
                {"round": "Semifinals", "home": seeds[1], "away": seeds[2], "winner": None}
            ]
            
        # --- SCENARIO B: 32-TEAM LEAGUE (Start at Quarterfinals) ---
        else:
            seeds = [t[0] for t in sorted_teams[:8]]
            start_round = "Quarterfinals"
            bracket = [
                {"round": "Quarterfinals", "home": seeds[0], "away": seeds[7], "winner": None},
                {"round": "Quarterfinals", "home": seeds[1], "away": seeds[6], "winner": None},
                {"round": "Quarterfinals", "home": seeds[2], "away": seeds[5], "winner": None},
                {"round": "Quarterfinals", "home": seeds[3], "away": seeds[4], "winner": None}
            ]
        
        # Save Bracket
        with open(PLAYOFF_FILE, 'w') as f: json.dump(bracket, f)
        
        # Update State
        self.state['phase'] = 'playoffs'
        self.state['round'] = start_round
        save_state(self.state)
        
        self.bracket = bracket
        return bracket

    def play_playoff_round(self):
        summary = []; next_round = []
        
        # 1. Sim current round
        for game in self.bracket:
            t1 = self.teams[game['home']]
            t2 = self.teams[game['away']]
            
            # Sim Game
            scores, drives, stats = simulate_game(t1, t2)
            
            s1, s2 = scores[t1.name], scores[t2.name]
            winner = t1.name if s1 > s2 else t2.name
            
            # --- NEW: PROCESS BOX SCORES (Copied from play_week) ---
            t1_box = []; t2_box = []
            
            # Create a lookup set for Team 1's players
            t1_roster = {p.name for p in t1.qbs + t1.rbs + t1.wrs + t1.tes + t1.defs}
            
            for p_name, p_stats in stats.items():
                p_stats['name'] = p_name
                if p_name in t1_roster:
                    t1_box.append(p_stats)
                else:
                    t2_box.append(p_stats)
            
            # Sort stats for display
            def sort_key(s): return (-s.get('pass_yds',0), -s.get('rush_yds',0), -s.get('rec_yds',0))
            t1_box.sort(key=sort_key); t2_box.sort(key=sort_key)
            # -------------------------------------------------------

            # Build Summary with Box Data
            summary.append({
                "matchup": f"{t1.abbr} {s1} - {s2} {t2.abbr}",
                "home": t1.abbr, "away": t2.abbr,
                "drives": drives,
                "box_home": t1_box, # <--- Added
                "box_away": t2_box, # <--- Added
                "winner": winner
            })
            next_round.append(winner)

        # 2. Determine Next Round (Logic remains the same)
        new_bracket = []
        round_name = ""
        current_round = self.state.get('round', '')

        if current_round == "Quarterfinals":
            round_name = "Semifinals"
            # Winner 1 vs Winner 4, Winner 2 vs Winner 3
            if len(next_round) >= 4:
                new_bracket.append({"round": round_name, "home": next_round[0], "away": next_round[3], "winner": None})
                new_bracket.append({"round": round_name, "home": next_round[1], "away": next_round[2], "winner": None})
            
        elif current_round == "Semifinals":
            round_name = "Super Bowl"
            if len(next_round) >= 2:
                new_bracket.append({"round": round_name, "home": next_round[0], "away": next_round[1], "winner": None})
            
        elif current_round == "Super Bowl":
            round_name = "Champion"
            self.state['phase'] = 'offseason'
            
            if 'log_transaction' in globals():
                log_transaction(f"🏆 SUPER BOWL CHAMPION: {next_round[0]}!")

        # 3. Save State & Bracket
        self.state['round'] = round_name
        save_state(self.state)
        
        if round_name != "Champion":
            with open(PLAYOFF_FILE, 'w') as f: json.dump(new_bracket, f)
            self.bracket = new_bracket
        else:
            if os.path.exists(PLAYOFF_FILE): os.remove(PLAYOFF_FILE)

        return summary

    def play_week(self):
        # 1. CHECK PHASE
        if self.state['phase'] == 'offseason':
            return [], {}

        # 2. PLAY THE GAMES
        current_week = self.state['week']
        matchups = self.schedule
        summary = []; master_stats = {}

        # ---Prepare list for Game Log ---
        weekly_results_log = []
        
        for m in matchups:
            t1 = self.teams[m['home']]
            t2 = self.teams[m['away']]
            
            # Sim Game
            scores, drives, game_stats = simulate_game(t1, t2)
            master_stats.update(game_stats)
            
            # Organize Box Score
            t1_box = []; t2_box = []
            t1_roster = {p.name for p in t1.qbs + t1.rbs + t1.wrs + t1.tes + t1.defs}
            for p_name, stats in game_stats.items():
                stats['name'] = p_name
                if p_name in t1_roster: t1_box.append(stats)
                else: t2_box.append(stats)
            
            def sort_key(s): return (-s.get('pass_yds',0), -s.get('rush_yds',0), -s.get('rec_yds',0))
            t1_box.sort(key=sort_key); t2_box.sort(key=sort_key)

            # Standings
            s1, s2 = scores[t1.name], scores[t2.name]
            self.standings[t1.name]['PF'] += s1; self.standings[t1.name]['PA'] += s2
            self.standings[t2.name]['PF'] += s2; self.standings[t2.name]['PA'] += s1
            
            if s1 > s2:
                self.standings[t1.name]['W'] += 1
                self.standings[t2.name]['L'] += 1
            elif s2 > s1:
                self.standings[t2.name]['W'] += 1
                self.standings[t1.name]['L'] += 1
            else:
                # IT IS A DRAW
                self.standings[t1.name]['D'] += 1
                self.standings[t2.name]['D'] += 1
            
            summary.append({
                "matchup": f"{t1.abbr} {s1} - {s2} {t2.abbr}",
                "home": t1.abbr, "away": t2.abbr,
                "home_score": s1, "away_score": s2,
                "drives": drives, "box_home": t1_box, "box_away": t2_box
            })

            # --- : Append to History Log ---
            weekly_results_log.append({
                "week": current_week,
                "home": t1.name, "home_abbr": t1.abbr, "home_score": s1,
                "away": t2.name, "away_abbr": t2.abbr, "away_score": s2
            })

        # 3. SAVE STATS TO CSV (DETAILED VERSION)
        df = pd.read_csv(self.filename)
        stat_cols = ['Season_Pts', 'Games_Played', 'Pass_Yds', 'Pass_TD', 'Int', 'Rush_Yds', 'Rush_TD', 'Rec_Yds', 'Rec_TD', 'Rec', 'Targets']
        for col in stat_cols:
            if col not in df.columns: df[col] = 0

        for player, stats in master_stats.items():
            pts = calculate_fantasy_points(stats)
            mask = df['Player_Name'] == player
            
            if mask.any():
                df.loc[mask, 'Season_Pts'] += pts
                df.loc[mask, 'Games_Played'] += 1
                df.loc[mask, 'Pass_Yds'] += stats.get('pass_yds', 0)
                df.loc[mask, 'Pass_TD']  += stats.get('pass_td', 0)
                df.loc[mask, 'Int']      += stats.get('int', 0)
                df.loc[mask, 'Rush_Yds'] += stats.get('rush_yds', 0)
                df.loc[mask, 'Rush_TD']  += stats.get('rush_td', 0)
                df.loc[mask, 'Rec_Yds']  += stats.get('rec_yds', 0)
                df.loc[mask, 'Rec_TD']   += stats.get('rec_td', 0)
                df.loc[mask, 'Rec']      += stats.get('rec', 0)
                df.loc[mask, 'Targets']  += stats.get('targets', 0)

        df.to_csv(self.filename, index=False)

        # --- SAVE GAME LOG TO JSON ---
        if os.path.exists(GAME_LOG_FILE):
            with open(GAME_LOG_FILE, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        history.extend(weekly_results_log)
        
        with open(GAME_LOG_FILE, 'w') as f:
            json.dump(history, f)
        
       # 4. ADVANCE WEEK
        self.state['week'] += 1
        
        # Check for End of Season
        if self.state['week'] > 18:
            # TRIGGER PLAYOFFS
            self.start_playoffs() # <--- NEW FUNCTION CALL
            
        save_state(self.state)
        
        # Generate next week's schedule
        self.schedule = self.generate_schedule()
        
        return summary, master_stats

# ==============================================================================
# 5. TRANSACTIONS
# ==============================================================================
# ... (Keep trade_fantasy_players, draft_player_to_fantasy, drop_fantasy_player same as before) ...
def trade_fantasy_players(owner1, p1_name, owner2, p2_name, fantasy_file='fantasy_teams.csv'):
    if not os.path.exists(fantasy_file): return False
    df = pd.read_csv(fantasy_file)
    mask1 = (df['Owner'] == owner1) & (df['Player_Name'] == p1_name)
    mask2 = (df['Owner'] == owner2) & (df['Player_Name'] == p2_name)
    if not any(mask1) or not any(mask2): return False
    df.loc[mask1, 'Owner'] = owner2
    df.loc[mask2, 'Owner'] = owner1
    df.to_csv(fantasy_file, index=False)
    return True

def draft_player_to_fantasy(fantasy_team, owner, player_name, roster_file, fantasy_file):
    sim_df = pd.read_csv(roster_file)
    p_row = sim_df[sim_df['Player_Name'] == player_name]
    if p_row.empty: return False, "Player not found in NFL"
    
    sim_team = p_row.iloc[0]['Team_Name']
    pos = p_row.iloc[0]['Position']
    
    if os.path.exists(fantasy_file): f_df = pd.read_csv(fantasy_file)
    else: f_df = pd.DataFrame(columns=["Fantasy_Team", "Owner", "Player_Name", "Sim_Team", "Position"])
    
    if player_name in f_df['Player_Name'].values: return False, "Taken"
    
    new_entry = {"Fantasy_Team": fantasy_team, "Owner": owner, "Player_Name": player_name, "Sim_Team": sim_team, "Position": pos}
    pd.concat([f_df, pd.DataFrame([new_entry])], ignore_index=True).to_csv(fantasy_file, index=False)
    return True, f"Drafted {player_name}"

def drop_fantasy_player(owner, player_name, fantasy_file):
    if not os.path.exists(fantasy_file): return False
    df = pd.read_csv(fantasy_file)
    df = df[~((df['Owner'] == owner) & (df['Player_Name'] == player_name))]
    df.to_csv(fantasy_file, index=False)
    return True
    
# ==============================================================================
# 6. OFFSEASON (AI GM + Transaction Logging)
# ==============================================================================
import csv
from datetime import datetime

TRANSACTION_FILE = 'transactions.csv'

def log_transaction(message):
    """Writes a message to the transaction log with a timestamp"""
    # Create file with header if it doesn't exist
    if not os.path.exists(TRANSACTION_FILE):
        with open(TRANSACTION_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Message"])
            
    with open(TRANSACTION_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        # We use a simple counter or 'Offseason' as the date for now
        writer.writerow(["Offseason", message])

def run_offseason(filename):
    # 1. LOAD STATE TO UPDATE YEAR
    state = load_state()
    
    df = pd.read_csv(filename)
    
    # Clear old logs
    if os.path.exists(TRANSACTION_FILE):
        os.remove(TRANSACTION_FILE)
    
    log_transaction(f"--- 🏆 {state['year']} SEASON COMPLETE 🏆 ---")
    
    # 2. RESET STATS FOR NEW SEASON
    # We keep career history in our hearts, but the columns must be wiped for the new year
    cols_to_reset = ['Season_Pts', 'Games_Played', 'Pass_Yds', 'Pass_TD', 'Int', 'Rush_Yds', 'Rush_TD', 'Rec_Yds', 'Rec_TD', 'Rec', 'Targets']
    for col in cols_to_reset:
        if col in df.columns:
            df[col] = 0

    # 3. AGE & DEVELOP
    df['Age'] += 1
    if 'Skill_Bonus' not in df.columns: df['Skill_Bonus'] = 0.0
    
    updates = []
    for _, row in df.iterrows():
        try: bonus = float(row.get('Skill_Bonus', 0.0))
        except: bonus = 0.0
        
        # --- NEW DEFENSE LOGIC ---
        if row['Position'] == 'DEF':
            # Defenses don't age, they "retool"
            # Random fluctuation between -5% and +5%
            change = random.uniform(-0.05, 0.05)
            bonus += change
            # Optional: Log big changes
            if change > 0.04:
                log_transaction(f"NEWS: {row['Team_Name']} Defense has signed key free agents (Defense Upgraded).")
            elif change < -0.04:
                log_transaction(f"NEWS: {row['Team_Name']} Defense lost starters in free agency (Defense Downgraded).")
        # -------------------------
        
        # Standard Player Aging
        elif row['Age'] >= 29: 
            bonus -= random.uniform(0.02, 0.05)
        else:
            pot = row.get('Potential', 'C')
            chance = {'A':0.60, 'B':0.40, 'C':0.20, 'D':0.05}.get(pot, 0.20)
            if random.random() < chance:
                if pot == 'A' and random.random() < 0.15: bonus += 0.15
                else: bonus += random.uniform(0.01, 0.04)
        
        updates.append(bonus)
    df['Skill_Bonus'] = updates

    # 4. RETIREMENT
    active = []; retire_count = 0
    for _, row in df.iterrows():
        chance = 0
        if row['Age'] > 32: chance = 0.1
        if row['Age'] > 35: chance = 0.4
        if row['Team_Name'] == 'FA': chance = 0 # FAs don't retire, they just vanish or stay
        
        if random.random() < chance: 
            retire_count += 1
            log_transaction(f"RETIRED: {row['Player_Name']} ({row['Position']})")
        else: 
            active.append(row)
            
    # 5. GENERATE ROOKIES
    log_transaction(f"--- 🎓 ROOKIE DRAFT CLASS ENTERING ---")
    rookies = []
    positions = ["QB", "RB", "WR", "TE"]
    first_names = ["Caleb", "Drake", "Jayden", "Bo", "Rome", "Brock", "Ty", "Zay", "Ashton", "Quinn", "Spencer", "Jordan", "Jja", "Kool", "Tank", "Bucky"]
    last_names = ["Williams", "Maye", "Daniels", "Nix", "Odunze", "Bowers", "Harrison", "Worthy", "Ewers", "Jeanty", "Rattler", "Travis", "McCarthy", "Corum", "Brooks"]
    
    for _ in range(retire_count + 15):
        pos = random.choice(positions)
        arch = random.choice(VALID_ARCHETYPES[pos])
        
        while True:
            fname = random.choice(first_names); lname = random.choice(last_names)
            if pos == "DEF": name = f"Rookie Defense {random.randint(100,999)}"
            else: name = f"{fname} {lname}"
            
            if name not in df['Player_Name'].values and not any(r['Player_Name'] == name for r in rookies):
                break

        pot = random.choices(["A", "B", "C", "D"], weights=[10, 25, 40, 25])[0]
        rookies.append({"Team_Name":"FA", "Abbr":"FA", "Player_Name":name, "Position":pos, "Archetype":arch, "Age":21, "Potential":pot, "Skill_Bonus":0.0, "Season_Pts":0, "Games_Played":0, "Pass_Yds":0, "Rush_Yds":0, "Rec_Yds":0})
    
    df_master = pd.concat([pd.DataFrame(active), pd.DataFrame(rookies)], ignore_index=True)

    # 6. AI GM (Auto-Sign FAs)
    log_transaction(f"--- ✍️ FREE AGENCY FRENZY ---")
    TARGETS = {"QB": 2, "RB": 3, "WR": 5, "TE": 2, "DEF": 1}
    real_teams = [t for t in df_master['Team_Name'].unique() if t != "FA"]

    for team in real_teams:
        team_roster = df_master[df_master['Team_Name'] == team]
        if not team_roster.empty: team_abbr = team_roster.iloc[0]['Abbr']
        else: team_abbr = team[:3].upper()

        for pos, count in TARGETS.items():
            curr = len(team_roster[team_roster['Position'] == pos])
            needed = count - curr
            if needed > 0:
                fa_pool = df_master[(df_master['Team_Name'] == "FA") & (df_master['Position'] == pos)]
                if not fa_pool.empty:
                    fa_pool = fa_pool.sort_values(by="Skill_Bonus", ascending=False)
                    signings = fa_pool.head(needed)
                    for _, player in signings.iterrows():
                        mask = (df_master['Player_Name'] == player['Player_Name'])
                        df_master.loc[mask, 'Team_Name'] = team
                        df_master.loc[mask, 'Abbr'] = team_abbr
                        log_transaction(f"SIGNED: {team} signs {player['Position']} {player['Player_Name']}")

    df_master.to_csv(filename, index=False)

    # 7. UPDATE CALENDAR (THE MISSING PIECE)
    state['year'] += 1
    state['week'] = 1
    state['phase'] = 'regular_season'
    save_state(state)
    
    # 8. GENERATE NEW SCHEDULE
    # We need to temporarily instantiate the league to run the generator logic
    # Or just wipe the schedule file and let the app reload it
    if os.path.exists(SCHEDULE_FILE):
        os.remove(SCHEDULE_FILE) # This forces a fresh generation on next load