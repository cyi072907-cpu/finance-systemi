from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "secret_key_123"

DB = "data.db"

def get_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        amount REAL,
        payment TEXT,
        remark TEXT,
        balance REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS balance (
        id INTEGER PRIMARY KEY,
        total REAL
    )
    """)

    c.execute("INSERT OR IGNORE INTO balance (id, total) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_balance():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT total FROM balance WHERE id=1")
    bal = c.fetchone()[0]
    conn.close()
    return bal

def update_balance(amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE balance SET total = total + ? WHERE id=1", (amount,))
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "Wrong password"
    return '''
    <form method="POST">
        <input name="password" type="password" placeholder="Password">
        <button type="submit">Login</button>
    </form>
    '''

@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("index.html", data=data, balance=get_balance())

@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    amount = float(request.form["amount"])
    payment = request.form["payment"]
    remark = request.form["remark"]

    # 模式1规则
    update_balance(amount)

    bal = get_balance()
    time = get_time()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO records (time, amount, payment, remark, balance)
    VALUES (?, ?, ?, ?, ?)
    """, (time, amount, payment, remark, bal))
    conn.commit()
    conn.close()

    return redirect("/home")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
