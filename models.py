import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ==============================================================================
# AUTH
# ==============================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_commissioner = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fantasy_team = db.relationship('FantasyTeam', back_populates='owner', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class InviteCode(db.Model):
    __tablename__ = 'invite_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False)
    used_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    used_by = db.relationship('User', foreign_keys=[used_by_user_id])


# ==============================================================================
# LEAGUE STATE
# ==============================================================================

class LeagueState(db.Model):
    __tablename__ = 'league_state'
    id = db.Column(db.Integer, primary_key=True)
    season_year = db.Column(db.Integer, default=2025)
    week = db.Column(db.Integer, default=1)
    # setup → draft → regular_season → playoffs → offseason
    phase = db.Column(db.String(20), default='setup')


# ==============================================================================
# NFL (SIMULATION LAYER)
# ==============================================================================

class NflTeam(db.Model):
    __tablename__ = 'nfl_teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    abbr = db.Column(db.String(5), nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    points_for = db.Column(db.Integer, default=0)
    points_against = db.Column(db.Integer, default=0)

    players = db.relationship('Player', back_populates='nfl_team')


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    # null nfl_team_id = free agent
    nfl_team_id = db.Column(db.Integer, db.ForeignKey('nfl_teams.id'), nullable=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    position = db.Column(db.String(5), nullable=False)   # QB/RB/WR/TE/DEF
    archetype = db.Column(db.String(30), nullable=False)
    age = db.Column(db.Integer, default=21)
    potential = db.Column(db.String(1), default='C')     # A/B/C/D
    skill_bonus = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(10), default='active')  # active/retired

    # Season cumulative stats (reset each offseason)
    season_pts = db.Column(db.Float, default=0.0)
    games_played = db.Column(db.Integer, default=0)
    pass_yds = db.Column(db.Integer, default=0)
    pass_td = db.Column(db.Integer, default=0)
    ints = db.Column(db.Integer, default=0)
    rush_yds = db.Column(db.Integer, default=0)
    rush_td = db.Column(db.Integer, default=0)
    rec_yds = db.Column(db.Integer, default=0)
    rec_td = db.Column(db.Integer, default=0)
    rec = db.Column(db.Integer, default=0)
    targets = db.Column(db.Integer, default=0)

    nfl_team = db.relationship('NflTeam', back_populates='players')
    game_stats = db.relationship('PlayerGameStat', back_populates='player')
    fantasy_roster = db.relationship('FantasyRoster', back_populates='player', uselist=False)
    lineups = db.relationship('FantasyLineup', back_populates='player')


class NflSchedule(db.Model):
    __tablename__ = 'nfl_schedule'
    id = db.Column(db.Integer, primary_key=True)
    season_year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('nfl_teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('nfl_teams.id'), nullable=False)
    simulated = db.Column(db.Boolean, default=False)

    home_team = db.relationship('NflTeam', foreign_keys=[home_team_id])
    away_team = db.relationship('NflTeam', foreign_keys=[away_team_id])
    game = db.relationship('NflGame', back_populates='schedule', uselist=False)


class NflGame(db.Model):
    __tablename__ = 'nfl_games'
    id = db.Column(db.Integer, primary_key=True)
    nfl_schedule_id = db.Column(db.Integer, db.ForeignKey('nfl_schedule.id'), nullable=False)
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    game_log = db.Column(db.Text)  # JSON: list of drive dicts

    schedule = db.relationship('NflSchedule', back_populates='game')
    player_stats = db.relationship('PlayerGameStat', back_populates='game')


class PlayerGameStat(db.Model):
    __tablename__ = 'player_game_stats'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('nfl_games.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    season_year = db.Column(db.Integer, nullable=False)
    pass_yds = db.Column(db.Integer, default=0)
    pass_td = db.Column(db.Integer, default=0)
    ints = db.Column(db.Integer, default=0)
    rush_yds = db.Column(db.Integer, default=0)
    rush_td = db.Column(db.Integer, default=0)
    rec_yds = db.Column(db.Integer, default=0)
    rec_td = db.Column(db.Integer, default=0)
    rec = db.Column(db.Integer, default=0)
    targets = db.Column(db.Integer, default=0)
    sacks = db.Column(db.Integer, default=0)
    fantasy_pts = db.Column(db.Float, default=0.0)

    player = db.relationship('Player', back_populates='game_stats')
    game = db.relationship('NflGame', back_populates='player_stats')


# ==============================================================================
# FANTASY LEAGUE
# ==============================================================================

class FantasyTeam(db.Model):
    __tablename__ = 'fantasy_teams'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    points_for = db.Column(db.Float, default=0.0)
    points_against = db.Column(db.Float, default=0.0)
    draft_position = db.Column(db.Integer, nullable=True)  # 1-10, set when draft opens

    owner = db.relationship('User', back_populates='fantasy_team')
    roster = db.relationship('FantasyRoster', back_populates='fantasy_team')
    lineups = db.relationship('FantasyLineup', back_populates='fantasy_team')


class FantasyRoster(db.Model):
    """Tracks which fantasy team owns each player."""
    __tablename__ = 'fantasy_rosters'
    id = db.Column(db.Integer, primary_key=True)
    fantasy_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), unique=True, nullable=False)
    acquired_week = db.Column(db.Integer, nullable=True)
    acquired_via = db.Column(db.String(10), default='draft')  # draft/waiver/trade

    fantasy_team = db.relationship('FantasyTeam', back_populates='roster')
    player = db.relationship('Player', back_populates='fantasy_roster')


