import os
import time
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, session, redirect, render_template_string, jsonify, make_response

app = Flask(__name__)
app.secret_key = "super_secret_trading_key_2026"

DEFAULT_PASSWORD = "1234"

SYMBOLS_CONFIG = {
    "XAUUSD": {"pip_buffer": 14.6},
    "BTCUSD": {"pip_buffer": 19.5}
}

TELEGRAM_CHAT_IDS = ["8910581056"]
TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"
RENDER_APP_URL = "https://bot-y282.onrender.com"

latest_status = {
    "XAUUSD": "Waiting for TradingView Signal...",
    "BTCUSD": "Waiting for TradingView Signal..."
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
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }
        input, button { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-right: 5px; margin-bottom: 5px; }
        button { background: #0284c7; cursor: pointer; border: none; font-weight: bold; }
        button:hover { background: #0369a1; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #334155; padding: 8px; text-align: left; font-size: 14px; }
        th { background: #334155; color: #f8fafc; }
        .login-box { max-width: 380px; margin: 80px auto; padding: 25px; text-align: center; }
        .chart-container { height: 380px; margin-top: 10px; }
        .badge { background: #0284c7; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card login-box">
            <h2>🔒 Dashboard Access</h2>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="Enter Password" required style="width: 80%;">
                <br><br>
                <button type="submit">Unlock Terminal</button>
            </form>
            {% if error %}<p style="color: #ef4444;">{{ error }}</p>{% endif %}
        </div>
        {% else %}
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h2 style="margin:0;">🤖 TradingView Webhook Engine</h2>
            <a href="/logout" style="color: #ef4444; text-decoration: none; font-weight: bold;">Logout</a>
        </div>

        <div class="card">
            <h3>⚙️ Actions</h3>
            <form method="POST" action="/test_alert" style="display: inline-block;">
                <button type="submit" style="background: #16a34a;">🚀 Test Telegram</button>
            </form>
        </div>

        <!-- Live Price Grid -->
        <div class="grid">
            <div class="card">
                <h3>📌 XAUUSD (Gold Spot)</h3>
                <p id="status_xau" style="font-size: 15px; font-weight: bold; color: #f8fafc;">{{ status['XAUUSD'] }}</p>
            </div>
            <div class="card">
                <h3>📌 BTCUSD (Bitcoin)</h3>
                <p id="status_btc" style="font-size: 15px; font-weight: bold; color: #f8fafc;">{{ status['BTCUSD'] }}</p>
            </div>
        </div>

        <!-- History Log -->
        <div class="card">
            <h3>📜 Live Alert Log</h3>
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
                        <td>{{ log['price'] }}</td>
                        <td>{{ log['basis'] }}</td>
                        <td>{{ log['distance'] }} Pips</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="text-align: center; color: #64748b;">No alerts received from TradingView yet.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <script>
            function updateData() {
                fetch('/api/live_data?_nocache=' + new Date().getTime(), { cache: 'no-store' })
                    .then(response => response.json())
                    .then(data => {
                        if(data.status) {
                            if(data.status.XAUUSD) document.getElementById('status_xau').innerText = data.status.XAUUSD;
                            if(data.status.BTCUSD) document.getElementById('status_btc').innerText = data.status.BTCUSD;
                        }

                        let historyHtml = '';
                        if (!data.history || data.history.length === 0) {
                            historyHtml = '<tr><td colspan="5" style="text-align: center; color: #64748b;">No alerts received from TradingView yet.</td></tr>';
                        } else {
                            data.history.forEach(log => {
                                historyHtml += `<tr>
                                    <td>${log.time}</td>
                                    <td><b>${log.symbol}</b></td>
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
    return render_template_string(HTML_LAYOUT, logged_in=logged_in, status=latest_status, history=alert_history)

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

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if session.get('logged_in'):
        send_telegram_broadcast("✅ *TEST ALERT:* TradingView Webhook Engine Active!")
    return redirect('/')

# TRADINGVIEW WEBHOOK RECEIVER
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload"}), 400

        symbol = data.get("symbol", "UNKNOWN")
        price = float(data.get("price", 0))
        basis = float(data.get("basis", 0))
        distance = float(data.get("distance", 0))

        status_text = f"Price: {price:.2f} | 200 Line: {basis:.2f} | Distance: {distance:.1f} Pips"
        latest_status[symbol] = status_text

        # Telegram Alert Message
        msg = (
            f"🚨 *TRADINGVIEW PROXIMITY ALERT!* 🚨\n\n"
            f"📊 **Symbol:** {symbol}\n"
            f"📍 **Current Price:** {price:.2f}\n"
            f"📉 **200 Basis Line:** {basis:.2f}\n"
            f"📏 **Distance:** {distance:.1f} Pips"
        )
        send_telegram_broadcast(msg)

        alert_history.insert(0, {
            "time": get_bd_time(),
            "symbol": symbol,
            "price": f"{price:.2f}",
            "basis": f"{basis:.2f}",
            "distance": f"{distance:.1f}"
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
    
