from flask import Blueprint, flash, redirect, render_template, url_for, request

from enums.equipment_status import EquipmentStatus
from enums.loan_status import LoanStatus

from models.equipment import Equipment
from models.loan import Loan

from services.loan_service import LoanService
from services.validation_reminder_service import ValidationReminderService
from services.backup_service import BackupService
from services.external_pending_service import ExternalPendingService

from utils.query_options import loan_full_options


main_bp = Blueprint("main_bp", __name__)


def _loan_has_pending_validation(loan) -> bool:
    """
    Verifica se o empréstimo possui algum equipamento não validado.
    """

    for item in getattr(loan, "items", []) or []:
        equipment = getattr(item, "equipment", None)

        if equipment is not None and not bool(getattr(equipment, "validado", False)):
            return True

    return False


@main_bp.route("/")
def dashboard():
    """
    Dashboard operacional.

    Importante:
    - não envia e-mails automaticamente ao abrir;
    - mostra apenas empréstimos ativos, pendentes de aprovação e pendentes de validação;
    - empréstimos finalizados não aparecem.
    """

    LoanService.mark_overdue_loans()

    try:
        BackupService.create_weekly_automatic_backup_if_needed()
    except Exception:
        pass

    borrowed_statuses = [
        LoanStatus.RETIRADO.value,
        LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
        LoanStatus.ATRASADO.value,
    ]

    dashboard_candidate_statuses = [
        LoanStatus.PENDENTE_APROVACAO.value,
        LoanStatus.APROVADO.value,
        LoanStatus.RETIRADO.value,
        LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
        LoanStatus.ATRASADO.value,
    ]

    borrowed_loans = (
        Loan.query
        .options(*loan_full_options())
        .filter(Loan.status.in_(borrowed_statuses))
        .order_by(Loan.created_at.desc())
        .all()
    )

    pending_approval_loans = (
        Loan.query
        .options(*loan_full_options())
        .filter_by(status=LoanStatus.PENDENTE_APROVACAO.value)
        .order_by(Loan.created_at.desc())
        .all()
    )

    candidate_loans = (
        Loan.query
        .options(*loan_full_options())
        .filter(Loan.status.in_(dashboard_candidate_statuses))
        .order_by(Loan.created_at.desc())
        .all()
    )

    pending_validation_loans = [
        loan for loan in candidate_loans
        if _loan_has_pending_validation(loan)
    ]

    available_equipment = Equipment.query.filter_by(
        status=EquipmentStatus.DISPONIVEL.value
    ).count()

    last_validation_check = request.args.get("validation_check", "")

    external_pending_count = ExternalPendingService.count_active_pendings()

    return render_template(
        "dashboard.html",
        borrowed_loans=borrowed_loans,
        pending_approval_loans=pending_approval_loans,
        pending_validation_loans=pending_validation_loans,
        borrowed_count=len(borrowed_loans),
        pending_approval_count=len(pending_approval_loans),
        pending_validation_count=len(pending_validation_loans),
        available_equipment=available_equipment,
                external_pending_count=external_pending_count,
        last_validation_check=last_validation_check,
    )


@main_bp.route("/verificar-validacoes", methods=["POST"])
def check_validation_reminders():
    """
    Verifica manualmente pendências de validação com mais de 24h
    e reenvia os e-mails necessários.

    Melhor do que disparar automaticamente ao abrir o Dashboard.
    """

    try:
        result = ValidationReminderService.run_validation_reminder_check()

        flash(
            "Verificação concluída. "
            f"Empréstimos verificados: {result['checked']} | "
            f"Lembretes enviados: {result['sent']} | "
            f"Falhas: {result['failed']}",
            "success",
        )

    except Exception as exc:
        flash(
            "Erro ao verificar pendências de validação: " + str(exc),
            "error",
        )

    return redirect(url_for("main_bp.dashboard", validation_check="done"))