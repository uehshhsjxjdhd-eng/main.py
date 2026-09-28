import os
import time
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "rakib_trading_dashboard_secret_key_2026"

# ---------------------------------------------------------
# Security & Access Control
# ---------------------------------------------------------
ACCESS_PASSWORD = "Rakib98"

# ---------------------------------------------------------
# Dynamic Memory & Active Bot Credentials
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"
telegram_user_ids = ["8910581056"]

latest_status = {
    "XAUUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "BTCUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "GBPUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "EURUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"}
}

alert_history = []
last_alert_times = {}

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def get_bd_time():
    bd_tz = timezone(timedelta(hours=6))
    return datetime.now(bd_tz).strftime("%Y-%m-%d %I:%M:%S %p")

def send_telegram_broadcast(message_text):
    if not TELEGRAM_BOT_TOKEN or not telegram_user_ids:
        return False
    
    success = True
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in telegram_user_ids:
        try:
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "Markdown"
            }
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code != 200:
                success = False
        except Exception:
            success = False
    return success

# ---------------------------------------------------------
# Modern High-End Dark UI Template
# ---------------------------------------------------------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rakib Pro Trading Terminal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .glass { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glass-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.05); }
        .glow-emerald { box-shadow: 0 0 20px -5px rgba(16, 185, 129, 0.3); }
        .glow-red { box-shadow: 0 0 20px -5px rgba(239, 68, 68, 0.3); }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8 relative overflow-x-hidden selection:bg-blue-500 selection:text-white">

    <!-- Ambient Background Lighting -->
    <div class="fixed top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
    <div class="fixed bottom-0 right-1/4 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none"></div>

    {% if not authenticated %}
    <!-- Login Screen -->
    <div class="min-h-[85vh] flex items-center justify-center relative z-10">
        <div class="glass p-8 md:p-10 rounded-2xl shadow-2xl max-w-md w-full border border-slate-800/80 text-center space-y-6">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-emerald-500 text-white font-bold text-2xl shadow-lg shadow-blue-500/20 mb-2">
                ⚡
            </div>
            <div>
                <h1 class="text-2xl font-bold tracking-tight text-white">Rakib Trading Terminal</h1>
                <p class="text-xs text-slate-400 mt-1">Authorized Access Only</p>
            </div>

            {% if error %}
            <div class="bg-red-500/10 border border-red-500/20 text-red-400 text-xs py-2 px-3 rounded-lg">
                {{ error }}
            </div>
            {% endif %}

            <form action="/login" method="POST" class="space-y-4">
                <div class="relative">
                    <input type="password" name="password" placeholder="Enter Access Password" required
                           class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-center text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition shadow-inner">
                </div>
                <button type="submit" 
                        class="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold text-sm py-3 px-4 rounded-xl shadow-lg shadow-blue-600/25 transition duration-200">
                    Unlock Terminal
                </button>
            </form>
            <p class="text-[11px] text-slate-600">24/7 High-Frequency Proximity Engine</p>
        </div>
    </div>
    {% else %}

    <!-- Main Terminal Dashboard -->
    <div class="max-w-6xl mx-auto space-y-6 relative z-10">
        
        <!-- Header Bar -->
        <div class="glass rounded-2xl p-5 md:p-6 flex flex-wrap justify-between items-center gap-4 shadow-xl">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-emerald-500 flex items-center justify-center font-bold text-lg text-white shadow-md">
                    ⚡
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white">Rakib Proximity Terminal</h1>
                    <div class="flex items-center gap-2 mt-0.5">
                        <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        <p class="text-xs text-slate-400 font-medium">MT4 Engine Connected (15m Timeframe)</p>
                    </div>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <button onclick="sendTestAlert()" id="testBtn" 
                        class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-emerald-400 hover:text-emerald-300 font-semibold text-xs px-4 py-2.5 rounded-xl transition duration-200 shadow-md flex items-center gap-2">
                    <span>🧪</span> Send Test Alert
                </button>
                <a href="/logout" class="bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-semibold px-3.5 py-2.5 rounded-xl border border-red-500/20 transition">
                    Logout
                </a>
            </div>
        </div>

        <!-- Symbol Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5" id="symbolCards">
            {% for symbol, data in status.items() %}
            <div class="glass-card rounded-2xl p-6 shadow-xl transition-all duration-300 hover:border-slate-700/80">
                <div class="flex justify-between items-center mb-4">
                    <div class="flex items-center gap-2.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm shadow-blue-500"></span>
                        <h2 class="text-lg font-bold tracking-wide text-white">{{ symbol }}</h2>
                    </div>
                    <span class="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                        200 SMA
                    </span>
                </div>
                <div id="status-{{ symbol }}" 
                     class="p-4 rounded-xl text-sm font-mono font-semibold transition-all duration-300 border border-slate-800/80 shadow-inner" 
                     style="background-color: #090d16; color: {{ data.color }};">
                    {{ data.text }}
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Telegram Subscribers Management -->
        <div class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
            <div class="flex justify-between items-center">
                <div>
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <span>📱</span> Telegram Alert Broadcast Subscribers
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">Manage Chat IDs that receive instant <= 20 Pip proximity alerts</p>
                </div>
            </div>
            
            <div class="flex gap-3">
                <input type="text" id="newUserId" placeholder="Enter Telegram Chat ID (e.g. 8910581056)" 
                       class="bg-slate-950 border border-slate-800 text-slate-100 text-sm font-mono rounded-xl px-4 py-3 flex-1 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition shadow-inner">
                <button onclick="addTelegramUser()" 
                        class="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm px-5 py-3 rounded-xl transition shadow-lg shadow-blue-600/20">
                    Add Chat ID
                </button>
            </div>

            <div class="flex flex-wrap gap-2.5 pt-2" id="userBadgeContainer">
                {% for uid in users %}
                <span class="inline-flex items-center gap-2 bg-slate-900 border border-slate-800 text-slate-200 text-xs font-mono px-3.5 py-2 rounded-xl shadow-sm" id="badge-{{ uid }}">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    {{ uid }}
                    <button onclick="removeTelegramUser('{{ uid }}')" class="text-slate-500 hover:text-red-400 font-bold ml-1 transition">✕</button>
                </span>
                {% else %}
                <p id="noUserText" class="text-xs text-slate-500 italic">No Telegram Chat IDs registered yet.</p>
                {% endfor %}
            </div>
        </div>

        <!-- Alert History Table -->
        <div class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
            <div class="flex justify-between items-center">
                <h2 class="text-base font-bold text-white flex items-center gap-2">
                    <span>📜</span> Proximity Trigger Log (Threshold <= 20 Pips)
                </h2>
                <span class="text-[11px] text-slate-400 font-mono">Live Session</span>
            </div>

            <div class="overflow-x-auto rounded-xl border border-slate-800/80">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="text-xs text-slate-400 uppercase bg-slate-900/90 font-mono border-b border-slate-800">
                        <tr>
                            <th class="py-3 px-4">Time (BD)</th>
                            <th class="py-3 px-4">Symbol</th>
                            <th class="py-3 px-4">Price</th>
                            <th class="py-3 px-4">200 Basis</th>
                            <th class="py-3 px-4">Distance</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60 bg-slate-950/40" id="historyTableBody">
                        {% for item in history %}
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-4 text-xs font-mono text-slate-400">{{ item.time }}</td>
                            <td class="py-3 px-4 font-bold text-white">{{ item.symbol }}</td>
                            <td class="py-3 px-4 font-mono font-semibold" style="color: {{ item.color }}">{{ item.price }}</td>
                            <td class="py-3 px-4 font-mono text-slate-300">{{ item.basis }}</td>
                            <td class="py-3 px-4 font-mono font-bold text-amber-400">{{ item.distance }} Pips</td>
                        </tr>
                        {% else %}
                        <tr id="emptyHistoryRow">
                            <td colspan="5" class="py-6 text-center text-xs text-slate-500 italic">No proximity triggers recorded in this session.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Client-side Background JavaScript -->
    <script>
        async function fetchMarketData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                
                for (const [symbol, info] of Object.entries(data.status)) {
                    const el = document.getElementById(`status-${symbol}`);
                    if (el) {
                        el.innerText = info.text;
                        el.style.color = info.color;
                    }
                }

                if (data.history && data.history.length > 0) {
                    const historyBody = document.getElementById('historyTableBody');
                    historyBody.innerHTML = data.history.map(item => `
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-4 text-xs font-mono text-slate-400">${item.time}</td>
                            <td class="py-3 px-4 font-bold text-white">${item.symbol}</td>
                            <td class="py-3 px-4 font-mono font-semibold" style="color: ${item.color}">${item.price}</td>
                            <td class="py-3 px-4 font-mono text-slate-300">${item.basis}</td>
                            <td class="py-3 px-4 font-mono font-bold text-amber-400">${item.distance} Pips</td>
                        </tr>
                    `).join('');
                }
            } catch (err) {
                console.error("Error syncing terminal data:", err);
            }
        }

        async function addTelegramUser() {
            const input = document.getElementById('newUserId');
            const uid = input.value.trim();
            if (!uid) return;

            const res = await fetch('/add_user', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `user_id=${encodeURIComponent(uid)}`
            });
            if (res.ok) {
                input.value = '';
                renderUsers(await res.json());
            }
        }

        async function removeTelegramUser(uid) {
            const res = await fetch('/delete_user', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `user_id=${encodeURIComponent(uid)}`
            });
            if (res.ok) {
                renderUsers(await res.json());
            }
        }

        function renderUsers(resData) {
            const container = document.getElementById('userBadgeContainer');
            if (!resData.users || resData.users.length === 0) {
                container.innerHTML = `<p id="noUserText" class="text-xs text-slate-500 italic">No Telegram Chat IDs registered yet.</p>`;
                return;
            }
            container.innerHTML = resData.users.map(uid => `
                <span class="inline-flex items-center gap-2 bg-slate-900 border border-slate-800 text-slate-200 text-xs font-mono px-3.5 py-2 rounded-xl shadow-sm" id="badge-${uid}">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    ${uid}
                    <button onclick="removeTelegramUser('${uid}')" class="text-slate-500 hover:text-red-400 font-bold ml-1 transition">✕</button>
                </span>
            `).join('');
        }

        async function sendTestAlert() {
            const btn = document.getElementById('testBtn');
            btn.innerText = "⏳ Sending...";
            btn.disabled = true;

            try {
                const res = await fetch('/test_alert', { method: 'POST' });
                const result = await res.json();
                alert(result.message);
            } catch (e) {
                alert("Error sending test alert");
            } finally {
                btn.innerText = "🧪 Send Test Alert";
                btn.disabled = false;
            }
        }

        setInterval(fetchMarketData, 3000);
    </script>
    {% endif %}
