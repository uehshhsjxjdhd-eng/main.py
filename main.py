import os, time, requests, json
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "rakib_trading_dashboard_secret_key_2026"

ACCESS_PASSWORD = "Rakib98"
TELEGRAM_BOT_TOKEN = "8642092487:AAEIHzt94t8xNMfn6kyWZP2FgdRqprPJWV8"
telegram_user_ids = ["8910581056"]

latest_status = {
    "XAUUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "BTCUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "GBPUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"},
    "EURUSD": {"text": "Waiting for MT4 Signal...", "color": "#94a3b8"}
}
alert_history, last_alert_times = [], {}

def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6))).strftime("%I:%M:%S %p")

def send_telegram_broadcast(msg):
    if not TELEGRAM_BOT_TOKEN or not telegram_user_ids: return False
    ok = True
    for cid in telegram_user_ids:
        try:
            r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            if r.status_code != 200: ok = False
        except: ok = False
    return ok

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rakib Pro Trading Terminal</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Inter', sans-serif; }
.font-mono { font-family: 'JetBrains Mono', monospace; }
.glass { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
.glass-card { background: rgba(30, 41, 59, 0.75); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.05); }
</style></head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8 relative selection:bg-blue-500 selection:text-white">
<div class="fixed top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
<div class="fixed bottom-0 right-1/4 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none"></div>
{% if not authenticated %}
<div class="min-h-[85vh] flex items-center justify-center relative z-10">
    <div class="glass p-8 rounded-2xl max-w-md w-full text-center space-y-6 shadow-2xl">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-emerald-500 text-white font-bold text-2xl flex items-center justify-center mx-auto shadow-lg shadow-blue-500/20">⚡</div>
        <div><h1 class="text-2xl font-bold text-white">Rakib Trading Terminal</h1><p class="text-xs text-slate-400 mt-1">Authorized Access Only</p></div>
        {% if error %}<div class="bg-red-500/10 border border-red-500/20 text-red-400 text-xs py-2 px-3 rounded-lg">{{ error }}</div>{% endif %}
        <form action="/login" method="POST" class="space-y-4">
            <input type="password" name="password" placeholder="Enter Password" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-center text-white focus:outline-none focus:border-blue-500">
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm py-3 rounded-xl shadow-lg transition">Unlock Terminal</button>
        </form>
    </div>
