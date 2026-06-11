from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"


# ================= SAFE DB INIT =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 交易表（自动兼容旧数据库）
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

    # credit 表
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
        <input name='password' type='password'>
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


# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form.get("account", "")
    amount = float(request.form.get("amount", 0))
    payment = request.form.get("payment", "")
    remark = request.form.get("remark", "")

    # credit 更新
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


# ================= REPORT =================
@app.route("/reports")
def reports():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM records")
    total = c.fetchone()[0] or 0

    c.execute("SELECT payment, SUM(amount) FROM records GROUP BY payment")
    payment_stats = c.fetchall()

    conn.close()

    return render_template(
        "reports.html",
        total=total,
        credit=get_credit(),
        payment_stats=payment_stats
    )


# ================= SEARCH =================
@app.route("/search", methods=["GET", "POST"])
def search():
    if not session.get("login"):
        return redirect("/")

    results = []

    if request.method == "POST":
        d = request.form["date"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("""
        SELECT * FROM records
        WHERE date(time)=?
        ORDER BY id DESC
        """, (d,))

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
