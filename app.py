from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import os
import pytz

app = Flask(__name__)
app.secret_key = "finance_v5_pro_clean"

DB = "data.db"

# ================= TIME (Malaysia 24h) =================
def now():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        amount REAL,
        payment TEXT,
        note TEXT,
        balance_before REAL,
        balance_after REAL,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS manual_balance (
        account TEXT PRIMARY KEY,
        balance REAL
    )
    """)

    # default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?,?)",
                  ("admin", "123456"))

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/dashboard")

        return render_template("login.html", error="登录失败")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 100")
    data = c.fetchall()

    c.execute("SELECT SUM(amount) FROM transactions")
    total = c.fetchone()[0] or 0

    conn.close()

    return render_template("dashboard.html", data=data, total=total)

# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    note = request.form["note"]

    amount = abs(amount)

    if payment == "OUT":
        amount = -amount

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT balance FROM manual_balance WHERE account=?", (account,))
    row = c.fetchone()
    old = row[0] if row else 0

    new = old + amount

    c.execute("""
        INSERT INTO transactions
        (account, amount, payment, note, balance_before, balance_after, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account, amount, payment, note, old, new, now()))

    c.execute("""
        INSERT OR REPLACE INTO manual_balance VALUES (?,?)
    """, (account, new))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= UPDATE PAYMENT =================
@app.route("/update_payment/<int:id>/<pay>")
def update_payment(id, pay):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE transactions SET payment=? WHERE id=?", (pay, id))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= MANUAL CREDIT =================
@app.route("/update_balance", methods=["POST"])
def update_balance():
    account = request.form["account"]
    balance = float(request.form["balance"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO manual_balance VALUES (?,?)", (account, balance))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= BALANCE =================
@app.route("/balance")
def balance():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM manual_balance")
    data = c.fetchall()
    conn.close()
    return render_template("balance.html", data=data)

# ================= HISTORY (30 days) =================
@app.route("/history")
def history():
    limit = datetime.now() - timedelta(days=30)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE created_at >= ? ORDER BY id DESC",
              (limit.strftime("%Y-%m-%d %H:%M:%S"),))

    data = c.fetchall()
    conn.close()

    return render_template("history.html", data=data)

# ================= CLEAN =================
def clean_old():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    limit = datetime.now() - timedelta(days=30)
    c.execute("DELETE FROM transactions WHERE created_at < ?",
              (limit.strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)