from datetime import datetime, timedelta
from typing import Any

from database.database import db

from enums.loan_status import LoanStatus

from models.email_log import EmailLog
from models.external_pending import ExternalPending
from models.loan import Loan

from services.backup_service import BackupService
from services.external_pending_service import ExternalPendingService
from services.sync_pending_service import SyncPendingService


class OperationalStatusService:
    """
    Serviço de status operacional.

    Mostra indicadores úteis para o dia a dia:
    - backups;
    - pendências externas;
    - sincronizações;
    - atrasos;
    - aprovações;
    - validações;
    - falhas de e-mail.
    """

    @staticmethod
    def run() -> dict[str, Any]:
        return {
            "summary_cards": OperationalStatusService.get_summary_cards(),
            "backup_status": OperationalStatusService.get_backup_status(),
            "external_pending_status": OperationalStatusService.get_external_pending_status(),
            "sync_status": OperationalStatusService.get_sync_status(),
            "loan_status": OperationalStatusService.get_loan_status(),
            "email_status": OperationalStatusService.get_email_status(),
        }

    @staticmethod
    def _status_level(
        count: int,
        warning_when_positive: bool = True,
    ) -> str:
        if count <= 0:
            return "success"

        if warning_when_positive:
            return "warning"

        return "info"

    @staticmethod
    def get_summary_cards() -> list[dict[str, Any]]:
        overdue_count = (
            Loan.query
            .filter(Loan.status == LoanStatus.ATRASADO.value)
            .count()
        )

        pending_approval_count = (
            Loan.query
            .filter(Loan.status == LoanStatus.PENDENTE_APROVACAO.value)
            .count()
        )

        pending_validation_count = OperationalStatusService.count_pending_validation_loans()

        external_pending_count = ExternalPendingService.count_active_pendings()
        sync_pending_count = SyncPendingService.count_active_pendings()

        failed_email_count = (
            EmailLog.query
            .filter(EmailLog.success.is_(False))
            .count()
        )

        return [
            {
                "title": "Empréstimos atrasados",
                "count": overdue_count,
                "level": "danger" if overdue_count > 0 else "success",
                "description": "Empréstimos com prazo vencido.",
                "url_endpoint": "loan_bp.overdue_report",
            },
            {
                "title": "Aprovações pendentes",
                "count": pending_approval_count,
                "level": "warning" if pending_approval_count > 0 else "success",
                "description": "Solicitações aguardando aprovação.",
                "url_endpoint": "approval_bp.my_approvals",
            },
            {
                "title": "Validações pendentes",
                "count": pending_validation_count,
                "level": "warning" if pending_validation_count > 0 else "success",
                "description": "Equipamentos emprestados ainda não validados.",
                "url_endpoint": "loan_bp.list_loans",
                "url_params": {
                    "validacao": "PENDENTE",
                },
            },
            {
                "title": "Pendências externas",
                "count": external_pending_count,
                "level": "warning" if external_pending_count > 0 else "success",
                "description": "E-mails, PDFs ou exportações pendentes.",
                "url_endpoint": "external_pending_bp.external_pending_page",
            },
            {
                "title": "Sincronizações pendentes",
                "count": sync_pending_count,
                "level": "danger" if sync_pending_count > 0 else "success",
                "description": "Falhas ou pendências de sincronização.",
                "url_endpoint": "sync_bp.sync_pending_page",
            },
            {
                "title": "E-mails com falha",
                "count": failed_email_count,
                "level": "danger" if failed_email_count > 0 else "success",
                "description": "Registros de envio de e-mail com erro.",
                "url_endpoint": "email_bp.email_logs",
            },
        ]

    @staticmethod
    def count_pending_validation_loans() -> int:
        """
        Conta empréstimos ativos que têm algum equipamento não validado.
        """

        active_statuses = [
            LoanStatus.RETIRADO.value,
            LoanStatus.ATRASADO.value,
            LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
        ]

        loans = (
            Loan.query
            .filter(Loan.status.in_(active_statuses))
            .all()
        )

        count = 0

        for loan in loans:
            for item in getattr(loan, "items", []) or []:
                equipment = getattr(item, "equipment", None)

                if equipment and not equipment.validado:
                    count += 1
                    break

        return count

    @staticmethod
    def get_backup_status() -> dict[str, Any]:
        """
        Verifica informações básicas de backup.
        """

        try:
            automatic_backup = BackupService.get_automatic_backup()

            if not automatic_backup:
                return {
                    "status": "warning",
                    "message": "Nenhum backup automático encontrado.",
                    "automatic_backup": None,
                }

            created_at = automatic_backup.get("created_at")
            age_days = None

            if created_at:
                age_days = (datetime.utcnow() - created_at).days

            status = "success"

            if age_days is not None and age_days > 7:
                status = "warning"

            return {
                "status": status,
                "message": "Backup automático encontrado.",
                "automatic_backup": automatic_backup,
                "age_days": age_days,
            }

        except Exception as exc:
            return {
                "status": "danger",
                "message": "Erro ao verificar backup automático.",
                "error": str(exc),
                "automatic_backup": None,
            }

    @staticmethod
    def get_external_pending_status() -> dict[str, Any]:
        active_count = ExternalPendingService.count_active_pendings()

        error_count = (
            ExternalPending.query
            .filter(ExternalPending.status == ExternalPendingService.STATUS_ERRO)
            .count()
        )

        latest_errors = (
            ExternalPending.query
            .filter(ExternalPending.status == ExternalPendingService.STATUS_ERRO)
            .order_by(ExternalPending.last_attempt_at.desc())
            .limit(10)
            .all()
        )

        return {
            "active_count": active_count,
            "error_count": error_count,
            "latest_errors": latest_errors,
            "status": "danger" if error_count > 0 else ("warning" if active_count > 0 else "success"),
        }

    @staticmethod
    def get_sync_status() -> dict[str, Any]:
        active_count = SyncPendingService.count_active_pendings()

        return {
            "active_count": active_count,
            "status": "danger" if active_count > 0 else "success",
        }

    @staticmethod
    def get_loan_status() -> dict[str, Any]:
        overdue_loans = (
            Loan.query
            .filter(Loan.status == LoanStatus.ATRASADO.value)
            .order_by(Loan.data_prevista_devolucao.asc())
            .limit(10)
            .all()
        )

        pending_approval_loans = (
            Loan.query
            .filter(Loan.status == LoanStatus.PENDENTE_APROVACAO.value)
            .order_by(Loan.created_at.desc())
            .limit(10)
            .all()
        )

        return {
            "overdue_loans": overdue_loans,
            "pending_approval_loans": pending_approval_loans,
        }

    @staticmethod
    def get_email_status() -> dict[str, Any]:
        latest_failed_emails = (
            EmailLog.query
            .filter(EmailLog.success.is_(False))
            .order_by(EmailLog.created_at.desc())
            .limit(10)
            .all()
        )

        return {
            "latest_failed_emails": latest_failed_emails,
            "failed_count": len(latest_failed_emails),
            "status": "danger" if latest_failed_emails else "success",
        }