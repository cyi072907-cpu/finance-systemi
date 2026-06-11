from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import pytz
import requests

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================= TELEGRAM CONFIG =================
BOT_TOKEN = 8660820217:AAFCfgnb-J6c7AdB6j2OABIkHNtqE4flHxo
CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except:
        pass

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today():
    return now_time()[:10]

def today_start():
    return today() + " 00:00:00"

def get_week_start():
    tz = pytz.timezone("Asia/Kuala_LUMPUR")
    d = datetime.now(tz)
    start = d - timedelta(days=d.weekday())
    return start.strftime("%Y-%m-%d")

# ================= DB =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        amount REAL,
        payment TEXT,
        remark TEXT,
        time TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_close (
        date TEXT PRIMARY KEY,
        profit REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_close (
        week TEXT PRIMARY KEY,
        profit REAL
    )
    """)

    default = [
        ("credit", 5000),
        ("tng", 0),
        ("cash", 0),
        ("bank", 0),
        ("a", 0)
    ]

    for k, v in default:
        c.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================
def get_value(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    v = c.fetchone()[0]
    conn.close()
    return v

def set_value(key, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def update_value(key, amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = value + ? WHERE key=?", (amount, key))
    conn.commit()
    conn.close()

# ================= PROFIT =================
def calc_profit():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT amount FROM records WHERE time >= ?", (today_start(),))
    rows = c.fetchall()
    conn.close()
    return sum(-r[0] for r in rows)

# ================= DAILY CLOSE =================
def daily_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    date = today()

    c.execute("SELECT date FROM daily_close WHERE date=?", (date,))
    if c.fetchone():
        conn.close()
        return

    profit = calc_profit()

    c.execute("""
    INSERT INTO daily_close (date, profit)
    VALUES (?,?)
    """, (date, profit))

    conn.commit()
    conn.close()

    send_telegram(
        f"📊 Daily Report\nDate: {date}\nProfit: {profit}"
    )

# ================= WEEKLY CLOSE =================
def weekly_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    week = get_week_start()

    c.execute("SELECT week FROM weekly_close WHERE week=?", (week,))
    if c.fetchone():
        conn.close()
        return

    c.execute("""
    SELECT SUM(profit) FROM daily_close
    WHERE date >= ?
    """, (week,))

    result = c.fetchone()[0]
    profit = result if result else 0

    c.execute("""
    INSERT INTO weekly_close (week, profit)
    VALUES (?,?)
    """, (week, profit))

    conn.commit()
    conn.close()

    send_telegram(
        f"📈 Weekly Report\nWeek Start: {week}\nProfit: {profit}"
    )

# ================= AUTO =================
_last_run = None

def auto_close_check():
    global _last_run

    tz = pytz.timezone("Asia/Kuala_LUMPUR")
    now = datetime.now(tz)

    key = now.strftime("%Y-%m-%d")
    t = now.strftime("%H:%M")

    if _last_run == key:
        return

    if t == "23:59":
        daily_settlement()

        if now.weekday() == 6:
            weekly_settlement()

        _last_run = key

# ================= API =================
@app.route("/api/weekly")
def api_weekly():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT week, profit FROM weekly_close
    ORDER BY week DESC LIMIT 10
    """)

    data = c.fetchall()
    conn.close()

    return jsonify(data)

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "Login Failed"
    return render_template("login.html")

# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    auto_close_check()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    data = c.fetchall()

    conn.close()

    return render_template(
        "index.html",
        data=data,
        credit=get_value("credit"),
        tng=get_value("tng"),
        cash=get_value("cash"),
        bank=get_value("bank"),
        a=get_value("a"),
        profit=calc_profit()
    )

# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    remark = request.form["remark"]

    update_value("credit", -amount)
    update_value(payment.lower(), amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT INTO records (account, amount, payment, remark, time)
    VALUES (?,?,?,?,?)
    """, (account, amount, payment, remark, now_time()))

    conn.commit()
    conn.close()

    return redirect("/home")

# ================= DELETE =================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT amount, payment FROM records WHERE id=?", (id,))
    row = c.fetchone()

    if row:
        amount, payment = row
        update_value("credit", amount)
        update_value(payment.lower(), -amount)

        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")

# ================= SET BALANCE =================
@app.route("/set_balance", methods=["POST"])
def set_balance():
    if not session.get("login"):
        return redirect("/")

    set_value("credit", float(request.form["credit"]))
    return redirect("/home")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)