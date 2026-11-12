from pathlib import Path

from flask import Flask
from sqlalchemy import inspect, text

from app.models import Gasto, Transferencia, db
from app.modules.gastos import gastos_bp
from app.modules.transferencias import transferencias_bp


def _migrate_existing_database() -> None:
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("expenses")}
    required_columns = {
        "payment_month",
        "statement_month",
        "card_type",
        "movement_type",
    }

    if "category_id" in columns or not required_columns.issubset(columns):
        legacy_month = (
            "COALESCE(month, substr(date, 1, 7))"
            if "month" in columns
            else "substr(date, 1, 7)"
        )
        payment_month = (
            f"COALESCE(payment_month, {legacy_month})"
            if "payment_month" in columns
            else legacy_month
        )
        statement_month = (
            "statement_month" if "statement_month" in columns else "NULL"
        )
        card_type = "card_type" if "card_type" in columns else "NULL"
        movement_type = (
            "COALESCE(movement_type, 'expense')"
            if "movement_type" in columns
            else "'expense'"
        )
        month_value = legacy_month if "month" in columns else payment_month

        with db.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE expenses_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month VARCHAR NOT NULL,
                        date VARCHAR NOT NULL,
                        description VARCHAR NOT NULL,
                        amount NUMERIC(12, 2) NOT NULL CHECK(amount > 0),
                        payment_method VARCHAR NOT NULL DEFAULT 'Efectivo',
                        source VARCHAR NOT NULL DEFAULT 'Manual',
                        payment_month VARCHAR(7) NOT NULL,
                        statement_month VARCHAR(7),
                        card_type VARCHAR(10),
                        movement_type VARCHAR(10) NOT NULL DEFAULT 'expense'
                            CHECK(movement_type IN ('expense', 'refund')),
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            connection.execute(
                text(
                    f"""
                    INSERT INTO expenses_new
                        (id, month, date, description, amount, payment_method,
                         source, payment_month, statement_month, card_type,
                         movement_type, created_at)
                    SELECT id, {month_value}, date, description, amount, payment_method,
                           source, {payment_month}, {statement_month}, {card_type},
                           {movement_type}, created_at
                    FROM expenses
                    """
                )
            )
            connection.execute(text("DROP TABLE expenses"))
            connection.execute(
                text("ALTER TABLE expenses_new RENAME TO expenses")
            )

    if "categories" in inspector.get_table_names():
        with db.engine.begin() as connection:
            connection.execute(text("DROP TABLE categories"))


def create_app(config_object=None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    if config_object is None:
        from config import DevelopmentConfig

        app.config.from_object(DevelopmentConfig)
    elif isinstance(config_object, dict):
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object)

    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if database_uri.startswith("sqlite:///"):
        database_path = Path(database_uri.removeprefix("sqlite:///"))
        database_path.parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(transferencias_bp)
    with app.app_context():
        db.create_all()
        _migrate_existing_database()
    return app
