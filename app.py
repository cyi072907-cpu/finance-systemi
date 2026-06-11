from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB = "data.db"

# =========================
# DB INIT
# =========================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT,
            amount REAL,
            type TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# HOME
# =========================
@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM records ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    balance = 0
    records = []

    for r in rows:
        rid, account, amount, rtype, time = r
        amount = float(amount)

        # ✅ 核心修复：盈亏统一逻辑
        if rtype == "in":
            balance += amount
        elif rtype == "out":
            balance -= amount

        records.append({
            "id": rid,
            "account": account,
            "amount": amount,
            "type": rtype,
            "time": time,
            "balance": balance
        })

    return render_template("index.html", records=records, balance=balance)

# =========================
# ADD RECORD
# =========================
@app.route("/add", methods=["POST"])
def add():
    account = request.form.get("account", "").strip()
    amount = request.form.get("amount", "0")
    rtype = request.form.get("type", "in")

    try:
        amount = float(amount)
    except:
        amount = 0

    if amount < 0:
        amount = abs(amount)

    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO records (account, amount, type, time) VALUES (?, ?, ?, ?)",
        (account, amount, rtype, time)
    )
    conn.commit()
    conn.close()

    return redirect("/")

# =========================
# DELETE
# =========================
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# =========================
# RENDER START
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)