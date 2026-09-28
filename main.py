import os
import time
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ---------------------------------------------------------
# Global In-Memory Data Storage
# ---------------------------------------------------------
latest_status = {
    "XAUUSD": {"text": "Waiting for MT4 Signal...", "color": "#9ca3af"},
    "BTCUSD": {"text": "Waiting for MT4 Signal...", "color": "#9ca3af"},
    "GBPUSD": {"text": "Waiting for MT4 Signal...", "color": "#9ca3af"},
    "EURUSD": {"text": "Waiting for MT4 Signal...", "color": "#9ca3af"}
}

alert_history = []
last_alert_times = {}

# User-managed Telegram User ID/Chat ID list
telegram_user_ids = []

# Fetch Telegram Bot Token from environment variable or hardcoded fallback
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def get_bd_time():
    """Returns formatted Bangladesh Local Time (UTC+6)."""
    bd_tz = timezone(timedelta(hours=6))
    return datetime.now(bd_tz).strftime("%Y-%m-%d %I:%M:%S %p")

def send_telegram_broadcast(message_text):
    """Sends broadcast alert to all registered Telegram chat IDs."""
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Bot Token is missing.")
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
                print(f"Failed to send to {chat_id}: {res.text}")
                success = False
        except Exception as e:
            print(f"Error sending message to {chat_id}: {e}")
            success = False
    return success

