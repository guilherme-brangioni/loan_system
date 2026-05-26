from flask import Blueprint, render_template

from enums.user_role import UserRole
from services.diagnostic_service import DiagnosticService
from utils.auth_decorators import role_required


diagnostic_bp = Blueprint(
    "diagnostic_bp",
    __name__,
    url_prefix="/diagnostico",
)


@diagnostic_bp.route("/")
@role_required(UserRole.ADMIN.value)
def diagnostic_page():
    """
    Tela de diagnóstico do sistema.
    """

    checks = DiagnosticService.run_all_checks()

    summary = {
        "ok": len([item for item in checks if item["status"] == "OK"]),
        "warning": len([item for item in checks if item["status"] == "AVISO"]),
        "error": len([item for item in checks if item["status"] == "ERRO"]),
    }

    return render_template(
        "diagnostic.html",
        checks=checks,
        summary=summary,
    )