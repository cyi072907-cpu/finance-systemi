from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import os
import pytz

app = Flask(__name__)
app.secret_key = "finance_v5_pro"

DB = "data.db"

# ================= TIME =================
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS credit_base (
        account TEXT PRIMARY KEY,
        base REAL
    )
    """)

    c.execute("SELECT * FROM users WHERE username=?", ("huat888",))
    if not c.fetchone():
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                  ("huat888", "Aaa8888", "admin"))

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        if c.fetchone():
            session["user"] = u
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

    # payment统计
    c.execute("SELECT payment, SUM(amount) FROM transactions GROUP BY payment")
    payment_stat = c.fetchall()

    conn.close()

    return render_template("dashboard.html",
                           data=data,
                           total=total,
                           payment_stat=payment_stat)

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
        (account,amount,payment,note,balance_before,balance_after,created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account,amount,payment,note,old,new,now()))

    c.execute("INSERT OR REPLACE INTO manual_balance VALUES (?,?)", (account,new))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= CREDIT MODAL SET =================
@app.route("/set_credit", methods=["POST"])
def set_credit():
    account = request.form["account"]
    credit = float(request.form["credit"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT OR REPLACE INTO credit_base VALUES (?,?)", (account,credit))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= HISTORY FILTER =================
@app.route("/history", methods=["GET","POST"])
def history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if request.method == "POST":
        if request.form.get("payment"):
            query += " AND payment=?"
            params.append(request.form["payment"])

        if request.form.get("start") and request.form.get("end"):
            query += " AND created_at BETWEEN ? AND ?"
            params.append(request.form["start"])
            params.append(request.form["end"])

    query += " ORDER BY id DESC"

    c.execute(query, params)
    data = c.fetchall()

    conn.close()

    return render_template("history.html", data=data)

# ================= TODAY PROFIT =================
@app.route("/report")
def report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT amount FROM transactions WHERE created_at LIKE ?", (today+"%",))
    data = c.fetchall()

    total = sum([x[0] for x in data]) if data else 0

    conn.close()

    return render_template("report.html", total=total)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))