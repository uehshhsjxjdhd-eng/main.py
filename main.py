import os, time, threading, requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, session, redirect, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = "super_secret_trading_key_2026"
DEFAULT_PASSWORD = "Rakib98"

SYMBOLS_CONFIG = {
    "XAUUSD": {"pip_multiplier": 10, "pip_buffer": 14.6, "decimals": 2, "cg_id": "tether-gold"},
    "BTCUSD": {"pip_multiplier": 1,  "pip_buffer": 19.5, "decimals": 2, "cg_id": "bitcoin"}
}

TELEGRAM_CHAT_IDS = ["8910581056"]
latest_status = {"XAUUSD": "Fetching...", "BTCUSD": "Fetching...", "last_update": "Initializing..."}
alert_history = []
sma_cache = {"XAUUSD": 0.0, "BTCUSD": 0.0}

TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"
RENDER_APP_URL = "https://telegram-signal-bot-1-uhq3.onrender.com"

def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6))).strftime("%I:%M:%S %p BST")

HTML_LAYOUT = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Pro Trading Terminal</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0f19;--card:rgba(30,41,59,0.6);--border:rgba(255,255,255,0.08);--cyan:#38bdf8;--green:#10b981;--red:#f43f5e;--text:#f8fafc;}
*{box-sizing:border-box;} body{font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px 10px;}
.container{max-width:1200px;margin:auto;} .card{background:var(--card);border:1px solid var(--border);padding:20px;border-radius:14px;margin-bottom:20px;}
input{padding:10px;border-radius:8px;border:1px solid var(--border);background:#0f172a;color:#fff;margin:5px 0;}
button{padding:10px 18px;border-radius:8px;border:none;background:#0284c7;color:#fff;font-weight:600;cursor:pointer;}
.btn-alert{background:#10b981;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;}
table{width:100%;border-collapse:collapse;margin-top:10px;} th,td{padding:10px;text-align:left;border-bottom:1px solid var(--border);}
th{color:var(--cyan);} .badge{background:rgba(56,189,248,0.2);color:var(--cyan);padding:3px 8px;border-radius:4px;font-size:12px;}
</style></head><body><div class="container">
{% if not logged_in %}
<div class="card" style="max-width:380px;margin:50px auto;text-align:center;">
<h2>🔒 Terminal Access</h2>
<form method="POST" action="/login">
<input type="password" name="password" placeholder="Admin Password" required style="width:100%;"><br>
<button type="submit" style="width:100%;margin-top:10px;">Unlock Dashboard</button>
</form>{% if error %}<p style="color:var(--red);">{{error}}</p>{% endif %}</div>
{% else %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
<h2>🤖 15M Proximity Pro</h2><a href="/logout" style="color:var(--red);text-decoration:none;">Logout</a>
</div>
<p><b>Last Sync:</b> <span id="last_update" style="color:var(--cyan);font-weight:bold;">{{status['last_update']}}</span></p>

<div class="card" style="display:flex;gap:15px;align-items:center;">
<h3>🔔 System Test:</h3>
<form method="POST" action="/test_alert" style="margin:0;">
<button type="submit" class="btn-alert">⚡ Send Test Alert</button>
</form>
</div>

<div class="card">
<h3>⚙️ Buffer Settings</h3>
<form method="POST" action="/update_settings" style="display:flex;gap:10px;flex-wrap:wrap;">
XAU Buffer: <input type="number" step="0.1" name="xau_buffer" value="{{config['XAUUSD']['pip_buffer']}}" style="width:90px;">
BTC Buffer: <input type="number" step="0.1" name="btc_buffer" value="{{config['BTCUSD']['pip_buffer']}}" style="width:90px;">
<button type="submit">Save Settings</button>
</form></div>

<div class="card">
<h3>📲 Telegram Recipients</h3>
<form method="POST" action="/add_chat_id">
<input type="text" name="new_chat_id" placeholder="New Chat ID" required>
<input type="password" name="auth_password" placeholder="Admin Password" required>
<button type="submit">Add Chat ID</button>
</form>
<div>{% for cid in chat_ids %}<span class="badge">ID: {{cid}}</span> {% endfor %}</div>
</div>

<div class="grid">
<div class="card"><h3>📌 XAUUSD</h3><p id="status_xau">{{status['XAUUSD']}}</p></div>
<div class="card"><h3>📌 BTCUSD</h3><p id="status_btc">{{status['BTCUSD']}}</p></div>
</div>

<div class="card">
<h3>📈 Live Chart</h3>
<div style="height:350px;">
<div id="tv_chart" style="height:100%;"></div>
<script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
<script type="text/javascript">
new TradingView.widget({"autosize":true,"symbol":"OANDA:XAUUSD","interval":"15","timezone":"Asia/Dhaka","theme":"dark","container_id":"tv_chart"});
</script></div></div>

<div class="card">
<h3>📜 Alert Logs</h3>
<table><thead><tr><th>Time</th><th>Symbol</th><th>Price</th><th>200 Line</th><th>Distance</th></tr></thead>
<tbody id="history_body">
{% for log in history %}
<tr><td>{{log['time']}}</td><td><b>{{log['symbol']}}</b></td><td>{{log['price']}}</td><td>{{log['basis']}}</td><td>{{log['distance']}} Pips</td></tr>
{% else %}<tr><td colspan="5" style="text-align:center;">No alerts yet.</td></tr>{% endfor %}
</tbody></table></div>

<script>
function fetchUpdates() {
    fetch('/api/live_data?_t=' + Date.now())
        .then(res => res.json())
        .then(d => {
            document.getElementById('status_xau').innerText = d.status.XAUUSD;
            document.getElementById('status_btc').innerText = d.status.BTCUSD;
            document.getElementById('last_update').innerText = d.status.last_update;
            let h = '';
            if (!d.history || d.history.length === 0) {
                h = '<tr><td colspan="5" style="text-align:center;">No alerts yet.</td></tr>';
            } else {
                d.history.forEach(l => {
                    h += `<tr><td>${l.time}</td><td><b>${l.symbol}</b></td><td>${l.price}</td><td>${l.basis}</td><td>${l.distance} Pips</td></tr>`;
                });
            }
            document.getElementById('history_body').innerHTML = h;
        }).catch(err => console.log(err));
}
setInterval(fetchUpdates, 3000);
</script>{% endif %}</div></body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_LAYOUT, logged_in=session.get('logged_in', False), status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS)

@app.route('/api/live_data')
def live_data():
    return jsonify({"status": latest_status, "history": alert_history})

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == DEFAULT_PASSWORD:
        session['logged_in'] = True
        return redirect('/')
    return render_template_string(HTML_LAYOUT, logged_in=False, error="Wrong Password!", status=latest_status, config=SYMBOLS_CONFIG, history=alert_history, chat_ids=TELEGRAM_CHAT_IDS)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/')

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if session.get('logged_in'):
        send_telegram_broadcast("🧪 *TEST ALERT:* Telegram Notification Bot is Working Fine!")
    return redirect('/')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if session.get('logged_in'):
        try:
            SYMBOLS_CONFIG['XAUUSD']['pip_buffer'] = float(request.form.get('xau_buffer'))
            SYMBOLS_CONFIG['BTCUSD']['pip_buffer'] = float(request.form.get('btc_buffer'))
        except ValueError: pass
    return redirect('/')

@app.route('/add_chat_id', methods=['POST'])
def add_chat_id():
    if session.get('logged_in') and request.form.get('auth_password') == DEFAULT_PASSWORD:
        new_id = request.form.get('new_chat_id').strip()
        if new_id and new_id not in TELEGRAM_CHAT_IDS:
            TELEGRAM_CHAT_IDS.append(new_id)
    return redirect('/')

def send_telegram_broadcast(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for cid in TELEGRAM_CHAT_IDS:
        try: requests.post(url, data={"chat_id": cid, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except Exception: pass

def keep_alive():
    while True:
        time.sleep(300)
        try: requests.get(RENDER_APP_URL, timeout=10)
        except Exception: pass

def fetch_coingecko_prices():
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://api.coingecko.com/api/v3/simple/price?ids=tether-gold,bitcoin&vs_currencies=usd"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return float(data["tether-gold"]["usd"]), float(data["bitcoin"]["usd"])
    except Exception: pass
    return None, None

def bot_loop():
    last_alerts = {p: 0 for p in SYMBOLS_CONFIG}
    
    while True:
        try:
            xau_p, btc_p = fetch_coingecko_prices()
            prices = {"XAUUSD": xau_p, "BTCUSD": btc_p}
            
            for pair, cfg in SYMBOLS_CONFIG.items():
                price = prices.get(pair)
                if price:
                    # ২০০ SMA-এর আনুমানিক বেসিস ধরে ডিসটেন্স ক্যালকুলেশন
                    basis = sma_cache[pair] if sma_cache[pair] > 0 else price
                    diff = abs(price - basis) * cfg["pip_multiplier"]
                    
                    latest_status[pair] = f"Price: {price:.{cfg['decimals']}f} | 200 Line: {basis:.{cfg['decimals']}f} | Dist: {diff:.1f} Pips"
                    
                    if diff <= cfg["pip_buffer"] and (time.time() - last_alerts[pair] > 300):
                        msg = f"🚨 *{pair} ALERT!*\nPrice: {price:.{cfg['decimals']}f}\n200 Line: {basis:.{cfg['decimals']}f}\nDist: {diff:.1f} Pips\nTime: {get_bd_time()}"
                        send_telegram_broadcast(msg)
                        last_alerts[pair] = time.time()
                        alert_history.insert(0, {"time": get_bd_time(), "symbol": pair, "price": f"{price:.{cfg['decimals']}f}", "basis": f"{basis:.{cfg['decimals']}f}", "distance": f"{diff:.1f}"})
            
            latest_status["last_update"] = get_bd_time()
        except Exception: pass
        time.sleep(3)

def start_threads():
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=bot_loop, daemon=True).start()

start_threads()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    
