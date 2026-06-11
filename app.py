from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = "Aaa8888"

DB = "data.db"

# ================= TIME =================
def now_time():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


# ================= INIT =================
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        time TEXT
    )
    """)

    default = [
        ("credit", 5000),
        ("open_credit", 5000),
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


# ================= HELPERS =================
def get_value(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    v = c.fetchone()[0]
    conn.close()
    return v


def update_value(key, amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = value + ? WHERE key=?", (amount, key))
    conn.commit()
    conn.close()


def log(action):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (action, time) VALUES (?,?)", (action, now_time()))
    conn.commit()
    conn.close()


# ================= DAILY OPEN =================
def set_open():
    today = now_time()[:10]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT value FROM settings WHERE key='open_credit'")
    open_credit = c.fetchone()[0]

    c.execute("SELECT value FROM settings WHERE key='credit'")
    credit = c.fetchone()[0]

    c.execute("SELECT action FROM logs ORDER BY id DESC LIMIT 1")
    last = c.fetchone()

    if not last or today not in last[0]:
        c.execute("UPDATE settings SET value=? WHERE key='open_credit'", (credit,))
        conn.commit()

    conn.close()


# ================= PROFIT =================
def calc_profit():
    open_credit = get_value("open_credit")
    current = get_value("credit")
    return open_credit - current


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        log(f"LOGIN {username}")

        if password == "Aaa8888":
            session["login"] = True
            return redirect("/home")

        return "密码错误"

    return render_template("login.html")


# ================= HOME =================
@app.route("/home")
def home():
    if not session.get("login"):
        return redirect("/")

    set_open()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    data = c.fetchall()

    def get(k):
        c.execute("SELECT value FROM settings WHERE key=?", (k,))
        return c.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        data=data,
        credit=get("credit"),
        tng=get("tng"),
        cash=get("cash"),
        bank=get("bank"),
        a=get("a"),
        profit=calc_profit()
    )


# ================= ADD =================
@app.route("/add", methods=["POST"])
def add():
    if not session.get("login"):
        return redirect("/")

    account = request.form["account"]
    amount = float(request.form["amount"])
    payment = request.form["payment"]
    remark = request.form["remark"]

    update_value("credit", -amount)
    update_value(payment.lower(), amount)

    log(f"ADD {account} {amount}")

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

        update_value("credit", amount)
        update_value(payment.lower(), -amount)

        log(f"DELETE {id}")

        c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/home")


# ================= REPORTS =================
@app.route("/report/daily")
def daily():
    if not session.get("login"):
        return redirect("/")

    today = now_time()[:10] + " 00:00:00"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT account, amount, payment, time FROM records WHERE time>=?", (today,))
    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Daily")


@app.route("/report/weekly")
def weekly():
    if not session.get("login"):
        return redirect("/")

    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT account, amount, payment, time FROM records WHERE time>=?", (start,))
    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Weekly")


@app.route("/report/monthly")
def monthly():
    if not session.get("login"):
        return redirect("/")

    month = now_time()[:7]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT account, amount, payment, time FROM records WHERE time LIKE ?", (month+"%",))
    data = c.fetchall()
    conn.close()

    return render_template("reports.html", data=data, title="Monthly")


# ================= HISTORY =================
@app.route("/history", methods=["GET", "POST"])
def history():
    if not session.get("login"):
        return redirect("/")

    data = []

    if request.method == "POST":
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        query = "SELECT account, amount, payment, time FROM records WHERE 1=1"
        params = []

        if request.form.get("account"):
            query += " AND account=?"
            params.append(request.form["account"])

        if request.form.get("payment"):
            query += " AND payment=?"
            params.append(request.form["payment"])

        query += " ORDER BY id DESC"

        c.execute(query, params)
        data = c.fetchall()
        conn.close()

    return render_template("history.html", data=data)


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)