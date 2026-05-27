from flask import current_app
from itsdangerous import URLSafeTimedSerializer

from datetime import datetime

from sqlalchemy import func

from database.database import db

from enums.equipment_status import EquipmentStatus
from enums.loan_item_status import LoanItemStatus
from enums.loan_status import LoanStatus
from enums.user_role import UserRole

from models.approver import Approver
from models.loan import Loan

from services.audit_service import AuditService
from services.auth_service import AuthService
from services.external_pending_service import ExternalPendingService

from utils.query_options import loan_full_options


class ApprovalService:
    """
    Serviço de geração e validação de tokens.

    O token evita links simples como /aprovar?id=1.
    """

    SALT = "loan-approval"

    @staticmethod
    def _serializer():
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    @staticmethod
    def generate_token(loan_id: int) -> str:
        serializer = ApprovalService._serializer()

        return serializer.dumps(
            {"loan_id": loan_id},
            salt=ApprovalService.SALT,
        )

    @staticmethod
    def validate_token(token: str):
        serializer = ApprovalService._serializer()

        max_age = current_app.config["APPROVAL_TOKEN_MAX_AGE_SECONDS"]

        try:
            return serializer.loads(
                token,
                salt=ApprovalService.SALT,
                max_age=max_age,
            )
        except Exception:
            return None
        
    @staticmethod
    def _normalize_email(email: str) -> str:
        """
        Normaliza e-mail para comparação.
        """

        return str(email or "").strip().lower()

    @staticmethod
    def get_pending_approvals_for_current_user():
        """
        Lista aprovações pendentes para o usuário logado.

        ADMIN enxerga todas as aprovações pendentes.
        Outros usuários enxergam apenas aprovações direcionadas ao próprio e-mail.
        """

        current_user = AuthService.get_current_user()

        if not current_user:
            return []

        query = (
            Loan.query
            .options(*loan_full_options())
            .join(Approver, Loan.approver_id == Approver.id)
            .filter(Loan.status == LoanStatus.PENDENTE_APROVACAO.value)
        )

        if current_user.role == UserRole.ADMIN.value:
            return query.order_by(Loan.created_at.desc()).all()

        current_email = ApprovalService._normalize_email(current_user.email)

        if not current_email:
            return []

        return (
            query
            .filter(func.lower(Approver.email) == current_email)
            .order_by(Loan.created_at.desc())
            .all()
        )

    @staticmethod
    def count_pending_for_current_user() -> int:
        """
        Conta aprovações pendentes para exibir no menu.
        """

        current_user = AuthService.get_current_user()

        if not current_user:
            return 0

        query = (
            Loan.query
            .join(Approver, Loan.approver_id == Approver.id)
            .filter(Loan.status == LoanStatus.PENDENTE_APROVACAO.value)
        )

        if current_user.role == UserRole.ADMIN.value:
            return query.count()

        current_email = ApprovalService._normalize_email(current_user.email)

        if not current_email:
            return 0

        return (
            query
            .filter(func.lower(Approver.email) == current_email)
            .count()
        )

    @staticmethod
    def current_user_can_approve(loan: Loan) -> bool:
        """
        Verifica se o usuário logado pode aprovar/rejeitar este empréstimo.

        ADMIN pode aprovar qualquer empréstimo.
        Demais usuários só podem aprovar se o e-mail logado for igual ao e-mail do aprovador.
        """

        current_user = AuthService.get_current_user()

        if not current_user:
            return False

        if current_user.role == UserRole.ADMIN.value:
            return True

        current_email = ApprovalService._normalize_email(current_user.email)

        approver = getattr(loan, "approver", None)
        approver_email = ApprovalService._normalize_email(
            getattr(approver, "email", "")
        )

        return bool(
            current_email
            and approver_email
            and current_email == approver_email
        )

    @staticmethod
    def approve_from_system(loan_id: int, performed_by: str) -> Loan:
        """
        Aprova empréstimo pela tela interna de aprovações.
        """

        loan = db.session.get(Loan, loan_id)

        if not loan:
            raise ValueError("Empréstimo não encontrado.")

        if loan.status != LoanStatus.PENDENTE_APROVACAO.value:
            raise ValueError("Somente empréstimos pendentes podem ser aprovados.")

        if not ApprovalService.current_user_can_approve(loan):
            raise PermissionError("Você não tem permissão para aprovar este empréstimo.")

        loan.status = LoanStatus.APROVADO.value

        if hasattr(loan, "approved_at"):
            setattr(loan, "approved_at", datetime.utcnow())

        if hasattr(loan, "approval_token"):
            loan.approval_token = None

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="APPROVE_LOAN_FROM_SYSTEM",
            performed_by=performed_by,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
            },
        )

        ExternalPendingService.enqueue_loan_movement(
            loan_id=loan.id,
            movement_type="APROVACAO",
            performed_by=performed_by,
            notes="Solicitação aprovada pelo sistema.",
            created_by=performed_by,
        )

        return loan

    @staticmethod
    def reject_from_system(
        loan_id: int,
        reason: str,
        performed_by: str,
    ) -> Loan:
        """
        Rejeita empréstimo pela tela interna de aprovações.
        """

        loan = db.session.get(Loan, loan_id)

        if not loan:
            raise ValueError("Empréstimo não encontrado.")

        if loan.status != LoanStatus.PENDENTE_APROVACAO.value:
            raise ValueError("Somente empréstimos pendentes podem ser rejeitados.")

        if not ApprovalService.current_user_can_approve(loan):
            raise PermissionError("Você não tem permissão para rejeitar este empréstimo.")

        loan.status = LoanStatus.REJEITADO.value

        if hasattr(loan, "rejection_reason"):
            setattr(loan, "rejection_reason", reason)

        if hasattr(loan, "approval_token"):
            setattr(loan, "approval_token", None)

        for item in getattr(loan, "items", []) or []:
            item.status = LoanItemStatus.CANCELADO.value

            equipment = getattr(item, "equipment", None)

            if equipment:
                equipment.status = EquipmentStatus.DISPONIVEL.value

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="REJECT_LOAN_FROM_SYSTEM",
            performed_by=performed_by,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
                "reason": reason,
            },
        )

        ExternalPendingService.enqueue_loan_movement(
            loan_id=loan.id,
            movement_type="REJEICAO",
            performed_by=performed_by,
            notes=reason or "Solicitação rejeitada pelo sistema.",
            created_by=performed_by,
        )

        return loan
    
    @staticmethod
    def get_approvals_for_current_user(
        status_filter: str = "PENDENTE_APROVACAO",
        search_text: str = "",
    ):
        """
        Lista aprovações direcionadas ao usuário logado.

        ADMIN enxerga todas.
        Demais usuários enxergam apenas empréstimos onde:
        e-mail do usuário logado = e-mail do aprovador.

        Permite filtro por status e busca por controle/solicitante.
        """

        current_user = AuthService.get_current_user()

        if not current_user:
            return []

        query = (
            Loan.query
            .options(*loan_full_options())
            .join(Approver, Loan.approver_id == Approver.id)
        )

        if current_user.role != UserRole.ADMIN.value:
            current_email = ApprovalService._normalize_email(current_user.email)

            if not current_email:
                return []

            query = query.filter(func.lower(Approver.email) == current_email)

        if status_filter:
            query = query.filter(Loan.status == status_filter)

        search_text = str(search_text or "").strip()

        if search_text:
            from models.user import User

            pattern = f"%{search_text}%"

            query = (
                query
                .outerjoin(User, Loan.user_id == User.id)
                .filter(
                    (Loan.numero_controle.ilike(pattern))
                    | (Loan.status.ilike(pattern))
                    | (User.nome.ilike(pattern))
                    | (User.matricula.ilike(pattern))
                    | (User.email.ilike(pattern))
                    | (Approver.nome.ilike(pattern))
                    | (Approver.email.ilike(pattern))
                )
            )

        return (
            query
            .order_by(Loan.created_at.desc())
            .all()
        )