import os
from database.database import db

from models.app_setting import AppSetting
from models.loan import Loan

from services.pdf_service import PDFService
from services.backup_service import BackupService
from services.excel_inventory_service import ExcelInventoryService
from services.excel_movement_service import ExcelMovementService

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

def test_pdf_logo_path_uses_logo_path_from_settings(
    app,
    login_user,
):
    """
    Garante que o PDFService usa LOGO_PATH salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "LOGO_PATH"
        setting.value = r"C:\logo_teste\logo.png"
        setting.description = "Caminho da logo"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        logo_path = PDFService._get_logo_path()

        assert logo_path == r"C:\logo_teste\logo.png"






def test_backup_dir_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que BackupService usa BACKUP_DIR salvo nas configurações.
    """

    login_user(role="ADMIN")

    custom_backup_dir = os.path.join(
        app.config["BACKUP_DIR"],
        "custom_backups",
    )

    with app.app_context():
        setting = AppSetting()
        setting.key = "BACKUP_DIR"
        setting.value = custom_backup_dir
        setting.description = "Pasta de backups"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        backup = BackupService.create_backup()

        assert backup["type"] == "MANUAL"
        assert backup["path"].startswith(custom_backup_dir)
        assert os.path.exists(backup["path"])


def test_auto_backup_filename_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que BackupService usa AUTO_BACKUP_FILENAME salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "AUTO_BACKUP_FILENAME"
        setting.value = "backup_auto_teste.db"
        setting.description = "Nome do backup automático"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        result = BackupService.create_weekly_automatic_backup_if_needed()

        assert result["filename"] == "backup_auto_teste.db"
        assert os.path.exists(result["path"])


def test_auto_backup_interval_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que BackupService usa AUTO_BACKUP_INTERVAL_DAYS salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "AUTO_BACKUP_INTERVAL_DAYS"
        setting.value = "3"
        setting.description = "Intervalo do backup automático"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        # O login pode ter passado pelo Dashboard e criado backup automático
        # antes da configuração do teste. Removemos para testar criação limpa.
        existing_backup = BackupService.get_automatic_backup()

        if existing_backup and os.path.exists(existing_backup["path"]):
            os.remove(existing_backup["path"])

        result = BackupService.create_weekly_automatic_backup_if_needed()

        assert result["created"] is True

        automatic_backup = BackupService.get_automatic_backup()

        assert automatic_backup is not None

        delta = automatic_backup["next_backup_at"] - automatic_backup["created_at"]

        assert delta.days == 3


def test_backup_keep_last_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que BACKUP_KEEP_LAST limita backups manuais.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "BACKUP_KEEP_LAST"
        setting.value = "2"
        setting.description = "Quantidade de backups manuais"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        BackupService.create_backup()
        BackupService.create_backup()
        BackupService.create_backup()

        manual_backups = BackupService.list_manual_backups()

        assert len(manual_backups) <= 2

def test_excel_inventory_file_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que ExcelInventoryService usa EXCEL_INVENTORY_FILE salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "EXCEL_INVENTORY_FILE"
        setting.value = r"\\SERVIDOR_TESTE\PASTA\inventario_teste.xlsx"
        setting.description = "Planilha de inventário"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        file_path = ExcelInventoryService._get_inventory_file_path()

        assert file_path == r"\\SERVIDOR_TESTE\PASTA\inventario_teste.xlsx"


def test_excel_inventory_sheet_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que ExcelInventoryService usa EXCEL_INVENTORY_SHEET salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "EXCEL_INVENTORY_SHEET"
        setting.value = "Inventario_Teste"
        setting.description = "Aba da planilha de inventário"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        sheet_name = ExcelInventoryService._get_inventory_sheet_name()

        assert sheet_name == "Inventario_Teste"


def test_excel_movements_file_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que ExcelMovementService usa EXCEL_MOVEMENTS_FILE salvo nas configurações.
    """

    login_user(role="ADMIN")

    custom_file = os.path.join(
        app.config["BACKUP_DIR"],
        "movimentacoes_teste.xlsx",
    )

    with app.app_context():
        setting = AppSetting()
        setting.key = "EXCEL_MOVEMENTS_FILE"
        setting.value = custom_file
        setting.description = "Planilha de movimentações Power BI"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        file_path = ExcelMovementService._get_movements_file_path()

        assert file_path == custom_file


def test_excel_movements_sheet_uses_setting_value(
    app,
    login_user,
):
    """
    Garante que ExcelMovementService usa EXCEL_MOVEMENTS_SHEET salvo nas configurações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        setting = AppSetting()
        setting.key = "EXCEL_MOVEMENTS_SHEET"
        setting.value = "Movimentacoes_Teste"
        setting.description = "Aba de movimentações Power BI"
        setting.updated_by = "TESTE"

        db.session.add(setting)
        db.session.commit()

        sheet_name = ExcelMovementService._get_movements_sheet_name()

        assert sheet_name == "Movimentacoes_Teste"