# ---------------------------------------------------------
# HTML Template for Dashboard
# ---------------------------------------------------------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Engine Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-4 md:p-8 font-sans">
    <div class="max-w-5xl mx-auto space-y-6">
        
        <!-- Header -->
        <div class="flex flex-wrap justify-between items-center border-b border-slate-700 pb-4 gap-4">
            <div>
                <h1 class="text-2xl font-bold text-white">MT4 Proximity Alert Dashboard</h1>
                <p class="text-sm text-slate-400">Real-time status tracking & Telegram alerts</p>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="sendTestAlert()" id="testBtn" class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs px-3 py-2 rounded transition shadow">
                    🧪 Send Test Alert
                </button>
                <span class="text-xs text-slate-400 bg-slate-800 px-2.5 py-1.5 rounded border border-slate-700">Live API Syncing</span>
            </div>
        </div>

        <!-- Symbol Live Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="symbolCards">
            {% for symbol, data in status.items() %}
            <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow-lg">
                <div class="flex justify-between items-center mb-2">
                    <h2 class="text-lg font-semibold text-slate-200">{{ symbol }}</h2>
                    <span class="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300">15m</span>
                </div>
                <div id="status-{{ symbol }}" class="p-3 rounded text-sm font-mono font-medium" style="background-color: #1e293b; color: {{ data.color }};">
                    {{ data.text }}
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Telegram User ID Management -->
        <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow-lg space-y-4">
            <h2 class="text-lg font-semibold text-slate-200">Telegram Alert Subscribers</h2>
            
            <div class="flex gap-2">
                <input type="text" id="newUserId" placeholder="Enter Telegram Chat/User ID" 
                       class="bg-slate-900 border border-slate-700 text-slate-100 text-sm rounded px-3 py-2 flex-1 focus:outline-none focus:border-blue-500">
                <button onclick="addTelegramUser()" class="bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm px-4 py-2 rounded transition">
                    Add ID
                </button>
            </div>

            <div class="flex flex-wrap gap-2" id="userBadgeContainer">
                {% for uid in users %}
                <span class="inline-flex items-center gap-2 bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-full" id="badge-{{ uid }}">
                    {{ uid }}
                    <button onclick="removeTelegramUser('{{ uid }}')" class="text-slate-400 hover:text-red-400 font-bold">✕</button>
                </span>
                {% else %}
                <p id="noUserText" class="text-xs text-slate-500">No Telegram User IDs registered yet.</p>
                {% endfor %}
            </div>
        </div>

        <!-- Alert History Log -->
        <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow-lg space-y-3">
            <h2 class="text-lg font-semibold text-slate-200">Proximity Alert History (<= 20 Pips)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="text-xs text-slate-400 uppercase bg-slate-900/50 border-b border-slate-700">
                        <tr>
                            <th class="py-2 px-3">Time (BD)</th>
                            <th class="py-2 px-3">Symbol</th>
                            <th class="py-2 px-3">Price</th>
                            <th class="py-2 px-3">200 Basis</th>
                            <th class="py-2 px-3">Distance</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-700/50" id="historyTableBody">
                        {% for item in history %}
                        <tr class="hover:bg-slate-750">
                            <td class="py-2 px-3 text-xs text-slate-400">{{ item.time }}</td>
                            <td class="py-2 px-3 font-semibold">{{ item.symbol }}</td>
                            <td class="py-2 px-3 font-mono" style="color: {{ item.color }}">{{ item.price }}</td>
                            <td class="py-2 px-3 font-mono">{{ item.basis }}</td>
                            <td class="py-2 px-3 font-mono font-bold text-amber-400">{{ item.distance }} Pips</td>
                        </tr>
                        {% else %}
                        <tr id="emptyHistoryRow">
                            <td colspan="5" class="py-4 text-center text-xs text-slate-500">No proximity alerts recorded yet.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Client-side JavaScript for Background AJAX Polling -->
    <script>
        async function fetchMarketData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                
                // Update Market Cards
                for (const [symbol, info] of Object.entries(data.status)) {
                    const el = document.getElementById(`status-${symbol}`);
                    if (el) {
                        el.innerText = info.text;
                        el.style.color = info.color;
                    }
                }

                // Update Alert History Table dynamically
                if (data.history && data.history.length > 0) {
                    const historyBody = document.getElementById('historyTableBody');
                    historyBody.innerHTML = data.history.map(item => `
                        <tr class="hover:bg-slate-750">
                            <td class="py-2 px-3 text-xs text-slate-400">${item.time}</td>
                            <td class="py-2 px-3 font-semibold">${item.symbol}</td>
                            <td class="py-2 px-3 font-mono" style="color: ${item.color}">${item.price}</td>
                            <td class="py-2 px-3 font-mono">${item.basis}</td>
                            <td class="py-2 px-3 font-mono font-bold text-amber-400">${item.distance} Pips</td>
                        </tr>
                    `).join('');
                }
            } catch (err) {
                console.error("Error fetching market data:", err);
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
                container.innerHTML = `<p id="noUserText" class="text-xs text-slate-500">No Telegram User IDs registered yet.</p>`;
                return;
            }
            container.innerHTML = resData.users.map(uid => `
                <span class="inline-flex items-center gap-2 bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-full" id="badge-${uid}">
                    ${uid}
                    <button onclick="removeTelegramUser('${uid}')" class="text-slate-400 hover:text-red-400 font-bold">✕</button>
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

        // Poll every 3 seconds for smooth background updates without reloading full page
        setInterval(fetchMarketData, 3000);
    </script>
</body>
</html>
"""

# ---------------------------------------------------------
# Flask Web Routes
# ---------------------------------------------------------
@app.route('/')
def dashboard():
    return render_template_string(
        DASHBOARD_HTML, 
        status=latest_status, 
        users=telegram_user_ids, 
        history=alert_history
    )

@app.route('/api/data', methods=['GET'])
def api_data():
    """Endpoint for asynchronous UI data fetching without full page reloads."""
    return jsonify({
        "status": latest_status,
        "history": alert_history
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Flexible JSON parsing to accept MQL4 payloads smoothly
        data = request.get_json(silent=True, force=True)
        if not data:
            import json
            raw_text = request.get_data(as_text=True)
            data = json.loads(raw_text)

        raw_symbol = str(data.get("symbol", "")).upper()
        
        # Match incoming symbol string
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

        text_color = "#22c55e" if price >= basis else "#ef4444"
        position_text = "ABOVE" if price >= basis else "BELOW"

        # Decimal precision formatting based on asset class
        fmt_price = f"{price:.5f}" if ("GBP" in symbol or "EUR" in symbol) else f"{price:.2f}"
        fmt_basis = f"{basis:.5f}" if ("GBP" in symbol or "EUR" in symbol) else f"{basis:.2f}"

        status_text = f"Price: {fmt_price} | 200 Line: {fmt_basis} | Dist: {distance:.1f} Pips ({position_text})"
        
        # Update live dashboard state
        latest_status[symbol] = {
            "text": status_text,
            "color": text_color
        }

        # Telegram Proximity Trigger Condition
        limit_pips = 20.0
        if distance <= limit_pips:
            # 5-minute cooldown per symbol to avoid spam
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

                # Add to history log
                alert_history.insert(0, {
                    "time": get_bd_time(),
                    "symbol": symbol,
                    "price": fmt_price,
                    "basis": fmt_basis,
                    "distance": f"{distance:.1f}",
                    "color": text_color
                })

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("Webhook Processing Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 200

@app.route('/add_user', methods=['POST'])
def add_user():
    user_id = request.form.get('user_id', '').strip()
    if user_id and user_id not in telegram_user_ids:
        telegram_user_ids.append(user_id)
    return jsonify({"status": "user_added", "users": telegram_user_ids}), 200

@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_id = request.form.get('user_id', '').strip()
    if user_id in telegram_user_ids:
        telegram_user_ids.remove(user_id)
    return jsonify({"status": "user_deleted", "users": telegram_user_ids}), 200

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if not telegram_user_ids:
        return jsonify({"status": "error", "message": "No Telegram IDs added to send alert!"}), 400
    
    test_msg = (
        "🧪 *TEST ALERT FROM TRADING ENGINE* 🧪\n\n"
        "Your Telegram ID is successfully connected to the MT4 Proximity Alert Engine!"
    )
    sent = send_telegram_broadcast(test_msg)
    if sent:
        return jsonify({"status": "success", "message": "Test alert sent to all subscribed Telegram IDs!"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to send alert. Check Bot Token or User IDs."}), 500

# ---------------------------------------------------------
# Application Entrypoint
# ---------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
