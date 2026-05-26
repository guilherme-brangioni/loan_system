from flask import Blueprint, flash, redirect, render_template, url_for

from enums.user_role import UserRole
from models.external_pending import ExternalPending
from services.auth_service import AuthService
from services.external_pending_service import ExternalPendingService
from utils.auth_decorators import role_required


external_pending_bp = Blueprint(
    "external_pending_bp",
    __name__,
    url_prefix="/pendencias-externas",
)


@external_pending_bp.route("/")
@role_required(UserRole.ADMIN.value, UserRole.OPERADOR.value)
def external_pending_page():
    active_pendings = ExternalPendingService.list_active_pendings()
    resolved_pendings = ExternalPendingService.list_resolved_pendings()

    return render_template(
        "external_pending.html",
        active_pendings=active_pendings,
        resolved_pendings=resolved_pendings,
    )


@external_pending_bp.route("/<int:pending_id>/processar", methods=["POST"])
@role_required(UserRole.ADMIN.value, UserRole.OPERADOR.value)
def process_one(pending_id: int):
    pending = ExternalPending.query.get_or_404(pending_id)

    performed_by = AuthService.get_current_user_display_name()

    result = ExternalPendingService.process_pending(
        pending=pending,
        performed_by=performed_by,
    )

    if result.get("success"):
        flash("Pendência processada com sucesso.", "success")
    else:
        flash(
            "Falha ao processar pendência: "
            + result.get("error", "Erro desconhecido."),
            "error",
        )

    return redirect(url_for("external_pending_bp.external_pending_page"))


@external_pending_bp.route("/processar-todas", methods=["POST"])
@role_required(UserRole.ADMIN.value, UserRole.OPERADOR.value)
def process_all():
    performed_by = AuthService.get_current_user_display_name()

    result = ExternalPendingService.process_all_active(
        performed_by=performed_by,
    )

    flash(
        "Processamento concluído. "
        f"Total: {result['total']} | "
        f"Sucesso: {result['success']} | "
        f"Falhas: {result['failed']}",
        "success",
    )

    return redirect(url_for("external_pending_bp.external_pending_page"))