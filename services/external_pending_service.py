from datetime import datetime
from typing import Any

from database.database import db

from models.external_pending import ExternalPending
from models.loan import Loan

from services.email_log_service import EmailLogService
from services.email_service import EmailService
from services.excel_movement_service import ExcelMovementService
from services.notification_recipient_service import NotificationRecipientService
from services.pdf_service import PDFService


class ExternalPendingService:
    """
    Serviço de pendências externas.

    Mantém fora do fluxo principal tarefas que podem ser lentas:
    - enviar e-mail;
    - gerar PDF;
    - exportar para Excel.
    """

    STATUS_PENDENTE = "PENDENTE"
    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_ERRO = "ERRO"
    STATUS_RESOLVIDO = "RESOLVIDO"

    ACTION_GENERATE_LOAN_PDF = "GENERATE_LOAN_PDF"
    ACTION_SEND_LOAN_RECEIPT_EMAIL = "SEND_LOAN_RECEIPT_EMAIL"
    ACTION_SEND_RETURN_CONFIRMATION_EMAIL = "SEND_RETURN_CONFIRMATION_EMAIL"
    ACTION_EXPORT_LOAN_MOVEMENT = "EXPORT_LOAN_MOVEMENT"

    @staticmethod
    def _active_statuses() -> list[str]:
        return [
            ExternalPendingService.STATUS_PENDENTE,
            ExternalPendingService.STATUS_ERRO,
        ]

    @staticmethod
    def create_pending(
        action: str,
        entity_type: str,
        entity_id: int,
        payload: dict | None = None,
        created_by: str = "SISTEMA",
        dedupe_key: str | None = None,
        max_attempts: int = 5,
    ) -> ExternalPending:
        """
        Cria uma pendência.

        Se existir pendência ativa com a mesma dedupe_key, reaproveita.
        Isso evita duplicidade de e-mail/exportação.
        """

        if dedupe_key:
            existing = (
                ExternalPending.query
                .filter(
                    ExternalPending.dedupe_key == dedupe_key,
                    ExternalPending.status.in_(ExternalPendingService._active_statuses()),
                )
                .first()
            )

            if existing:
                return existing

        pending = ExternalPending()
        pending.action = action
        pending.entity_type = entity_type
        pending.entity_id = entity_id
        pending.status = ExternalPendingService.STATUS_PENDENTE
        pending.created_by = created_by
        pending.dedupe_key = dedupe_key
        pending.max_attempts = max_attempts
        pending.set_payload(payload or {})

        db.session.add(pending)
        db.session.commit()

        return pending

    @staticmethod
    def enqueue_loan_pdf(
        loan_id: int,
        created_by: str = "SISTEMA",
    ) -> ExternalPending:
        return ExternalPendingService.create_pending(
            action=ExternalPendingService.ACTION_GENERATE_LOAN_PDF,
            entity_type="LOAN",
            entity_id=loan_id,
            created_by=created_by,
            dedupe_key=f"PDF:{loan_id}",
        )

    @staticmethod
    def enqueue_loan_receipt_email(
        loan_id: int,
        created_by: str = "SISTEMA",
    ) -> ExternalPending:
        return ExternalPendingService.create_pending(
            action=ExternalPendingService.ACTION_SEND_LOAN_RECEIPT_EMAIL,
            entity_type="LOAN",
            entity_id=loan_id,
            created_by=created_by,
            dedupe_key=f"EMAIL_RECEIPT:{loan_id}",
        )

    @staticmethod
    def enqueue_return_confirmation_email(
        loan_id: int,
        returned_by: str,
        return_type: str,
        created_by: str = "SISTEMA",
        source_item_id: int | None = None,
    ) -> ExternalPending:
        payload: dict[str, Any] = {
            "returned_by": returned_by,
            "return_type": return_type,
        }

        dedupe_key = f"EMAIL_RETURN:{return_type}:{loan_id}:{returned_by}"

        if source_item_id is not None:
            payload["source_item_id"] = source_item_id
            dedupe_key = f"{dedupe_key}:ITEM:{source_item_id}"

        return ExternalPendingService.create_pending(
            action=ExternalPendingService.ACTION_SEND_RETURN_CONFIRMATION_EMAIL,
            entity_type="LOAN",
            entity_id=loan_id,
            payload=payload,
            created_by=created_by,
            dedupe_key=dedupe_key,
        )

    @staticmethod
    def enqueue_loan_movement(
        loan_id: int,
        movement_type: str,
        performed_by: str = "",
        notes: str = "",
        created_by: str = "SISTEMA",
        source_item_id: int | None = None,
    ) -> ExternalPending:
        payload: dict[str, Any] = {
            "movement_type": movement_type,
            "performed_by": performed_by,
            "notes": notes,
        }

        dedupe_key = f"MOVEMENT:{movement_type}:{loan_id}"

        if source_item_id is not None:
            payload["source_item_id"] = source_item_id
            dedupe_key = f"{dedupe_key}:ITEM:{source_item_id}"

        return ExternalPendingService.create_pending(
            action=ExternalPendingService.ACTION_EXPORT_LOAN_MOVEMENT,
            entity_type="LOAN",
            entity_id=loan_id,
            payload=payload,
            created_by=created_by,
            dedupe_key=dedupe_key,
        )
    
    @staticmethod
    def enqueue_and_process_return_pendings(
        loan_id: int,
        returned_by: str,
        return_type: str,
        created_by: str = "SISTEMA",
        source_item_id: int | None = None,
    ) -> dict:
        """
        Cria e processa imediatamente as pendências externas de devolução.

        Usado em:
        - devolução parcial;
        - devolução total.

        Se alguma pendência falhar, ela permanece como ERRO.
        """

        pending_movement = ExternalPendingService.enqueue_loan_movement(
            loan_id=loan_id,
            movement_type=return_type,
            performed_by=returned_by,
            notes=(
                "Devolução total registrada."
                if return_type == "DEVOLUCAO_TOTAL"
                else "Devolução de item registrada."
            ),
            created_by=created_by,
            source_item_id=source_item_id,
        )

        pending_email = ExternalPendingService.enqueue_return_confirmation_email(
            loan_id=loan_id,
            returned_by=returned_by,
            return_type=return_type,
            created_by=created_by,
            source_item_id=source_item_id,
        )

        return ExternalPendingService.process_pendings(
            pendings=[
                pending_movement,
                pending_email,
            ],
            performed_by=returned_by,
        )

    @staticmethod
    def list_active_pendings():
        return (
            ExternalPending.query
            .filter(
                ExternalPending.status.in_(ExternalPendingService._active_statuses())
            )
            .order_by(
                ExternalPending.created_at.asc(),
                ExternalPending.id.asc(),
            )
            .all()
        )
    
    @staticmethod
    def count_active_pendings() -> int:
        """
        Conta pendências externas ainda não resolvidas.

        Considera ativas:
        - PENDENTE
        - ERRO
        """

        return (
            ExternalPending.query
            .filter(
                ExternalPending.status.in_(
                    ExternalPendingService._active_statuses()
                )
            )
            .count()
        )

    @staticmethod
    def list_resolved_pendings(limit: int = 100):
        return (
            ExternalPending.query
            .filter_by(status=ExternalPendingService.STATUS_RESOLVIDO)
            .order_by(ExternalPending.resolved_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def process_pending(
        pending: ExternalPending,
        performed_by: str = "SISTEMA",
    ) -> dict[str, Any]:
        """
        Processa uma pendência.
        """

        if pending.status == ExternalPendingService.STATUS_RESOLVIDO:
            return {
                "success": True,
                "message": "Pendência já resolvida.",
            }

        pending.status = ExternalPendingService.STATUS_PROCESSANDO
        pending.attempts = int(pending.attempts or 0) + 1
        pending.last_attempt_at = datetime.utcnow()
        db.session.commit()

        try:
            if pending.action == ExternalPendingService.ACTION_GENERATE_LOAN_PDF:
                result = ExternalPendingService._process_generate_loan_pdf(pending)

            elif pending.action == ExternalPendingService.ACTION_SEND_LOAN_RECEIPT_EMAIL:
                result = ExternalPendingService._process_send_loan_receipt_email(pending)

            elif pending.action == ExternalPendingService.ACTION_SEND_RETURN_CONFIRMATION_EMAIL:
                result = ExternalPendingService._process_send_return_confirmation_email(pending)

            elif pending.action == ExternalPendingService.ACTION_EXPORT_LOAN_MOVEMENT:
                result = ExternalPendingService._process_export_loan_movement(pending)

            else:
                raise ValueError(f"Ação não suportada: {pending.action}")

            pending.status = ExternalPendingService.STATUS_RESOLVIDO
            pending.last_error = None
            pending.resolved_by = performed_by
            pending.resolved_at = datetime.utcnow()
            db.session.commit()

            return {
                "success": True,
                "result": result,
            }

        except Exception as exc:
            pending.status = ExternalPendingService.STATUS_ERRO
            pending.last_error = str(exc)
            db.session.commit()

            return {
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def process_all_active(
        performed_by: str = "SISTEMA",
    ) -> dict:
        pendings = ExternalPendingService.list_active_pendings()

        total = len(pendings)
        success = 0
        failed = 0

        for pending in pendings:
            result = ExternalPendingService.process_pending(
                pending=pending,
                performed_by=performed_by,
            )

            if result.get("success"):
                success += 1
            else:
                failed += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
        }

    @staticmethod
    def _get_loan_or_raise(loan_id: int) -> Loan:
        loan = db.session.get(Loan, loan_id)

        if not loan:
            raise ValueError(f"Empréstimo ID {loan_id} não encontrado.")

        return loan

    @staticmethod
    def _process_generate_loan_pdf(pending: ExternalPending) -> dict:
        loan = ExternalPendingService._get_loan_or_raise(pending.entity_id)

        pdf_path = PDFService.generate_loan_pdf(loan)

        return {
            "pdf_path": pdf_path,
        }

    @staticmethod
    def _process_send_loan_receipt_email(pending: ExternalPending) -> dict:
        loan = ExternalPendingService._get_loan_or_raise(pending.entity_id)

        pdf_path = PDFService.generate_loan_pdf(loan)

        recipients = NotificationRecipientService.get_loan_receipt_recipients(loan)

        if not recipients:
            raise ValueError("Nenhum destinatário encontrado para o comprovante.")

        subject = f"Comprovante de empréstimo - {loan.numero_controle}"

        body = EmailService.build_loan_receipt_body(loan)

        result = EmailService.try_send_email(
            recipients=recipients,
            subject=subject,
            body=body,
            attachment_path=pdf_path,
        )

        EmailLogService.register(
            email_type="LOAN_RECEIPT_ASYNC",
            loan_id=loan.id,
            recipients=recipients,
            subject=subject,
            success=bool(result.get("success")),
            error=result.get("error"),
        )

        if not result.get("success"):
            raise ValueError(result.get("error", "Falha ao enviar e-mail."))

        return result

    @staticmethod
    def _process_send_return_confirmation_email(pending: ExternalPending) -> dict:
        loan = ExternalPendingService._get_loan_or_raise(pending.entity_id)

        payload = pending.get_payload()

        returned_by = str(payload.get("returned_by", "")).strip()
        return_type = str(payload.get("return_type", "DEVOLUCAO")).strip()

        pdf_path = PDFService.generate_loan_pdf(loan)

        recipients = NotificationRecipientService.get_loan_receipt_recipients(loan)

        if not recipients:
            raise ValueError("Nenhum destinatário encontrado para confirmação de devolução.")

        if return_type == "DEVOLUCAO_TOTAL":
            subject = f"Confirmação de devolução total - {loan.numero_controle}"
            email_type = "RETURN_TOTAL_CONFIRMATION_ASYNC"
        else:
            subject = f"Confirmação de devolução - {loan.numero_controle}"
            email_type = "RETURN_CONFIRMATION_ASYNC"

        body = EmailService.build_return_confirmation_body(
            loan=loan,
            returned_by=returned_by,
            return_type=return_type,
        )

        result = EmailService.try_send_email(
            recipients=recipients,
            subject=subject,
            body=body,
            attachment_path=pdf_path,
        )

        EmailLogService.register(
            email_type=email_type,
            loan_id=loan.id,
            recipients=recipients,
            subject=subject,
            success=bool(result.get("success")),
            error=result.get("error"),
        )

        if not result.get("success"):
            raise ValueError(result.get("error", "Falha ao enviar e-mail."))

        return result

    @staticmethod
    def _process_export_loan_movement(pending: ExternalPending) -> dict:
        loan = ExternalPendingService._get_loan_or_raise(pending.entity_id)

        payload = pending.get_payload()

        movement_type = str(payload.get("movement_type", "")).strip()
        performed_by = str(payload.get("performed_by", "")).strip()
        notes = str(payload.get("notes", "")).strip()

        if not movement_type:
            raise ValueError("Tipo de movimentação não informado.")

        return ExcelMovementService.append_loan_movement(
            loan=loan,
            movement_type=movement_type,
            performed_by=performed_by,
            notes=notes,
        )
    
    @staticmethod
    def process_pendings(
        pendings: list[ExternalPending],
        performed_by: str = "SISTEMA",
    ) -> dict:
        """
        Processa uma lista específica de pendências.

        Usado quando queremos processar imediatamente apenas as pendências
        criadas por uma ação específica.
        """

        total = 0
        success = 0
        failed = 0

        processed_ids = set()

        for pending in pendings:
            if not pending:
                continue

            if pending.id in processed_ids:
                continue

            processed_ids.add(pending.id)
            total += 1

            result = ExternalPendingService.process_pending(
                pending=pending,
                performed_by=performed_by,
            )

            if result.get("success"):
                success += 1
            else:
                failed += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
        }