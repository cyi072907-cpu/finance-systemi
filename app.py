from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today():
    return now_time()[:10]

def today_start():
    return today() + " 00:00:00"

def week_start():
    today_dt = datetime.now(pytz.timezone("Asia/Kuala_Lumpur"))
    start = today_dt - timedelta(days=today_dt.weekday())
    return start.strftime("%Y-%m-%d") + " 00:00:00"


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
        open_balance REAL,
        close_balance REAL,
        profit REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_close (
        week TEXT PRIMARY KEY,
        profit REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS balance_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_value REAL,
        new_value REAL,
        time TEXT
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


def log_balance_change(old, new):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO balance_log (old_value, new_value, time) VALUES (?,?,?)",
              (old, new, now_time()))
    conn.commit()
    conn.close()


# ================= PROFIT =================
def calc_profit(start_time):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT amount FROM records WHERE time >= ?", (start_time,))
    rows = c.fetchall()
    conn.close()
    return sum(-r[0] for r in rows)


# ================= DAILY CLOSE =================
def daily_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    date = today()
    open_bal = get_value("credit")
    close_bal = get_value("credit")
    profit = calc_profit(today_start())

    c.execute("""
    INSERT OR REPLACE INTO daily_close
    (date, open_balance, close_balance, profit)
    VALUES (?,?,?,?)
    """, (date, open_bal, close_bal, profit))

    conn.commit()
    conn.close()


# ================= WEEKLY CLOSE =================
def weekly_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    week = today()[:10]
    profit = calc_profit(week_start())

    c.execute("""
    INSERT OR REPLACE INTO weekly_close
    (week, profit)
    VALUES (?,?)
    """, (week, profit))

    conn.commit()
    conn.close()


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
        profit=calc_profit(today_start())
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


# ================= BALANCE MANUAL SET =================
@app.route("/set_balance", methods=["POST"])
def set_balance():
    if not session.get("login"):
        return redirect("/")

    new_balance = float(request.form["credit"])

    old = get_value("credit")
    set_value("credit", new_balance)
    log_balance_change(old, new_balance)

    return redirect("/home")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)