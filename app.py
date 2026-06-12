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

def today():
    return datetime.now().strftime("%Y-%m-%d")

# ================= INIT =================
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
    CREATE TABLE IF NOT EXISTS credit_base (
        account TEXT PRIMARY KEY,
        base REAL
    )
    """)

    c.execute("SELECT * FROM users WHERE username=?", ("huat888",))
    if not c.fetchone():
        c.execute("INSERT INTO users (username,password) VALUES (?,?)",
                  ("huat888", "Aaa8888"))

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

    # 最近记录
    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    data = c.fetchall()

    # credit（唯一控制总余额）
    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    # 今日交易
    c.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today() + "%",))
    today_profit = c.fetchone()[0] or 0

    c.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today() + "%",))
    today_count = c.fetchone()[0] or 0

    # 付款统计
    c.execute("""
        SELECT payment, SUM(amount)
        FROM transactions
        GROUP BY payment
    """)
    payment_stat = dict(c.fetchall())

    conn.close()

    return render_template(
        "dashboard.html",
        data=data,
        total=credit,              # 🔥 关键：总余额 = credit（不再混tx）
        today_profit=today_profit,
        today_count=today_count,
        payment_stat=payment_stat
    )

# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    note = request.form["note"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 当前credit
    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    # 强制统一扣减逻辑
    amount = -abs(amount)

    before = credit
    after = before + amount

    # 写入交易
    c.execute("""
        INSERT INTO transactions
        (account,amount,payment,note,balance_before,balance_after,created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account,amount,payment,note,before,after,now()))

    # 更新 credit_base（关键修复点）
    c.execute("DELETE FROM credit_base")
    c.execute("INSERT INTO credit_base VALUES (?,?)", ("MAIN", after))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= CREDIT =================
@app.route("/set_credit", methods=["POST"])
def set_credit():
    credit = float(request.form["credit"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM credit_base")
    c.execute("INSERT INTO credit_base VALUES (?,?)", ("MAIN", credit))

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

# ================= REPORT =================
@app.route("/report")
def report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today() + "%",))

    total = c.fetchone()[0] or 0

    conn.close()

    return render_template("report.html", total=total)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))