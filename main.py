import time

# --- CONFIGURATION ---
FRIENDS = ["Josh", "Jack", "Levi", "Shap", "Eitan", "Jonny", "Fisher", "Isaac", 
           "Charlie", "James", "Max", "Matan", "Sam", "Noah", "Jamie", "Oliver"]

CHICKEN_INDEX = ["Teriyaki Chicken", "North African Chicken", "Chicken Chimichurri", "Chicken Tostada", "BBQ Chicken Drumsticks", "Chicken Fried Rice", "Chicken Dakota", "Chicken Bahn Mi Sandwich", "BBQ Chicken on White Bun", "Lebanese Chicken", "Herb Baked Chicken Thighs", "Roasted Chicken", "Italian Chicken", "Taco Chicken", "Schwarma Pita Folds", "Gyro Chicken"]
BEEF_INDEX = ["Beef and Three Mushroom Goulash", "Korean Chuck Eye", "Slow Roasted Chuck Eye", "Beef Stew", "Beef Mostaccioli", "Sloppy Joes", "Beef Bulgogi", "Sloppy Joe on Pretzel Bun", "Roast Beef Chipotle on Baguette", "Beef Hot Dogs", "Corned Beef Sandwich", "Corned Beef", "Hamburger on Pretzel Bun", "Lamb Gyro", "Lamb Korma", "Lamb Meatballs w/ Green Harissa Sauce"]
MISC_INDEX = ["Turkey Chipotle on Baguette", "Turkey Dogs", "Kosher Deli", "Salmon Chimmichuri", "Honey Glazed Salmon", "Whitefish RAS AL HANOUT", "UNIT CHOICE MEAL", "Roasted Turkey Breast", "Brown Sugar Oatmeal", "Scrambled Eggs"]

ALL_MEALS = CHICKEN_INDEX + BEEF_INDEX + MISC_INDEX

# --- DATA INITIALIZATION ---
balances = {name: 10000.0 for name in FRIENDS}
portfolios = {name: {meal: 0 for meal in ALL_MEALS} for name in FRIENDS}
house_supply = {meal: 500 for meal in ALL_MEALS}
trade_history = []
ipo_start_time = None

asks = {meal: [] for meal in ALL_MEALS} 
bids = {meal: [] for meal in ALL_MEALS}

