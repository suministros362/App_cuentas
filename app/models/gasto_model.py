from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from app.models.database import db


class Gasto(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        db.CheckConstraint(
            "movement_type IN ('expense', 'refund')",
            name="ck_expenses_movement_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(
        db.String, nullable=False, default="Efectivo", server_default="Efectivo"
    )
    source = db.Column(
        db.String, nullable=False, default="Manual", server_default="Manual"
    )
    payment_month = db.Column(db.String(7), nullable=False)
    statement_month = db.Column(db.String(7), nullable=True)
    card_type = db.Column(db.String(10), nullable=True)
    movement_type = db.Column(
        db.String(10), nullable=False, default="expense", server_default="expense"
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=func.current_timestamp()
    )

    def to_dict(self):
        created_at = self.created_at
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "id": self.id,
            "month": self.month,
            "date": self.date,
            "description": self.description,
            "amount": float(Decimal(self.amount)),
            "payment_method": self.payment_method,
            "source": self.source,
            "payment_month": self.payment_month,
            "statement_month": self.statement_month,
            "card_type": self.card_type,
            "movement_type": self.movement_type,
            "created_at": created_at,
        }
