from datetime import datetime, timedelta
from typing import Any

from models.email_log import EmailLog
from models.loan import Loan

from enums.loan_status import LoanStatus

from services.email_log_service import EmailLogService
from services.email_service import EmailService
from services.notification_recipient_service import NotificationRecipientService


class ValidationReminderService:
    """
    Serviço responsável por reenviar e-mail de validação quando um equipamento
    emprestado ainda não foi validado após 24 horas.

    Nesta versão, a verificação roda quando o dashboard é aberto.
    """

    EMAIL_TYPE = "VALIDATION_REMINDER"

    ACTIVE_STATUSES = [
        LoanStatus.PENDENTE_APROVACAO.value,
        LoanStatus.APROVADO.value,
        LoanStatus.RETIRADO.value,
        LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
        LoanStatus.ATRASADO.value,
    ]

    @staticmethod
    def _get_loan_items(loan: Any) -> list:
        """
        Retorna os itens do empréstimo de forma segura.
        """

        items = getattr(loan, "items", None)

        if not items:
            return []

        return list(items)

    @staticmethod
    def loan_has_pending_equipment_validation(loan: Loan) -> bool:
        """
        Verifica se o empréstimo possui equipamento ainda não validado.
        """

        for item in ValidationReminderService._get_loan_items(loan):
            equipment = getattr(item, "equipment", None)

            if equipment is not None and not bool(getattr(equipment, "validado", False)):
                return True

        return False

    @staticmethod
    def _loan_age_is_over_24h(loan: Loan) -> bool:
        """
        Verifica se o empréstimo foi criado há mais de 24 horas.
        """

        reference_date = getattr(loan, "created_at", None) or getattr(
            loan,
            "data_emprestimo",
            None,
        )

        if reference_date is None:
            return False

        return reference_date <= datetime.utcnow() - timedelta(hours=24)

    @staticmethod
    def _reminder_sent_in_last_24h(loan_id: int) -> bool:
        """
        Evita reenviar lembrete várias vezes no mesmo dia.
        """

        last_log = (
            EmailLog.query
            .filter_by(
                loan_id=loan_id,
                email_type=ValidationReminderService.EMAIL_TYPE,
            )
            .order_by(EmailLog.created_at.desc())
            .first()
        )

        if not last_log:
            return False

        return last_log.created_at >= datetime.utcnow() - timedelta(hours=24)

    @staticmethod
    def send_validation_reminder_for_loan(loan: Loan) -> dict:
        """
        Envia lembrete de validação para um empréstimo específico.
        """

        if loan.status not in ValidationReminderService.ACTIVE_STATUSES:
            return {
                "sent": False,
                "reason": "Empréstimo não está ativo ou pendente.",
            }

        if not ValidationReminderService.loan_has_pending_equipment_validation(loan):
            return {
                "sent": False,
                "reason": "Sem equipamentos pendentes de validação.",
            }

        if not ValidationReminderService._loan_age_is_over_24h(loan):
            return {
                "sent": False,
                "reason": "Empréstimo ainda não completou 24 horas.",
            }

        if ValidationReminderService._reminder_sent_in_last_24h(loan.id):
            return {
                "sent": False,
                "reason": "Lembrete já enviado nas últimas 24 horas.",
            }

        recipients = NotificationRecipientService.get_loan_receipt_recipients(loan)

        if not recipients:
            return {
                "sent": False,
                "reason": "Nenhum destinatário válido encontrado.",
            }

        subject = f"Validação pendente de equipamento - {loan.numero_controle}"

        body = EmailService.build_validation_reminder_body(loan)

        result = EmailService.try_send_email(
            recipients=recipients,
            subject=subject,
            body=body,
        )

        EmailLogService.register(
            email_type=ValidationReminderService.EMAIL_TYPE,
            loan_id=loan.id,
            recipients=recipients,
            subject=subject,
            success=bool(result.get("success")),
            error=result.get("error"),
        )

        return {
            "sent": bool(result.get("success")),
            "error": result.get("error"),
        }

    @staticmethod
    def run_validation_reminder_check() -> dict:
        """
        Verifica todos os empréstimos ativos/pendentes e envia lembretes
        quando necessário.
        """

        loans = (
            Loan.query
            .filter(Loan.status.in_(ValidationReminderService.ACTIVE_STATUSES))
            .order_by(Loan.created_at.asc())
            .all()
        )

        checked = 0
        sent = 0
        failed = 0

        for loan in loans:
            checked += 1

            result = ValidationReminderService.send_validation_reminder_for_loan(loan)

            if result.get("sent"):
                sent += 1
            elif result.get("error"):
                failed += 1

        return {
            "checked": checked,
            "sent": sent,
            "failed": failed,
        }