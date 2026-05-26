from datetime import datetime, timedelta

from database.database import db

from enums.equipment_status import EquipmentStatus
from enums.loan_status import LoanStatus

from models.equipment import Equipment
from models.loan import Loan

from services.equipment_service import EquipmentService


def create_available_equipment(app):
    """
    Cria equipamento disponível diretamente pelo service.
    """

    with app.app_context():
        equipment = EquipmentService.create_equipment(
            fabricante="FLUKE",
            modelo="87V",
            tipo_equipamento="MULTIMETRO",
            patrimonio="N/A",
            codigo_equipamento="EQ-FLOW-001",
            serial="SN-FLOW-001",
            categoria="MEDICAO",
            observacoes="Equipamento criado para teste de fluxo.",
            validado=True,
        )

        return equipment.id


def test_complete_loan_flow(client, app, login_user):
    """
    Testa o fluxo principal:

    1. Cria equipamento.
    2. Cria empréstimo.
    3. Aprova.
    4. Confirma retirada.
    5. Devolve tudo.
    """

    login_user(role="ADMIN")

    equipment_id = create_available_equipment(app)

    due_date = datetime.now() + timedelta(days=7)

    response = client.post(
        "/emprestimos/novo",
        data={
            "nome": "Solicitante Teste",
            "matricula": "123456",
            "email": "solicitante@teste.com",
            "telefone": "31999999999",
            "gerencia": "GERENCIA TESTE",
            "regional": "REGIONAL TESTE",
            "equipe": "EQUIPE TESTE",
            "approver_nome": "Aprovador Teste",
            "approver_matricula": "654321",
            "approver_email": "aprovador@teste.com",
            "responsavel_entrega_nome": "Responsável Entrega",
            "responsavel_entrega_matricula": "111222",
            "responsavel_entrega_email": "responsavel@teste.com",
            "local_utilizacao": "LOCAL DE TESTE",
            "data_prevista_devolucao": due_date.strftime("%Y-%m-%d"),
            "selected_equipment_ids[]": [str(equipment_id)],
            "notification_emails": "",
            "observacoes": "Teste automatizado de fluxo.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        loan = Loan.query.order_by(Loan.id.desc()).first()

        assert loan is not None
        assert loan.status == LoanStatus.PENDENTE_APROVACAO.value
        assert loan.approval_token is not None

        equipment = db.session.get(Equipment, equipment_id)

        assert equipment is not None
        assert equipment.status == EquipmentStatus.RESERVADO.value

        approval_token = loan.approval_token
        loan_id = loan.id

    response = client.post(
        f"/emprestimos/aprovar/{approval_token}",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        loan = db.session.get(Loan, loan_id)

        assert loan is not None
        assert loan.status == LoanStatus.APROVADO.value

    response = client.post(
        f"/emprestimos/{loan_id}/confirmar-retirada",
        data={
            "performed_by": "Operador Teste",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        loan = db.session.get(Loan, loan_id)
        equipment = db.session.get(Equipment, equipment_id)

        assert loan is not None
        assert equipment is not None

        assert loan.status == LoanStatus.RETIRADO.value
        assert equipment.status == EquipmentStatus.EMPRESTADO.value

    response = client.post(
        f"/emprestimos/{loan_id}/devolver-tudo",
        data={
            "devolvido_por": "Solicitante Teste",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        loan = db.session.get(Loan, loan_id)
        equipment = db.session.get(Equipment, equipment_id)

        assert loan is not None
        assert equipment is not None

        assert loan.status == LoanStatus.FINALIZADO.value
        assert equipment.status == EquipmentStatus.DISPONIVEL.value
        assert loan.data_real_devolucao is not None


def test_cannot_create_loan_without_equipment(client, login_user):
    """
    Não deve permitir criar empréstimo sem equipamento selecionado.
    """

    login_user(role="ADMIN")

    due_date = datetime.now() + timedelta(days=7)

    response = client.post(
        "/emprestimos/novo",
        data={
            "nome": "Solicitante Teste",
            "matricula": "123456",
            "email": "solicitante@teste.com",
            "approver_nome": "Aprovador Teste",
            "approver_email": "aprovador@teste.com",
            "responsavel_entrega_nome": "Responsável Entrega",
            "responsavel_entrega_email": "responsavel@teste.com",
            "local_utilizacao": "LOCAL DE TESTE",
            "data_prevista_devolucao": due_date.strftime("%Y-%m-%d"),
            "notification_emails": "",
            "observacoes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Selecione ao menos um equipamento".encode("utf-8") in response.data