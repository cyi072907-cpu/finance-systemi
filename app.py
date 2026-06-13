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

    conn.close()


init_db()


@app.route("/")
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

    balance = 0

    last_record = conn.execute("""
        SELECT *
        FROM records
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if last_record:
        balance = last_record["after_balance"]

    conn.close()

    return render_template(
        "dashboard.html",
        balance=balance,
        records=records
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

    before_balance = 0

    if last:
        before_balance = last["after_balance"]

    after_balance = before_balance - amount

    malaysia_time = datetime.now(TIMEZONE).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

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


if __name__ == "__main__":
    app.run(debug=True)