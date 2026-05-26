from flask import Blueprint, flash, redirect, render_template, request, url_for

from models.sync_pending import SyncPending

from services.sync_pending_service import SyncPendingService
from services.auth_service import AuthService


sync_bp = Blueprint(
    "sync_bp",
    __name__,
    url_prefix="/sincronizacao",
)


@sync_bp.route("/")
def sync_pending_page():
    """
    Tela de pendências de sincronização.
    """

    active_pendings = SyncPendingService.list_active_pendings()
    resolved_pendings = SyncPendingService.list_resolved_pendings()

    return render_template(
        "sync_pending.html",
        active_pendings=active_pendings,
        resolved_pendings=resolved_pendings,
    )


@sync_bp.route("/<int:pending_id>/tentar", methods=["POST"])
def retry_pending(pending_id: int):
    """
    Tenta reprocessar uma pendência específica.
    """

    pending = SyncPending.query.get_or_404(pending_id)

    performed_by = AuthService.get_current_user_display_name()

    result = SyncPendingService.retry_pending(
        pending=pending,
        performed_by=performed_by,
    )

    if result.get("success"):
        flash("Pendência resolvida com sucesso.", "success")
    else:
        flash(
            "Falha ao reprocessar pendência: "
            + result.get("error", "Erro desconhecido."),
            "error",
        )

    return redirect(url_for("sync_bp.sync_pending_page"))


@sync_bp.route("/tentar-todas", methods=["POST"])
def retry_all():
    """
    Tenta reprocessar todas as pendências ativas.
    """

    performed_by = AuthService.get_current_user_display_name()

    result = SyncPendingService.retry_all_active(
        performed_by=performed_by,
    )

    flash(
        "Reprocessamento concluído. "
        f"Total: {result['total']} | "
        f"Resolvidas: {result['success']} | "
        f"Falhas: {result['failed']}",
        "success",
    )

    return redirect(url_for("sync_bp.sync_pending_page"))