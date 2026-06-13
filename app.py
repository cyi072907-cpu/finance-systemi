from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "huat888_secret"

TIMEZONE = pytz.timezone("Asia/Kuala_Lumpur")


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        amount REAL,
        payment_method TEXT,
        before_balance REAL,
        after_balance REAL,
        remark TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY,
        target_balance REAL
    )
    """)

    conn.commit()

    user = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users(username,password) VALUES (?,?)",
            ("admin", "123456")
        )
        conn.commit()

    setting = conn.execute(
        "SELECT * FROM settings WHERE id=1"
    ).fetchone()

    if not setting:
        conn.execute(
            "INSERT INTO settings(id,target_balance) VALUES(1,5000)"
        )
        conn.commit()

    conn.close()


init_db()


@app.route(”/”)
def index():

if "user" not in session:
    return redirect("/login")
conn = get_db()
records = conn.execute("""
    SELECT *
    FROM records
    ORDER BY id DESC
    LIMIT 10
""").fetchall()
setting = conn.execute("""
    SELECT *
    FROM settings
    WHERE id=1
""").fetchone()
balance = setting["target_balance"]
last_record = conn.execute("""
    SELECT *
    FROM records
    ORDER BY id DESC
    LIMIT 1
""").fetchone()
if last_record:
    balance = last_record["after_balance"]
today = datetime.now(
    TIMEZONE
).strftime("%Y-%m-%d")
today_records = conn.execute("""
    SELECT *
    FROM records
    WHERE substr(created_at,1,10)=?
""", (today,)).fetchall()
income_total = 0
expense_total = 0
income_count = 0
expense_count = 0
for row in today_records:
    amount = row["amount"]
    if amount > 0:
        income_total += amount
        income_count += 1
    elif amount < 0:
        expense_total += abs(amount)
        expense_count += 1
transaction_count = len(today_records)
net_income = income_total - expense_total
conn.close()
return render_template(
    "dashboard.html",
    balance=balance,
    records=records,
    income_total=income_total,
    expense_total=expense_total,
    net_income=net_income,
    transaction_count=transaction_count,
    income_count=income_count,
    expense_count=expense_count
)


@app.route("/settings", methods=["GET", "POST"])
def settings():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":

        target_balance = float(
            request.form["target_balance"]
        )

        conn.execute("""
        UPDATE settings
        SET target_balance=?
        WHERE id=1
        """, (target_balance,))

        conn.commit()

    setting = conn.execute("""
    SELECT *
    FROM settings
    WHERE id=1
    """).fetchone()

    conn.close()

    return render_template(
        "settings.html",
        setting=setting
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect("/")

    return render_template("login.html")


@app.route("/add", methods=["POST"])
def add_record():

    if "user" not in session:
        return redirect("/login")

    account = request.form["account"]
    amount = float(request.form["amount"])
    payment_method = request.form["payment_method"]
    remark = request.form["remark"]

    conn = get_db()

    last = conn.execute("""
        SELECT *
        FROM records
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    setting = conn.execute("""
        SELECT *
        FROM settings
        WHERE id=1
    """).fetchone()

    before_balance = setting["target_balance"]

    if last:
        before_balance = last["after_balance"]

    after_balance = before_balance - amount

    malaysia_time = datetime.now(
        TIMEZONE
    ).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
    INSERT INTO records(
        account,
        amount,
        payment_method,
        before_balance,
        after_balance,
        remark,
        created_at
    )
    VALUES(?,?,?,?,?,?,?)
    """,
    (
        account,
        amount,
        payment_method,
        before_balance,
        after_balance,
        remark,
        malaysia_time
    ))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)