import os
import random
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import (db, User, InviteCode, LeagueState, FantasyTeam, FantasyRoster,
                    Player, NflTeam, FantasySchedule, FantasyResult, FantasyLineup,
                    Draft, DraftPick, LINEUP_SLOTS, STARTER_SLOTS, SLOT_ELIGIBILITY)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "blitz.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access Blitz Dynasty.'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


# ==============================================================================
# AUTH
# ==============================================================================

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.count() > 0:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        team_name = request.form['team_name'].strip()

        if not username or not password or not team_name:
            flash('All fields are required.')
            return render_template('setup.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.')
            return render_template('setup.html')

        user = User(username=username, is_commissioner=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(FantasyTeam(user_id=user.id, name=team_name))
        db.session.add(LeagueState(season_year=2025, week=1, phase='setup'))
        for _ in range(9):
            db.session.add(InviteCode(code=secrets.token_hex(4).upper()))
        db.session.commit()
        login_user(user)
        return redirect(url_for('commissioner'))

    return render_template('setup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/join', methods=['GET', 'POST'])
@app.route('/join/<code>', methods=['GET', 'POST'])
def join(code=None):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        username = request.form['username'].strip()
        password = request.form['password']
        team_name = request.form['team_name'].strip()

        invite = InviteCode.query.filter_by(code=code, used_by_user_id=None).first()
        if not invite:
            flash('Invalid or already-used invite code.')
            return render_template('join.html', code=code)
        if User.query.filter_by(username=username).first():
            flash('Username already taken.')
            return render_template('join.html', code=code)
        if not username or not password or not team_name:
            flash('All fields are required.')
            return render_template('join.html', code=code)
        if len(password) < 6:
            flash('Password must be at least 6 characters.')
            return render_template('join.html', code=code)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        invite.used_by_user_id = user.id
        db.session.add(FantasyTeam(user_id=user.id, name=team_name))
        db.session.commit()
        login_user(user, remember=True)
        flash(f'Welcome to Blitz Dynasty, {username}!')
        return redirect(url_for('index'))

    return render_template('join.html', code=code or '')


# ==============================================================================
# DRAFT HELPERS
# ==============================================================================

def get_drafted_ids(draft):
    return {p.player_id for p in draft.picks}


def best_available(draft, fantasy_team_id):
    """Pick the highest skill_bonus player at a position the team still needs."""
    drafted = get_drafted_ids(draft)
    my_picks = [p for p in draft.picks if p.fantasy_team_id == fantasy_team_id]
    pos_counts = {}
    for p in my_picks:
        pos = p.player.position
        pos_counts[pos] = pos_counts.get(pos, 0) + 1

    # Target counts for a 17-round draft
    targets = {'QB': 3, 'RB': 5, 'WR': 6, 'TE': 3}
    needed = [pos for pos, target in targets.items() if pos_counts.get(pos, 0) < target]

    available = Player.query.filter(
        Player.position != 'DEF',
        Player.status == 'active',
        ~Player.id.in_(drafted) if drafted else True,
    ).order_by(Player.skill_bonus.desc())

    if needed:
        pick = available.filter(Player.position.in_(needed)).first()
        if pick:
            return pick

    return available.first()


def do_pick(draft, player, auto=False):
    """Record a pick, update roster, advance draft state."""
    fantasy_team_id = draft.current_team_id()
    n = len(draft.snake_order)
    round_num = ((draft.current_pick - 1) // n) + 1

    pick = DraftPick(
        draft_id=draft.id,
        pick_number=draft.current_pick,
        round_num=round_num,
        fantasy_team_id=fantasy_team_id,
        player_id=player.id,
        picked_at=datetime.utcnow(),
        auto_picked=auto,
    )
    db.session.add(pick)

    # Add to fantasy roster immediately
    db.session.add(FantasyRoster(
        fantasy_team_id=fantasy_team_id,
        player_id=player.id,
        acquired_week=0,
        acquired_via='draft',
    ))

    total = draft.total_picks()
    if draft.current_pick >= total:
        draft.status = 'complete'
        draft.timer_expires_at = None
        _finalise_draft(draft)
    else:
        draft.current_pick += 1
        draft.timer_expires_at = datetime.utcnow() + timedelta(seconds=draft.auto_pick_seconds)

    db.session.commit()


def _finalise_draft(draft):
    """Set league to regular_season when draft completes."""
    state = LeagueState.query.first()
    state.phase = 'regular_season'


def check_auto_pick(draft):
    """If the timer has expired, auto-pick for the team on the clock."""
    if (draft.status == 'active'
            and draft.timer_expires_at
            and datetime.utcnow() > draft.timer_expires_at):
        team_id = draft.current_team_id()
        player = best_available(draft, team_id)
        if player:
            do_pick(draft, player, auto=True)
            return True
    return False


def draft_state_json(draft, my_team_id):
    """Serialise full draft state for the polling API."""
    check_auto_pick(draft)
    db.session.refresh(draft)

    now = datetime.utcnow()
    seconds_left = 0
    if draft.timer_expires_at and draft.status == 'active':
        seconds_left = max(0, int((draft.timer_expires_at - now).total_seconds()))

    on_clock_id = draft.current_team_id() if draft.status == 'active' else None
    on_clock_team = db.session.get(FantasyTeam, on_clock_id) if on_clock_id else None

    # Last 20 picks for the feed
    recent = draft.picks[-20:] if draft.picks else []
    picks_data = [{
        'pick_number': p.pick_number,
        'round': p.round_num,
        'team_name': p.fantasy_team.name,
        'player_name': p.player.name,
        'position': p.player.position,
        'archetype': p.player.archetype,
        'auto': p.auto_picked,
    } for p in reversed(recent)]

    # My roster so far
    my_picks = [p for p in draft.picks if p.fantasy_team_id == my_team_id]
    roster_data = [{
        'player_name': p.player.name,
        'position': p.player.position,
        'archetype': p.player.archetype,
        'round': p.round_num,
    } for p in sorted(my_picks, key=lambda x: x.pick_number)]

    n = len(draft.snake_order)
    round_num = ((draft.current_pick - 1) // n) + 1 if draft.status == 'active' else 17
    pick_in_round = ((draft.current_pick - 1) % n) + 1 if draft.status == 'active' else n

    return {
        'status': draft.status,
        'current_pick': draft.current_pick,
        'total_picks': draft.total_picks(),
        'round': round_num,
        'pick_in_round': pick_in_round,
        'on_clock_team_id': on_clock_id,
        'on_clock_team_name': on_clock_team.name if on_clock_team else None,
        'is_my_turn': on_clock_id == my_team_id,
        'seconds_left': seconds_left,
        'auto_pick_seconds': draft.auto_pick_seconds,
        'picks': picks_data,
        'my_roster': roster_data,
    }


# ==============================================================================
# DRAFT ROUTES
# ==============================================================================

@app.route('/draft')
@login_required
def draft_room():
    state = LeagueState.query.first()
    if state.phase not in ('draft', 'regular_season', 'playoffs', 'offseason'):
        flash('The draft has not opened yet.')
        return redirect(url_for('index'))

    draft = Draft.query.order_by(Draft.id.desc()).first()
    if not draft:
        flash('No draft found.')
        return redirect(url_for('index'))

    return render_template('draft.html', draft=draft, state=state)


@app.route('/api/draft/state')
@login_required
def api_draft_state():
    draft = Draft.query.order_by(Draft.id.desc()).first()
    if not draft:
        return jsonify({'error': 'no draft'}), 404

    my_team = current_user.fantasy_team
    return jsonify(draft_state_json(draft, my_team.id if my_team else None))


@app.route('/api/draft/available')
@login_required
def api_draft_available():
    draft = Draft.query.order_by(Draft.id.desc()).first()
    if not draft:
        return jsonify([])

    pos_filter = request.args.get('pos', '').upper()
    search = request.args.get('q', '').strip().lower()

    drafted = get_drafted_ids(draft)
    query = Player.query.filter(
        Player.position != 'DEF',
        Player.status == 'active',
    )
    if drafted:
        query = query.filter(~Player.id.in_(drafted))
    if pos_filter and pos_filter in ('QB', 'RB', 'WR', 'TE'):
        query = query.filter(Player.position == pos_filter)
    if search:
        query = query.filter(Player.name.ilike(f'%{search}%'))

    players = query.order_by(Player.skill_bonus.desc()).limit(100).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'position': p.position,
        'archetype': p.archetype,
        'age': p.age,
        'potential': p.potential,
        'skill_bonus': round(p.skill_bonus, 3),
        'nfl_team': p.nfl_team.name if p.nfl_team else 'FA',
    } for p in players])


