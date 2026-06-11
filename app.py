from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"


# ---------------- INIT ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        account TEXT,
        amount REAL,
        payment TEXT,
        remark TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        credit REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        profit REAL,
        summary TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week TEXT,
        profit REAL,
        summary TEXT
    )
    """)

    c.execute("INSERT OR IGNORE INTO settings (id, credit) VALUES (1, 0)")

    conn.commit()
    conn.close()


init_db()


# ---------------- CREDIT ----------------
def get_credit():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT credit FROM settings WHERE id=1")
    val = c.fetchone()[0]
    conn.close()
    return val


def update_credit(amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET credit = credit + ? WHERE id=1", (amount,))
    conn.commit()
    conn.close()


# ---------------- TIME ----------------
def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- DAILY REPORT ----------------
def generate_daily():
    today = date.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM records WHERE date(time)=?", (today,))
    profit = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM records WHERE date(time)=?", (today,))
    count = c.fetchone()[0]

    summary = f"交易数:{count}"

    c.execute("INSERT INTO daily_reports (date, profit, summary) VALUES (?,?,?)",
              (today, profit, summary))

    conn.commit()
    conn.close()


# ---------------- WEEKLY REPORT ----------------
def generate_weekly():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT SUM(amount) FROM records
        WHERE date(time) BETWEEN ? AND ?
    """, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

    profit = c.fetchone()[0] or 0

    summary = f"{start} - {end}"

    c.execute("INSERT INTO weekly_reports (week, profit, summary) VALUES (?,?,?)",
              (summary, profit, summary))

    conn.commit()
    conn.close()


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "密码错误"

    return """
    <form method='POST'>
        <input name='password' type='password'>
        <button>Login</button>
    </form>
    """


# ---------------- HOME ----------------
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    # 自动生成日报/周报（访问触发）
    generate_daily()
    generate_weekly()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("index.html", data=data, credit=get_credit())


# ---------------- ADD ----------------
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    remark = request.form["remark"]

    update_credit(amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO records (time, account, amount, payment, remark)
        VALUES (?,?,?,?,?)
    """, (now_time(), account, amount, payment, remark))
    conn.commit()
    conn.close()

    return redirect("/home")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
