import os
import time
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, session, redirect, render_template_string, jsonify, make_response

app = Flask(__name__)
app.secret_key = "super_secret_trading_key_2026"

DEFAULT_PASSWORD = "1234"

# Fixed 20.0 Pips threshold for all pairs
SYMBOLS_CONFIG = {
    "XAUUSD": {"pip_buffer": 20.0},
    "BTCUSD": {"pip_buffer": 20.0},
    "GBPUSD": {"pip_buffer": 20.0},
    "EURUSD": {"pip_buffer": 20.0}
}

# Dynamic Telegram Chat IDs Storage
TELEGRAM_CHAT_IDS = ["8910581056"]
TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"

latest_status = {
    "XAUUSD": {"text": "Waiting for MT4 Signal...", "color": "#f8fafc"},
    "BTCUSD": {"text": "Waiting for MT4 Signal...", "color": "#f8fafc"},
    "GBPUSD": {"text": "Waiting for MT4 Signal...", "color": "#f8fafc"},
    "EURUSD": {"text": "Waiting for MT4 Signal...", "color": "#f8fafc"}
}

last_alert_times = {
    "XAUUSD": 0, "BTCUSD": 0, "GBPUSD": 0, "EURUSD": 0
}

alert_history = []

def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6))).strftime("%I:%M:%S %p BST")

HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Trading Terminal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 15px; background: #0f172a; color: #38bdf8; margin: 0; }
        .container { max-width: 1200px; margin: auto; }
        .card { background: #1e293b; border: 1px solid #334155; padding: 18px; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        h1, h2, h3 { color: #f8fafc; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 15px; }
        input, button { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-right: 5px; margin-bottom: 5px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; }
        button:hover { background: #0369a1; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #334155; padding: 8px; text-align: left; font-size: 14px; }
        th { background: #334155; color: #f8fafc; }
        .login-box { max-width: 380px; margin: 80px auto; padding: 25px; text-align: center; }
        .modal { display: none; position: fixed; z-index: 10; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
        .modal-content { background: #1e293b; margin: 10% auto; padding: 20px; border-radius: 12px; max-width: 450px; border: 1px solid #475569; }
        .close-btn { color: #ef4444; float: right; font-size: 24px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card login-box">
            <h2>🔒 Terminal Access</h2>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="Enter Password" required style="width: 80%;">
                <br><br>
                <button type="submit">Unlock</button>
            </form>
        </div>
        {% else %}
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h2 style="margin:0;">🤖 MT4 Multi-Asset Proximity Terminal</h2>
            <a href="/logout" style="color: #ef4444; text-decoration: none; font-weight: bold;">Logout</a>
        </div>

        <div class="card">
            <h3>⚙️ Actions & Telegram Broadcasts</h3>
            <form method="POST" action="/test_alert" style="display: inline-block;">
                <button type="submit" style="background: #16a34a;">🚀 Test Telegram</button>
            </form>
            <button onclick="openModal()" style="background: #6366f1;">📋 Telegram IDs (Details)</button>
        </div>

        <!-- Telegram ID Modal -->
        <div id="idModal" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
                <h3>📱 Managed Telegram Chat IDs</h3>
                <ul>
                    {% for cid in chat_ids %}
                    <li><b>{{ cid }}</b> 
                        {% if loop.index > 1 %}
                        <a href="/remove_id/{{ cid }}" style="color:#ef4444; margin-left:10px; text-decoration:none;">[Remove]</a>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                <hr style="border-color: #334155;">
                <h4>Add New Chat ID</h4>
                <form method="POST" action="/add_id">
                    <input type="text" name="chat_id" placeholder="Enter Telegram Chat ID" required style="width: 70%;">
                    <button type="submit">Add ID</button>
                </form>
            </div>
        </div>

        <!-- Live Market Grid -->
        <div class="grid">
            <div class="card">
                <h3>📌 XAUUSD (Gold 15m)</h3>
                <p id="status_XAUUSD" style="font-size: 15px; font-weight: bold; color: {{ status['XAUUSD']['color'] }};">{{ status['XAUUSD']['text'] }}</p>
                <small>Target: <= 20.0 Pips</small>
            </div>
            <div class="card">
                <h3>📌 BTCUSD (Bitcoin 15m)</h3>
                <p id="status_BTCUSD" style="font-size: 15px; font-weight: bold; color: {{ status['BTCUSD']['color'] }};">{{ status['BTCUSD']['text'] }}</p>
                <small>Target: <= 20.0 Pips</small>
            </div>
            <div class="card">
                <h3>📌 GBPUSD (Cable 15m)</h3>
                <p id="status_GBPUSD" style="font-size: 15px; font-weight: bold; color: {{ status['GBPUSD']['color'] }};">{{ status['GBPUSD']['text'] }}</p>
                <small>Target: <= 20.0 Pips</small>
            </div>
            <div class="card">
                <h3>📌 EURUSD (Euro 15m)</h3>
                <p id="status_EURUSD" style="font-size: 15px; font-weight: bold; color: {{ status['EURUSD']['color'] }};">{{ status['EURUSD']['text'] }}</p>
                <small>Target: <= 20.0 Pips</small>
            </div>
        </div>

        <!-- Alert History Log -->
        <div class="card">
            <h3>📜 Proximity Alert Log</h3>
            <table>
                <thead>
                    <tr>
                        <th>Time (BST)</th>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>200 Line</th>
                        <th>Distance</th>
                    </tr>
                </thead>
                <tbody id="history_body">
                    {% for log in history %}
                    <tr>
                        <td>{{ log['time'] }}</td>
                        <td><b>{{ log['symbol'] }}</b></td>
                        <td style="color: {{ log['color'] }}; font-weight:bold;">{{ log['price'] }}</td>
                        <td>{{ log['basis'] }}</td>
                        <td style="color: {{ log['color'] }}; font-weight:bold;">{{ log['distance'] }} Pips</td>
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
            function openModal() { document.getElementById('idModal').style.display = 'block'; }
            function closeModal() { document.getElementById('idModal').style.display = 'none'; }

            function updateData() {
                fetch('/api/live_data?_nocache=' + new Date().getTime(), { cache: 'no-store' })
                    .then(response => response.json())
                    .then(data => {
                        if(data.status) {
                            ["XAUUSD", "BTCUSD", "GBPUSD", "EURUSD"].forEach(sym => {
                                if(data.status[sym]) {
                                    let el = document.getElementById('status_' + sym);
                                    if(el) {
                                        el.innerText = data.status[sym].text;
                                        el.style.color = data.status[sym].color;
                                    }
                                }
                            });
                        }

                        let historyHtml = '';
                        if (!data.history || data.history.length === 0) {
                            historyHtml = '<tr><td colspan="5" style="text-align: center; color: #64748b;">No alerts triggered yet.</td></tr>';
                        } else {
                            data.history.forEach(log => {
                                historyHtml += `<tr>
                                    <td>${log.time}</td>
                                    <td><b>${log.symbol}</b></td>
                                    <td style="color:${log.color}; font-weight:bold;">${log.price}</td>
                                    <td>${log.basis}</td>
                                    <td style="color:${log.color}; font-weight:bold;">${log.distance} Pips</td>
                                </tr>`;
                            });
                        }
                        document.getElementById('history_body').innerHTML = historyHtml;
                    })
                    .catch(err => console.error("Fetch Error:", err));
            }

            setInterval(updateData, 2000);
        </script>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    logged_in = session.get('logged_in', False)
    return render_template_string(HTML_LAYOUT, logged_in=logged_in, status=latest_status, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS)

@app.route('/api/live_data', methods=['GET'])
def live_data():
    res = make_response(jsonify({
        "status": latest_status,
        "history": alert_history
    }))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return res

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == DEFAULT_PASSWORD:
        session['logged_in'] = True
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/')

@app.route('/add_id', methods=['POST'])
def add_id():
    if session.get('logged_in'):
        new_id = request.form.get('chat_id', '').strip()
        if new_id and new_id not in TELEGRAM_CHAT_IDS:
            TELEGRAM_CHAT_IDS.append(new_id)
            send_telegram_broadcast(f"✅ *New Chat ID Added:* `{new_id}`")
    return redirect('/')

@app.route('/remove_id/<chat_id>', methods=['GET'])
def remove_id(chat_id):
    if session.get('logged_in') and chat_id in TELEGRAM_CHAT_IDS:
        if len(TELEGRAM_CHAT_IDS) > 1:
            TELEGRAM_CHAT_IDS.remove(chat_id)
    return redirect('/')

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if session.get('logged_in'):
        send_telegram_broadcast("🚀 *TEST ALERT:* MT4 Live Webhook Engine Active!")
    return redirect('/')

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"status": "error"}), 400

        raw_symbol = data.get("symbol", "").upper()
        symbol = "XAUUSD"
        if "BTC" in raw_symbol: symbol = "BTCUSD"
        elif "XAU" in raw_symbol or "GOLD" in raw_symbol: symbol = "XAUUSD"
        elif "GBP" in raw_symbol: symbol = "GBPUSD"
        elif "EUR" in raw_symbol: symbol = "EURUSD"

        price = float(data.get("price", 0))
        basis = float(data.get("basis", 0))
        distance = float(data.get("distance", 0))

        # Color logic: Green above 200 Line, Red below 200 Line
        text_color = "#22c55e" if price >= basis else "#ef4444"
        position_text = "ABOVE" if price >= basis else "BELOW"

        status_text = f"Price: {price:.5f if 'USD' in symbol and 'BTC' not in symbol and 'XAU' not in symbol else price:.2f} | 200 Line: {basis:.5f if 'USD' in symbol and 'BTC' not in symbol and 'XAU' not in symbol else basis:.2f} | Dist: {distance:.1f} Pips ({position_text})"
        
        latest_status[symbol] = {
            "text": status_text,
            "color": text_color
        }

        # 20 Pips Limit
        limit_pips = 20.0
        
        if distance <= limit_pips:
            if time.time() - last_alert_times.get(symbol, 0) > 300:
                direction_icon = "🟢 (ABOVE)" if price >= basis else "🔴 (BELOW)"
                msg = (
                    f"🚨 *MT4 PROXIMITY ALERT ({limit_pips} PIPS)!* 🚨\n\n"
                    f"📊 **Symbol:** {symbol} (15m)\n"
                    f"📈 **Position:** {direction_icon}\n"
                    f"📍 **Current Price:** {price}\n"
                    f"📉 **200 Basis Line:** {basis}\n"
                    f"📏 **Distance:** {distance:.1f} Pips"
                )
                send_telegram_broadcast(msg)
                last_alert_times[symbol] = time.time()

                alert_history.insert(0, {
                    "time": get_bd_time(),
                    "symbol": symbol,
                    "price": f"{price}",
                    "basis": f"{basis}",
                    "distance": f"{distance:.1f}",
                    "color": text_color
                })

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

def send_telegram_broadcast(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
                
