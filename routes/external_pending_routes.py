from flask import Blueprint, flash, redirect, render_template, url_for, request

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
    """
    Lista pendências externas com filtros.
    """

    status_filter = request.args.get("status", "").strip()
    action_filter = request.args.get("action", "").strip()
    entity_id_filter = request.args.get("entity_id", "").strip()

    query = ExternalPending.query

    if status_filter:
        query = query.filter(ExternalPending.status == status_filter)

    if action_filter:
        query = query.filter(ExternalPending.action == action_filter)

    if entity_id_filter:
        try:
            query = query.filter(ExternalPending.entity_id == int(entity_id_filter))
        except ValueError:
            flash("ID informado inválido.", "error")

    pendings = (
        query
        .order_by(
            ExternalPending.status.asc(),
            ExternalPending.created_at.desc(),
        )
        .limit(300)
        .all()
    )

    active_count = ExternalPendingService.count_active_pendings()

    action_options = [
        ExternalPendingService.ACTION_GENERATE_LOAN_PDF,
        ExternalPendingService.ACTION_SEND_LOAN_RECEIPT_EMAIL,
        ExternalPendingService.ACTION_SEND_RETURN_CONFIRMATION_EMAIL,
        ExternalPendingService.ACTION_EXPORT_LOAN_MOVEMENT,
    ]

    status_options = [
        ExternalPendingService.STATUS_PENDENTE,
        ExternalPendingService.STATUS_PROCESSANDO,
        ExternalPendingService.STATUS_ERRO,
        ExternalPendingService.STATUS_RESOLVIDO,
    ]

    return render_template(
        "external_pending.html",
        pendings=pendings,
        active_count=active_count,
        status_filter=status_filter,
        action_filter=action_filter,
        entity_id_filter=entity_id_filter,
        action_options=action_options,
        status_options=status_options,
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