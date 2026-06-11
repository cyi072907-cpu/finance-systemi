import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, render_template_string, session

app = Flask(__name__)
app.secret_key = "v6_secret_key"

# ================= BOT TOKEN =================
BOT_TOKEN = os.environ.get("8660820217:AAFCfgnb_J6c7AdBlkHNtqE4flHxo")  # Render 里填

# ================= DATABASE =================
DB = "data.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        amount REAL,
        type TEXT,
        remark TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= TIME =================
def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_start():
    return datetime.now().strftime("%Y-%m-%d")

# ================= PROFIT =================
def calc_profit():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT amount, type FROM records")
    rows = c.fetchall()
    conn.close()

    profit = 0
    for amount, t in rows:
        if t == "in":
            profit += amount
        else:
            profit -= amount

    return profit

# ================= LOGIN (简单版) =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "1234":
            session["login"] = True
            return redirect("/home")
        return "密码错误"

    return """
    <h2>Login</h2>
    <form method="post">
        <input name="password" placeholder="密码">
        <button>进入</button>
    </form>
    """

# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()

    profit = calc_profit()

    html = """
    <h2>📊 资金系统 V6</h2>

    <h3>💰 当前盈亏：{{profit}}</h3>

    <hr>

    <h3>➕ 新增记录</h3>
    <form method="post" action="/add">
        账号：<input name="account"><br><br>
        金额：<input name="amount"><br><br>
        类型：
        <select name="type">
            <option value="in">收入(+)</option>
            <option value="out">支出(-)</option>
        </select><br><br>
        备注：<input name="remark"><br><br>
        <button>提交</button>
    </form>

    <hr>

    <h3>📜 历史记录</h3>
    <table border="1" cellpadding="5">
        <tr>
            <th>ID</th>
            <th>账号</th>
            <th>金额</th>
            <th>类型</th>
            <th>备注</th>
            <th>时间</th>
        </tr>
        {% for r in rows %}
        <tr>
            <td>{{r[0]}}</td>
            <td>{{r[1]}}</td>
            <td>{{r[2]}}</td>
            <td>{{r[3]}}</td>
            <td>{{r[4]}}</td>
            <td>{{r[5]}}</td>
        </tr>
        {% endfor %}
    </table>
    """

    return render_template_string(html, rows=rows, profit=profit)

# ================= ADD RECORD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form["account"]
    amount = float(request.form["amount"])
    t = request.form["type"]
    remark = request.form["remark"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO records (account, amount, type, remark, time)
        VALUES (?,?,?,?,?)
    """, (account, amount, t, remark, now_time()))

    conn.commit()
    conn.close()

    return redirect("/home")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)