from datetime import datetime
from decimal import Decimal

from flask import jsonify, render_template, request
from pypdf.errors import ParseError, PdfReadError
from sqlalchemy import case, func

from app.models import Gasto, db
from app.modules.gastos import gastos_bp
from app.services.money_service import parse_positive_amount
from app.services.pdf_service import parse_pdf_expenses
from app.services.period_service import parse_period_date, validate_period_args


CARD_TYPES = {"visa": "Visa", "mastercard": "Mastercard"}


def _period_from_fields(month_value, year_value, label):
    month_value = str(month_value or "").strip()
    year_value = str(year_value or "").strip()
    if not month_value.isdecimal() or not year_value.isdecimal():
        return None, {"error": f"Ingresa mes y año válidos para {label}."}
    month_number = int(month_value)
    year_number = int(year_value)
    if not 1 <= month_number <= 12 or not 1 <= year_number <= 9999:
        return None, {"error": f"Ingresa mes y año válidos para {label}."}
    return f"{year_number:04d}-{month_number:02d}", None


def validate_expense(data, allow_refund=True):
    if not isinstance(data, dict):
        return None, ({"error": "Los datos del gasto no son válidos."}, 400)

    required = ("month", "date", "description", "amount")
    if any(data.get(field) is None or not str(data[field]).strip() for field in required):
        return None, ({"error": "Completa todos los campos obligatorios."}, 400)
    if not all(isinstance(data[field], str) for field in ("month", "date", "description")):
        return None, ({"error": "Fecha, mes y descripción deben ser texto válido."}, 400)
    if parse_period_args_month(data["month"]) is None:
        return None, ({"error": "El mes debe tener formato YYYY-MM."}, 400)
    if parse_period_date(data["date"]) is None:
        return None, ({"error": "La fecha debe ser válida y tener formato YYYY-MM-DD."}, 400)

    amount = parse_positive_amount(data["amount"])
    if amount is None:
        return None, (
            {"error": "El importe debe ser válido, finito, positivo y tener hasta dos decimales."},
            400,
        )

    movement_type = data.get("movement_type", "expense")
    if not isinstance(movement_type, str) or movement_type not in {"expense", "refund"}:
        return None, ({"error": "El tipo de movimiento no es válido."}, 400)
    if movement_type == "refund" and not allow_refund:
        return None, ({"error": "El tipo de movimiento no es válido."}, 400)

    card_type = data.get("card_type") or None
    if card_type is not None and (
        not isinstance(card_type, str) or card_type not in CARD_TYPES
    ):
        return None, ({"error": "El tipo de tarjeta no es válido."}, 400)

    payment_month = data.get("payment_month") or data["month"]
    statement_month = data.get("statement_month") or None
    if not isinstance(payment_month, str) or (
        statement_month is not None and not isinstance(statement_month, str)
    ):
        return None, ({"error": "Los meses de pago y resumen no son válidos."}, 400)
    payment_month = payment_month.strip()
    statement_month = statement_month.strip() if statement_month else None
    if parse_period_args_month(payment_month) is None:
        return None, ({"error": "El mes de pago debe tener formato YYYY-MM."}, 400)
    if statement_month is not None and parse_period_args_month(statement_month) is None:
        return None, ({"error": "El mes de resumen debe tener formato YYYY-MM."}, 400)
    if card_type and not statement_month:
        return None, ({"error": "Indica el mes de resumen de la tarjeta."}, 400)

    return (
        {
            "month": payment_month,
            "date": data["date"],
            "description": data["description"].strip()[:180],
            "amount": amount,
            "payment_method": CARD_TYPES.get(card_type, "Manual"),
            "source": "PDF" if card_type else "Manual",
            "payment_month": payment_month,
            "statement_month": statement_month,
            "card_type": card_type,
            "movement_type": movement_type,
        },
        None,
    )


def parse_period_args_month(value):
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        return None
    year, month = value[:4], value[5:]
    if not year.isdecimal() or not month.isdecimal():
        return None
    if not 1 <= int(year) <= 9999 or not 1 <= int(month) <= 12:
        return None
    return value


