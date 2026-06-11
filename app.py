from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today_date():
    return now_time()[:10]

# ================= INIT =================
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
    CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        open_credit REAL,
        close_credit REAL,
        profit REAL,
        time TEXT
    )
    """)

    default = [
        ("credit", 5000),
        ("open_credit", 5000),
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

# ================= DAILY SYSTEM =================
def ensure_open():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM daily_summary WHERE date=?", (today_date(),))
    row = c.fetchone()

    if not row:
        credit = get_value("credit")

        c.execute("""
            INSERT INTO daily_summary (date, open_credit, close_credit, profit, time)
            VALUES (?,?,?,?,?)
        """, (today_date(), credit, credit, 0, now_time()))

        conn.commit()

    conn.close()

def update_close():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    open_credit = get_value("open_credit")
    close_credit = get_value("credit")
    profit = open_credit - close_credit

    c.execute("""
        UPDATE daily_summary
        SET close_credit=?, profit=?, time=?
        WHERE date=?
    """, (close_credit, profit, now_time(), today_date()))

    conn.commit()
    conn.close()

def get_today_profit():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT profit FROM daily_summary WHERE date=?", (today_date(),))
    row = c.fetchone()

    conn.close()
    return row[0] if row else 0

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] and request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "密码错误"

    return render_template("login.html")

# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    ensure_open()
    update_close()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    data = c.fetchall()
    conn.close()

    profit = get_today_profit()

    return render_template(
        "index.html",
        data=data,
        credit=get_value("credit"),
        tng=get_value("tng"),
        cash=get_value("cash"),
        bank=get_value("bank"),
        a=get_value("a"),
        profit=profit
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
@app.route("/history")
def history():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT account, amount, payment, time FROM records ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("history.html", data=data)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)