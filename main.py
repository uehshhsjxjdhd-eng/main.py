import os
import time
import threading
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, session, redirect, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = "super_secret_trading_key_2026"

DEFAULT_PASSWORD = "Rakib98"

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
RENDER_APP_URL = "https://telegram-signal-bot-1-uhq3.onrender.com"
CHECK_INTERVAL = 3

def get_bd_time():
    bd_tz = timezone(timedelta(hours=6))
    return datetime.now(bd_tz).strftime("%I:%M:%S %p BST")

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Trading Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-grad: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #070a12 100%);
            --card-bg: rgba(30, 41, 59, 0.6);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-cyan: #38bdf8;
            --accent-purple: #a855f7;
            --accent-green: #10b981;
            --accent-red: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; transition: all 0.25s ease-in-out; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-grad);
            color: var(--text-main);
            margin: 0;
            padding: 30px 15px;
            min-height: 100vh;
        }

        .container { max-width: 1280px; margin: auto; }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }

        .card:hover {
            border-color: rgba(56, 189, 248, 0.3);
            box-shadow: 0 12px 40px -10px rgba(56, 189, 248, 0.15);
        }

        h1, h2, h3 { color: var(--text-main); font-weight: 700; margin-top: 0; letter-spacing: -0.5px; }

        .header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .title-glow {
            background: linear-gradient(90deg, #38bdf8, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        input {
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid var(--card-border);
            background: rgba(15, 23, 42, 0.8);
            color: #fff;
            margin-right: 10px;
            margin-bottom: 10px;
            outline: none;
            font-size: 14px;
        }

        input:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
        }

        button {
            padding: 12px 20px;
            border-radius: 10px;
            border: none;
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5);
        }

        .btn-green {
            background: linear-gradient(135deg, #059669, #10b981);
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .btn-purple {
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }

        .price-card {
            background: rgba(15, 23, 42, 0.6);
            border-left: 4px solid var(--accent-cyan);
            padding: 18px;
            border-radius: 12px;
        }

        .status-text {
            font-size: 15px;
            font-weight: 600;
            color: #e2e8f0;
            margin: 10px 0;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 15px;
            border-radius: 12px;
            overflow: hidden;
        }

        th, td {
            padding: 14px 18px;
            text-align: left;
        }

        th {
            background: rgba(51, 65, 85, 0.5);
            color: var(--accent-cyan);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        td {
            background: rgba(15, 23, 42, 0.4);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 14px;
        }

        tr:hover td {
            background: rgba(56, 189, 248, 0.05);
        }

        .live-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            margin-right: 6px;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .login-box {
            max-width: 420px;
            margin: 80px auto;
            text-align: center;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }

        .chart-container { height: 420px; margin-top: 15px; border-radius: 12px; overflow: hidden; }
        .badge { background: rgba(56, 189, 248, 0.2); color: var(--accent-cyan); padding: 4px 10px; border-radius: 6px; font-size: 12px; border: 1px solid rgba(56, 189, 248, 0.3); }
        .logout-btn { color: var(--accent-red); text-decoration: none; font-weight: 600; padding: 8px 16px; border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 8px; }
        .logout-btn:hover { background: rgba(244, 63, 94, 0.1); }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card login-box">
            <h2 class="title-glow" style="font-size: 28px; margin-bottom: 20px;">🔒 Terminal Access</h2>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="Enter Admin Password" required style="width: 100%; margin-bottom: 15px;">
                <button type="submit" style="width: 100%;">Unlock Dashboard</button>
            </form>
            {% if error %}<p style="color: var(--accent-red); margin-top: 15px;">{{ error }}</p>{% endif %}
        </div>
        {% else %}
        
        <div class="header-bar">
            <div>
                <h1 class="title-glow">🤖 15M Proximity Pro Control</h1>
                <p style="color: var(--text-muted); margin: 0; font-size: 14px;">
                    <span class="live-dot"></span><b>Last System Sync (BD Time):</b> <span id="last_update" style="color: var(--accent-cyan);">{{ status['last_update'] }}</span>
                </p>
            </div>
            <a href="/logout" class="logout-btn">Logout</a>
        </div>

        <div class="card">
            <h3>⚙️ Settings & Buffer Limits</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                <form method="POST" action="/update_settings" style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 0;">
                    <div>
                        <label style="color: var(--text-muted); font-size: 13px;">XAUUSD Buffer (Pips): </label>
                        <input type="number" step="0.1" name="xau_buffer" value="{{ config['XAUUSD']['pip_buffer'] }}" style="width: 110px;">
                    </div>
                    <div>
                        <label style="color: var(--text-muted); font-size: 13px;">BTCUSD Buffer (Pips): </label>
                        <input type="number" step="0.1" name="btc_buffer" value="{{ config['BTCUSD']['pip_buffer'] }}" style="width: 110px;">
                    </div>
                    <button type="submit">Save Buffer Settings</button>
                </form>
                <form method="POST" action="/test_alert" style="margin: 0;">
                    <button type="submit" class="btn-green">🚀 Test Telegram Alert</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h3>📲 Telegram Recipients Manager</h3>
            <form method="POST" action="/add_chat_id" style="margin-bottom: 15px;">
                <input type="text" name="new_chat_id" placeholder="New Telegram Chat ID" required>
                <input type="password" name="auth_password" placeholder="Admin Password" required>
                <button type="submit" class="btn-purple">➕ Add Telegram Subscriber</button>
            </form>

            {% if msg %}<p style="color: var(--accent-green); font-weight: 600;">{{ msg }}</p>{% endif %}
            {% if chat_error %}<p style="color: var(--accent-red); font-weight: 600;">{{ chat_error }}</p>{% endif %}

            <p style="color: var(--text-muted); margin-bottom: 10px; font-size: 14px;"><b>Active Recipients List:</b></p>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                {% for cid in chat_ids %}
                    <div style="background: rgba(15, 23, 42, 0.6); padding: 8px 14px; border-radius: 8px; border: 1px solid var(--card-border);">
                        Chat ID: <code>{{ cid }}</code> <span class="badge">Active</span>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="grid">
            <div class="card price-card">
                <h3>📌 XAUUSD (Gold Spot)</h3>
                <p id="status_xau" class="status-text">{{ status['XAUUSD'] }}</p>
                <p style="color: var(--text-muted); font-size: 12px; margin: 0;">Alert Trigger: <= {{ config['XAUUSD']['pip_buffer'] }} Pips</p>
            </div>
            <div class="card price-card" style="border-left-color: var(--accent-purple);">
                <h3>📌 BTCUSD (Bitcoin)</h3>
                <p id="status_btc" class="status-text">{{ status['BTCUSD'] }}</p>
                <p style="color: var(--text-muted); font-size: 12px; margin: 0;">Alert Trigger: <= {{ config['BTCUSD']['pip_buffer'] }} Pips</p>
            </div>
        </div>

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

        <div class="card">
            <h3>📜 Alert History Log</h3>
            <table>
                <thead>
                    <tr>
                        <th>Time (BD Time)</th>
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
                        <td colspan="5" style="text-align: center; color: var(--text-muted);">No alerts triggered yet.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <script>
            function updateData() {
                fetch('/api/live_data')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status_xau').innerText = data.status.XAUUSD;
                        document.getElementById('status_btc').innerText = data.status.BTCUSD;
                        document.getElementById('last_update').innerText = data.status.last_update;

                        let historyHtml = '';
                        if (data.history.length === 0) {
                            historyHtml = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No alerts triggered yet.</td></tr>';
                        } else {
                            data.history.forEach(log => {
                                historyHtml += `<tr>
                                    <td>${log.time}</td>
                                    <td><b>${log.symbol}</b></td>
                                    <td>${log.price}</td>
                                    <td>${log.basis}</td>
                                    <td><span style="color: var(--accent-cyan); font-weight: 600;">${log.distance} Pips</span></td>
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
    return jsonify({
        "status": latest_status,
        "history": alert_history
    })

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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    while True:
        time.sleep(300)
        try:
            if RENDER_APP_URL and "onrender.com" in RENDER_APP_URL:
                requests.get(RENDER_APP_URL, headers=headers, timeout=10)
        except Exception:
            pass

def fetch_gold_spot():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=15m&limit=200"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) >= 200:
                closes = [float(c[4]) for c in data]
                return closes[-1], (sum(closes[-200:]) / 200)
    except Exception:
        pass

    try:
        url_vision = "https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval=15m&limit=200"
        res_v = requests.get(url_vision, headers=headers, timeout=5)
        if res_v.status_code == 200:
            data = res_v.json()
            if isinstance(data, list) and len(data) >= 200:
                closes = [float(c[4]) for c in data]
                return closes[-1], (sum(closes[-200:]) / 200)
    except Exception:
        pass

    try:
        url2 = "https://api.coingecko.com/api/v3/simple/price?ids=tether-gold&vs_currencies=usd"
        res2 = requests.get(url2, headers=headers, timeout=5)
        if res2.status_code == 200:
            price = float(res2.json()["tether-gold"]["usd"])
            return price, price - 1.5
    except Exception:
        pass

    return None, None

def fetch_btc_spot():
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=200",
        "https://data-api.binance.vision/api/v3/klines?s
