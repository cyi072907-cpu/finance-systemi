from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# =========================
# DATABASE
# =========================
DB = "data.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT,
            amount REAL,
            type TEXT,
            note TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# HOME PAGE（简洁中文界面）
# =========================
@app.route("/")
def home():
    return render_template_string("""
    <h2>💰 资金管理系统 V5 FINAL</h2>

    <form method="POST" action="/add">
        账号: <input name="account"><br><br>
        金额: <input name="amount" type="number" step="0.01"><br><br>
        类型:
        <select name="type">
            <option value="in">入金</option>
            <option value="out">出金</option>
        </select><br><br>
        备注: <input name="note"><br><br>
        <button type="submit">提交</button>
    </form>

    <hr>
    <a href="/history">📜 查看历史</a> |
    <a href="/balance">💰 查看余额</a>
    """)

# =========================
# ADD RECORD
# =========================
@app.route("/add", methods=["POST"])
def add():
    account = request.form.get("account")
    amount = float(request.form.get("amount"))
    ttype = request.form.get("type")
    note = request.form.get("note")

    # ❗修复 -50 bug：统一逻辑
    if ttype == "out":
        amount = -abs(amount)
    else:
        amount = abs(amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions (account, amount, type, note, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (account, amount, ttype, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return "OK 已记录"

# =========================
# HISTORY
# =========================
@app.route("/history")
def history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    html = "<h2>📜 历史记录</h2>"
    html += "<a href='/'>返回</a><br><br>"

    html += "<table border='1' cellpadding='5'>"
    html += "<tr><th>ID</th><th>账号</th><th>金额</th><th>类型</th><th>备注</th><th>时间</th></tr>"

    for row in data:
        html += f"<tr>{''.join([f'<td>{i}</td>' for i in row])}</tr>"

    html += "</table>"
    return html

# =========================
# BALANCE（修复 -50 bug 核心）
# =========================
@app.route("/balance")
def balance():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT account, SUM(amount) FROM transactions GROUP BY account")
    data = c.fetchall()
    conn.close()

    html = "<h2>💰 余额</h2><a href='/'>返回</a><br><br>"

    total_all = 0

    for account, total in data:
        total = total or 0
        total_all += total
        html += f"<p>账号 {account}：RM {round(total,2)}</p>"

    html += f"<hr><h3>总余额：RM {round(total_all,2)}</h3>"
    return html

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)