@app.route('/api/draft/pick', methods=['POST'])
@login_required
def api_draft_pick():
    draft = Draft.query.order_by(Draft.id.desc()).first()
    if not draft or draft.status != 'active':
        return jsonify({'error': 'Draft is not active'}), 400

    my_team = current_user.fantasy_team
    if not my_team:
        return jsonify({'error': 'You have no team'}), 400
    if draft.current_team_id() != my_team.id:
        return jsonify({'error': 'Not your turn'}), 403

    player_id = request.json.get('player_id')
    player = db.session.get(Player, player_id)
    if not player or player.position == 'DEF':
        return jsonify({'error': 'Invalid player'}), 400
    if player_id in get_drafted_ids(draft):
        return jsonify({'error': 'Player already drafted'}), 400

    do_pick(draft, player)
    return jsonify({'ok': True})


# ==============================================================================
# COMMISSIONER
# ==============================================================================

@app.route('/')
@login_required
def index():
    return redirect(url_for('my_team'))


@app.route('/api/team/<int:team_id>/roster')
@login_required
def api_team_roster(team_id):
    team = db.session.get(FantasyTeam, team_id)
    if not team:
        return jsonify([])
    return jsonify([{
        'id': r.player.id,
        'name': r.player.name,
        'position': r.player.position,
        'archetype': r.player.archetype,
        'season_pts': round(r.player.season_pts, 1),
    } for r in team.roster])


