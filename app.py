from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
app.secret_key = "V5PRO_ENTERPRISE"

DB = "data.db"

# ================= TIME =================
def now():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz)

def fmt():
    return now().strftime("%Y-%m-%d %H:%M:%S")

# ================= DB =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY,
        account TEXT,
        amount REAL,
        payment TEXT,
        note TEXT,
        before_balance REAL,
        after_balance REAL,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS balance(
        account TEXT PRIMARY KEY,
        amount REAL
    )
    """)

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
        user = c.fetchone()
        conn.close()

        if user:
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

    c.execute("SELECT amount FROM balance WHERE account=?", (account,))
    row = c.fetchone()
    before = row[0] if row else 0

    after = before + amount

    c.execute("""
        INSERT INTO transactions VALUES(NULL,?,?,?,?,?,?,?)
    """,(account,amount,payment,note,before,after,fmt()))

    c.execute("INSERT OR REPLACE INTO balance VALUES(?,?)",(account,after))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= PAYMENT EDIT =================
@app.route("/edit_payment/<int:id>/<payment>")
def edit_payment(id,payment):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE transactions SET payment=? WHERE id=?", (payment,id))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= BALANCE CONTROL =================
@app.route("/balance_update", methods=["POST"])
def balance_update():
    account = request.form["account"]
    amount = float(request.form["amount"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO balance VALUES(?,?)",(account,amount))
    conn.commit()
    conn.close()

    return redirect("/balance")

@app.route("/balance")
def balance():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM balance")
    data = c.fetchall()
    conn.close()
    return render_template("balance.html", data=data)

# ================= HISTORY (DATE RANGE) =================
@app.route("/history", methods=["GET","POST"])
def history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        start = request.form["start"]
        end = request.form["end"]

        c.execute("""
        SELECT * FROM transactions
        WHERE created_at BETWEEN ? AND ?
        ORDER BY id DESC
        """,(start,end))
    else:
        limit = (now()-timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("SELECT * FROM transactions WHERE created_at>=?",(limit,))

    data = c.fetchall()
    conn.close()

    return render_template("history.html", data=data)

# ================= REPORT ENGINE =================
@app.route("/report")
def report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM transactions WHERE amount>0")
    income = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions WHERE amount<0")
    expense = c.fetchone()[0] or 0

    profit = income + expense

    c.execute("SELECT payment, SUM(amount) FROM transactions GROUP BY payment")
    breakdown = c.fetchall()

    conn.close()

    return render_template("report.html",
        income=income,
        expense=expense,
        profit=profit,
        breakdown=breakdown
    )

# ================= CLEAN =================
def clean():
    limit = (now()-timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE created_at<?",(limit,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))