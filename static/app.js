// API helper functions
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(endpoint, options);
    return await response.json();
}

// Global variable to store meals by category
let allMeals = [];

// Login/Logout
async function login() {
    const username = document.getElementById('loginUsername').value;
    const result = await apiCall('/api/login', 'POST', { username });
    
    if (result.success) {
        // Store username in localStorage for persistent sessions
        localStorage.setItem('username', username);
        
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('mainApp').style.display = 'block';
        loadUserData();
        loadMarketData();
        loadTradeHistory();
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
            loadUserData();
            loadMarketData();
            loadTradeHistory();
        }, 5000);
    } else {
        alert('Invalid username');
    }
}

async function logout() {
    await apiCall('/api/logout', 'POST');
    localStorage.removeItem('username');
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('mainApp').style.display = 'none';
    document.getElementById('loginUsername').value = '';
}

// Check for existing session on page load
window.addEventListener('DOMContentLoaded', async () => {
    const savedUsername = localStorage.getItem('username');
    if (savedUsername) {
        // Try to restore session
        const result = await apiCall('/api/login', 'POST', { username: savedUsername });
        if (result.success) {
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('mainApp').style.display = 'block';
            loadUserData();
            loadMarketData();
            loadTradeHistory();
            
            // Auto-refresh every 5 seconds
            setInterval(() => {
                loadUserData();
                loadMarketData();
                loadTradeHistory();
            }, 5000);
        } else {
            localStorage.removeItem('username');
        }
    }
});

// Load user data
async function loadUserData() {
    const result = await apiCall('/api/current_user');
    if (result.username) {
        document.getElementById('username').textContent = result.username;
        document.getElementById('balance').textContent = result.balance.toFixed(2);
        document.getElementById('ipoPrice').textContent = result.ipo_price.toFixed(2);
    }
}

// Load market data
async function loadMarketData() {
    const result = await apiCall('/api/market_summary');
    const tbody = document.getElementById('marketBody');
    tbody.innerHTML = '';
    
    // Store all meals globally
    allMeals = result.meals;
    
    result.meals.forEach(meal => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meal.name}</td>
            <td>${meal.category}</td>
            <td>${meal.house_supply > 0 ? meal.house_supply : '-'}</td>
            <td>${meal.best_ask ? '$' + meal.best_ask.toFixed(2) : 'N/A'}</td>
            <td>${meal.best_bid ? '$' + meal.best_bid.toFixed(2) : 'N/A'}</td>
            <td>${meal.spread ? '$' + meal.spread.toFixed(2) : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Update meal dropdown based on selected category
function updateMealDropdown(type) {
    const categorySelect = document.getElementById(type + 'Category');
    const mealSelect = document.getElementById(type + 'Meal');
    const selectedCategory = categorySelect.value;
    
    mealSelect.innerHTML = '';
    
    if (!selectedCategory) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Select category first';
        mealSelect.appendChild(option);
        return;
    }
    
    const mealsInCategory = allMeals.filter(meal => meal.category === selectedCategory);
    mealsInCategory.forEach(meal => {
        const option = document.createElement('option');
        option.value = meal.name;
        option.textContent = meal.name;
        mealSelect.appendChild(option);
    });
}

// Load trade history
async function loadTradeHistory() {
    const result = await apiCall('/api/trade_history');
    const tbody = document.getElementById('tradeBody');
    tbody.innerHTML = '';
    
    result.forEach(trade => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${trade.buyer}</td>
            <td>${trade.seller}</td>
            <td>${trade.meal}</td>
            <td>${trade.qty}</td>
            <td>$${trade.price.toFixed(2)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Load portfolio
async function loadPortfolio() {
    const result = await apiCall('/api/portfolio');
    const display = document.getElementById('portfolioDisplay');
    
    if (Object.keys(result).length === 0) {
        display.innerHTML = '<p style="color: #999;">No positions</p>';
        return;
    }
    
    let html = '<table style="width: 100%;"><tr><th>Meal</th><th>Shares</th></tr>';
    for (const [meal, data] of Object.entries(result)) {
        const badge = data.is_short ? '<span class="badge badge-danger">SHORT</span>' : '';
        html += `<tr><td>${meal}</td><td>${data.shares} ${badge}</td></tr>`;
    }
    html += '</table>';
    display.innerHTML = html;
}

// Start IPO
async function startIPO() {
    const result = await apiCall('/api/start_ipo', 'POST');
    if (result.success) {
        alert('IPO started! Price will decay over time.');
        loadUserData();
    }
}

// Buy from IPO
async function buyIPO() {
    const meal = document.getElementById('buyIPOMeal').value;
    const qty = parseInt(document.getElementById('buyIPOQty').value);
    
    if (!meal) {
        alert('Please select a category and meal');
        return;
    }
    
    const result = await apiCall('/api/buy_ipo', 'POST', { meal, qty });
    alert(result.message);
    
    if (result.success) {
        closeModal('buyIPO');
        // Reset dropdowns
        document.getElementById('buyIPOCategory').value = '';
        document.getElementById('buyIPOMeal').innerHTML = '<option value="">Select category first</option>';
        loadUserData();
        loadMarketData();
        loadPortfolio();
        loadTradeHistory();
    }
}

// Secondary buy
async function secondaryBuy() {
    const meal = document.getElementById('secondaryBuyMeal').value;
    const price = parseFloat(document.getElementById('secondaryBuyPrice').value);
    const qty = parseInt(document.getElementById('secondaryBuyQty').value);
    const snap_buy = document.getElementById('snapBuy').checked;
    
    if (!meal) {
        alert('Please select a category and meal');
        return;
    }
    
    const result = await apiCall('/api/secondary_buy', 'POST', { meal, price, qty, snap_buy });
    alert(result.message);
    
    if (result.success) {
        closeModal('secondaryBuy');
        // Reset dropdowns
        document.getElementById('secondaryBuyCategory').value = '';
        document.getElementById('secondaryBuyMeal').innerHTML = '<option value="">Select category first</option>';
        loadUserData();
        loadMarketData();
        loadPortfolio();
        loadTradeHistory();
    }
}

// Sell
async function sell() {
    const meal = document.getElementById('sellMeal').value;
    const price = parseFloat(document.getElementById('sellPrice').value);
    const qty = parseInt(document.getElementById('sellQty').value);
    const is_short = document.getElementById('isShort').checked;
    
    if (!meal) {
        alert('Please select a category and meal');
        return;
    }
    
    const result = await apiCall('/api/sell', 'POST', { meal, price, qty, is_short });
    alert(result.message);
    
    if (result.success) {
        closeModal('sell');
        // Reset dropdowns
        document.getElementById('sellCategory').value = '';
        document.getElementById('sellMeal').innerHTML = '<option value="">Select category first</option>';
        loadUserData();
        loadMarketData();
        loadPortfolio();
        loadTradeHistory();
    }
}

// Modal functions
function openModal(type) {
    document.getElementById(type + 'Modal').style.display = 'block';
}

function closeModal(type) {
    document.getElementById(type + 'Modal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}