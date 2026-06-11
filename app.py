import os
import sqlite3
from datetime import datetime, date
from flask import Flask, request, redirect, render_template_string, session

app = Flask(__name__)
app.secret_key = "v7_secret_key"

# ================= TOKEN（只留环境变量） =================
BOT_TOKEN = os.environ.get("BOT8660820217:AAFCfgnb_J6c7AdB6j2OABIkHNtqE4flHxo")

# ================= DB =================
DB = "finance.db"

def db():
    return sqlite3.connect(DB)

def init():
    conn = db()
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

init()

# ================= TIME =================
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today():
    return datetime.now().strftime("%Y-%m-%d")

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "1234":
            session["ok"] = True
            return redirect("/home")
        return "密码错误"

    return """
    <h2>Login V7</h2>
    <form method="post">
        <input name="password">
        <button>进入</button>
    </form>
    """

# ================= CALC =================
def profit_all():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT amount, type FROM records")
    rows = c.fetchall()
    conn.close()

    total = 0
    for a, t in rows:
        if t == "in":
            total += a
        else:
            total -= a
    return total

def profit_today():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT amount, type FROM records WHERE time LIKE ?", (today()+"%",))
    rows = c.fetchall()
    conn.close()

    total = 0
    for a, t in rows:
        if t == "in":
            total += a
        else:
            total -= a
    return total

# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("ok"):
        return redirect("/")

    q = request.args.get("q", "")

    conn = db()
    c = conn.cursor()

    if q:
        c.execute("SELECT * FROM records WHERE account LIKE ? ORDER BY id DESC", ("%"+q+"%",))
    else:
        c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 50")

    rows = c.fetchall()
    conn.close()

    html = """
    <h2>💰 V7 财务系统</h2>

    <h3>📊 总盈亏：{{total}}</h3>
    <h3>📅 今日盈亏：{{today}}</h3>

    <hr>

    <form action="/add" method="post">
        账号 <input name="account"><br>
        金额 <input name="amount"><br>
        类型
        <select name="type">
            <option value="in">收入(+)</option>
            <option value="out">支出(-)</option>
        </select><br>
        备注 <input name="remark"><br>
        <button>提交</button>
    </form>

    <hr>

    <form method="get">
        搜索账号：<input name="q">
        <button>搜索</button>
    </form>

    <hr>

    <h3>📜 记录</h3>
    <table border="1">
        <tr>
            <th>ID</th><th>账号</th><th>金额</th><th>类型</th><th>备注</th><th>时间</th><th>操作</th>
        </tr>

        {% for r in rows %}
        <tr>
            <td>{{r[0]}}</td>
            <td>{{r[1]}}</td>
            <td>{{r[2]}}</td>
            <td>{{r[3]}}</td>
            <td>{{r[4]}}</td>
            <td>{{r[5]}}</td>
            <td><a href="/delete/{{r[0]}}">删除</a></td>
        </tr>
        {% endfor %}
    </table>
    """

    return render_template_string(
        html,
        rows=rows,
        total=profit_all(),
        today=profit_today()
    )

# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("ok"):
        return redirect("/")

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO records (account, amount, type, remark, time)
    VALUES (?,?,?,?,?)
    """, (
        request.form["account"],
        float(request.form["amount"]),
        request.form["type"],
        request.form["remark"],
        now()
    ))

    conn.commit()
    conn.close()

    return redirect("/home")

# ================= DELETE =================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("ok"):
        return redirect("/")

    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/home")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)