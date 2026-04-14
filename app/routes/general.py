from typing import Optional
from flask import Blueprint, render_template
from app.managers import PilotManager
from app.classes.socket import SocketService
from app.utils.constants import DEFAULT_STEPS

general_bp = Blueprint("general", __name__)
pilot_manager : Optional[PilotManager] = None
socket_service : Optional[SocketService] = None

@general_bp.route("/")
def index():
    request_overlays = DEFAULT_STEPS
    return render_template("index.html", request_overlays=request_overlays)
