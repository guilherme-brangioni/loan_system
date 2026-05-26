from database.database import db
from models.app_setting import AppSetting
from models.loan import Loan

from services.pdf_service import PDFService
from tests.test_pdf_and_verification import create_test_loan_with_item


def test_pdf_verification_url_uses_app_base_url_from_settings(
    app,
    login_user,
):
    """
    Garante que o QR Code/PDF usa APP_BASE_URL salvo nas configurações.

    Esse teste não valida visualmente o QR Code.
    Ele valida a URL gerada pelo PDFService.
    """

    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        setting = AppSetting()
        setting.key = "APP_BASE_URL"
        setting.value = "http://sistema-teste.local:5000"
        setting.description = "URL base do sistema"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        loan = db.session.get(Loan, loan_id)

        assert loan is not None

        verification_url = PDFService._build_verification_url(loan)

        assert verification_url.startswith(
            "http://sistema-teste.local:5000/emprestimos/verificar/"
        )