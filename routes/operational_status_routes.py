from flask import Blueprint, render_template

from enums.user_role import UserRole
from services.operational_status_service import OperationalStatusService
from utils.auth_decorators import role_required


operational_status_bp = Blueprint(
    "operational_status_bp",
    __name__,
    url_prefix="/status-operacional",
)


@operational_status_bp.route("/")
@role_required(UserRole.ADMIN.value)
def operational_status_page():
    """
    Tela de status operacional do sistema.
    """

    status_data = OperationalStatusService.run()

    return render_template(
        "operational_status.html",
        status_data=status_data,
    )