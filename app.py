from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"


# ================= DB INIT =================
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

    c.execute("INSERT OR IGNORE INTO settings (id, credit) VALUES (1, 0)")

    conn.commit()
    conn.close()


init_db()


# ================= CREDIT =================
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


# ================= TIME =================
def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "密码错误"

    return """
    <form method='POST'>
        <input name='password' type='password' placeholder='Password'>
        <button>Login</button>
    </form>
    """


# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("index.html", data=data, credit=get_credit())


# ================= ADD RECORD =================
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


# ================= REPORT PAGE =================
@app.route("/reports")
def reports():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 今日盈亏
    c.execute("SELECT SUM(amount) FROM records WHERE date(time)=date('now','localtime')")
    today_profit = c.fetchone()[0] or 0

    # 本周盈亏
    c.execute("""
        SELECT SUM(amount) FROM records
        WHERE date(time) >= date('now','weekday 1','-7 days')
    """)
    week_profit = c.fetchone()[0] or 0

    # 付款方式统计
    c.execute("SELECT payment, SUM(amount) FROM records GROUP BY payment")
    payment_stats = c.fetchall()

    conn.close()

    return render_template(
        "reports.html",
        today_profit=today_profit,
        week_profit=week_profit,
        credit=get_credit(),
        payment_stats=payment_stats
    )


# ================= SEARCH PAGE =================
@app.route("/search", methods=["GET", "POST"])
def search():
    if not session.get("login"):
        return redirect("/")

    results = []

    if request.method == "POST":
        query_date = request.form["date"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("""
            SELECT * FROM records
            WHERE date(time)=?
            ORDER BY id DESC
        """, (query_date,))

        results = c.fetchall()
        conn.close()

    return render_template("search.html", results=results)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
