#!/usr/bin/env python
"""
Database management script for the Dining Exchange
"""
import sys
from flask import Flask
from database import db, User, Meal, Position, Order, Trade, MarketState
from init_db import init_database
from config import FRIENDS, CHICKEN_INDEX, BEEF_INDEX, MISC_INDEX

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dining_exchange.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def reset_database():
    """Drop all tables and recreate from scratch"""
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating fresh tables...")
        init_database()
        print("Database reset complete!")

def show_stats():
    """Display database statistics"""
    with app.app_context():
        users = User.query.count()
        meals = Meal.query.count()
        positions = Position.query.filter(Position.shares != 0).count()
        active_orders = Order.query.filter_by(status='ACTIVE').count()
        trades = Trade.query.count()
        
        print("\n=== Database Statistics ===")
        print(f"Users: {users}")
        print(f"Meals: {meals}")
        print(f"Active Positions: {positions}")
        print(f"Active Orders: {active_orders}")
        print(f"Total Trades: {trades}")
        
        # Show top traders
        print("\n=== Top Traders (by trade count) ===")
        from sqlalchemy import func
        top_buyers = db.session.query(
            User.username,
            func.count(Trade.id).label('trade_count')
        ).join(Trade, Trade.buyer_id == User.id).group_by(User.username).order_by(func.count(Trade.id).desc()).limit(5).all()
        
        for i, (username, count) in enumerate(top_buyers, 1):
            print(f"{i}. {username}: {count} trades")

def list_users():
    """List all users and their balances"""
    with app.app_context():
        users = User.query.all()
        print("\n=== All Users ===")
        for user in users:
            print(f"{user.username}: ${user.balance:.2f}")

def list_meals():
    """List all meals and their house supply"""
    with app.app_context():
        meals = Meal.query.all()
        print("\n=== All Meals ===")
        for meal in meals:
            print(f"{meal.name} ({meal.category}): {meal.house_supply} shares")

def backup_database():
    """Create a backup of the database"""
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"dining_exchange_backup_{timestamp}.db"
    shutil.copy("dining_exchange.db", backup_file)
    print(f"Database backed up to: {backup_file}")

def reset_ipo():
    """Reset IPO state (stop IPO and reset price to 200)"""
    with app.app_context():
        from database import MarketState
        state = MarketState.query.first()
        if state:
            state.ipo_start_time = None
            state.ipo_active = False
            db.session.commit()
            print("IPO state reset - price back to $200.00")
        else:
            print("No market state found")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py [command]")
        print("\nCommands:")
        print("  reset       - Drop and recreate all tables")
        print("  stats       - Show database statistics")
        print("  users       - List all users")
        print("  meals       - List all meals")
        print("  backup      - Create a database backup")
        print("  reset_ipo   - Reset IPO state (price back to $200)")
        return
    
    command = sys.argv[1]
    
    if command == "reset":
        confirm = input("This will DELETE all data. Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("Reset cancelled.")
    elif command == "stats":
        show_stats()
    elif command == "users":
        list_users()
    elif command == "meals":
        list_meals()
    elif command == "backup":
        backup_database()
    elif command == "reset_ipo":
        reset_ipo()
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()