</div>
{% else %}
<div class="max-w-6xl mx-auto space-y-6 relative z-10">
    <div class="glass rounded-2xl p-5 flex flex-wrap justify-between items-center gap-4 shadow-xl">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-emerald-500 flex items-center justify-center font-bold text-lg text-white">⚡</div>
            <div>
                <h1 class="text-xl font-bold text-white">Rakib Proximity Terminal</h1>
                <div class="flex items-center gap-2 mt-0.5"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span><p class="text-xs text-slate-400">MT4 Active (15m Timeframe)</p></div>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <button onclick="sendTestAlert()" id="testBtn" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-emerald-400 font-semibold text-xs px-4 py-2.5 rounded-xl transition shadow">🧪 Test Alert</button>
            <a href="/logout" class="bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-semibold px-3.5 py-2.5 rounded-xl border border-red-500/20 transition">Logout</a>
        </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5" id="symbolCards">
        {% for symbol, data in status.items() %}
        <div class="glass-card rounded-2xl p-6 shadow-xl">
            <div class="flex justify-between items-center mb-4">
                <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-blue-500"></span><h2 class="text-lg font-bold text-white">{{ symbol }}</h2></div>
                <span class="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">200 SMA</span>
            </div>
            <div id="status-{{ symbol }}" class="p-4 rounded-xl text-sm font-mono font-semibold border border-slate-800" style="background:#090d16; color:{{ data.color }};">{{ data.text }}</div>
        </div>
        {% endfor %}
    </div>
    <div class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">📱 Telegram Alert Subscribers</h2>
        <div class="flex gap-3">
            <input type="text" id="newUserId" placeholder="Enter Chat ID (e.g. 8910581056)" class="bg-slate-950 border border-slate-800 text-slate-100 text-sm font-mono rounded-xl px-4 py-3 flex-1 focus:outline-none focus:border-blue-500">
            <button onclick="addTelegramUser()" class="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm px-5 py-3 rounded-xl transition shadow">Add Chat ID</button>
        </div>
        <div class="flex flex-wrap gap-2.5 pt-2" id="userBadgeContainer">
            {% for uid in users %}
            <span class="inline-flex items-center gap-2 bg-slate-900 border border-slate-800 text-slate-200 text-xs font-mono px-3.5 py-2 rounded-xl" id="badge-{{ uid }}">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>{{ uid }}
                <button onclick="removeTelegramUser('{{ uid }}')" class="text-slate-500 hover:text-red-400 font-bold ml-1">✕</button>
            </span>
            {% else %}<p id="noUserText" class="text-xs text-slate-500 italic">No Telegram Chat IDs registered.</p>{% endfor %}
        </div>
    </div>
    <div class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">📜 Trigger Log (<= 20 Pips)</h2>
        <div class="overflow-x-auto rounded-xl border border-slate-800">
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="text-xs text-slate-400 uppercase bg-slate-900/90 font-mono border-b border-slate-800">
                    <tr><th class="py-3 px-4">Time (BD)</th><th class="py-3 px-4">Symbol</th><th class="py-3 px-4">Price</th><th class="py-3 px-4">200 Basis</th><th class="py-3 px-4">Distance</th></tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 bg-slate-950/40" id="historyTableBody">
                    {% for item in history %}
                    <tr class="hover:bg-slate-800/30">
                        <td class="py-3 px-4 text-xs font-mono text-slate-400">{{ item.time }}</td>
                        <td class="py-3 px-4 font-bold text-white">{{ item.symbol }}</td>
                        <td class="py-3 px-4 font-mono font-semibold" style="color:{{ item.color }}">{{ item.price }}</td>
                        <td class="py-3 px-4 font-mono text-slate-300">{{ item.basis }}</td>
                        <td class="py-3 px-4 font-mono font-bold text-amber-400">{{ item.distance }} Pips</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5" class="py-6 text-center text-xs text-slate-500 italic">No proximity triggers recorded.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
<script>
async function fetchMarketData() {
    try {
        const res = await fetch('/api/data');
        const data = await res.json();
        for (const [sym, info] of Object.entries(data.status)) {
            const el = document.getElementById(`status-${sym}`);
            if (el) { el.innerText = info.text; el.style.color = info.color; }
        }
        if (data.history && data.history.length > 0) {
            document.getElementById('historyTableBody').innerHTML = data.history.map(item => `
                <tr class="hover:bg-slate-800/30">
                    <td class="py-3 px-4 text-xs font-mono text-slate-400">${item.time}</td>
                    <td class="py-3 px-4 font-bold text-white">${item.symbol}</td>
                    <td class="py-3 px-4 font-mono font-semibold" style="color: ${item.color}">${item.price}</td>
                    <td class="py-3 px-4 font-mono text-slate-300">${item.basis}</td>
                    <td class="py-3 px-4 font-mono font-bold text-amber-400">${item.distance} Pips</td>
                </tr>`).join('');
        }
    } catch(e){}
}
async function addTelegramUser() {
    const input = document.getElementById('newUserId');
    const uid = input.value.trim();
    if (!uid) return;
    const res = await fetch('/add_user', { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: `user_id=${encodeURIComponent(uid)}` });
    if (res.ok) { input.value = ''; renderUsers(await res.json()); }
}
async function removeTelegramUser(uid) {
    const res = await fetch('/delete_user', { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: `user_id=${encodeURIComponent(uid)}` });
    if (res.ok) renderUsers(await res.json());
}
function renderUsers(resData) {
    const container = document.getElementById('userBadgeContainer');
    if (!resData.users || resData.users.length === 0) {
        container.innerHTML = `<p id="noUserText" class="text-xs text-slate-500 italic">No Telegram Chat IDs registered.</p>`;
        return;
    }
    container.innerHTML = resData.users.map(uid => `
        <span class="inline-flex items-center gap-2 bg-slate-900 border border-slate-800 text-slate-200 text-xs font-mono px-3.5 py-2 rounded-xl" id="badge-${uid}">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>${uid}
            <button onclick="removeTelegramUser('${uid}')" class="text-slate-500 hover:text-red-400 font-bold ml-1">✕</button>
        </span>`).join('');
}
async function sendTestAlert() {
    const btn = document.getElementById('testBtn');
    btn.innerText = "⏳ Sending..."; btn.disabled = true;
    try {
        const res = await fetch('/test_alert', { method: 'POST' });
        const result = await res.json(); alert(result.message);
    } catch(e) { alert("Error sending test alert"); }
    finally { btn.innerText = "🧪 Test Alert"; btn.disabled = false; }
}
setInterval(fetchMarketData, 3000);
</script>
{% endif %}</body></html>"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML, authenticated=session.get('authenticated', False), error=request.args.get('error'), status=latest_status, users=telegram_user_ids, history=alert_history)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password', '') == ACCESS_PASSWORD:
        session['authenticated'] = True
        return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard', error="Invalid Password!"))

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('dashboard'))

