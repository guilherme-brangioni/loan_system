from database.database import db

from models.external_pending import ExternalPending
from models.loan import Loan

from services.external_pending_service import ExternalPendingService
from tests.test_pdf_and_verification import create_test_loan_with_item


def test_enqueue_loan_movement(app, login_user):
    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        pending = ExternalPendingService.enqueue_loan_movement(
            loan_id=loan_id,
            movement_type="TESTE",
            performed_by="TESTE",
            notes="Movimentação de teste.",
            created_by="TESTE",
        )

        assert pending.id is not None
        assert pending.action == ExternalPendingService.ACTION_EXPORT_LOAN_MOVEMENT
        assert pending.status == ExternalPendingService.STATUS_PENDENTE


def test_process_loan_movement_pending(app, login_user):
    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        pending = ExternalPendingService.enqueue_loan_movement(
            loan_id=loan_id,
            movement_type="TESTE",
            performed_by="TESTE",
            notes="Movimentação de teste.",
            created_by="TESTE",
        )

        result = ExternalPendingService.process_pending(
            pending=pending,
            performed_by="TESTE",
        )

        assert result["success"] is True

        updated = db.session.get(ExternalPending, pending.id)

        assert updated is not None
        assert updated.status == ExternalPendingService.STATUS_RESOLVIDO


def test_enqueue_and_process_loan_receipt_email(app, login_user):
    login_user(role="ADMIN")

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        pending = ExternalPendingService.enqueue_loan_receipt_email(
            loan_id=loan_id,
            created_by="TESTE",
        )

        result = ExternalPendingService.process_pending(
            pending=pending,
            performed_by="TESTE",
        )

        assert result["success"] is True

        updated = db.session.get(ExternalPending, pending.id)

        assert updated is not None
        assert updated.status == ExternalPendingService.STATUS_RESOLVIDO


def test_external_pending_page_admin(client, login_user):
    login_user(
        email="admin.external@teste.com",
        role="ADMIN",
    )

    response = client.get(
        "/pendencias-externas/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Pendências externas".encode("utf-8") in response.data

from services.external_pending_service import ExternalPendingService
from tests.test_pdf_and_verification import create_test_loan_with_item


def test_dashboard_shows_external_pending_count(client, app, login_user):
    """
    Dashboard deve mostrar quantidade de pendências externas ativas.
    """

    login_user(
        email="admin.dashboard.pending@teste.com",
        role="ADMIN",
    )

    loan_id = create_test_loan_with_item(app)

    with app.app_context():
        ExternalPendingService.enqueue_loan_movement(
            loan_id=loan_id,
            movement_type="TESTE_DASHBOARD",
            performed_by="TESTE",
            notes="Pendência para teste de Dashboard.",
            created_by="TESTE",
        )

    response = client.get(
        "/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Pendências externas".encode("utf-8") in response.data