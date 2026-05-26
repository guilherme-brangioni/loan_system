import os
import tempfile

import pytest
from sqlalchemy import text

from app import create_app
from database.database import db
from models.system_user import SystemUser


@pytest.fixture()
def app():
    """
    Cria uma aplicação Flask isolada para testes.

    Usa banco SQLite temporário para não alterar o banco real.
    """

    temp_dir = tempfile.mkdtemp()

    database_path = os.path.join(temp_dir, "test_database.db")
    database_uri_path = database_path.replace("\\", "/")

    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_uri_path}",
            "SECRET_KEY": "test-secret-key",
            "APP_BASE_URL": "http://localhost",
            "GENERATED_PDF_DIR": os.path.join(temp_dir, "generated", "pdfs"),
            "EQUIPMENT_IMAGE_UPLOAD_DIR": os.path.join(
                temp_dir,
                "generated",
                "equipment_images",
            ),
            "BACKUP_DIR": os.path.join(temp_dir, "backups"),
            "EXCEL_MOVEMENTS_FILE": os.path.join(
                temp_dir,
                "powerbi_movimentacoes.xlsx",
            ),
            "EXCEL_INVENTORY_FILE": os.path.join(
                temp_dir,
                "inventario_fake.xlsx",
            ),
            "EXCEL_INVENTORY_SHEET": "Inventario",
            "FIXED_NOTIFICATION_EMAILS_FILE": os.path.join(
                temp_dir,
                "fixed_notification_emails.txt",
            ),
            "AUTO_BACKUP_FILENAME": "database_backup_automatico_semanal.db",
            "AUTO_BACKUP_INTERVAL_DAYS": 7,
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.execute(text("SELECT 1"))
        db.session.commit()

        assert os.path.exists(database_path), (
            f"Banco de teste não foi criado: {database_path}"
        )

        assert os.path.getsize(database_path) > 0, (
            f"Banco de teste foi criado vazio: {database_path}"
        )

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def create_system_user(app):
    """
    Cria usuário do sistema para testes.
    """

    def _create_user(
        nome="Usuário Teste",
        email="usuario@teste.com",
        password="123456",
        role="ADMIN",
        active=True,
    ):
        with app.app_context():
            user = SystemUser()
            user.nome = nome
            user.email = email
            user.role = role
            user.active = active
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            return user.id

    return _create_user


@pytest.fixture()
def login_user(client, create_system_user):
    """
    Cria e faz login com usuário de teste.
    """

    def _login(
        email="usuario@teste.com",
        password="123456",
        role="ADMIN",
    ):
        create_system_user(
            email=email,
            password=password,
            role=role,
        )

        return client.post(
            "/auth/login",
            data={
                "email": email,
                "password": password,
            },
            follow_redirects=True,
        )

    return _login


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """
    Impede que os testes usem serviços externos reais.

    Durante testes, não queremos:
    - enviar e-mail real;
    - atualizar planilha real;
    - exportar movimentações reais para Excel.
    """

    def fake_send_email(*args, **kwargs):
        return {
            "success": True,
            "mocked": True,
            "error": None,
        }

    def fake_excel_upsert(*args, **kwargs):
        return {
            "success": True,
            "mocked": True,
            "action": "mocked",
        }

    def fake_excel_movement(*args, **kwargs):
        return {
            "success": True,
            "mocked": True,
            "rows": 1,
        }

    monkeypatch.setattr(
        "services.email_service.EmailService.try_send_email",
        fake_send_email,
    )

    monkeypatch.setattr(
        "services.excel_inventory_service.ExcelInventoryService.upsert_equipment_to_excel",
        fake_excel_upsert,
    )

    monkeypatch.setattr(
        "services.excel_movement_service.ExcelMovementService.try_append_loan_movement",
        fake_excel_movement,
    )