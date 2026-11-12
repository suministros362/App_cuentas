from datetime import datetime

from sqlalchemy import func

from app.models.database import db


class Transferencia(db.Model):
    __tablename__ = "transfers"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    destination = db.Column(db.String, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=func.current_timestamp()
    )

    def to_dict(self):
        created_at = self.created_at
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "id": self.id,
            "month": self.date[:7],
            "date": self.date,
            "destination": self.destination,
            "amount": float(self.amount),
            "created_at": created_at,
        }
