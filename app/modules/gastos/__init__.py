from flask import Blueprint


gastos_bp = Blueprint("gastos", __name__)

from app.modules.gastos import routes  # noqa: E402,F401