def get_current_ipo_price():
    if ipo_start_time is None: return 200.0
    elapsed = time.time() - ipo_start_time
    return max(0.0, 200.0 - (int(elapsed // 3) * 1.0))

def select_meal_from_indices():
    print("\n[1] Chicken | [2] Beef | [3] Misc")
    idx = input("Select Index: ")
    s_list = CHICKEN_INDEX if idx=="1" else BEEF_INDEX if idx=="2" else MISC_INDEX if idx=="3" else None
    if not s_list: return None
    for i, m in enumerate(s_list, 1): print(f"{i}. {m}")
    try:
        m_idx = int(input("Meal #: ")) - 1
        return s_list[m_idx]
    except: return None

def show_market_summary():
    ipo_p = get_current_ipo_price()
    print("\n" + "="*85)
    print(f"   U-M DINING EXCHANGE | IPO PRICE: ${ipo_p:.2f}")
    print("="*85)
    print(f"{'Meal':<30} | {'IPO':<6} | {'Best Ask':<10} | {'Best Bid'}")
    print("-" * 85)
    for meal in ALL_MEALS:
        b_ask = sorted(asks[meal], key=lambda x: x['price'])[0]['price'] if asks[meal] else "N/A"
        b_bid = sorted(bids[meal], key=lambda x: x['price'], reverse=True)[0]['price'] if bids[meal] else "N/A"
        supply = house_supply[meal] if house_supply[meal] > 0 else "-"
        a_str = f"${b_ask:.2f}" if isinstance(b_ask, float) else b_ask
        b_str = f"${b_bid:.2f}" if isinstance(b_bid, float) else b_bid
        print(f"{meal[:29]:<30} | {str(supply):<6} | {a_str:<10} | {b_str}")

def execute_trade(buyer, seller, meal, price, qty, listing=None):
    cost = price * qty
    # 1. Deduct from Buyer
    balances[buyer] -= cost
    
    # 2. Add to Seller (If they aren't the House)
    if seller != "IPO_HOUSE":
        balances[seller] += cost
    
    # 3. Transfer Shares
    portfolios[buyer][meal] += qty
    if seller != "IPO_HOUSE":
        portfolios[seller][meal] -= qty
    
    trade_history.append({"meal": meal, "buyer": buyer, "seller": seller, "qty": qty, "price": price})
    
    # 4. Cleanup Order Book
    if listing:
        listing['qty'] -= qty
        if listing['qty'] <= 0:
            if 'seller' in listing: asks[meal].remove(listing)
            else: bids[meal].remove(listing)
    print(f"\n>>> TRADE: {buyer} bought {qty} {meal} from {seller} at ${price:.2f}")

def secondary_buy(user):
    meal = select_meal_from_indices()
    if not meal: return
    
    cheapest_listings = sorted(asks[meal], key=lambda x: x['price'])
    
    if cheapest_listings:
        best_price = cheapest_listings[0]['price']
        print(f"\nCheapest {meal} available: ${best_price:.2f}")
        confirm = input(f"Snap-buy at ${best_price:.2f}? (y/n): ").lower()
        if confirm == 'y':
            try:
                qty = int(input("Quantity: "))
                while qty > 0 and cheapest_listings:
                    match = cheapest_listings[0]
                    if match['price'] > best_price: break 
                    t_qty = min(qty, match['qty'])
                    if balances[user] >= (match['price'] * t_qty):
                        execute_trade(user, match['seller'], meal, match['price'], t_qty, match)
                        qty -= t_qty
                        cheapest_listings = sorted(asks[meal], key=lambda x: x['price'])
                    else:
                        print("Insufficient funds.")
                        break
                return
            except: return print("Invalid input.")
    
    print(f"\nNo snap-buys available. Place a custom bid.")
    try:
        price = float(input(f"Your Max Bid Price: $"))
        qty = int(input("Quantity: "))
        while qty > 0:
            cheapest = sorted(asks[meal], key=lambda x: x['price'])
            if cheapest and cheapest[0]['price'] <= price:
                match = cheapest[0]
                t_qty = min(qty, match['qty'])
                execute_trade(user, match['seller'], meal, match['price'], t_qty, match)
                qty -= t_qty
            else: break
        if qty > 0: bids[meal].append({"user": user, "qty": qty, "price": price})
    except: print("Invalid input.")

def secondary_sell(user, is_short=False):
    meal = select_meal_from_indices()
    if not meal: return
    if not is_short and portfolios[user][meal] <= 0: return print("No shares to sell.")
    try:
        qty = int(input(f"Qty to {'Short' if is_short else 'Sell'}: "))
        price = float(input("Min Ask Price: $"))
        while qty > 0:
            highest = sorted(bids[meal], key=lambda x: x['price'], reverse=True)
            if highest and highest[0]['price'] >= price:
                match = highest[0]
                t_qty = min(qty, match['qty'])
                execute_trade(match['user'], user, meal, match['price'], t_qty, match)
                qty -= t_qty
            else: break
        if qty > 0: asks[meal].append({"seller": user, "qty": qty, "price": price})
    except: print("Invalid input.")

# --- MAIN LOOP ---
current_user = ""
while True:
    if not current_user:
        u = input("\nLogin: ")
        if u in FRIENDS: current_user = u
        else: continue
    ipo_p = get_current_ipo_price()
    print(f"\n[{current_user}] Cash: ${balances[current_user]:.2f} | IPO Price: ${ipo_p:.2f}")
    print("1. Market | 2. BUY IPO | 3. START IPO | 4. SECONDARY BUY | 5. SELL | 6. SHORT | 7. Portfolio | 8. History | 9. Switch User")
    choice = input("Select: ")
    if choice == "1": show_market_summary()
    elif choice == "2": 
        if ipo_start_time:
            meal = select_meal_from_indices()
            if meal:
                try:
                    qty = int(input(f"Buying {meal} at ${ipo_p:.2f}. Qty: "))
                    if qty <= house_supply[meal] and balances[current_user] >= (ipo_p * qty):
                        house_supply[meal] -= qty
                        execute_trade(current_user, "IPO_HOUSE", meal, ipo_p, qty)
                    else: print("Error: Supply or funds.")
                except: print("Invalid entry.")
        else: print("IPO not started.")
    elif choice == "3":
        ipo_start_time = time.time()
        print("CLOCK STARTED")
    elif choice == "4": secondary_buy(current_user)
    elif choice == "5": secondary_sell(current_user, is_short=False)
    elif choice == "6": secondary_sell(current_user, is_short=True)
    elif choice == "7":
        for m, s in portfolios[current_user].items():
            if s != 0: print(f"{m}: {s} shares {'(SHORT)' if s < 0 else ''}")
    elif choice == "8":
        for t in reversed(trade_history[-10:]): print(f"{t['buyer']} <- {t['seller']} | {t['qty']} {t['meal']} @ ${t['price']:.2f}")
    elif choice == "9": current_user = ""
