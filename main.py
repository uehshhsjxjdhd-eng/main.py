import os
import time
import threading
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, session, redirect, render_template_string, jsonify, make_response

app = Flask(__name__)
app.secret_key = "super_secret_trading_key_2026"

DEFAULT_PASSWORD = "1234"

SYMBOLS_CONFIG = {
    "XAUUSD": {"pip_multiplier": 10, "pip_buffer": 14.6, "decimals": 2},
    "BTCUSD": {"pip_multiplier": 1,  "pip_buffer": 19.5, "decimals": 2}
}

TELEGRAM_CHAT_IDS = ["8910581056"]

latest_status = {
    "XAUUSD": "Fetching data...",
    "BTCUSD": "Fetching data...",
    "last_update": "Initializing..."
}

alert_history = []

TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"
RENDER_APP_URL = "https://bot-y282.onrender.com"
CHECK_INTERVAL = 3

def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6))).strftime("%I:%M:%S %p BST")

HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Trading Terminal</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #0f172a; color: #38bdf8; margin: 0; }
        .container { max-width: 1200px; margin: auto; }
        .card { background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        h1, h2, h3 { color: #f8fafc; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        input, button { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-right: 10px; margin-bottom: 5px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; }
        button:hover { background: #0369a1; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #334155; padding: 10px; text-align: left; }
        th { background: #334155; color: #f8fafc; }
        .login-box { max-width: 400px; margin: 100px auto; padding: 30px; text-align: center; }
        .chart-container { height: 400px; margin-top: 15px; }
        .badge { background: #0284c7; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card login-box">
            <h2>🔒 Dashboard Access</h2>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="Enter Password" required>
                <button type="submit">Unlock</button>
            </form>
            {% if error %}<p style="color: #ef4444;">{{ error }}</p>{% endif %}
        </div>
        {% else %}
        
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>🤖 15M Proximity Pro Control</h1>
            <a href="/logout" style="color: #ef4444; text-decoration: none; font-weight: bold;">Logout</a>
        </div>
        <p><b>Last System Sync:</b> <span id="last_update" style="color:#38bdf8; font-weight:bold;">{{ status['last_update'] }}</span></p>

        <!-- Settings -->
        <div class="card">
            <h3>⚙️ Settings & Buffer Limits</h3>
            <form method="POST" action="/update_settings" style="display: inline-block; margin-bottom: 10px;">
                <label>XAUUSD Buffer (Pips): </label>
                <input type="number" step="0.1" name="xau_buffer" value="{{ config['XAUUSD']['pip_buffer'] }}">
                <label>BTCUSD Buffer (Pips): </label>
                <input type="number" step="0.1" name="btc_buffer" value="{{ config['BTCUSD']['pip_buffer'] }}">
                <button type="submit">Save Buffer Settings</button>
            </form>
            <form method="POST" action="/test_alert" style="display: inline-block;">
                <button type="submit" style="background: #16a34a;">🚀 Test Telegram Alert</button>
            </form>
        </div>

        <!-- Telegram Subscriber Manager -->
        <div class="card">
            <h3>📲 Telegram Recipients Manager</h3>
            <p><small>নতুন যেকোনো টেলিগ্রাম ইউজার আইডি যোগ করুন, সিগন্যাল সবার কাছে একসাথে চলে যাবে।</small></p>
            
            <form method="POST" action="/add_chat_id" style="margin-bottom: 15px;">
                <input type="text" name="new_chat_id" placeholder="New Telegram Chat ID" required>
                <input type="password" name="auth_password" placeholder="Admin Password" required>
                <button type="submit" style="background: #8b5cf6;">➕ Add Telegram Subscriber</button>
            </form>

            {% if msg %}<p style="color: #10b981;">{{ msg }}</p>{% endif %}
            {% if chat_error %}<p style="color: #ef4444;">{{ chat_error }}</p>{% endif %}

            <p><b>Active Recipients List:</b></p>
            <ul>
                {% for cid in chat_ids %}
                    <li>Chat ID: <code>{{ cid }}</code> <span class="badge">Active</span></li>
                {% endfor %}
            </ul>
        </div>

        <!-- Live Price Grid -->
        <div class="grid">
            <div class="card">
                <h3>📌 XAUUSD (Gold Spot)</h3>
                <p id="status_xau">{{ status['XAUUSD'] }}</p>
                <p><small>Alert Trigger: <= {{ config['XAUUSD']['pip_buffer'] }} Pips</small></p>
            </div>
            <div class="card">
                <h3>📌 BTCUSD (Bitcoin)</h3>
                <p id="status_btc">{{ status['BTCUSD'] }}</p>
                <p><small>Alert Trigger: <= {{ config['BTCUSD']['pip_buffer'] }} Pips</small></p>
            </div>
        </div>

        <!-- TradingView Chart -->
        <div class="card">
            <h3>📈 Live TradingView Chart</h3>
            <div class="chart-container">
                <div class="tradingview-widget-container" style="height:100%;width:100%">
                  <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget({
                  "autosize": true,
                  "symbol": "OANDA:XAUUSD",
                  "interval": "15",
                  "timezone": "Asia/Dhaka",
                  "theme": "dark",
                  "style": "1",
                  "locale": "en",
                  "enable_publishing": false,
                  "hide_side_toolbar": false,
                  "container_id": "tradingview_chart"
                });
                  </script>
                </div>
            </div>
        </div>

        <!-- History Log -->
        <div class="card">
            <h3>📜 Alert History Log</h3>
            <table>
                <thead>
                    <tr>
                        <th>Time (BST)</th>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>200 Line</th>
                        <th>Distance (Pips)</th>
                    </tr>
                </thead>
                <tbody id="history_body">
                    {% for log in history %}
                    <tr>
                        <td>{{ log['time'] }}</td>
                        <td>{{ log['symbol'] }}</td>
                        <td>{{ log['price'] }}</td>
                        <td>{{ log['basis'] }}</td>
                        <td>{{ log['distance'] }} Pips</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="text-align: center; color: #64748b;">No alerts triggered yet.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <script>
            function updateData() {
                fetch('/api/live_data?_t=' + new Date().getTime(), { cache: 'no-store' })
                    .then(response => response.json())
                    .then(data => {
                        if(data.status) {
                            document.getElementById('status_xau').innerText = data.status.XAUUSD;
                            document.getElementById('status_btc').innerText = data.status.BTCUSD;
                            document.getElementById('last_update').innerText = data.status.last_update;
                        }

                        let historyHtml = '';
                        if (!data.history || data.history.length === 0) {
                            historyHtml = '<tr><td colspan="5" style="text-align: center; color: #64748b;">No alerts triggered yet.</td></tr>';
                        } else {
                            data.history.forEach(log => {
                                historyHtml += `<tr>
                                    <td>${log.time}</td>
                                    <td>${log.symbol}</td>
                                    <td>${log.price}</td>
                                    <td>${log.basis}</td>
                                    <td>${log.distance} Pips</td>
                                </tr>`;
                            });
                        }
                        document.getElementById('history_body').innerHTML = historyHtml;
                    })
                    .catch(err => console.error("API Fetch Error:", err));
            }

            setInterval(updateData, 3000);
        </script>
        
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    logged_in = session.get('logged_in', False)
    return render_template_string(HTML_LAYOUT, logged_in=logged_in, status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS)

@app.route('/api/live_data', methods=['GET'])
def live_data():
    res = make_response(jsonify({
        "status": latest_status,
        "history": alert_history
    }))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    res.headers['Pragma'] = 'no-cache'
    res.headers['Expires'] = '0'
    return res

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    if password == DEFAULT_PASSWORD:
        session['logged_in'] = True
        return redirect('/')
    return render_template_string(HTML_LAYOUT, logged_in=False, error="Wrong Password!", status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if session.get('logged_in'):
        try:
            SYMBOLS_CONFIG['XAUUSD']['pip_buffer'] = float(request.form.get('xau_buffer'))
            SYMBOLS_CONFIG['BTCUSD']['pip_buffer'] = float(request.form.get('btc_buffer'))
        except ValueError:
            pass
    return redirect('/')

@app.route('/add_chat_id', methods=['POST'])
def add_chat_id():
    if session.get('logged_in'):
        new_id = request.form.get('new_chat_id').strip()
        auth_pass = request.form.get('auth_password').strip()
        
        if auth_pass == DEFAULT_PASSWORD:
            if new_id and new_id not in TELEGRAM_CHAT_IDS:
                TELEGRAM_CHAT_IDS.append(new_id)
                return render_template_string(HTML_LAYOUT, logged_in=True, status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS, msg=f"✅ Chat ID {new_id} added successfully!")
            else:
                return render_template_string(HTML_LAYOUT, logged_in=True, status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS, chat_error="Chat ID already exists or invalid!")
        else:
            return render_template_string(HTML_LAYOUT, logged_in=True, status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS, chat_error="Incorrect Admin Password!")
    return redirect('/')

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if session.get('logged_in'):
        send_telegram_broadcast("✅ *TEST ALERT:* Multicast Notification Pipeline Working Fine!")
    return redirect('/')

def send_telegram_broadcast(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception:
            pass

def keep_alive():
    headers = {"User-Agent": "Mozilla/5.0"}
    while True:
        time.sleep(300)
        try:
            requests.get(RENDER_APP_URL, headers=headers, timeout=10)
        except Exception:
            pass

def fetch_klines(symbol):
    endpoints = [
        f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=15m&limit=200",
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for url in endpoints:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) >= 10:
                    closes = [float(c[4]) for c in data]
                    current_price = closes[-1]
                    sma_200 = sum(closes) / len(closes)
                    return current_price, sma_200
        except Exception:
            continue
    return None, None

def get_market_data(symbol):
    if symbol == "XAUUSD":
        return fetch_klines("PAXGUSDT")
    elif symbol == "BTCUSD":
        return fetch_klines("BTCUSDT")
    return None, None

def bot_loop():
    last_alert_times = {pair: 0 for pair in SYMBOLS_CONFIG}
    
    while True:
        try:
            for pair_name, config in SYMBOLS_CONFIG.items():
                price, bb_basis = get_market_data(pair_name)
                
                if price is not None and bb_basis is not None:
                    raw_diff = abs(price - bb_basis)
                    pips_diff = raw_diff * config["pip_multiplier"]
                    dec = config["decimals"]
                    buffer_limit = config["pip_buffer"]
                    
                    status_text = f"Price: {price:.{dec}f} | 200 Line: {bb_basis:.{dec}f} | Distance: {pips_diff:.1f} Pips"
                    latest_status[pair_name] = status_text
                    
                    if pips_diff <= buffer_limit:
                        if time.time() - last_alert_times[pair_name] > 300:
                            msg = (
                                f"🚨 *15M PROXIMITY ALERT ({buffer_limit:.0f} PIPS)!* 🚨\n\n"
                                f"📊 **Symbol:** {pair_name}\n"
                                f"📍 **Current Price:** {price:.{dec}f}\n"
                                f"📉 **200 Basis Line:** {bb_basis:.{dec}f}\n"
                                f"📏 **Distance:** {pips_diff:.1f} Pips"
                            )
                            send_telegram_broadcast(msg)
                            last_alert_times[pair_name] = time.time()
                            
                            alert_history.insert(0, {
                                "time": get_bd_time(),
                                "symbol": pair_name,
                                "price": f"{price:.{dec}f}",
                                "basis": f"{bb_basis:.{dec}f}",
                                "distance": f"{pips_diff:.1f}"
                            })
                
                latest_status["last_update"] = get_bd_time()
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)

# Thread Protection
if not any(t.name == "bot_loop_thread" for t in threading.enumerate()):
    threading.Thread(target=bot_loop, daemon=True, name="bot_loop_thread").start()

if not any(t.name == "keep_alive_thread" for t in threading.enumerate()):
    threading.Thread(target=keep_alive, daemon=True, name="keep_alive_thread").start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
                    