def _expense_period_filters(period, field=Gasto.month):
    filters = []
    if period["month"]:
        filters.append(field == period["month"])
    elif period["year"]:
        filters.extend(
            (field >= f"{period['year']}-01", field <= f"{period['year']}-12")
        )
    if period["date"]:
        filters.append(Gasto.date == period["date"])
    if period["from"]:
        filters.append(Gasto.date >= period["from"])
    if period["to"]:
        filters.append(Gasto.date <= period["to"])
    return filters


def _net_amount_expression():
    return case(
        (Gasto.movement_type == "refund", -Gasto.amount),
        else_=Gasto.amount,
    )


@gastos_bp.get("/")
def index():
    return render_template("index.html")


@gastos_bp.get("/api/expenses")
def get_expenses():
    period, error = validate_period_args(request.args)
    if error:
        return jsonify(error[0]), error[1]

    period_filters = _expense_period_filters(period)
    filters = list(period_filters)
    search = request.args.get("q", "").strip()
    if search:
        filters.append(Gasto.description.ilike(f"%{search}%"))

    expenses = Gasto.query.filter(*filters, Gasto.card_type.is_(None)).order_by(
        Gasto.date.desc(), Gasto.id.desc()
    ).all()
    total = (
        db.session.query(func.coalesce(func.sum(_net_amount_expression()), 0))
        .filter(*filters)
        .scalar()
    )
    summary = (
        db.session.query(
            Gasto.month.label("month"),
            func.coalesce(func.sum(_net_amount_expression()), 0).label("total"),
        )
        .filter(*period_filters)
        .group_by(Gasto.month)
        .order_by(Gasto.month.desc())
        .limit(12)
        .all()
    )
    return jsonify(
        {
            "expenses": [expense.to_dict() for expense in expenses],
            "total": float(Decimal(total)),
            "summary": [
                {"month": row.month, "total": float(Decimal(row.total))}
                for row in summary
            ],
            "period": {
                "month": int(period["month"][5:]) if period["month"] else None,
                "year": period["year"],
                "from": period["from"],
                "to": period["to"],
            },
        }
    )


@gastos_bp.get("/api/expenses/card-summary")
def card_summary():
    period, error = validate_period_args(request.args)
    if error:
        return jsonify(error[0]), error[1]
    month = period["month"] or datetime.now().strftime("%Y-%m")
    filters = _expense_period_filters(period, Gasto.payment_month)
    totals = dict(
        db.session.query(
            Gasto.card_type,
            func.coalesce(func.sum(_net_amount_expression()), 0),
        )
        .filter(*filters, Gasto.card_type.in_(CARD_TYPES))
        .group_by(Gasto.card_type)
        .all()
    )
    counts = dict(
        db.session.query(Gasto.card_type, func.count(Gasto.id))
        .filter(*filters, Gasto.card_type.in_(CARD_TYPES))
        .group_by(Gasto.card_type)
        .all()
    )
    return jsonify(
        {
            "month": int(month[5:]) if period["month"] else None,
            "year": period["year"] or int(month[:4]),
            "cards": [
                {
                    "card_type": card_type,
                    "label": label,
                    "total": float(Decimal(totals.get(card_type, 0))),
                    "count": counts.get(card_type, 0),
                }
                for card_type, label in CARD_TYPES.items()
            ],
        }
    )


@gastos_bp.get("/api/expenses/cards/<card_type>")
def card_expenses(card_type):
    if card_type not in CARD_TYPES:
        return jsonify({"error": "La tarjeta solicitada no es válida."}), 404
    period, error = validate_period_args(request.args)
    if error:
        return jsonify(error[0]), error[1]
    month = period["month"]
    card_filters = [Gasto.card_type == card_type]
    if month:
        card_filters.append(Gasto.payment_month == month)
    elif period["year"]:
        card_filters.extend(
            (
                Gasto.payment_month >= f"{period['year']}-01",
                Gasto.payment_month <= f"{period['year']}-12",
            )
        )
    else:
        month = datetime.now().strftime("%Y-%m")
        card_filters.append(Gasto.payment_month == month)
    expenses = Gasto.query.filter(*card_filters).order_by(
        Gasto.payment_month.desc(),
        Gasto.statement_month.desc(),
        Gasto.date.desc(),
        Gasto.id.desc(),
    ).all()
    return jsonify(
        {
            "card_type": card_type,
            "label": CARD_TYPES[card_type],
            "month": int(month[5:]) if period["month"] else None,
            "year": period["year"] or int(month[:4]),
            "expenses": [expense.to_dict() for expense in expenses],
        }
    )


