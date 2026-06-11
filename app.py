from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz
import requests

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================== 填这里 ==================
BOT_TOKEN = 8660820217:AAFCfgnb-J6c7AdB6j2OABIkHNtqE4flHxo
CHAT_ID = 6691555924
# ==========================================


# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today():
    return now_time()[:10]

def today_start():
    return today() + " 00:00:00"

def get_week_start():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    d = datetime.now(tz)
    start = d - timedelta(days=d.weekday())
    return start.strftime("%Y-%m-%d")


# ================= TELEGRAM =================
def send_telegram(msg):
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE" or CHAT_ID == "PUT_YOUR_CHAT_ID_HERE":
        print("Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except:
        pass


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


# ================= DAILY =================
def daily_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    date = today()
    start = get_value("credit")
    end = get_value("credit")
    profit = calc_profit()

    c.execute("""
    INSERT OR REPLACE INTO daily_close
    (date, start_credit, end_credit, profit)
    VALUES (?,?,?,?)
    """, (date, start, end, profit))

    conn.commit()
    conn.close()

    send_telegram(
        f"📊 Daily Report\nDate: {date}\nProfit: {profit}"
    )


# ================= WEEKLY =================
def weekly_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    week_start = get_week_start()

    c.execute("""
    SELECT SUM(profit) FROM daily_close
    WHERE date >= ?
    """, (week_start,))

    result = c.fetchone()[0]
    profit = result if result else 0

    c.execute("""
    INSERT OR REPLACE INTO weekly_close
    (week, profit)
    VALUES (?,?)
    """, (week_start, profit))

    conn.commit()
    conn.close()

    send_telegram(
        f"📈 Weekly Report\nWeek: {week_start}\nProfit: {profit}"
    )


# ================= AUTO CHECK =================
def auto_close_check():
    now = datetime.now(pytz.timezone("Asia/Kuala_Lumpur"))
    t = now.strftime("%H:%M")

    if t == "23:59":
        daily_settlement()

        if now.weekday() == 6:
            weekly_settlement()


# ================= ROUTES =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "Login Failed"
    return render_template("login.html")


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

    send_telegram(f"➕ New Record\n{account} | {amount} | {payment}")

    return redirect("/home")


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


@app.route("/set_balance", methods=["POST"])
def set_balance():
    if not session.get("login"):
        return redirect("/")

    credit = float(request.form["credit"])
    set_value("credit", credit)

    return redirect("/home")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)