@app.route('/commissioner')
@login_required
def commissioner():
    if not current_user.is_commissioner:
        return redirect(url_for('index'))
    state = LeagueState.query.first()
    invite_codes = InviteCode.query.all()
    owners = User.query.all()
    draft = Draft.query.order_by(Draft.id.desc()).first()
    return render_template('commissioner.html', state=state, invite_codes=invite_codes,
                           owners=owners, draft=draft)


@app.route('/commissioner/draft/open', methods=['POST'])
@login_required
def commissioner_draft_open():
    if not current_user.is_commissioner:
        return redirect(url_for('index'))

    state = LeagueState.query.first()
    if state.phase != 'setup':
        flash('Draft can only be opened from setup phase.')
        return redirect(url_for('commissioner'))

    teams = FantasyTeam.query.all()
    if len(teams) < 2:
        flash('Need at least 2 owners to open the draft.')
        return redirect(url_for('commissioner'))

    random.shuffle(teams)
    for i, team in enumerate(teams):
        team.draft_position = i + 1

    draft = Draft(
        season_year=state.season_year,
        status='active',
        current_pick=1,
        auto_pick_seconds=90,
    )
    draft.snake_order = [t.id for t in teams]
    draft.timer_expires_at = datetime.utcnow() + timedelta(seconds=90)
    db.session.add(draft)

    # Generate fantasy schedule for the season
    from sim import generate_fantasy_schedule
    generate_fantasy_schedule(state.season_year)

    state.phase = 'draft'
    db.session.commit()

    flash('Draft is now open!')
    return redirect(url_for('draft_room'))


@app.route('/commissioner/sim', methods=['POST'])
@login_required
def commissioner_sim():
    if not current_user.is_commissioner:
        return redirect(url_for('index'))

    state = LeagueState.query.first()
    if state.phase not in ('regular_season', 'playoffs'):
        flash('Can only simulate during regular season or playoffs.')
        return redirect(url_for('commissioner'))

    from sim import simulate_week
    result = simulate_week(state)

    if 'error' in result:
        flash(result['error'])
        return redirect(url_for('commissioner'))

    return render_template('results.html', result=result, state=state)


@app.route('/results')
@login_required
def results():
    state  = LeagueState.query.first()
    week   = request.args.get('week', state.week - 1, type=int)
    year   = state.season_year
    from models import NflGame, NflSchedule, PlayerGameStat
    games  = (NflSchedule.query
              .filter_by(week=week, season_year=year, simulated=True)
              .join(NflGame, NflGame.nfl_schedule_id == NflSchedule.id)
              .all())
    fantasy = (FantasySchedule.query
               .filter_by(week=week, season_year=year)
               .all())
    return render_template('results.html',
                           result={'week_simmed': week, 'nfl_games': len(games),
                                   'nfl_results': [], 'fantasy_results': []},
                           games=games, fantasy=fantasy, state=state, week=week)


