from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import os
import pytz

app = Flask(__name__)
app.secret_key = "finance_v5_pro"

DB = "data.db"

# ================= TIME (Malaysia) =================
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
        password TEXT,
        role TEXT DEFAULT 'user'
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

    # ================= NEW: CREDIT BASE =================
    c.execute("""
    CREATE TABLE IF NOT EXISTS credit_base (
        account TEXT PRIMARY KEY,
        base REAL
    )
    """)

    # ================= DEFAULT USER =================
    c.execute("SELECT * FROM users WHERE username=?", ("huat888",))
    if not c.fetchone():
        c.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        """, ("huat888", "Aaa8888", "admin"))

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "登录失败"

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    data = c.fetchall()

    c.execute("SELECT SUM(amount) FROM transactions")
    total = c.fetchone()[0] or 0

    # ================= NEW: CREDIT DATA =================
    c.execute("SELECT * FROM credit_base")
    credit_data = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        data=data,
        total=total,
        credit_data=credit_data
    )

# ================= ADD TRANSACTION =================
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
    old_balance = row[0] if row else 0

    new_balance = old_balance + amount

    c.execute("""
        INSERT INTO transactions
        (account, amount, payment, note, balance_before, balance_after, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (account, amount, payment, note, old_balance, new_balance, now()))

    c.execute("""
        INSERT OR REPLACE INTO manual_balance (account, balance)
        VALUES (?, ?)
    """, (account, new_balance))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= UPDATE PAYMENT =================
@app.route("/update_payment/<int:id>/<new_payment>")
def update_payment(id, new_payment):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE transactions SET payment=? WHERE id=?", (new_payment, id))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= SET CREDIT (NEW) =================
@app.route("/set_credit", methods=["POST"])
def set_credit():
    account = request.form["account"]
    credit = float(request.form["credit"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO credit_base (account, base)
    VALUES (?, ?)
    """, (account, credit))

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

# ================= HISTORY (30 DAYS) =================
@app.route("/history")
def history():
    limit_date = datetime.now() - timedelta(days=30)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT * FROM transactions
    WHERE created_at >= ?
    ORDER BY id DESC
    """, (limit_date.strftime("%Y-%m-%d %H:%M:%S"),))

    data = c.fetchall()
    conn.close()

    return render_template("history.html", data=data)

# ================= FLOW (NEW SIMPLE PROFIT LOSS) =================
@app.route("/flow")
def flow():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT amount FROM transactions ORDER BY id DESC LIMIT 50")
    flow = c.fetchall()

    conn.close()

    return render_template("flow.html", flow=flow)

# ================= CLEAN OLD =================
def clean_old():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    limit = datetime.now() - timedelta(days=30)
    c.execute("DELETE FROM transactions WHERE created_at < ?", (limit.strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)