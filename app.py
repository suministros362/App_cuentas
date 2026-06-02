from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "gastos.sqlite3"
DEFAULT_EXPENSES = ["alquiler", "luz", "gas", "agua", "patente"]
MONTH_NAMES = {
    "ene": "01",
    "feb": "02",
    "mar": "03",
    "abr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "ago": "08",
    "sep": "09",
    "set": "09",
    "oct": "10",
    "nov": "11",
    "dic": "12",
}

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                payment_method TEXT NOT NULL DEFAULT 'Efectivo',
                source TEXT NOT NULL DEFAULT 'Manual',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                destination TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        migrate_db(conn)
        conn.commit()


def migrate_db(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]: row for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    }

    if "source" not in columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN source TEXT NOT NULL DEFAULT 'Manual'")

    if "month" not in columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN month TEXT")
        conn.execute("UPDATE expenses SET month = substr(date, 1, 7) WHERE month IS NULL")

    if "category" not in columns:
        conn.execute("UPDATE expenses SET month = substr(date, 1, 7) WHERE month IS NULL")
        return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            payment_method TEXT NOT NULL DEFAULT 'Efectivo',
            source TEXT NOT NULL DEFAULT 'Manual',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO expenses_new
            (id, month, date, description, amount, payment_method, source, created_at)
        SELECT id, COALESCE(month, substr(date, 1, 7)), date, description, amount, payment_method, source, created_at
        FROM expenses
        """
    )
    conn.execute("DROP TABLE expenses")
    conn.execute("ALTER TABLE expenses_new RENAME TO expenses")


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "month": row["month"],
        "date": row["date"],
        "description": row["description"],
        "amount": row["amount"],
        "payment_method": row["payment_method"],
        "source": row["source"],
        "created_at": row["created_at"],
    }


def transfer_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "month": row["date"][:7],
        "date": row["date"],
        "destination": row["destination"],
        "amount": row["amount"],
        "created_at": row["created_at"],
    }


def validate_expense(data: dict) -> tuple[dict | None, tuple[dict, int] | None]:
    required = ["month", "date", "description", "amount"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]

    if missing:
        return None, ({"error": "Completa todos los campos obligatorios."}, 400)

    try:
        amount = float(str(data["amount"]).replace(",", "."))
    except (TypeError, ValueError):
        return None, ({"error": "El importe debe ser un numero valido."}, 400)

    if amount <= 0:
        return None, ({"error": "El importe debe ser mayor a cero."}, 400)

    return (
        {
            "date": data["date"].strip(),
            "month": data["month"].strip(),
            "description": data["description"].strip(),
            "amount": amount,
            "payment_method": "Manual",
            "source": "Manual",
        },
        None,
    )


def validate_transfer(data: dict) -> tuple[dict | None, tuple[dict, int] | None]:
    required = ["date", "destination", "amount"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]

    if missing:
        return None, ({"error": "Completa todos los campos obligatorios."}, 400)

    destination = data["destination"].strip()
    if destination not in {"Banco Nacion", "Mercado Pago"}:
        return None, ({"error": "Selecciona un destino valido."}, 400)

    try:
        amount = float(str(data["amount"]).replace(",", "."))
    except (TypeError, ValueError):
        return None, ({"error": "El importe debe ser un numero valido."}, 400)

    if amount <= 0:
        return None, ({"error": "El importe debe ser mayor a cero."}, 400)

    return (
        {
            "date": data["date"].strip(),
            "destination": destination,
            "amount": amount,
        },
        None,
    )


def parse_amount(value: str, keep_sign: bool = False) -> float | None:
    cleaned = re.sub(r"[^\d,.-]", "", value).strip()
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        amount = float(cleaned)
    except ValueError:
        return None

    if not keep_sign:
        amount = abs(amount)

    return amount if amount > 0 else None


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def parse_visa_expenses(text: str, month: str) -> list[dict]:
    expenses: list[dict] = []
    transaction_pattern = re.compile(
        r"^"
        r"(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{2})\s+"
        r"(?:(?P<receipt>\d{6})\s+)?"
        r"(?P<description>.+?)\s+"
        r"(?P<pesos>-?\d{1,3}(?:\.\d{3})*,\d{2})\s+"
        r"(?P<dollar>-?\d{1,3}(?:\.\d{3})*,\d{2})"
        r"$"
    )

    for line in text.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            continue

        match = transaction_pattern.match(normalized)
        if not match:
            continue

        amount = parse_amount(match.group("pesos"), keep_sign=True)
        if amount is None:
            continue

        description = match.group("description").strip(" -:|")
        lowered = description.lower()
        if lowered.startswith("su pago") or "total consumos" in lowered:
            continue

        expenses.append(
            {
                "month": month,
                "date": f"20{match.group('year')}-{match.group('month')}-{match.group('day')}",
                "description": description[:180],
                "amount": amount,
                "payment_method": "Manual",
                "source": "Manual",
            }
        )

    return expenses


def parse_master_expenses(text: str, month: str) -> list[dict]:
    expenses: list[dict] = []
    transaction_pattern = re.compile(
        r"^"
        r"(?P<day>\d{2})-(?P<month_name>[A-Za-zÁÉÍÓÚáéíóú]+)-(?P<year>\d{2})\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<receipt>\d{5})\s+"
        r"(?P<pesos>-?\d+(?:,\d{2})?)"
        r"$"
    )

    for line in text.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            continue

        match = transaction_pattern.match(normalized)
        if not match:
            continue

        amount = parse_amount(match.group("pesos"), keep_sign=True)
        if amount is None:
            continue

        month_key = match.group("month_name").lower()[:3]
        transaction_month = MONTH_NAMES.get(month_key)
        if not transaction_month:
            continue

        expenses.append(
            {
                "month": month,
                "date": f"20{match.group('year')}-{transaction_month}-{match.group('day')}",
                "description": match.group("description").strip(" -:|")[:180],
                "amount": amount,
                "payment_method": "Manual",
                "source": "Manual",
            }
        )

    return expenses


def parse_pdf_expenses(file_storage, card_type: str) -> list[dict]:
    reader = PdfReader(file_storage.stream)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Los resumenes importados se asignan al mes vigente al momento de subir el PDF.
    month = current_month()

    if card_type == "visa":
        return parse_visa_expenses(text, month)
    if card_type == "master":
        return parse_master_expenses(text, month)

    raise ValueError("Tipo de tarjeta invalido")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/expenses")
def list_expenses():
    date = request.args.get("date", "").strip()
    month = request.args.get("month", "").strip()
    search = request.args.get("q", "").strip()

    query = "SELECT * FROM expenses WHERE 1 = 1"
    params: list[str] = []

    if date:
        query += " AND date = ?"
        params.append(date)
    if month:
        query += " AND month = ?"
        params.append(month)
    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY date DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        total = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total FROM ({query})",
            params,
        ).fetchone()["total"]
        summary = conn.execute(
            """
            SELECT month, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
            """
        ).fetchall()

    return jsonify(
        {
            "expenses": [row_to_dict(row) for row in rows],
            "total": total,
            "summary": [dict(row) for row in summary],
            "defaults": DEFAULT_EXPENSES,
        }
    )


@app.get("/api/transfers")
def list_transfers():
    date = request.args.get("date", "").strip()
    month = request.args.get("month", "").strip() or current_month()

    query = "SELECT * FROM transfers WHERE substr(date, 1, 7) = ?"
    params: list[str] = [month]

    if date:
        query += " AND date = ?"
        params.append(date)

    query += " ORDER BY date DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        transfers_total = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total FROM ({query})",
            params,
        ).fetchone()["total"]
        expenses_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE month = ?",
            (month,),
        ).fetchone()["total"]
        half_expenses_total = expenses_total / 2

    return jsonify(
        {
            "transfers": [transfer_row_to_dict(row) for row in rows],
            "month": month,
            "total": transfers_total,
            "expenses_total": half_expenses_total,
            "full_expenses_total": expenses_total,
            "balance": half_expenses_total - transfers_total,
        }
    )


@app.post("/api/expenses")
def create_expense():
    data = request.get_json(silent=True) or {}
    expense, error = validate_expense(data)
    if error:
        return jsonify(error[0]), error[1]

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (month, date, description, amount, payment_method, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                expense["month"],
                expense["date"],
                expense["description"],
                expense["amount"],
                expense["payment_method"],
                expense["source"],
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return jsonify(row_to_dict(row)), 201


@app.post("/api/transfers")
def create_transfer():
    data = request.get_json(silent=True) or {}
    transfer, error = validate_transfer(data)
    if error:
        return jsonify(error[0]), error[1]

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transfers (date, destination, amount)
            VALUES (?, ?, ?)
            """,
            (
                transfer["date"],
                transfer["destination"],
                transfer["amount"],
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM transfers WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return jsonify(transfer_row_to_dict(row)), 201


@app.put("/api/expenses/<int:expense_id>")
def update_expense(expense_id: int):
    data = request.get_json(silent=True) or {}
    expense, error = validate_expense(data)
    if error:
        return jsonify(error[0]), error[1]

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE expenses
            SET month = ?, date = ?, description = ?, amount = ?, payment_method = ?, source = ?
            WHERE id = ?
            """,
            (
                expense["month"],
                expense["date"],
                expense["description"],
                expense["amount"],
                expense["payment_method"],
                expense["source"],
                expense_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()

    if cursor.rowcount == 0:
        return jsonify({"error": "Gasto no encontrado."}), 404

    return jsonify(row_to_dict(row))


@app.delete("/api/transfers/<int:transfer_id>")
def delete_transfer(transfer_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM transfers WHERE id = ?", (transfer_id,))
        conn.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Transferencia no encontrada."}), 404

    return "", 204


@app.post("/api/import/pdf")
def import_pdf():
    file_storage = request.files.get("pdf")
    card_type = request.form.get("card_type", "").strip().lower()

    if not file_storage or not file_storage.filename:
        return jsonify({"error": "Selecciona un archivo PDF."}), 400
    if card_type not in {"visa", "master"}:
        return jsonify({"error": "Selecciona si el resumen es Visa o Master."}), 400

    try:
        parsed_expenses = parse_pdf_expenses(file_storage, card_type)
    except Exception:
        return jsonify(
            {
                "error": "No se pudo leer el PDF. Proba con una factura con texto seleccionable."
            }
        ), 400

    if not parsed_expenses:
        return jsonify({"error": "No encontre movimientos en pesos en el PDF."}), 400

    with get_db() as conn:
        conn.executemany(
            """
            INSERT INTO expenses (month, date, description, amount, payment_method, source)
            VALUES (:month, :date, :description, :amount, :payment_method, :source)
            """,
            parsed_expenses,
        )
        conn.commit()

    return jsonify({"imported": len(parsed_expenses), "expenses": parsed_expenses}), 201


@app.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Gasto no encontrado."}), 404

    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