# ==============================================================================
# MY TEAM
# ==============================================================================

@app.route('/team')
@login_required
def my_team():
    state    = LeagueState.query.first()
    my_ft    = current_user.fantasy_team
    if not my_ft:
        flash('You have no fantasy team.')
        return redirect(url_for('index'))

    week     = state.week
    year     = state.season_year

    # Current roster
    roster   = [r.player for r in my_ft.roster]

    # Current week lineup (or last set one)
    lineup_q = FantasyLineup.query.filter_by(
        fantasy_team_id=my_ft.id, week=week, season_year=year
    ).all()
    lineup   = {l.slot: l.player for l in lineup_q}

    # This week's matchup
    matchup  = (FantasySchedule.query
                .filter(
                    FantasySchedule.week == week,
                    FantasySchedule.season_year == year,
                    db.or_(FantasySchedule.home_team_id == my_ft.id,
                           FantasySchedule.away_team_id == my_ft.id)
                ).first())

    # Pending incoming trades
    from models import Trade
    pending_trades = Trade.query.filter_by(
        receiving_team_id=my_ft.id, status='pending'
    ).all()

    return render_template('team.html',
                           state=state, team=my_ft, roster=roster,
                           lineup=lineup, matchup=matchup,
                           pending_trades=pending_trades,
                           STARTER_SLOTS=STARTER_SLOTS,
                           SLOT_ELIGIBILITY=SLOT_ELIGIBILITY,
                           LINEUP_SLOTS=LINEUP_SLOTS)


@app.route('/api/team/lineup', methods=['POST'])
@login_required
def api_set_lineup():
    state  = LeagueState.query.first()
    my_ft  = current_user.fantasy_team
    week   = state.week
    year   = state.season_year

    assignments = request.json   # {slot: player_id, ...}
    if not assignments:
        return jsonify({'error': 'No assignments'}), 400

    # Validate all players are on the roster
    roster_ids = {r.player_id for r in my_ft.roster}
    for slot, pid in assignments.items():
        if pid not in roster_ids:
            return jsonify({'error': f'Player {pid} not on your roster'}), 400
        if slot in SLOT_ELIGIBILITY:
            player = db.session.get(Player, pid)
            if player.position not in SLOT_ELIGIBILITY[slot]:
                return jsonify({'error': f'{player.name} cannot play {slot}'}), 400

    # Delete existing lineup for this week and replace
    FantasyLineup.query.filter_by(
        fantasy_team_id=my_ft.id, week=week, season_year=year
    ).delete()

    for slot, pid in assignments.items():
        db.session.add(FantasyLineup(
            fantasy_team_id=my_ft.id,
            player_id=int(pid),
            season_year=year,
            week=week,
            slot=slot,
        ))

    db.session.commit()
    return jsonify({'ok': True})


# ==============================================================================
# WAIVER WIRE
# ==============================================================================

@app.route('/waiver')
@login_required
def waiver():
    state   = LeagueState.query.first()
    my_ft   = current_user.fantasy_team
    roster  = [r.player for r in my_ft.roster] if my_ft else []

    pos_filter = request.args.get('pos', '').upper()
    search     = request.args.get('q', '').strip()

    # Players on any roster
    rostered_ids = db.session.query(FantasyRoster.player_id).subquery()

    query = Player.query.filter(
        Player.position != 'DEF',
        Player.status == 'active',
        ~Player.id.in_(rostered_ids),
    )
    if pos_filter in ('QB', 'RB', 'WR', 'TE'):
        query = query.filter(Player.position == pos_filter)
    if search:
        query = query.filter(Player.name.ilike(f'%{search}%'))

    free_agents = query.order_by(Player.skill_bonus.desc()).limit(150).all()

    return render_template('waiver.html', state=state, team=my_ft,
                           free_agents=free_agents, roster=roster,
                           pos_filter=pos_filter, search=search)


