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
let currentFilter = 'all';
let priceHistory = {}; // Store price history for charts
let chartInstance = null;

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
        
        // Only show Start IPO button for Josh
        const startIPOContainer = document.getElementById('startIPOContainer');
        if (result.username !== 'Josh') {
            const startBtn = startIPOContainer.querySelector('.btn-success');
            if (startBtn) {
                startBtn.style.display = 'none';
            }
        }
    }
}

// Load market data
async function loadMarketData() {
    const result = await apiCall('/api/market_summary');
    const tbody = document.getElementById('marketBody');
    tbody.innerHTML = '';
    
    // Store all meals globally
    allMeals = result.meals;
    
    // Populate chart meal selector
    const chartSelect = document.getElementById('chartMealSelect');
    if (chartSelect.options.length === 1) { // Only populate once
        result.meals.forEach(meal => {
            const option = document.createElement('option');
            option.value = meal.name;
            option.textContent = meal.name;
            chartSelect.appendChild(option);
        });
    }
    
    // Filter meals based on current filter
    const filteredMeals = currentFilter === 'all' 
        ? result.meals 
        : result.meals.filter(meal => meal.category === currentFilter);
    
    filteredMeals.forEach(meal => {
        // Track price history for charts
        if (!priceHistory[meal.name]) {
            priceHistory[meal.name] = [];
        }
        if (meal.best_bid || meal.best_ask) {
            const price = meal.best_bid || meal.best_ask;
            priceHistory[meal.name].push({
                time: Date.now(),
                price: price
            });
            // Keep only last 20 data points
            if (priceHistory[meal.name].length > 20) {
                priceHistory[meal.name].shift();
            }
        }
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meal.name}</td>
            <td>${meal.category}</td>
            <td>${meal.house_supply > 0 ? meal.house_supply : '-'}</td>
            <td>${meal.best_ask ? '$' + meal.best_ask.toFixed(2) : 'N/A'}</td>
            <td>${meal.best_bid ? '$' + meal.best_bid.toFixed(2) : 'N/A'}</td>
            <td><canvas class="ticker-mini" id="mini-${meal.name.replace(/\s/g, '-')}" onclick="selectMealForChart('${meal.name}')"></canvas></td>
        `;
        tbody.appendChild(row);
        
        // Draw mini chart
        drawMiniChart(meal.name);
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
            <td>${trade.buyer || 'N/A'}</td>
            <td>${trade.seller || 'N/A'}</td>
            <td>${trade.meal_name || 'N/A'}</td>
            <td>${trade.quantity || 0}</td>
            <td>$${trade.price ? trade.price.toFixed(2) : '0.00'}</td>
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

// Switch between index tabs
function switchIndex(category) {
    currentFilter = category;
    
    // Update active tab
    document.querySelectorAll('.index-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById('tab-' + category).classList.add('active');
    
    // Reload market data with filter
    loadMarketData();
}

// Draw mini sparkline chart
function drawMiniChart(mealName) {
    const canvasId = 'mini-' + mealName.replace(/\s/g, '-');
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const history = priceHistory[mealName] || [];
    
    if (history.length < 2) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }
    
    const prices = history.map(h => h.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = prices[prices.length - 1] >= prices[0] ? '#27ae60' : '#c41e3a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    prices.forEach((price, i) => {
        const x = (i / (prices.length - 1)) * canvas.width;
        const y = canvas.height - ((price - min) / range) * canvas.height;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    
    ctx.stroke();
}

// Select meal for full chart
function selectMealForChart(mealName) {
    document.getElementById('chartMealSelect').value = mealName;
    updateChart();
}

// Update full price chart
function updateChart() {
    const mealName = document.getElementById('chartMealSelect').value;
    if (!mealName) return;
    
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');
    const history = priceHistory[mealName] || [];
    
    if (history.length < 2) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#999';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Not enough data yet', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    const prices = history.map(h => h.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const padding = 40;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw axes
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();
    
    // Draw grid lines
    ctx.strokeStyle = '#222';
    for (let i = 0; i <= 5; i++) {
        const y = padding + (i / 5) * (canvas.height - 2 * padding);
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
        
        // Price labels
        const price = max - (i / 5) * range;
        ctx.fillStyle = '#999';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText('$' + price.toFixed(2), padding - 5, y + 4);
    }
    
    // Draw price line
    ctx.strokeStyle = '#9b7fd4';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    prices.forEach((price, i) => {
        const x = padding + (i / (prices.length - 1)) * (canvas.width - 2 * padding);
        const y = padding + ((max - price) / range) * (canvas.height - 2 * padding);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    
    ctx.stroke();
    
    // Draw points
    ctx.fillStyle = '#9b7fd4';
    prices.forEach((price, i) => {
        const x = padding + (i / (prices.length - 1)) * (canvas.width - 2 * padding);
        const y = padding + ((max - price) / range) * (canvas.height - 2 * padding);
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Title
    ctx.fillStyle = 'white';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(mealName + ' - Price History', canvas.width / 2, 20);
    
    // Current price
    const currentPrice = prices[prices.length - 1];
    const priceChange = prices.length > 1 ? currentPrice - prices[0] : 0;
    const changePercent = prices[0] !== 0 ? (priceChange / prices[0] * 100) : 0;
    ctx.fillStyle = priceChange >= 0 ? '#27ae60' : '#c41e3a';
    ctx.font = '14px sans-serif';
    ctx.fillText(
        `$${currentPrice.toFixed(2)} (${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}, ${changePercent.toFixed(1)}%)`,
        canvas.width / 2,
        canvas.height - 10
    );
}