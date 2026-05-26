from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from models.loan import Loan
from models.loan_item import LoanItem


def loan_full_options() -> tuple[Any, ...]:
    """
    Opções de carregamento para telas que mostram empréstimos completos.

    Usamos getattr(...) para evitar erros do Pylance com relacionamentos
    dinâmicos do SQLAlchemy.

    Evita várias consultas pequenas ao acessar:
    - loan.user
    - loan.approver
    - loan.items
    - item.equipment
    """

    loan_user = getattr(Loan, "user")
    loan_approver = getattr(Loan, "approver")
    loan_items = getattr(Loan, "items")
    item_equipment = getattr(LoanItem, "equipment")

    return (
        joinedload(loan_user),
        joinedload(loan_approver),
        selectinload(loan_items).joinedload(item_equipment),
    )


def loan_item_history_options() -> tuple[Any, ...]:
    """
    Opções de carregamento para histórico do equipamento.

    Carrega:
    - item.loan
    - item.loan.user
    - item.loan.approver
    - item.equipment
    """

    item_loan = getattr(LoanItem, "loan")
    item_equipment = getattr(LoanItem, "equipment")
    loan_user = getattr(Loan, "user")
    loan_approver = getattr(Loan, "approver")

    return (
        joinedload(item_loan).joinedload(loan_user),
        joinedload(item_loan).joinedload(loan_approver),
        joinedload(item_equipment),
    )