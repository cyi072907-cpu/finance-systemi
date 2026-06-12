from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "finance_v5_pro"

DB = "data.db"

# ================= LOGIN CHECK =================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper


# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    """)

    # transactions table
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

    # manual balance
    c.execute("""
    CREATE TABLE IF NOT EXISTS manual_balance (
        account TEXT PRIMARY KEY,
        balance REAL
    )
    """)

    # ================= AUTO ADMIN ACCOUNT =================
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            ("admin", "123456", "boss")
        )

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
        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "登录失败"

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    data = c.fetchall()

    c.execute("SELECT SUM(amount) FROM transactions")
    total = c.fetchone()[0] or 0

    conn.close()

    return render_template("dashboard.html", data=data, total=total)


# ================= ADD TRANSACTION =================
@app.route("/add", methods=["POST"])
def add():
    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    note = request.form["note"]

    # ================= FIX -50 BUG =================
    amount = float(abs(amount))

    if payment.upper() == "OUT":
        amount = -abs(amount)
    else:
        amount = abs(amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # get old balance
    c.execute("SELECT balance FROM manual_balance WHERE account=?", (account,))
    row = c.fetchone()
    old_balance = row[0] if row else 0

    new_balance = old_balance + amount

    # insert transaction
    c.execute("""
        INSERT INTO transactions
        (account, amount, payment, note, balance_before, balance_after, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        account,
        amount,
        payment,
        note,
        old_balance,
        new_balance,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # update balance
    c.execute("""
        INSERT OR REPLACE INTO manual_balance (account, balance)
        VALUES (?, ?)
    """, (account, new_balance))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ================= BALANCE =================
@app.route("/balance", methods=["GET", "POST"])
@login_required
def balance():
    if request.method == "POST":
        account = request.form["account"]
        new_balance = float(request.form["balance"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO manual_balance VALUES (?,?)
        """, (account, new_balance))
        conn.commit()
        conn.close()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM manual_balance")
    data = c.fetchall()
    conn.close()

    return render_template("balance.html", data=data)


# ================= HISTORY (30 DAYS) =================
@app.route("/history")
@login_required
def history():
    limit_date = datetime.now() - timedelta(days=30)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # stable version (no datetime compare bug)
    c.execute("""
        SELECT * FROM transactions
        ORDER BY id DESC
    """)

    data = c.fetchall()
    conn.close()

    # filter last 30 days in python
    filtered = []
    for row in data:
        try:
            t = datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
            if t >= limit_date:
                filtered.append(row)
        except:
            pass

    return render_template("history.html", data=filtered)


# ================= AUTO CLEAN OLD DATA =================
def clean_old():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    limit = datetime.now() - timedelta(days=30)

    c.execute("""
        DELETE FROM transactions
        WHERE created_at < ?
    """, (limit.strftime("%Y-%m-%d %H:%M:%S"),))

    conn.commit()
    conn.close()


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)