</body>
</html>
"""

# ---------------------------------------------------------
# Flask Web Routes
# ---------------------------------------------------------
@app.route('/')
def dashboard():
    authenticated = session.get('authenticated', False)
    error = request.args.get('error', None)
    return render_template_string(
        DASHBOARD_HTML, 
        authenticated=authenticated,
        error=error,
        status=latest_status, 
        users=telegram_user_ids, 
        history=alert_history
    )

@app.route('/login', methods=['POST'])
def login():
    pwd = request.form.get('password', '')
    if pwd == ACCESS_PASSWORD:
        session['authenticated'] = True
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('dashboard', error="Invalid Access Password!"))

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('dashboard'))

@app.route('/api/data', methods=['GET'])
def api_data():
    return jsonify({
        "status": latest_status,
        "history": alert_history
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True, force=True)
        if not data:
            import json
            raw_text = request.get_data(as_text=True)
            data = json.loads(raw_text)

        raw_symbol = str(data.get("symbol", "")).upper()
        
        symbol = "XAUUSD"
        if "BTC" in raw_symbol: 
            symbol = "BTCUSD"
        elif "XAU" in raw_symbol or "GOLD" in raw_symbol: 
            symbol = "XAUUSD"
        elif "GBP" in raw_symbol: 
            symbol = "GBPUSD"
        elif "EUR" in raw_symbol: 
            symbol = "EURUSD"

        price = float(data.get("price", 0))
        basis = float(data.get("basis", 0))
        distance = float(data.get("distance", 0))

        text_color = "#10b981" if price >= basis else "#ef4444"
        position_text = "ABOVE" if price >= basis else "BELOW"

        fmt_price = f"{price:.5f}" if ("GBP" in symbol or "EUR" in symbol) else f"{price:.2f}"
        fmt_basis = f"{basis:.5f}" if ("GBP" in symbol or "EUR" in symbol) else f"{basis:.2f}"

        status_text = f"Price: {fmt_price} | 200 Line: {fmt_basis} | Dist: {distance:.1f} Pips ({position_text})"
        
        latest_status[symbol] = {
            "text": status_text,
            "color": text_color
        }

        limit_pips = 20.0
        if distance <= limit_pips:
            if time.time() - last_alert_times.get(symbol, 0) > 300:
                direction_icon = "🟢 (ABOVE)" if price >= basis else "🔴 (BELOW)"
                msg = (
                    f"🚨 *MT4 PROXIMITY ALERT ({limit_pips} PIPS)!* 🚨\n\n"
                    f"📊 *Symbol:* {symbol} (15m)\n"
                    f"📈 *Position:* {direction_icon}\n"
                    f"📍 *Current Price:* {fmt_price}\n"
                    f"📉 *200 Basis Line:* {fmt_basis}\n"
                    f"📏 *Distance:* {distance:.1f} Pips"
                )
                send_telegram_broadcast(msg)
                last_alert_times[symbol] = time.time()

                alert_history.insert(0, {
                  
