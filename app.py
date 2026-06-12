from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
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
        role TEXT DEFAULT 'admin'
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

    # records
    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    data = c.fetchall()

    # credit base
    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    # total transactions
    c.execute("SELECT SUM(amount) FROM transactions")
    tx_total = c.fetchone()[0] or 0

    # ✅ CORRECT BALANCE LOGIC (FIXED)
    final_total = credit + tx_total

    # payment stat
    c.execute("SELECT payment, SUM(amount) FROM transactions GROUP BY payment")
    payment_stat = c.fetchall()

    # today profit
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today + "%",))

    today_profit = c.fetchone()[0] or 0

    # today count
    c.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today + "%",))

    today_count = c.fetchone()[0] or 0

    conn.close()

    return render_template(
        "dashboard.html",
        data=data,
        total=final_total,
        payment_stat=payment_stat,
        today_profit=today_profit,
        today_count=today_count
    )


# ================= ADD (FIXED BALANCE BEFORE/AFTER) =================
@app.route("/add", methods=["POST"])
def add():
    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    note = request.form["note"]

    # OUT = negative
    if payment == "OUT":
        amount = -abs(amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # get current system balance (NOT per user bug fix)
    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions")
    tx_total = c.fetchone()[0] or 0

    current_balance = credit + tx_total

    before = current_balance
    after = before + amount

    c.execute("""
        INSERT INTO transactions
        (account,amount,payment,note,balance_before,balance_after,created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account,amount,payment,note,before,after,now()))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ================= SET CREDIT =================
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


# ================= HISTORY =================
@app.route("/history")
def history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("history.html", data=data)


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))