@app.route('/api/data')
def api_data():
    return jsonify({"status": latest_status, "history": alert_history})

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True, force=True) or json.loads(request.get_data(as_text=True))
        raw_symbol = str(data.get("symbol", "")).upper()
        
        symbol = "XAUUSD"
        if "BTC" in raw_symbol: symbol = "BTCUSD"
        elif "XAU" in raw_symbol or "GOLD" in raw_symbol: symbol = "XAUUSD"
        elif "GBP" in raw_symbol: symbol = "GBPUSD"
        elif "EUR" in raw_symbol: symbol = "EURUSD"

        price, basis, distance = float(data.get("price", 0)), float(data.get("basis", 0)), float(data.get("distance", 0))
        
        # Filter out invalid prices (e.g. 5.50 or <= 10.0 for Gold/Forex)
        if price <= 10.0 or basis <= 10.0:
            return jsonify({"status": "ignored", "reason": "invalid_price"}), 200

        text_color = "#10b981" if price >= basis else "#ef4444"
        position_text = "ABOVE" if price >= basis else "BELOW"
        
        fmt_price = f"{price:.5f}" if symbol in ["GBPUSD", "EURUSD"] else f"{price:.2f}"
        fmt_basis = f"{basis:.5f}" if symbol in ["GBPUSD", "EURUSD"] else f"{basis:.2f}"

        latest_status[symbol] = {"text": f"Price: {fmt_price} | 200 Line: {fmt_basis} | Dist: {distance:.1f} Pips ({position_text})", "color": text_color}

        if distance <= 20.0 and time.time() - last_alert_times.get(symbol, 0) > 300:
            msg = f"🚨 *MT4 PROXIMITY ALERT (20 PIPS)!* 🚨\n\n📊 *Symbol:* {symbol} (15m)\n📈 *Position:* {'🟢 (ABOVE)' if price >= basis else '🔴 (BELOW)'}\n📍 *Current Price:* {fmt_price}\n📉 *200 Basis Line:* {fmt_basis}\n📏 *Distance:* {distance:.1f} Pips"
            send_telegram_broadcast(msg)
            last_alert_times[symbol] = time.time()
            alert_history.insert(0, {"time": get_bd_time(), "symbol": symbol, "price": fmt_price, "basis": fmt_basis, "distance": f"{distance:.1f}", "color": text_color})

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 200

@app.route('/add_user', methods=['POST'])
def add_user():
    uid = request.form.get('user_id', '').strip()
    if uid and uid not in telegram_user_ids:
        telegram_user_ids.append(uid)
        send_telegram_broadcast(f"✅ *New Telegram ID Subscribed:* `{uid}`")
    return jsonify({"status": "user_added", "users": telegram_user_ids})

@app.route('/delete_user', methods=['POST'])
def delete_user():
    uid = request.form.get('user_id', '').strip()
    if uid in telegram_user_ids: telegram_user_ids.remove(uid)
    return jsonify({"status": "user_deleted", "users": telegram_user_ids})

@app.route('/test_alert', methods=['POST'])
def test_alert():
    if not telegram_user_ids: return jsonify({"status": "error", "message": "No Telegram IDs added!"}), 400
    if send_telegram_broadcast("🧪 *TEST ALERT FROM TRADING ENGINE* 🧪\n\nYour Telegram ID is successfully connected!"):
        return jsonify({"status": "success", "message": "Test alert sent to all subscribed Telegram IDs!"})
    return jsonify({"status": "error", "message": "Failed to send alert."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
    
