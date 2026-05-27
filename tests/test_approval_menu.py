from datetime import datetime, timedelta

from database.database import db

from enums.equipment_status import EquipmentStatus
from enums.loan_status import LoanStatus
from enums.loan_item_status import LoanItemStatus
from enums.item_type import ItemType

from models.approver import Approver
from models.equipment import Equipment
from models.loan import Loan
from models.loan_item import LoanItem
from models.user import User

from services.approval_service import ApprovalService


def create_pending_approval_loan(app, approver_email: str):
    with app.app_context():
        user = User()
        user.nome = "Solicitante Aprovação"
        user.matricula = "111111"
        user.email = "solicitante.aprovacao@teste.com"

        approver = Approver()
        approver.nome = "Aprovador Sistema"
        approver.matricula = "222222"
        approver.email = approver_email

        equipment = Equipment()
        equipment.codigo_interno = "EQP-APR-001"
        equipment.nome = "EQUIPAMENTO APROVACAO"
        equipment.nome_normalizado = "EQUIPAMENTO APROVACAO"
        equipment.fabricante = "TESTE"
        equipment.modelo = "MODELO"
        equipment.tipo_equipamento = "TIPO"
        equipment.patrimonio = "N/A"
        equipment.codigo_equipamento = "EQ-APR-001"
        equipment.serial = "SN-APR-001"
        equipment.status = EquipmentStatus.RESERVADO.value
        equipment.validado = True

        db.session.add(user)
        db.session.add(approver)
        db.session.add(equipment)
        db.session.flush()

        loan = Loan()
        loan.numero_controle = "EMP-APR-TESTE"
        loan.user_id = user.id
        loan.approver_id = approver.id
        loan.status = LoanStatus.PENDENTE_APROVACAO.value
        loan.data_emprestimo = datetime.utcnow()
        loan.data_prevista_devolucao = datetime.utcnow() + timedelta(days=7)
        loan.local_utilizacao = "LOCAL TESTE"
        loan.responsavel_entrega_nome = "Responsável Teste"

        db.session.add(loan)
        db.session.flush()

        loan_item = LoanItem()
        loan_item.loan_id = loan.id
        loan_item.equipment_id = equipment.id
        loan_item.tipo_item = ItemType.PATRIMONIAL.value
        loan_item.quantidade = 1
        loan_item.quantidade_devolvida = 0
        loan_item.status = "RESERVADO"

        db.session.add(loan_item)
        db.session.commit()

        return loan.id


def test_approver_can_see_own_pending_approval(client, app, login_user):
    login_user(
        email="aprovador@teste.com",
        role="CONSULTA",
    )

    create_pending_approval_loan(
        app,
        approver_email="aprovador@teste.com",
    )

    response = client.get(
        "/aprovacoes/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "EMP-APR-TESTE".encode("utf-8") in response.data


def test_approver_can_approve_from_system(client, app, login_user):
    login_user(
        email="aprovador2@teste.com",
        role="CONSULTA",
    )

    loan_id = create_pending_approval_loan(
        app,
        approver_email="aprovador2@teste.com",
    )

    response = client.post(
        f"/aprovacoes/{loan_id}/aprovar",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        loan = db.session.get(Loan, loan_id)

        assert loan is not None
        assert loan.status == LoanStatus.APROVADO.value


def test_different_user_cannot_approve(client, app, login_user):
    login_user(
        email="outro.usuario@teste.com",
        role="CONSULTA",
    )

    loan_id = create_pending_approval_loan(
        app,
        approver_email="aprovador.real@teste.com",
    )

    response = client.post(
        f"/aprovacoes/{loan_id}/aprovar",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "permissão".encode("utf-8") in response.data

    with app.app_context():
        loan = db.session.get(Loan, loan_id)

        assert loan is not None
        assert loan.status == LoanStatus.PENDENTE_APROVACAO.value