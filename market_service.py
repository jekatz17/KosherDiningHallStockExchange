import time
from datetime import datetime
from database import db, User, Meal, Position, Order, Trade, MarketState
from config import (
    FRIENDS, ALL_MEALS, INITIAL_BALANCE, INITIAL_HOUSE_SUPPLY,
    IPO_START_PRICE, IPO_DECAY_RATE, IPO_DECAY_INTERVAL, MEAL_CATEGORIES
)

class MarketService:
    """Service layer for market operations using database"""
    
    @staticmethod
    def get_or_create_market_state():
        """Get or create the singleton market state"""
        state = MarketState.query.first()
        if not state:
            state = MarketState(ipo_active=False)
            db.session.add(state)
            db.session.commit()
        return state
    
    @staticmethod
    def get_current_ipo_price():
        """Calculate current IPO price based on time elapsed"""
        state = MarketService.get_or_create_market_state()
        
        # If IPO hasn't started or isn't active, return start price
        if not state.ipo_start_time or not state.ipo_active:
            return IPO_START_PRICE
        
        elapsed = (datetime.utcnow() - state.ipo_start_time).total_seconds()
        decay = int(elapsed // IPO_DECAY_INTERVAL) * IPO_DECAY_RATE
        current_price = max(0.0, IPO_START_PRICE - decay)
        return current_price
    
    @staticmethod
    def start_ipo():
        """Start the IPO clock"""
        state = MarketService.get_or_create_market_state()
        if not state.ipo_start_time:
            state.ipo_start_time = datetime.utcnow()
            state.ipo_active = True
            db.session.commit()
        return True
    
    @staticmethod
    def get_user(username):
        """Get or create user"""
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, balance=INITIAL_BALANCE)
            db.session.add(user)
            db.session.commit()
        return user
    
    @staticmethod
    def get_meal(meal_name):
        """Get meal by name"""
        return Meal.query.filter_by(name=meal_name).first()
    
    @staticmethod
    def get_or_create_position(user_id, meal_id):
        """Get or create position for user and meal"""
        position = Position.query.filter_by(user_id=user_id, meal_id=meal_id).first()
        if not position:
            position = Position(user_id=user_id, meal_id=meal_id, shares=0)
            db.session.add(position)
            db.session.commit()
        return position
    
    @staticmethod
    def get_portfolio(username):
        """Get user's portfolio with non-zero positions"""
        user = MarketService.get_user(username)
        positions = Position.query.filter_by(user_id=user.id).filter(Position.shares != 0).all()
        return {pos.meal.name: pos.to_dict() for pos in positions}
    
    @staticmethod
    def get_best_ask(meal_id):
        """Get lowest ask price for a meal"""
        order = Order.query.filter_by(
            meal_id=meal_id,
            order_type='ASK',
            status='ACTIVE'
        ).order_by(Order.price.asc()).first()
        return order
    
    @staticmethod
    def get_best_bid(meal_id):
        """Get highest bid price for a meal"""
        order = Order.query.filter_by(
            meal_id=meal_id,
            order_type='BID',
            status='ACTIVE'
        ).order_by(Order.price.desc()).first()
        return order
    
    @staticmethod
    def get_market_summary():
        """Get market overview with all meals"""
        ipo_price = MarketService.get_current_ipo_price()
        state = MarketService.get_or_create_market_state()
        
        summary = {
            'ipo_price': ipo_price,
            'ipo_active': state.ipo_active,
            'meals': []
        }
        
        meals = Meal.query.all()
        for meal in meals:
            best_ask = MarketService.get_best_ask(meal.id)
            best_bid = MarketService.get_best_bid(meal.id)
            
            meal_data = {
                'id': meal.id,
                'name': meal.name,
                'category': meal.category,
                'house_supply': meal.house_supply,
                'best_ask': best_ask.price if best_ask else None,
                'best_bid': best_bid.price if best_bid else None,
                'spread': (best_ask.price - best_bid.price) if (best_ask and best_bid) else None
            }
            summary['meals'].append(meal_data)
        
        return summary
    
    @staticmethod
    def get_order_book(meal_name):
        """Get full order book for a specific meal"""
        meal = MarketService.get_meal(meal_name)
        if not meal:
            return None
        
        asks = Order.query.filter_by(
            meal_id=meal.id,
            order_type='ASK',
            status='ACTIVE'
        ).order_by(Order.price.asc()).all()
        
        bids = Order.query.filter_by(
            meal_id=meal.id,
            order_type='BID',
            status='ACTIVE'
        ).order_by(Order.price.desc()).all()
        
        return {
            'meal': meal.name,
            'asks': [order.to_dict() for order in asks],
            'bids': [order.to_dict() for order in bids]
        }
    
    @staticmethod
    def execute_trade(buyer_username, seller_username, meal_id, price, quantity):
        """Execute a trade between buyer and seller"""
        buyer = MarketService.get_user(buyer_username)
        seller = MarketService.get_user(seller_username) if seller_username != "IPO_HOUSE" else None
        meal = Meal.query.get(meal_id)
        
        cost = price * quantity
        
        # Update balances
        buyer.balance -= cost
        if seller:
            seller.balance += cost
        
        # Transfer shares
        buyer_position = MarketService.get_or_create_position(buyer.id, meal_id)
        buyer_position.shares += quantity
        
        if seller:
            seller_position = MarketService.get_or_create_position(seller.id, meal_id)
            seller_position.shares -= quantity
        
        # Record trade
        trade = Trade(
            meal_id=meal_id,
            buyer_id=buyer.id,
            seller_id=seller.id if seller else None,
            seller_name=seller.username if seller else "IPO_HOUSE",
            quantity=quantity,
            price=price,
            timestamp=datetime.utcnow()
        )
        db.session.add(trade)
        db.session.commit()
        
        return trade.to_dict()
    
    @staticmethod
    def buy_from_ipo(username, meal_name, quantity):
        """Buy shares directly from IPO"""
        state = MarketService.get_or_create_market_state()
        if not state.ipo_active:
            return False, "IPO not started"
        
        meal = MarketService.get_meal(meal_name)
        if not meal:
            return False, "Invalid meal"
        
        user = MarketService.get_user(username)
        ipo_price = MarketService.get_current_ipo_price()
        cost = ipo_price * quantity
        
        if quantity > meal.house_supply:
            return False, "Insufficient supply"
        
        if user.balance < cost:
            return False, "Insufficient funds"
        
        # Update house supply
        meal.house_supply -= quantity
        
        # Execute trade
        MarketService.execute_trade(username, "IPO_HOUSE", meal.id, ipo_price, quantity)
        
        return True, f"Bought {quantity} shares of {meal_name} at ${ipo_price:.2f}"
    
    @staticmethod
    def place_buy_order(username, meal_name, price, quantity, snap_buy=False):
        """Place a buy order (bid) on the secondary market"""
        meal = MarketService.get_meal(meal_name)
        if not meal:
            return False, "Invalid meal", []
        
        user = MarketService.get_user(username)
        trades_executed = []
        remaining_qty = quantity
        
        # Try to match with existing asks
        while remaining_qty > 0:
            best_ask = MarketService.get_best_ask(meal.id)
            if not best_ask or best_ask.price > price:
                break
            
            # Execute trade
            trade_qty = min(remaining_qty, best_ask.remaining_quantity)
            
            if user.balance < (best_ask.price * trade_qty):
                break  # Insufficient funds
            
            # Execute the trade
            seller = User.query.get(best_ask.seller_id)
            trade = MarketService.execute_trade(
                username, seller.username, meal.id, best_ask.price, trade_qty
            )
            trades_executed.append(trade)
            
            # Update order
            best_ask.remaining_quantity -= trade_qty
            if best_ask.remaining_quantity <= 0:
                best_ask.status = 'FILLED'
            
            remaining_qty -= trade_qty
            db.session.commit()
        
        # If there's remaining quantity and not a snap-buy, place bid
        if remaining_qty > 0 and not snap_buy:
            order = Order(
                meal_id=meal.id,
                order_type='BID',
                price=price,
                quantity=remaining_qty,
                remaining_quantity=remaining_qty,
                buyer_id=user.id,
                status='ACTIVE'
            )
            db.session.add(order)
            db.session.commit()
            
            return True, f"Executed {quantity - remaining_qty} shares, {remaining_qty} shares added to order book", trades_executed
        
        if trades_executed:
            return True, f"Executed {quantity - remaining_qty} shares", trades_executed
        
        return False, "No matching orders", []
    
    @staticmethod
    def place_sell_order(username, meal_name, price, quantity, is_short=False):
        """Place a sell order (ask) on the secondary market"""
        meal = MarketService.get_meal(meal_name)
        if not meal:
            return False, "Invalid meal", []
        
        user = MarketService.get_user(username)
        
        # Check if user has shares (unless shorting)
        if not is_short:
            position = Position.query.filter_by(user_id=user.id, meal_id=meal.id).first()
            if not position or position.shares < quantity:
                return False, "Insufficient shares", []
        
        trades_executed = []
        remaining_qty = quantity
        
        # Try to match with existing bids
        while remaining_qty > 0:
            best_bid = MarketService.get_best_bid(meal.id)
            if not best_bid or best_bid.price < price:
                break
            
            # Execute trade
            trade_qty = min(remaining_qty, best_bid.remaining_quantity)
            buyer = User.query.get(best_bid.buyer_id)
            trade = MarketService.execute_trade(
                buyer.username, username, meal.id, best_bid.price, trade_qty
            )
            trades_executed.append(trade)
            
            # Update order
            best_bid.remaining_quantity -= trade_qty
            if best_bid.remaining_quantity <= 0:
                best_bid.status = 'FILLED'
            
            remaining_qty -= trade_qty
            db.session.commit()
        
        # If there's remaining quantity, place ask
        if remaining_qty > 0:
            order = Order(
                meal_id=meal.id,
                order_type='ASK',
                price=price,
                quantity=remaining_qty,
                remaining_quantity=remaining_qty,
                seller_id=user.id,
                status='ACTIVE'
            )
            db.session.add(order)
            db.session.commit()
            
            return True, f"Executed {quantity - remaining_qty} shares, {remaining_qty} shares added to order book", trades_executed
        
        if trades_executed:
            return True, f"Executed {quantity - remaining_qty} shares", trades_executed
        
        return False, "No matching orders", []
    
    @staticmethod
    def get_trade_history(limit=20):
        """Get recent trade history"""
        trades = Trade.query.order_by(Trade.timestamp.desc()).limit(limit).all()
        return [trade.to_dict() for trade in trades]
    
    @staticmethod
    def cancel_order(order_id, username):
        """Cancel an active order"""
        user = MarketService.get_user(username)
        order = Order.query.get(order_id)
        
        if not order:
            return False, "Order not found"
        
        # Check ownership
        if order.buyer_id != user.id and order.seller_id != user.id:
            return False, "Not your order"
        
        if order.status != 'ACTIVE':
            return False, "Order not active"
        
        order.status = 'CANCELLED'
        db.session.commit()
        
        return True, "Order cancelled"