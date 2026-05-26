import os
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

from services.pdf_service import PDFService
from services.verification_token_service import VerificationTokenService


def create_test_loan_with_item(app):
    """
    Cria um empréstimo completo diretamente no banco para testar PDF e QR Code.
    """

    with app.app_context():
        user = User()
        user.nome = "Solicitante Teste"
        user.matricula = "123456"
        user.email = "solicitante@teste.com"
        user.telefone = "31999999999"
        user.gerencia = "GERENCIA TESTE"
        user.regional = "REGIONAL TESTE"
        user.equipe = "EQUIPE TESTE"

        approver = Approver()
        approver.nome = "Aprovador Teste"
        approver.matricula = "654321"
        approver.email = "aprovador@teste.com"

        equipment = Equipment()
        equipment.codigo_interno = "EQP-TESTE-PDF"
        equipment.nome = "MULTIMETRO - FLUKE 87V"
        equipment.nome_normalizado = "MULTIMETRO - FLUKE 87V"
        equipment.fabricante = "FLUKE"
        equipment.modelo = "87V"
        equipment.tipo_equipamento = "MULTIMETRO"
        equipment.patrimonio = "N/A"
        equipment.codigo_equipamento = "EQ-PDF-001"
        equipment.serial = "SN-PDF-001"
        equipment.status = EquipmentStatus.EMPRESTADO.value
        equipment.validado = True

        db.session.add(user)
        db.session.add(approver)
        db.session.add(equipment)
        db.session.flush()

        loan = Loan()
        loan.numero_controle = "EMP-PDF-TESTE"
        loan.user_id = user.id
        loan.approver_id = approver.id
        loan.status = LoanStatus.RETIRADO.value
        loan.data_emprestimo = datetime.utcnow()
        loan.data_prevista_devolucao = datetime.utcnow() + timedelta(days=7)
        loan.local_utilizacao = "LOCAL DE TESTE"
        loan.responsavel_entrega_nome = "Responsável Teste"
        loan.responsavel_entrega_matricula = "111222"
        loan.responsavel_entrega_email = "responsavel@teste.com"

        db.session.add(loan)
        db.session.flush()

        loan_item = LoanItem()
        loan_item.loan_id = loan.id
        loan_item.equipment_id = equipment.id
        loan_item.tipo_item = ItemType.PATRIMONIAL.value
        loan_item.quantidade = 1
        loan_item.quantidade_devolvida = 0
        loan_item.status = LoanItemStatus.EMPRESTADO.value

        db.session.add(loan_item)
        db.session.commit()

        return loan.id


def test_verification_token_is_valid(client, app, login_user):
    """
    Gera e valida token de verificação.
    """

    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        token = VerificationTokenService.generate_token(loan_id)
        data = VerificationTokenService.validate_token(token)

        assert data["loan_id"] == loan_id


def test_invalid_verification_token_raises_error(app):
    """
    Token inválido deve gerar erro de validação.
    """

    with app.app_context():
        try:
            VerificationTokenService.validate_token("token-invalido")
            assert False
        except ValueError as exc:
            assert "inválido" in str(exc).lower()


def test_public_verification_page_opens(client, app, login_user):
    """
    Página pública de verificação deve abrir com token válido.
    """

    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        token = VerificationTokenService.generate_token(loan_id)

    response = client.get(
        f"/emprestimos/verificar/{token}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Verificação de comprovante".encode("utf-8") in response.data
    assert "EMP-PDF-TESTE".encode("utf-8") in response.data


def test_generate_loan_pdf(client, app, login_user):
    """
    Testa geração do PDF do empréstimo.
    """

    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        loan = db.session.get(Loan, loan_id)

        pdf_path = PDFService.generate_loan_pdf(loan)

        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        assert os.path.getsize(pdf_path) > 0