from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "dev-secret-key"
DB = "database.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT,
            item_description TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            amount REAL NOT NULL,
            bill_date TEXT NOT NULL,
            due_date TEXT,
            payment_mode TEXT DEFAULT 'Cash',
            status TEXT DEFAULT 'Unpaid'
        )
    """)
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()
    total_bills = conn.execute("SELECT COUNT(*) c FROM bills").fetchone()["c"]
    total_amount = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM bills").fetchone()["s"]
    paid_amount = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM bills WHERE status='Paid'").fetchone()["s"]
    unpaid_amount = total_amount - paid_amount
    recent_bills = conn.execute("SELECT * FROM bills ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template(
        "index.html",
        total_bills=total_bills,
        total_amount=total_amount,
        paid_amount=paid_amount,
        unpaid_amount=unpaid_amount,
        recent_bills=recent_bills,
    )


@app.route("/bills")
def bills():
    query = request.args.get("q", "").strip()
    conn = get_db()
    if query:
        rows = conn.execute(
            "SELECT * FROM bills WHERE customer_name LIKE ? OR item_description LIKE ? ORDER BY id DESC",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM bills ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("bills.html", bills=rows, query=query)


@app.route("/bills/add", methods=["GET", "POST"])
def add_bill():
    if request.method == "POST":
        customer_name = request.form["customer_name"]
        phone = request.form.get("phone", "")
        item_description = request.form["item_description"]
        quantity = request.form.get("quantity", 1)
        amount = request.form["amount"]
        bill_date = request.form.get("bill_date") or str(date.today())
        due_date = request.form.get("due_date", "")
        payment_mode = request.form.get("payment_mode", "Cash")

        conn = get_db()
        conn.execute(
            """INSERT INTO bills
               (customer_name, phone, item_description, quantity, amount, bill_date, due_date, payment_mode, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Unpaid')""",
            (customer_name, phone, item_description, quantity, amount, bill_date, due_date, payment_mode),
        )
        conn.commit()
        conn.close()
        flash("Bill created successfully.")
        return redirect(url_for("bills"))

    return render_template("add_bill.html", today=str(date.today()))


@app.route("/bills/<int:bill_id>")
def bill_details(bill_id):
    conn = get_db()
    bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    conn.close()
    if bill is None:
        flash("Bill not found.")
        return redirect(url_for("bills"))
    return render_template("bill_details.html", bill=bill)


@app.route("/bills/<int:bill_id>/mark-paid", methods=["POST"])
def mark_paid(bill_id):
    conn = get_db()
    conn.execute("UPDATE bills SET status='Paid' WHERE id=?", (bill_id,))
    conn.commit()
    conn.close()
    flash("Bill marked as paid.")
    return redirect(url_for("bill_details", bill_id=bill_id))


@app.route("/bills/<int:bill_id>/delete", methods=["POST"])
def delete_bill(bill_id):
    conn = get_db()
    conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))
    conn.commit()
    conn.close()
    flash("Bill deleted.")
    return redirect(url_for("bills"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
