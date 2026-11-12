from decimal import Decimal, ROUND_HALF_UP

from flask import jsonify, request
from sqlalchemy import case, func

from app.models import Gasto, Transferencia, db
from app.modules.transferencias import transferencias_bp
from app.services.money_service import parse_positive_amount
from app.services.period_service import parse_period_date, validate_period_args


def validate_transfer(data):
    if not isinstance(data, dict):
        return None, ({"error": "Los datos de la transferencia no son válidos."}, 400)

    required = ["date", "destination", "amount"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return None, ({"error": "Completa todos los campos obligatorios."}, 400)
    if not isinstance(data["date"], str) or not isinstance(data["destination"], str):
        return None, ({"error": "Fecha y destino deben ser texto válido."}, 400)

    transfer_date = data["date"].strip()
    if parse_period_date(transfer_date) is None:
        return None, ({"error": "La fecha debe ser válida y tener formato YYYY-MM-DD."}, 400)

    destination = data["destination"].strip()
    if destination not in {"Banco Nacion", "Mercado Pago"}:
        return None, ({"error": "Selecciona un destino valido."}, 400)

    amount = parse_positive_amount(data["amount"])
    if amount is None:
        return None, (
            {"error": "El importe debe ser válido, finito, positivo y tener hasta dos decimales."},
            400,
        )

    return {"date": transfer_date, "destination": destination, "amount": amount}, None


@transferencias_bp.get("/api/transfers")
def get_transfers():
    period, error = validate_period_args(request.args)
    if error:
        return jsonify(error[0]), error[1]

    transfer_filters = []
    expense_filters = []
    if period["month"]:
        transfer_filters.append(func.substr(Transferencia.date, 1, 7) == period["month"])
        expense_filters.append(Gasto.payment_month == period["month"])
    elif period["year"]:
        transfer_filters.extend(
            (
                Transferencia.date >= f"{period['year']}-01-01",
                Transferencia.date <= f"{period['year']}-12-31",
            )
        )
        expense_filters.extend(
            (
                Gasto.payment_month >= f"{period['year']}-01",
                Gasto.payment_month <= f"{period['year']}-12",
            )
        )
    if period["date"]:
        transfer_filters.append(Transferencia.date == period["date"])
        expense_filters.append(Gasto.date == period["date"])
    if period["from"]:
        transfer_filters.append(Transferencia.date >= period["from"])
        expense_filters.append(Gasto.date >= period["from"])
    if period["to"]:
        transfer_filters.append(Transferencia.date <= period["to"])
        expense_filters.append(Gasto.date <= period["to"])

    transfers = Transferencia.query.filter(*transfer_filters).order_by(
        Transferencia.date.desc(), Transferencia.id.desc()
    ).all()
    transfers_total = (
        db.session.query(func.coalesce(func.sum(Transferencia.amount), 0))
        .filter(*transfer_filters)
        .scalar()
    )
    net_expenses = (
        db.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (Gasto.movement_type == "refund", -Gasto.amount),
                        else_=Gasto.amount,
                    )
                ),
                0,
            )
        )
        .filter(*expense_filters)
        .scalar()
    )
    refund_total = (
        db.session.query(func.coalesce(func.sum(Gasto.amount), 0))
        .filter(*expense_filters, Gasto.movement_type == "refund")
        .scalar()
    )
    net_expenses = Decimal(net_expenses)
    refund_total = Decimal(refund_total)
    transfers_total = Decimal(transfers_total)
    half_expenses = (net_expenses / 2).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    coverage_gap = half_expenses - transfers_total
    response_month = (
        period["month"]
        or (period["date"][:7] if period["date"] else None)
    )

    return jsonify(
        {
            "transfers": [transfer.to_dict() for transfer in transfers],
            "month": response_month,
            "period": {
                "month": int(response_month[5:]) if response_month else None,
                "year": int(response_month[:4]) if response_month else period["year"],
                "from": period["from"],
                "to": period["to"],
            },
            "total": float(transfers_total),
            "total_transferred": float(transfers_total),
            "expenses_total": float(half_expenses),
            "full_expenses_total": float(net_expenses),
            "total_spent": float(net_expenses),
            "total_refunds": float(refund_total),
            "balance": float(coverage_gap),
            "coverage_gap": float(coverage_gap),
        }
    )


@transferencias_bp.post("/api/transfers")
def create_transfer():
    data = request.get_json(silent=True)
    transfer, error = validate_transfer(data)
    if error:
        return jsonify(error[0]), error[1]

    transferencia = Transferencia(**transfer)
    db.session.add(transferencia)
    db.session.commit()
    return jsonify(transferencia.to_dict()), 201


@transferencias_bp.delete("/api/transfers/<int:transfer_id>")
def delete_transfer(transfer_id: int):
    transferencia = db.session.get(Transferencia, transfer_id)
    if transferencia is None:
        return jsonify({"error": "Transferencia no encontrada."}), 404
    db.session.delete(transferencia)
    db.session.commit()
    return "", 204
