import os
from datetime import datetime, timedelta

from database.database import db

from models.sync_pending import SyncPending

from services.backup_service import BackupService
from services.equipment_service import EquipmentService
from services.sync_pending_service import SyncPendingService


def create_equipment_for_sync_test(app):
    """
    Cria equipamento para testes de pendência de sincronização.
    """

    with app.app_context():
        equipment = EquipmentService.create_equipment(
            fabricante="FLUKE",
            modelo="87V",
            tipo_equipamento="MULTIMETRO",
            patrimonio="N/A",
            codigo_equipamento="EQ-SYNC-001",
            serial="SN-SYNC-001",
            categoria="MEDICAO",
            observacoes="Equipamento para teste de sincronização.",
            validado=True,
        )

        return equipment.id


def test_create_manual_backup(app):
    """
    Testa criação de backup manual.

    O backup manual deve criar um arquivo .db com data/hora no nome.
    """

    with app.app_context():
        backup = BackupService.create_backup()

        assert backup["type"] == "MANUAL"
        assert backup["filename"].startswith("database_backup_manual_")
        assert backup["filename"].endswith(".db")
        assert os.path.exists(backup["path"])
        assert os.path.getsize(backup["path"]) > 0


def test_create_weekly_automatic_backup(app):
    """
    Testa criação do backup automático semanal.

    O backup automático deve usar arquivo fixo.
    """

    with app.app_context():
        result = BackupService.create_weekly_automatic_backup_if_needed()

        assert result["created"] is True
        assert result["type"] == "AUTOMATICO"
        assert result["filename"] == app.config["AUTO_BACKUP_FILENAME"]
        assert os.path.exists(result["path"])
        assert os.path.getsize(result["path"]) > 0


def test_weekly_automatic_backup_does_not_create_new_file_if_recent(app):
    """
    Se o backup automático semanal já existe e é recente,
    o sistema não deve criar outro arquivo.
    """

    with app.app_context():
        first_result = BackupService.create_weekly_automatic_backup_if_needed()

        assert first_result["created"] is True

        second_result = BackupService.create_weekly_automatic_backup_if_needed()

        assert second_result["created"] is False
        assert second_result["filename"] == app.config["AUTO_BACKUP_FILENAME"]

        automatic_backup = BackupService.get_automatic_backup()

        assert automatic_backup is not None
        assert automatic_backup["filename"] == app.config["AUTO_BACKUP_FILENAME"]


def test_weekly_automatic_backup_overwrites_old_file(app):
    """
    Se o backup automático tiver mais de 7 dias,
    o sistema deve sobrescrever o mesmo arquivo.
    """

    with app.app_context():
        first_result = BackupService.create_weekly_automatic_backup_if_needed()

        assert first_result["created"] is True

        backup_path = first_result["path"]

        old_date = datetime.now() - timedelta(days=8)

        old_timestamp = old_date.timestamp()

        os.utime(
            backup_path,
            (
                old_timestamp,
                old_timestamp,
            ),
        )

        result = BackupService.create_weekly_automatic_backup_if_needed()

        assert result["created"] is True
        assert result["filename"] == app.config["AUTO_BACKUP_FILENAME"]
        assert result["path"] == backup_path

        automatic_backup = BackupService.get_automatic_backup()

        assert automatic_backup is not None
        assert automatic_backup["created_at"] > old_date


def test_manual_backups_do_not_include_automatic_backup(app):
    """
    A listagem de backups manuais não deve incluir o backup automático.
    """

    with app.app_context():
        BackupService.create_weekly_automatic_backup_if_needed()

        manual_backup = BackupService.create_backup()

        manual_backups = BackupService.list_manual_backups()

        filenames = [
            backup["filename"]
            for backup in manual_backups
        ]

        assert manual_backup["filename"] in filenames
        assert app.config["AUTO_BACKUP_FILENAME"] not in filenames


def test_create_sync_pending_for_equipment(app):
    """
    Testa criação de pendência de sincronização com Excel.
    """

    equipment_id = create_equipment_for_sync_test(app)

    with app.app_context():
        from models.equipment import Equipment

        equipment = db.session.get(Equipment, equipment_id)

        assert equipment is not None

        pending = SyncPendingService.create_equipment_excel_pending(
            equipment=equipment,
            error="Erro simulado de planilha em rede.",
            created_by="TESTE",
        )

        assert pending is not None
        assert pending.entity_type == "EQUIPMENT"
        assert pending.entity_id == equipment.id
        assert pending.target == "EXCEL"
        assert pending.status == SyncPendingService.STATUS_ERRO
        assert "Erro simulado" in pending.last_error


def test_retry_sync_pending_success(app):
    """
    Testa reprocessamento de pendência.

    Como o conftest faz mock do ExcelInventoryService.upsert_equipment_to_excel,
    o retry deve resolver a pendência sem acessar planilha real.
    """

    equipment_id = create_equipment_for_sync_test(app)

    with app.app_context():
        from models.equipment import Equipment

        equipment = db.session.get(Equipment, equipment_id)

        assert equipment is not None

        pending = SyncPendingService.create_equipment_excel_pending(
            equipment=equipment,
            error="Erro simulado.",
            created_by="TESTE",
        )

        result = SyncPendingService.retry_pending(
            pending=pending,
            performed_by="TESTE",
        )

        assert result["success"] is True

        updated_pending = db.session.get(SyncPending, pending.id)

        assert updated_pending is not None
        assert updated_pending.status == SyncPendingService.STATUS_RESOLVIDO
        assert updated_pending.resolved_by == "TESTE"
        assert updated_pending.resolved_at is not None
        assert updated_pending.attempts == 1