from typing import cast

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)

from models.approver import Approver
from models.email_log import EmailLog
from models.loan import Loan
from services.notification_recipient_service import NotificationRecipientService

from services.email_log_service import EmailLogService
from services.email_service import EmailService
from services.pdf_service import PDFService
from services.app_setting_service import AppSettingService


email_bp = Blueprint("email_bp", __name__, url_prefix="/emails")


@email_bp.route("/")
def email_logs():
    """
    Lista as tentativas de envio de e-mail.

    Mantemos esta tela porque ela é útil para auditoria e diagnóstico
    quando algum envio falhar.
    """

    logs = EmailLog.query.order_by(
        EmailLog.created_at.desc()
    ).limit(300).all()

    return render_template(
        "email_logs.html",
        logs=logs,
    )


@email_bp.route("/emprestimo/<int:loan_id>/reenviar-aprovacao", methods=["POST"])
def resend_approval_email(loan_id: int):
    """
    Reenvia o e-mail de aprovação para o aprovador.

    Essa função continua existindo mesmo sem a tela de teste SMTP.
    """

    loan = Loan.query.get_or_404(loan_id)

    approver = cast(Approver, loan.approver)

    base_url = AppSettingService.get(
        "APP_BASE_URL",
        current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
    )

    base_url = str(base_url or "http://127.0.0.1:5000").strip().rstrip("/")

    approval_url = f"{base_url}{url_for('approval_bp.my_approvals')}"

    body = EmailService.build_approval_body(
        loan,
        approval_url,
    )

    subject = f"Aprovação de empréstimo - {loan.numero_controle}"

    result = EmailService.try_send_email(
        recipients=[approver.email],
        subject=subject,
        body=body,
    )

    EmailLogService.register(
        email_type="RESEND_APPROVAL",
        loan_id=loan.id,
        recipients=[approver.email],
        subject=subject,
        success=bool(result.get("success")),
        error=result.get("error"),
    )

    if result.get("success"):
        flash("E-mail de aprovação reenviado com sucesso.", "success")
    else:
        flash(
            "Falha ao reenviar aprovação: "
            + result.get("error", "Erro desconhecido."),
            "error",
        )

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan.id))


@email_bp.route("/emprestimo/<int:loan_id>/reenviar-comprovante", methods=["POST"])
def resend_receipt_email(loan_id: int):
    """
    Reenvia o comprovante PDF do empréstimo para o solicitante.
    """

    loan = Loan.query.get_or_404(loan_id)

    pdf_path = PDFService.generate_loan_pdf(loan)

    body = EmailService.build_confirmation_body(loan)

    subject = f"Comprovante de empréstimo - {loan.numero_controle}"

    receipt_recipients = (
        NotificationRecipientService.get_loan_receipt_recipients(loan)
    )

    if not receipt_recipients:
        flash(
            "Nenhum destinatário válido encontrado para envio do comprovante.",
            "error",
        )
        return redirect(url_for("loan_bp.loan_detail", loan_id=loan.id))

    result = EmailService.try_send_email(
        recipients=receipt_recipients,
        subject=subject,
        body=body,
        attachment_path=pdf_path,
    )

    EmailLogService.register(
        email_type="RESEND_RECEIPT",
        loan_id=loan.id,
        recipients=receipt_recipients,
        subject=subject,
        success=bool(result.get("success")),
        error=result.get("error"),
    )

    if result.get("success"):
        flash("Comprovante reenviado com sucesso.", "success")
    else:
        flash(
            "Falha ao reenviar comprovante: "
            + result.get("error", "Erro desconhecido."),
            "error",
        )

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan.id))