@app.route('/api/waiver/claim', methods=['POST'])
@login_required
def api_waiver_claim():
    state  = LeagueState.query.first()
    if state.phase not in ('regular_season', 'playoffs'):
        return jsonify({'error': 'Waivers only open during the season'}), 400

    my_ft  = current_user.fantasy_team
    data   = request.json
    add_id = data.get('add_id')
    drop_id= data.get('drop_id')

    if not add_id or not drop_id:
        return jsonify({'error': 'Must provide add_id and drop_id'}), 400

    # Verify add target is truly unclaimed
    if FantasyRoster.query.filter_by(player_id=add_id).first():
        return jsonify({'error': 'Player already on a roster'}), 400

    add_player = db.session.get(Player, add_id)
    if not add_player or add_player.position == 'DEF':
        return jsonify({'error': 'Invalid player'}), 400

    # Verify drop target is on owner's roster
    drop_entry = FantasyRoster.query.filter_by(
        fantasy_team_id=my_ft.id, player_id=drop_id
    ).first()
    if not drop_entry:
        return jsonify({'error': 'Drop target not on your roster'}), 400

    week = state.week

    # Remove dropped player's lineup slots for this week onwards
    FantasyLineup.query.filter(
        FantasyLineup.fantasy_team_id == my_ft.id,
        FantasyLineup.player_id == drop_id,
        FantasyLineup.week >= week,
    ).delete()

    # Execute the swap
    db.session.delete(drop_entry)
    db.session.add(FantasyRoster(
        fantasy_team_id=my_ft.id,
        player_id=add_id,
        acquired_week=week,
        acquired_via='waiver',
    ))
    db.session.commit()

    drop_player = db.session.get(Player, drop_id)
    return jsonify({
        'ok': True,
        'added': add_player.name,
        'dropped': drop_player.name,
    })


# ==============================================================================
# TRADES
# ==============================================================================

@app.route('/trades')
@login_required
def trades():
    from models import Trade, TradePlayer
    state    = LeagueState.query.first()
    my_ft    = current_user.fantasy_team
    all_teams= FantasyTeam.query.filter(FantasyTeam.id != my_ft.id).all()

    outgoing = Trade.query.filter_by(
        proposing_team_id=my_ft.id, status='pending'
    ).all()
    incoming = Trade.query.filter_by(
        receiving_team_id=my_ft.id, status='pending'
    ).all()

    my_roster = [r.player for r in my_ft.roster]

    return render_template('trades.html', state=state, team=my_ft,
                           all_teams=all_teams, outgoing=outgoing,
                           incoming=incoming, my_roster=my_roster)


@app.route('/api/trade/propose', methods=['POST'])
@login_required
def api_trade_propose():
    from models import Trade, TradePlayer
    state     = LeagueState.query.first()
    if state.phase not in ('regular_season', 'playoffs'):
        return jsonify({'error': 'Trades only open during the season'}), 400

    my_ft     = current_user.fantasy_team
    data      = request.json
    target_id = data.get('target_team_id')
    giving    = data.get('giving', [])    # player ids I'm sending
    receiving = data.get('receiving', []) # player ids I want back

    if not target_id or not giving or not receiving:
        return jsonify({'error': 'Must specify target team and players both ways'}), 400
    if target_id == my_ft.id:
        return jsonify({'error': 'Cannot trade with yourself'}), 400

    # Validate giving players are on my roster
    my_ids = {r.player_id for r in my_ft.roster}
    for pid in giving:
        if pid not in my_ids:
            return jsonify({'error': f'Player {pid} not on your roster'}), 400

    # Validate receiving players are on target's roster
    their_ids = {r.player_id for r in
                 FantasyRoster.query.filter_by(fantasy_team_id=target_id).all()}
    for pid in receiving:
        if pid not in their_ids:
            return jsonify({'error': f'Player {pid} not on target roster'}), 400

    trade = Trade(
        proposing_team_id=my_ft.id,
        receiving_team_id=target_id,
        week=state.week,
        status='pending',
    )
    db.session.add(trade)
    db.session.flush()

    for pid in giving:
        db.session.add(TradePlayer(trade_id=trade.id, player_id=pid,
                                   direction='to_receiver'))
    for pid in receiving:
        db.session.add(TradePlayer(trade_id=trade.id, player_id=pid,
                                   direction='to_proposer'))

    db.session.commit()
    return jsonify({'ok': True, 'trade_id': trade.id})


