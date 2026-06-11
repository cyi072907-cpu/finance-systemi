from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        amount REAL,
        payment TEXT,
        remark TEXT,
        time TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value REAL
    )
    """)

    default = [
        ("credit", 5000),
        ("tng", 0),
        ("cash", 0),
        ("bank", 0),
        ("a", 0)
    ]

    for k, v in default:
        c.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()

init_db()


# ================= GET VALUE =================
def get_value(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    v = c.fetchone()[0]
    conn.close()
    return v


# ================= UPDATE VALUE =================
def update_value(key, amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = value + ? WHERE key=?", (amount, key))
    conn.commit()
    conn.close()


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "Aaa8888":
            session["login"] = True
            return redirect("/home")
        return "密码错误"

    return render_template("login.html")


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

    return render_template("index.html", data=data, credit=get_value("credit"))


# ================= ADD RECORD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    remark = request.form["remark"]

    # ================= LOGIC =================
    # A模式：
    # +100 -> credit -100
    # -100 -> credit +100

    credit_change = -amount

    update_value("credit", credit_change)
    update_value(payment.lower(), amount)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO records (account, amount, payment, remark, time)
        VALUES (?,?,?,?,?)
    """, (account, amount, payment, remark, now_time()))

    conn.commit()
    conn.close()

    return redirect("/home")


# ================= DELETE =================
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT amount, payment FROM records WHERE id=?", (id,))
    row = c.fetchone()

    if row:
        amount, payment = row

        # rollback
        update_value("credit", amount)
        update_value(payment.lower(), -amount)

        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    def get_range_data(start_time):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT account, amount, payment, time
        FROM records
        WHERE time >= ?
        ORDER BY id DESC
    """, (start_time,))

    data = c.fetchall()
    conn.close()
    return data
    @app.route("/report/daily")
def daily_report():
    if not session.get("login"):
        return redirect("/")

    today = now_time()[:10] + " 00:00:00"
    data = get_range_data(today)

    return render_template("reports.html", data=data, title="Daily Report")
    @app.route("/report/weekly")
def weekly_report():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT account, amount, payment, time
        FROM records
        ORDER BY id DESC
    """)

    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Weekly Report")
    @app.route("/report/monthly")
def monthly_report():
    if not session.get("login"):
        return redirect("/")

    month = now_time()[:7]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT account, amount, payment, time
        FROM records
        WHERE time LIKE ?
        ORDER BY id DESC
    """, (month + "%",))

    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Monthly Report")
    
    @app.route("/history", methods=["GET", "POST"])
def history():
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    data = []

    if request.method == "POST":
        account = request.form.get("account")
        payment = request.form.get("payment")
        start = request.form.get("start")
        end = request.form.get("end")

        query = "SELECT account, amount, payment, time FROM records WHERE 1=1"
        params = []

        if account:
            query += " AND account=?"
            params.append(account)

        if payment:
            query += " AND payment=?"
            params.append(payment)

        if start:
            query += " AND time>=?"
            params.append(start)

        if end:
            query += " AND time<=?"
            params.append(end)

        query += " ORDER BY id DESC"

        c.execute(query, params)
        data = c.fetchall()

    conn.close()

    return render_template("history.html", data=data)
    @app.route("/delete/<int:id>")
def delete(id):
    if not session.get("login"):
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT amount, payment FROM records WHERE id=?", (id,))
    row = c.fetchone()

    if row:
        amount, payment = row

        # rollback
        update_value("credit", amount)
        update_value(payment.lower(), -amount)

        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")