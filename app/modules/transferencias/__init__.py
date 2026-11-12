from flask import Blueprint


transferencias_bp = Blueprint("transferencias", __name__)

from app.modules.transferencias import routes  # noqa: E402,F401
