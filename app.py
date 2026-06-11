from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
app.secret_key = "CHANGE_ME_123"

DB = "data.db"

# ================= BOT TOKEN（Render安全版）=================
BOT_TOKEN = os.environ.get(8660820217:AAFCfgnb-J6c7AdB6j2OABIkHNtqE4flHxo）

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today():
    return now_time()[:10]

def today_start():
    return today() + " 00:00:00"

def get_week_start():
    d = datetime.now(pytz.timezone("Asia/Kuala_Lumpur"))
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
        start_credit REAL,
        end_credit REAL,
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

# ================= PUSH（安全版，不会炸）=================
def send_push(title, msg):
    print(f"[PUSH] {title}: {msg}")

# ================= DAILY SETTLEMENT =================
def daily_settlement():
    profit = calc_profit()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO daily_close
    (date, start_credit, end_credit, profit)
    VALUES (?,?,?,?)
    """, (today(), get_value("credit"), get_value("credit"), profit))

    conn.commit()
    conn.close()

    send_push("Daily Report", f"Profit: {profit}")

# ================= WEEKLY =================
def get_week_profit():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT SUM(profit) FROM daily_close")
    result = c.fetchone()[0]
    conn.close()
    return result or 0

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
    update_value(payment, amount)

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
        update_value(payment, -amount)
        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")

# ================= WEEKLY PAGE =================
@app.route("/weekly")
def weekly():
    if not session.get("login"):
        return redirect("/")

    return render_template("weekly.html", profit=get_week_profit())