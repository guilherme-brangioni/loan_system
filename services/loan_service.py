from datetime import datetime, timedelta
from typing import List, cast, Optional

from flask import current_app

from database.database import db

from models.approver import Approver
from models.consumable import Consumable
from models.equipment import Equipment
from models.loan import Loan
from models.loan_item import LoanItem
from models.renewal import Renewal
from models.user import User

from enums.equipment_status import EquipmentStatus
from enums.item_type import ItemType
from enums.loan_item_status import LoanItemStatus
from enums.loan_status import LoanStatus

from services.approval_service import ApprovalService
from services.audit_service import AuditService
from services.equipment_service import EquipmentService
from services.notification_recipient_service import NotificationRecipientService

from utils.control_number import generate_control_number
from utils.form_helpers import get_date, get_optional, get_required
from utils.normalize import normalize_name


class LoanService:
    """
    Serviço principal de empréstimos.

    Correção importante:
    Todos os models SQLAlchemy são criados vazios e depois preenchidos.
    Isso elimina erros do Pylance como:
    'No parameter named data_emprestimo'.
    """

    @staticmethod
    def _get_loan_items(loan: Loan) -> List[LoanItem]:
        """
        Retorna os itens do empréstimo com tipagem explícita.

        Isso resolve alertas do Pylance em loan.items.
        """
        return cast(List[LoanItem], loan.items)

    @staticmethod
    def _get_item_equipment(item: LoanItem) -> Optional[Equipment]:
        """
        Retorna o equipamento do item com tipagem explícita.

        Isso resolve alertas do Pylance em item.equipment.status.
        """
        return cast(Optional[Equipment], item.equipment)

    @staticmethod
    def _get_item_consumable(item: LoanItem) -> Optional[Consumable]:
        """
        Retorna o consumível do item com tipagem explícita.

        Isso resolve alertas do Pylance em item.consumable.quantidade.
        """
        return cast(Optional[Consumable], item.consumable)

    @staticmethod
    def _get_loan_approver(loan: Loan) -> Approver:
        """
        Retorna o aprovador com tipagem explícita.
        """
        return cast(Approver, loan.approver)

    @staticmethod
    def get_or_create_user(data: dict) -> User:
        matricula = normalize_name(
            get_required(data, "matricula", "Matrícula")
        )

        user = User.query.filter_by(matricula=matricula).first()

        if user:
            user.nome = normalize_name(
                get_required(data, "nome", "Nome do solicitante")
            )
            user.email = get_required(data, "email", "E-mail do solicitante")
            user.telefone = get_optional(data, "telefone")
            user.gerencia = normalize_name(get_optional(data, "gerencia"))
            user.regional = normalize_name(get_optional(data, "regional"))
            user.equipe = normalize_name(get_optional(data, "equipe"))

            db.session.commit()
            return user

        user = User()

        user.nome = normalize_name(
            get_required(data, "nome", "Nome do solicitante")
        )
        user.matricula = matricula
        user.email = get_required(data, "email", "E-mail do solicitante")
        user.telefone = get_optional(data, "telefone")
        user.gerencia = normalize_name(get_optional(data, "gerencia"))
        user.regional = normalize_name(get_optional(data, "regional"))
        user.equipe = normalize_name(get_optional(data, "equipe"))

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def get_or_create_approver(data: dict) -> Approver:
        email = get_required(
            data,
            "approver_email",
            "E-mail do aprovador",
        ).lower()

        approver = Approver.query.filter_by(email=email).first()

        if approver:
            approver.nome = normalize_name(
                get_required(data, "approver_nome", "Nome do aprovador")
            )
            approver.matricula = normalize_name(
                get_optional(data, "approver_matricula")
            )

            db.session.commit()
            return approver

        approver = Approver()

        approver.nome = normalize_name(
            get_required(data, "approver_nome", "Nome do aprovador")
        )
        approver.matricula = normalize_name(
            get_optional(data, "approver_matricula")
        )
        approver.email = email

        db.session.add(approver)
        db.session.commit()

        return approver

    @staticmethod
    def user_has_overdue(user_id: int) -> bool:
        overdue = Loan.query.filter(
            Loan.user_id == user_id,
            Loan.status == LoanStatus.ATRASADO.value,
        ).first()

        return overdue is not None

    @staticmethod
    def validate_due_date(data_prevista: datetime) -> None:
        max_days = current_app.config["MAX_LOAN_DAYS"]
        today = datetime.utcnow()

        max_due_date = today + timedelta(days=max_days)

        if data_prevista > max_due_date:
            raise ValueError(
                f"Prazo máximo excedido. O limite é de {max_days} dias."
            )

        if data_prevista.date() < today.date():
            raise ValueError(
                "A data prevista de devolução não pode estar no passado."
            )

    @staticmethod
    def parse_items_text(items_text: str) -> List[dict]:
        items = []

        for line in items_text.splitlines():
            line = line.strip()

            if not line:
                continue

            parts = [part.strip() for part in line.split("|")]

            if len(parts) < 2:
                raise ValueError(f"Linha inválida: {line}")

            tipo = normalize_name(parts[0])
            nome = parts[1]
            campo_3 = parts[2] if len(parts) >= 3 else ""
            categoria = parts[3] if len(parts) >= 4 else ""

            if tipo not in [
                ItemType.PATRIMONIAL.value,
                ItemType.CONSUMIVEL.value,
            ]:
                raise ValueError(
                    f"Tipo inválido na linha: {line}. "
                    "Use PATRIMONIAL ou CONSUMIVEL."
                )

            items.append(
                {
                    "tipo": tipo,
                    "nome": nome,
                    "campo_3": campo_3,
                    "categoria": categoria,
                }
            )

        if not items:
            raise ValueError("Informe ao menos um item.")

        return items

    @staticmethod
    def create_loan(form_data: dict) -> Loan:
        user = LoanService.get_or_create_user(form_data)
        approver = LoanService.get_or_create_approver(form_data)

        if LoanService.user_has_overdue(user.id):
            raise ValueError(
                "Solicitante possui empréstimo em atraso. "
                "Novo empréstimo bloqueado."
            )

        data_prevista = get_date(
            form_data,
            "data_prevista_devolucao",
            "Data prevista de devolução",
        )

        if data_prevista is None:
            raise ValueError("Data prevista de devolução inválida.")

        LoanService.validate_due_date(data_prevista)

        selected_equipment_ids = form_data.get("selected_equipment_ids", [])

        if not isinstance(selected_equipment_ids, list):
            raise ValueError("Lista de equipamentos selecionados inválida.")

        if not selected_equipment_ids:
            raise ValueError("Informe ao menos um equipamento/material.")

        loan = Loan()

        loan.user_id = user.id
        loan.approver_id = approver.id
        loan.responsavel_entrega_nome = normalize_name(
            get_required(
                form_data,
                "responsavel_entrega_nome",
                "Responsável pela entrega",
            )
        )
        loan.responsavel_entrega_matricula = normalize_name(
            get_optional(form_data, "responsavel_entrega_matricula")
        )
        loan.responsavel_entrega_email = get_required(
            form_data,
            "responsavel_entrega_email",
            "E-mail do responsável pela coleta/entrega",
        ).lower()
        loan.local_utilizacao = normalize_name(
            get_optional(form_data, "local_utilizacao")
        )
        loan.data_emprestimo = datetime.utcnow()
        loan.data_prevista_devolucao = data_prevista
        loan.status = LoanStatus.PENDENTE_APROVACAO.value
        loan.observacoes = get_optional(form_data, "observacoes")

        fixed_notification_emails = (
            NotificationRecipientService.get_fixed_notification_emails()
        )

        extra_notification_emails = form_data.get(
            "notification_extra_emails",
            [],
        )

        if not isinstance(extra_notification_emails, list):
            extra_notification_emails = (
                NotificationRecipientService.parse_email_list(
                    str(extra_notification_emails)
                )
            )

        all_notification_emails = (
            NotificationRecipientService.merge_recipients(
                fixed_notification_emails,
                extra_notification_emails + [user.email],
            )
        )

        loan.notification_fixed_emails = (
            NotificationRecipientService.to_json(fixed_notification_emails)
        )

        loan.notification_extra_emails = (
            NotificationRecipientService.to_json(extra_notification_emails)
        )

        loan.notification_all_emails = (
            NotificationRecipientService.to_json(all_notification_emails)
        )

        db.session.add(loan)
        db.session.commit()

        loan.numero_controle = generate_control_number(loan.id)
        loan.approval_token = ApprovalService.generate_token(loan.id)

        db.session.commit()

        seen_equipment_ids = set()

        for equipment_id_text in selected_equipment_ids:
            try:
                equipment_id = int(equipment_id_text)
            except ValueError:
                raise ValueError(f"ID de equipamento inválido: {equipment_id_text}")

            if equipment_id in seen_equipment_ids:
                raise ValueError(
                    f"Equipamento duplicado na solicitação: ID {equipment_id}"
                )

            seen_equipment_ids.add(equipment_id)

            equipment = db.session.get(Equipment, equipment_id)

            if not equipment:
                raise ValueError(
                    f"Equipamento não encontrado: ID {equipment_id}"
                )

            if equipment.status != EquipmentStatus.DISPONIVEL.value:
                raise ValueError(
                    f"Equipamento indisponível: {equipment.nome} "
                    f"({equipment.codigo_interno})"
                )

            equipment.status = EquipmentStatus.RESERVADO.value

            loan_item = LoanItem()

            loan_item.loan_id = loan.id
            loan_item.equipment_id = equipment.id
            loan_item.tipo_item = ItemType.PATRIMONIAL.value
            loan_item.quantidade = 1
            loan_item.quantidade_devolvida = 0
            loan_item.status = LoanItemStatus.EMPRESTADO.value

            db.session.add(loan_item)

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="CREATE_LOAN",
            performed_by=loan.responsavel_entrega_nome,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
            },
        )

        return loan

    @staticmethod
    def approve_loan(token: str) -> Loan:
        data = ApprovalService.validate_token(token)

        if not data:
            raise ValueError("Token inválido ou expirado.")

        loan = Loan.query.get_or_404(data["loan_id"])

        if loan.status != LoanStatus.PENDENTE_APROVACAO.value:
            raise ValueError(
                f"Empréstimo não está pendente. Status atual: {loan.status}"
            )

        loan.aprovado = True
        loan.aprovado_em = datetime.utcnow()
        loan.status = LoanStatus.APROVADO.value

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="APPROVE_LOAN",
            performed_by=loan.approver.nome,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
            },
        )

        return loan

    @staticmethod
    def reject_loan(token: str, reason: str = "") -> Loan:
        """
        Rejeita um empréstimo pendente de aprovação.

        Ao rejeitar:
        - equipamentos reservados voltam para DISPONIVEL
        - consumíveis têm o estoque devolvido
        - itens do empréstimo são marcados como CANCELADO
        """

        data = ApprovalService.validate_token(token)

        if not data:
            raise ValueError("Token inválido ou expirado.")

        loan = Loan.query.get_or_404(data["loan_id"])

        if loan.status != LoanStatus.PENDENTE_APROVACAO.value:
            raise ValueError(
                f"Empréstimo não está pendente. Status atual: {loan.status}"
            )

        loan.status = LoanStatus.REJEITADO.value
        loan.rejeitado_em = datetime.utcnow()
        loan.motivo_rejeicao = reason or "Rejeitado pelo aprovador."

        for item in LoanService._get_loan_items(loan):
            item.status = LoanItemStatus.CANCELADO.value

            equipment = LoanService._get_item_equipment(item)

            if equipment is not None:
                equipment.status = EquipmentStatus.DISPONIVEL.value

            consumable = LoanService._get_item_consumable(item)

            if consumable is not None:
                consumable.quantidade += item.quantidade

        db.session.commit()

        approver = LoanService._get_loan_approver(loan)

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="REJECT_LOAN",
            performed_by=approver.nome,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
                "reason": reason,
            },
        )

        return loan

    @staticmethod
    def confirm_withdrawal(loan_id: int, performed_by: str) -> Loan:
        """
        Confirma a retirada dos itens.

        Ao confirmar:
        - empréstimo muda para RETIRADO
        - equipamentos reservados mudam para EMPRESTADO
        - consumíveis permanecem apenas abatidos no estoque
        """

        loan = Loan.query.get_or_404(loan_id)

        if loan.status != LoanStatus.APROVADO.value:
            raise ValueError(
                "Somente empréstimos aprovados podem ter retirada confirmada."
            )

        loan.status = LoanStatus.RETIRADO.value

        for item in LoanService._get_loan_items(loan):
            equipment = LoanService._get_item_equipment(item)

            if equipment is not None:
                equipment.status = EquipmentStatus.EMPRESTADO.value

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="CONFIRM_WITHDRAWAL",
            performed_by=performed_by,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
            },
        )

        return loan

    @staticmethod
    def return_item(
        loan_item_id: int,
        quantidade: int,
        devolvido_por: str,
    ) -> Loan:
        item = LoanItem.query.get_or_404(loan_item_id)
        loan = cast(Loan, item.loan)

        if item.status == LoanItemStatus.DEVOLVIDO.value:
            raise ValueError("Este item já foi devolvido.")

        if item.equipment:
            item.quantidade_devolvida = 1
            item.status = LoanItemStatus.DEVOLVIDO.value
            item.devolvido_em = datetime.utcnow()
            item.devolvido_por = normalize_name(devolvido_por)

            

        elif LoanService._get_item_consumable(item):
            consumable = LoanService._get_item_consumable(item)

            if consumable is None:
                raise ValueError("Consumível não encontrado para este item.")

            quantidade = int(quantidade or 0)

            if quantidade <= 0:
                raise ValueError("Quantidade devolvida deve ser maior que zero.")

            restante = item.quantidade - item.quantidade_devolvida

            if quantidade > restante:
                raise ValueError(
                    f"Quantidade maior que o restante. Restante: {restante}"
                )

            item.quantidade_devolvida += quantidade

            # Aqui o estoque do consumível volta a aumentar.
            consumable.quantidade += quantidade

            item.devolvido_por = normalize_name(devolvido_por)
            item.devolvido_em = datetime.utcnow()

            if item.quantidade_devolvida == item.quantidade:
                item.status = LoanItemStatus.DEVOLVIDO.value
            else:
                item.status = LoanItemStatus.PARCIALMENTE_DEVOLVIDO.value

        LoanService._refresh_loan_status(loan)

        db.session.commit()

        AuditService.register(
            entity_type="LOAN_ITEM",
            entity_id=item.id,
            action="RETURN_ITEM",
            performed_by=devolvido_por,
            new_data={
                "loan": loan.numero_controle,
                "item_status": item.status,
                "quantidade_devolvida": item.quantidade_devolvida,
            },
        )

        return loan

    @staticmethod
    def _refresh_loan_status(loan: Loan) -> None:
        """
        Atualiza o status do empréstimo conforme a devolução dos itens.

        Se todos os itens foram devolvidos:
        - FINALIZADO

        Se apenas parte dos itens foi devolvida:
        - PARCIALMENTE_DEVOLVIDO
        """

        loan_items = LoanService._get_loan_items(loan)

        total_items = len(loan_items)

        returned_items = sum(
            1
            for item in loan_items
            if item.status == LoanItemStatus.DEVOLVIDO.value
        )

        if total_items == 0:
            return

        if returned_items == total_items:
            loan.status = LoanStatus.FINALIZADO.value
            loan.data_real_devolucao = datetime.utcnow()

        elif returned_items > 0:
            loan.status = LoanStatus.PARCIALMENTE_DEVOLVIDO.value

    @staticmethod
    def renew_loan(
        loan_id: int,
        new_due_date_text: str,
        renewed_by: str,
        reason: str,
    ) -> Loan:
        loan = Loan.query.get_or_404(loan_id)

        form_data = {
            "new_due_date": new_due_date_text,
        }

        new_due_date = get_date(
            form_data,
            "new_due_date",
            "Nova data de devolução",
        )

        if new_due_date is None:
            raise ValueError("Nova data de devolução inválida.")

        LoanService.validate_due_date(new_due_date)

        renewal = Renewal()

        renewal.loan_id = loan.id
        renewal.old_due_date = loan.data_prevista_devolucao
        renewal.new_due_date = new_due_date
        renewal.renewed_by = normalize_name(renewed_by)
        renewal.reason = reason

        old_due = loan.data_prevista_devolucao
        loan.data_prevista_devolucao = new_due_date

        db.session.add(renewal)
        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="RENEW_LOAN",
            performed_by=renewed_by,
            old_data={
                "old_due_date": old_due,
            },
            new_data={
                "new_due_date": new_due_date,
            },
        )

        return loan

    @staticmethod
    def mark_overdue_loans():
        now = datetime.utcnow()

        loans = Loan.query.filter(
            Loan.status.in_(
                [
                    LoanStatus.RETIRADO.value,
                    LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
                ]
            ),
            Loan.data_prevista_devolucao < now,
        ).all()

        for loan in loans:
            loan.status = LoanStatus.ATRASADO.value

        db.session.commit()

        return loans
    
    @staticmethod
    def get_loan_by_approval_token(token: str) -> Loan:
        """
        Busca um empréstimo a partir do token de aprovação.

        Usado para abrir a tela de revisão antes de aprovar/rejeitar.
        """

        data = ApprovalService.validate_token(token)

        if not data:
            raise ValueError("Token inválido ou expirado.")

        loan = Loan.query.get_or_404(data["loan_id"])

        return loan
    
    @staticmethod
    def return_all_items(
        loan_id: int,
        devolvido_por: str,
    ) -> Loan:
        """
        Marca todos os itens pendentes do empréstimo como devolvidos.

        Uso:
        - devolução antecipada;
        - devolução total de todos os equipamentos;
        - encerramento rápido do empréstimo.

        Regras:
        - só pode devolver empréstimos RETIRADO, PARCIALMENTE_DEVOLVIDO ou ATRASADO;
        - equipamentos voltam para DISPONIVEL;
        - empréstimo muda para FINALIZADO;
        - data_real_devolucao é preenchida.
        """

        loan = Loan.query.get_or_404(loan_id)

        allowed_statuses = [
            LoanStatus.RETIRADO.value,
            LoanStatus.PARCIALMENTE_DEVOLVIDO.value,
            LoanStatus.ATRASADO.value,
        ]

        if loan.status not in allowed_statuses:
            raise ValueError(
                "Somente empréstimos retirados, parcialmente devolvidos "
                "ou atrasados podem ser marcados como devolvidos."
            )

        devolvido_por_normalizado = normalize_name(devolvido_por)

        if not devolvido_por_normalizado:
            raise ValueError("Informe quem recebeu a devolução.")

        for item in LoanService._get_loan_items(loan):
            if item.status == LoanItemStatus.DEVOLVIDO.value:
                continue

            equipment = LoanService._get_item_equipment(item)

            if equipment is not None:
                equipment.status = EquipmentStatus.DISPONIVEL.value

            # Mantém compatibilidade caso ainda exista algum consumível antigo.
            consumable = LoanService._get_item_consumable(item)

            if consumable is not None:
                quantidade_restante = item.quantidade - item.quantidade_devolvida

                if quantidade_restante > 0:
                    consumable.quantidade += quantidade_restante
                    item.quantidade_devolvida = item.quantidade

            item.status = LoanItemStatus.DEVOLVIDO.value
            item.quantidade_devolvida = item.quantidade
            item.devolvido_em = datetime.utcnow()
            item.devolvido_por = devolvido_por_normalizado

        loan.status = LoanStatus.FINALIZADO.value
        loan.data_real_devolucao = datetime.utcnow()

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="RETURN_ALL_ITEMS",
            performed_by=devolvido_por_normalizado,
            new_data={
                "numero_controle": loan.numero_controle,
                "status": loan.status,
                "data_real_devolucao": loan.data_real_devolucao,
            },
        )

        return loan