LINEUP_SLOTS = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'SUPERFLEX',
                'BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'BN7', 'BN8', 'BN9']
ROSTER_LIMIT = len(LINEUP_SLOTS)  # 17

STARTER_SLOTS = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'SUPERFLEX']

# Which positions are eligible for each slot
SLOT_ELIGIBILITY = {
    'QB':        ['QB'],
    'RB1':       ['RB'],
    'RB2':       ['RB'],
    'WR1':       ['WR'],
    'WR2':       ['WR'],
    'TE':        ['TE'],
    'FLEX':      ['RB', 'WR', 'TE'],
    'SUPERFLEX': ['QB', 'RB', 'WR', 'TE'],
}


class FantasyLineup(db.Model):
    """A player's slot assignment for a given week."""
    __tablename__ = 'fantasy_lineups'
    id = db.Column(db.Integer, primary_key=True)
    fantasy_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    season_year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    slot = db.Column(db.String(10), nullable=False)  # QB/RB1/RB2/WR1/WR2/TE/FLEX/SUPERFLEX/BN1-BN9

    fantasy_team = db.relationship('FantasyTeam', back_populates='lineups')
    player = db.relationship('Player', back_populates='lineups')

    __table_args__ = (
        db.UniqueConstraint('fantasy_team_id', 'season_year', 'week', 'slot', name='uq_lineup_slot'),
        db.UniqueConstraint('fantasy_team_id', 'season_year', 'week', 'player_id', name='uq_lineup_player'),
    )


class FantasySchedule(db.Model):
    __tablename__ = 'fantasy_schedule'
    id = db.Column(db.Integer, primary_key=True)
    season_year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)

    home_team = db.relationship('FantasyTeam', foreign_keys=[home_team_id])
    away_team = db.relationship('FantasyTeam', foreign_keys=[away_team_id])
    result = db.relationship('FantasyResult', back_populates='matchup', uselist=False)


class FantasyResult(db.Model):
    __tablename__ = 'fantasy_results'
    id = db.Column(db.Integer, primary_key=True)
    fantasy_schedule_id = db.Column(db.Integer, db.ForeignKey('fantasy_schedule.id'), nullable=False)
    home_score = db.Column(db.Float, default=0.0)
    away_score = db.Column(db.Float, default=0.0)
    winner_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=True)

    matchup = db.relationship('FantasySchedule', back_populates='result')
    winner = db.relationship('FantasyTeam', foreign_keys=[winner_id])


# ==============================================================================
# DRAFT
# ==============================================================================

class Draft(db.Model):
    __tablename__ = 'draft'
    id = db.Column(db.Integer, primary_key=True)
    season_year = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default='pending')  # pending/active/complete
    current_pick = db.Column(db.Integer, default=1)
    _snake_order = db.Column('snake_order', db.Text)      # JSON array of fantasy_team ids
    timer_expires_at = db.Column(db.DateTime, nullable=True)
    auto_pick_seconds = db.Column(db.Integer, default=90)
    draft_type = db.Column(db.String(10), default='initial')  # initial / rookie
    rounds = db.Column(db.Integer, default=17)

    picks = db.relationship('DraftPick', back_populates='draft', order_by='DraftPick.pick_number')

    @property
    def snake_order(self):
        return json.loads(self._snake_order) if self._snake_order else []

    @snake_order.setter
    def snake_order(self, order):
        self._snake_order = json.dumps(order)

    def current_team_id(self):
        order = self.snake_order
        if not order:
            return None
        n = len(order)
        idx = self.current_pick - 1          # 0-based pick index
        round_num = idx // n
        pos_in_round = idx % n
        if round_num % 2 == 1:               # odd rounds reverse (snake)
            pos_in_round = n - 1 - pos_in_round
        return order[pos_in_round]

    def total_picks(self):
        return len(self.snake_order) * self.rounds


class DraftPick(db.Model):
    __tablename__ = 'draft_picks'
    id = db.Column(db.Integer, primary_key=True)
    draft_id = db.Column(db.Integer, db.ForeignKey('draft.id'), nullable=False)
    pick_number = db.Column(db.Integer, nullable=False)
    round_num = db.Column(db.Integer, nullable=False)
    fantasy_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    picked_at = db.Column(db.DateTime, default=datetime.utcnow)
    auto_picked = db.Column(db.Boolean, default=False)

    draft = db.relationship('Draft', back_populates='picks')
    fantasy_team = db.relationship('FantasyTeam')
    player = db.relationship('Player')


# ==============================================================================
# ROSTER MOVES
# ==============================================================================

class WaiverClaim(db.Model):
    __tablename__ = 'waiver_claims'
    id = db.Column(db.Integer, primary_key=True)
    fantasy_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    drop_player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    week = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default='pending')  # pending/done/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fantasy_team = db.relationship('FantasyTeam')
    player = db.relationship('Player', foreign_keys=[player_id])
    drop_player = db.relationship('Player', foreign_keys=[drop_player_id])


class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    proposing_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    receiving_team_id = db.Column(db.Integer, db.ForeignKey('fantasy_teams.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default='pending')  # pending/accepted/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    proposing_team = db.relationship('FantasyTeam', foreign_keys=[proposing_team_id])
    receiving_team = db.relationship('FantasyTeam', foreign_keys=[receiving_team_id])
    players = db.relationship('TradePlayer', back_populates='trade')


class TradePlayer(db.Model):
    __tablename__ = 'trade_players'
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    direction = db.Column(db.String(15), nullable=False)  # to_proposer / to_receiver

    trade = db.relationship('Trade', back_populates='players')
    player = db.relationship('Player')
