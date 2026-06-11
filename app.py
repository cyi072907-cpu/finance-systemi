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


def today_start():
    return now_time()[:10] + " 00:00:00"


# ================= DB INIT =================
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
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        time TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_close (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        open_credit REAL,
        close_credit REAL,
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


def update_value(key, amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = value + ? WHERE key=?", (amount, key))
    conn.commit()
    conn.close()


def log(action):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (action, time) VALUES (?,?)", (action, now_time()))
    conn.commit()
    conn.close()


# ================= PROFIT (正确逻辑) =================
# +amount = 客人赢 = 你亏
# -amount = 客人输 = 你赚
def calc_profit(start_time):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT amount FROM records WHERE time >= ?", (start_time,))
    rows = c.fetchall()
    conn.close()

    return sum(-r[0] for r in rows)


# ================= 日结 =================
def daily_settlement():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    today = now_time()[:10]

    c.execute("SELECT value FROM settings WHERE key='credit'")
    open_credit = c.fetchone()[0]

    profit = calc_profit(today_start())
    close_credit = open_credit

    c.execute("""
        INSERT OR IGNORE INTO daily_close (date, open_credit, close_credit, profit)
        VALUES (?,?,?,?)
    """, (today, open_credit, close_credit, profit))

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

    # ✔ 正确逻辑
    update_value("credit", -amount)
    update_value(payment.lower(), amount)

    log(f"ADD {account} {amount}")

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

        log(f"DELETE {id}")

        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")


# ================= REPORT =================
@app.route("/report/daily")
def report_daily():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE time >= ?", (today_start(),))
    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Daily Report")


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)