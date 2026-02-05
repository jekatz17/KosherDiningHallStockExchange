from flask import Flask, render_template, request, jsonify, session
from datetime import datetime, timedelta
import os
from database import db
from market_service import MarketService
from config import FRIENDS, ALL_MEALS
from init_db import init_database

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Enable permanent sessions (stays logged in across browser restarts)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts 7 days

# Database configuration
# For development, use SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///dining_exchange.db')
# For production, use PostgreSQL:
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/dining_exchange')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)

# Create tables and initialize data
with app.app_context():
    init_database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    if username in FRIENDS:
        session.permanent = True  # Make session persistent
        session['user'] = username
        return jsonify({'success': True, 'user': username})
    return jsonify({'success': False, 'message': 'Invalid user'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/api/current_user')
def current_user():
    user = session.get('user')
    if user:
        user_obj = MarketService.get_user(user)
        return jsonify({
            'username': user,
            'balance': user_obj.balance,
            'ipo_price': MarketService.get_current_ipo_price()
        })
    return jsonify({'username': None}), 401

@app.route('/api/market_summary')
def market_summary():
    return jsonify(MarketService.get_market_summary())

@app.route('/api/start_ipo', methods=['POST'])
def start_ipo():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Only Josh can start the IPO
    if session['user'] != 'Josh':
        return jsonify({'success': False, 'message': 'Only Josh can start the IPO'}), 403
    
    MarketService.start_ipo()
    return jsonify({'success': True, 'ipo_price': MarketService.get_current_ipo_price()})

@app.route('/api/buy_ipo', methods=['POST'])
def buy_ipo():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user = session['user']
    meal = request.json.get('meal')
    qty = request.json.get('qty')
    
    success, message = MarketService.buy_from_ipo(user, meal, qty)
    return jsonify({'success': success, 'message': message})

@app.route('/api/secondary_buy', methods=['POST'])
def secondary_buy():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user = session['user']
    meal = request.json.get('meal')
    price = request.json.get('price')
    qty = request.json.get('qty')
    snap_buy = request.json.get('snap_buy', False)
    
    success, message, trades = MarketService.place_buy_order(user, meal, price, qty, snap_buy)
    return jsonify({'success': success, 'message': message, 'trades': trades})

@app.route('/api/sell', methods=['POST'])
def sell():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user = session['user']
    meal = request.json.get('meal')
    price = request.json.get('price')
    qty = request.json.get('qty')
    is_short = request.json.get('is_short', False)
    
    success, message, trades = MarketService.place_sell_order(user, meal, price, qty, is_short)
    return jsonify({'success': success, 'message': message, 'trades': trades})

@app.route('/api/portfolio')
def portfolio():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user = session['user']
    return jsonify(MarketService.get_portfolio(user))

@app.route('/api/trade_history')
def trade_history():
    return jsonify(MarketService.get_trade_history(limit=20))

@app.route('/api/order_book/<meal>')
def order_book(meal):
    return jsonify(MarketService.get_order_book(meal))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)