from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.approval_service import ApprovalService
from services.auth_service import AuthService


approval_bp = Blueprint(
    "approval_bp",
    __name__,
    url_prefix="/aprovacoes",
)


@approval_bp.route("/")
def my_approvals():
    """
    Lista aprovações direcionadas ao usuário logado.
    """

    status_filter = request.args.get(
        "status",
        "PENDENTE_APROVACAO",
    ).strip()

    search_text = request.args.get("q", "").strip()

    loans = ApprovalService.get_approvals_for_current_user(
        status_filter=status_filter,
        search_text=search_text,
    )

    pending_count = ApprovalService.count_pending_for_current_user()

    status_options = [
        "PENDENTE_APROVACAO",
        "APROVADO",
        "REJEITADO",
        "RETIRADO",
        "FINALIZADO",
    ]

    return render_template(
        "my_approvals.html",
        loans=loans,
        pending_count=pending_count,
        status_filter=status_filter,
        search_text=search_text,
        status_options=status_options,
    )


@approval_bp.route("/<int:loan_id>/aprovar", methods=["POST"])
def approve_loan(loan_id: int):
    """
    Aprova empréstimo pelo sistema.
    """

    try:
        performed_by = AuthService.get_current_user_display_name()

        loan = ApprovalService.approve_from_system(
            loan_id=loan_id,
            performed_by=performed_by,
        )

        flash(
            f"Empréstimo {loan.numero_controle} aprovado com sucesso.",
            "success",
        )

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("approval_bp.my_approvals"))


@approval_bp.route("/<int:loan_id>/rejeitar", methods=["POST"])
def reject_loan(loan_id: int):
    """
    Rejeita empréstimo pelo sistema.
    """

    try:
        form_data = request.form.to_dict(flat=True)

        reason = form_data.get("reason", "").strip()
        performed_by = AuthService.get_current_user_display_name()

        if not reason:
            raise ValueError("Informe o motivo da rejeição.")

        loan = ApprovalService.reject_from_system(
            loan_id=loan_id,
            reason=reason,
            performed_by=performed_by,
        )

        flash(
            f"Empréstimo {loan.numero_controle} rejeitado.",
            "success",
        )

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("approval_bp.my_approvals"))