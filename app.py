from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "data.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        account TEXT,
        type TEXT,
        amount REAL,
        before_amount REAL,
        after_amount REAL,
        remark TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template("index.html", data=data)

@app.route("/add", methods=["POST"])
def add():
    account = request.form["account"]
    type_ = request.form["type"]
    amount = float(request.form["amount"])
    before = float(request.form["before"])
    remark = request.form["remark"]

    after = before + amount if type_ == "入账" else before - amount
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO records (time, account, type, amount, before_amount, after_amount, remark)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (time, account, type_, amount, before, after, remark))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
