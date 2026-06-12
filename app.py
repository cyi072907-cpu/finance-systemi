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

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 记录
    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    data = c.fetchall()

    # 🔥 credit（手动设置总余额）
    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    # 🔥 所有交易
    c.execute("SELECT SUM(amount) FROM transactions")
    tx_total = c.fetchone()[0] or 0

    # ✔ 总余额（核心修复）
    total_balance = credit + tx_total

    # 🔥 今日盈亏（修复关键）
    c.execute("""
        SELECT SUM(amount)
        FROM transactions
        WHERE created_at LIKE ?
    """, (today() + "%",))
    today_profit = c.fetchone()[0] or 0

    # 今日交易
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
    payment_stat = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        data=data,
        total=total_balance,
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

    c.execute("SELECT SUM(base) FROM credit_base")
    credit = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions")
    tx_total = c.fetchone()[0] or 0

    before = credit + tx_total

    amount = -abs(amount)  # 默认扣钱

    after = before + amount

    c.execute("""
        INSERT INTO transactions
        (account,amount,payment,note,balance_before,balance_after,created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (account, amount, payment, note, before, after, now()))

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

    c.execute("INSERT OR REPLACE INTO credit_base VALUES (?,?)", (account, credit))

    conn.commit()
    conn.close()

    return redirect("/dashboard")