@gastos_bp.post("/api/expenses")
def create_expense():
    data = request.get_json(silent=True)
    expense, error = validate_expense(data)
    if error:
        return jsonify(error[0]), error[1]

    gasto = Gasto(**expense)
    db.session.add(gasto)
    db.session.commit()
    return jsonify(gasto.to_dict()), 201


@gastos_bp.put("/api/expenses/<int:expense_id>")
def update_expense(expense_id: int):
    data = request.get_json(silent=True)
    expense, error = validate_expense(data)
    if error:
        return jsonify(error[0]), error[1]
    gasto = db.session.get(Gasto, expense_id)
    if gasto is None:
        return jsonify({"error": "Gasto no encontrado."}), 404
    for field, value in expense.items():
        setattr(gasto, field, value)
    db.session.commit()
    return jsonify(gasto.to_dict())


@gastos_bp.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id: int):
    gasto = db.session.get(Gasto, expense_id)
    if gasto is None:
        return jsonify({"error": "Gasto no encontrado."}), 404
    db.session.delete(gasto)
    db.session.commit()
    return "", 204


@gastos_bp.post("/api/import/pdf")
def import_pdf():
    file_storage = request.files.get("pdf")
    card_type = request.form.get("card_type", "").strip().lower()
    if card_type == "master":
        card_type = "mastercard"
    if not file_storage or not file_storage.filename:
        return jsonify({"error": "Selecciona un archivo PDF."}), 400
    if card_type not in CARD_TYPES:
        return jsonify({"error": "Selecciona Visa o Mastercard."}), 400

    payment_month, error = _period_from_fields(
        request.form.get("payment_month_number"),
        request.form.get("payment_year"),
        "el pago",
    )
    if error:
        return jsonify(error), 400
    statement_month, error = _period_from_fields(
        request.form.get("statement_month_number"),
        request.form.get("statement_year"),
        "el resumen",
    )
    if error:
        return jsonify(error), 400

    try:
        parsed_expenses = parse_pdf_expenses(
            file_storage, card_type, payment_month, statement_month
        )
    except (EOFError, OSError, ParseError, PdfReadError, ValueError):
        return jsonify(
            {"error": "No se pudo leer el PDF. Proba con una factura con texto seleccionable."}
        ), 400
    if not parsed_expenses:
        return jsonify({"error": "No encontre movimientos en pesos en el PDF."}), 400
    for expense in parsed_expenses:
        expense.update(
            month=payment_month,
            payment_month=payment_month,
            statement_month=statement_month,
            card_type=card_type,
            payment_method=CARD_TYPES[card_type],
            source="PDF",
        )
    return jsonify(
        {
            "card_type": card_type,
            "payment_month": payment_month,
            "statement_month": statement_month,
            "preview": parsed_expenses,
        }
    ), 200


@gastos_bp.post("/api/import/pdf/confirm")
def confirm_pdf_import():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "El tipo de tarjeta no es válido."}), 400
    card_type = data.get("card_type")
    if card_type == "master":
        card_type = "mastercard"
    if not isinstance(card_type, str) or card_type not in CARD_TYPES:
        return jsonify({"error": "El tipo de tarjeta no es válido."}), 400
    rows = data.get("expenses")
    if not isinstance(rows, list) or not rows:
        return jsonify({"error": "No hay movimientos para confirmar."}), 400

    confirmed = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return jsonify({"error": f"Movimiento {index + 1}: los datos no son válidos."}), 400
        expense_data = {
            **row,
            "month": row.get("payment_month", row.get("month", "")),
            "payment_month": row.get("payment_month", row.get("month", "")),
            "card_type": card_type,
        }
        expense, error = validate_expense(expense_data)
        if error:
            return jsonify(
                {"error": f"Movimiento {index + 1}: {error[0]['error']}"}
            ), error[1]
        confirmed.append(Gasto(**expense))
    db.session.add_all(confirmed)
    db.session.commit()
    return jsonify(
        {
            "imported": len(confirmed),
            "expenses": [expense.to_dict() for expense in confirmed],
        }
    ), 201