@app.route('/api/trade/<int:trade_id>/respond', methods=['POST'])
@login_required
def api_trade_respond(trade_id):
    from models import Trade, TradePlayer
    trade  = db.session.get(Trade, trade_id)
    my_ft  = current_user.fantasy_team
    state  = LeagueState.query.first()

    if not trade or trade.status != 'pending':
        return jsonify({'error': 'Trade not found or already resolved'}), 404
    if trade.receiving_team_id != my_ft.id:
        return jsonify({'error': 'Not your trade to respond to'}), 403

    action = request.json.get('action')   # 'accept' or 'reject'
    if action == 'reject':
        trade.status = 'rejected'
        db.session.commit()
        return jsonify({'ok': True, 'status': 'rejected'})

    if action != 'accept':
        return jsonify({'error': 'action must be accept or reject'}), 400

    # Execute the trade: swap roster entries
    week = state.week
    for tp in trade.players:
        if tp.direction == 'to_receiver':
            # Move from proposer → receiver
            entry = FantasyRoster.query.filter_by(
                fantasy_team_id=trade.proposing_team_id, player_id=tp.player_id
            ).first()
            if entry:
                entry.fantasy_team_id = trade.receiving_team_id
                entry.acquired_week   = week
                entry.acquired_via    = 'trade'
            # Clear future lineups for this player on proposer's side
            FantasyLineup.query.filter(
                FantasyLineup.fantasy_team_id == trade.proposing_team_id,
                FantasyLineup.player_id == tp.player_id,
                FantasyLineup.week >= week,
            ).delete()

        else:  # to_proposer
            # Move from receiver → proposer
            entry = FantasyRoster.query.filter_by(
                fantasy_team_id=trade.receiving_team_id, player_id=tp.player_id
            ).first()
            if entry:
                entry.fantasy_team_id = trade.proposing_team_id
                entry.acquired_week   = week
                entry.acquired_via    = 'trade'
            # Clear future lineups for this player on receiver's side
            FantasyLineup.query.filter(
                FantasyLineup.fantasy_team_id == trade.receiving_team_id,
                FantasyLineup.player_id == tp.player_id,
                FantasyLineup.week >= week,
            ).delete()

    trade.status = 'accepted'
    db.session.commit()
    return jsonify({'ok': True, 'status': 'accepted'})


# ==============================================================================
# LEAGUE STANDINGS
# ==============================================================================

@app.route('/league')
@login_required
def league():
    state = LeagueState.query.first()
    teams = FantasyTeam.query.order_by(
        FantasyTeam.wins.desc(), FantasyTeam.points_for.desc()
    ).all()
    return render_template('league.html', state=state, teams=teams)


# ==============================================================================
# NFL STANDINGS
# ==============================================================================

@app.route('/nfl')
@login_required
def nfl_standings():
    state = LeagueState.query.first()
    nfl_teams = NflTeam.query.order_by(
        NflTeam.wins.desc(), NflTeam.points_for.desc()
    ).all()
    return render_template('nfl.html', state=state, nfl_teams=nfl_teams)


# ==============================================================================
# PLAYER BROWSER
# ==============================================================================

@app.route('/players')
@login_required
def players():
    state = LeagueState.query.first()
    pos_filter = request.args.get('pos', '').upper()
    search = request.args.get('q', '').strip()
    team_filter = request.args.get('team', type=int)

    query = Player.query.filter(Player.position != 'DEF', Player.status == 'active')
    if pos_filter in ('QB', 'RB', 'WR', 'TE'):
        query = query.filter(Player.position == pos_filter)
    if search:
        query = query.filter(Player.name.ilike(f'%{search}%'))
    if team_filter:
        query = query.filter(Player.nfl_team_id == team_filter)

    all_players = query.order_by(Player.season_pts.desc()).all()

    # Map player_id → fantasy team name
    roster_map = {r.player_id: r.fantasy_team.name
                  for r in FantasyRoster.query.all()}

    nfl_teams = NflTeam.query.order_by(NflTeam.name).all()
    return render_template('players.html', state=state, players=all_players,
                           roster_map=roster_map, nfl_teams=nfl_teams,
                           pos_filter=pos_filter, search=search,
                           team_filter=team_filter)


@app.route('/api/invite-codes')
@login_required
def api_invite_codes():
    if not current_user.is_commissioner:
        return jsonify({'error': 'forbidden'}), 403
    codes = InviteCode.query.all()
    return jsonify([{
        'code': c.code,
        'used': c.used_by_user_id is not None,
        'used_by': c.used_by.username if c.used_by_user_id else None,
    } for c in codes])


if __name__ == '__main__':
    app.run(debug=True)
