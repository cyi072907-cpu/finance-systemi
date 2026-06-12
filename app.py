from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
app.secret_key = "huat888_final"

DB = "data.db"

# ================= TIME =================
def now():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# ================= INIT DB =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
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
    CREATE TABLE IF NOT EXISTS balance (
        account TEXT PRIMARY KEY,
        credit REAL
    )
    """)

    # default user
    c.execute("SELECT * FROM users WHERE username='huat888'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?)", ("huat888", "Aaa8888"))

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

    c.execute("SELECT credit FROM balance WHERE account=?", (account,))
    row = c.fetchone()
    old = row[0] if row else 0

    new = old + amount

    c.execute("""
        INSERT INTO transactions
        (account, amount, payment, note, balance_before, balance_after, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account, amount, payment, note, old, new, now()))

    c.execute("INSERT OR REPLACE INTO balance VALUES (?,?)", (account, new))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= UPDATE PAYMENT =================
@app.route("/update_payment/<int:id>/<pay>")
def update_payment(id, pay):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE transactions SET payment=? WHERE id=?", (pay,id))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= BALANCE =================
@app.route("/balance", methods=["GET","POST"])
def balance():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        account = request.form["account"]
        credit = float(request.form["credit"])
        c.execute("INSERT OR REPLACE INTO balance VALUES (?,?)", (account, credit))
        conn.commit()

    c.execute("SELECT * FROM balance")
    data = c.fetchall()
    conn.close()

    return render_template("balance.html", data=data)

# ================= HISTORY =================
@app.route("/history")
def history():
    limit = datetime.now() - timedelta(days=90)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE created_at>=? ORDER BY id DESC",
              (limit.strftime("%Y-%m-%d %H:%M:%S"),))

    data = c.fetchall()
    conn.close()

    return render_template("history.html", data=data)

# ================= REPORT =================
@app.route("/report")
def report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM transactions")
    total = c.fetchone()[0] or 0

    c.execute("SELECT payment, SUM(amount) FROM transactions GROUP BY payment")
    payment = c.fetchall()

    return render_template("report.html", total=total, payment=payment)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))