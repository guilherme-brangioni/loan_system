import os
import shutil
from datetime import datetime, timedelta
from typing import List

from flask import current_app

from services.app_setting_service import AppSettingService


class BackupService:
    """
    Serviço responsável por backups do banco SQLite.

    Tipos:
    - backup automático semanal: arquivo único, sobrescreve o anterior;
    - backup manual: arquivos com data/hora, mantém histórico.

    Agora usa configurações salvas em /configuracoes/:
    - BACKUP_DIR
    - BACKUP_KEEP_LAST
    - AUTO_BACKUP_FILENAME
    - AUTO_BACKUP_INTERVAL_DAYS
    """

    @staticmethod
    def get_database_path() -> str:
        """
        Obtém o caminho real do banco SQLite.

        Este caminho continua vindo do config.py / DATABASE_URL.
        Não deve ser alterado pela tela de configurações.
        """

        database_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]

        prefix = "sqlite:///"

        if not database_uri.startswith(prefix):
            raise ValueError(
                "Backup disponível apenas para banco SQLite."
            )

        return database_uri.replace(prefix, "", 1)

    @staticmethod
    def _get_backup_dir() -> str:
        """
        Retorna a pasta de backup.

        Prioridade:
        1. Valor salvo no banco em BACKUP_DIR;
        2. Valor padrão do config.py.
        """

        backup_dir = AppSettingService.get(
            "BACKUP_DIR",
            current_app.config["BACKUP_DIR"],
        )

        backup_dir = str(backup_dir or "").strip()

        if not backup_dir:
            backup_dir = current_app.config["BACKUP_DIR"]

        os.makedirs(backup_dir, exist_ok=True)

        return backup_dir

    @staticmethod
    def _get_keep_last_manual_backups() -> int:
        """
        Quantidade de backups manuais a manter.
        """

        return AppSettingService.get_int(
            "BACKUP_KEEP_LAST",
            int(current_app.config.get("BACKUP_KEEP_LAST", 20)),
        )

    @staticmethod
    def _get_auto_backup_filename() -> str:
        """
        Nome do arquivo fixo do backup automático.
        """

        filename = AppSettingService.get(
            "AUTO_BACKUP_FILENAME",
            current_app.config["AUTO_BACKUP_FILENAME"],
        )

        filename = str(filename or "").strip()

        if not filename:
            filename = current_app.config["AUTO_BACKUP_FILENAME"]

        if not filename.endswith(".db"):
            filename += ".db"

        return filename

    @staticmethod
    def _get_auto_backup_interval_days() -> int:
        """
        Intervalo em dias do backup automático.
        """

        interval_days = AppSettingService.get_int(
            "AUTO_BACKUP_INTERVAL_DAYS",
            int(current_app.config.get("AUTO_BACKUP_INTERVAL_DAYS", 7)),
        )

        if interval_days < 1:
            interval_days = 7

        return interval_days

    @staticmethod
    def create_backup() -> dict:
        """
        Cria backup manual com data/hora no nome.

        Esse método é usado pelo botão manual em Manutenção.
        """

        database_path = BackupService.get_database_path()

        if not os.path.exists(database_path):
            raise FileNotFoundError(
                f"Banco de dados não encontrado: {database_path}"
            )

        backup_dir = BackupService._get_backup_dir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_filename = f"database_backup_manual_{timestamp}.db"

        backup_path = os.path.join(
            backup_dir,
            backup_filename,
        )

        shutil.copy2(database_path, backup_path)

        BackupService.cleanup_old_manual_backups()

        return {
            "type": "MANUAL",
            "filename": backup_filename,
            "path": backup_path,
            "created_at": datetime.now(),
            "size_bytes": os.path.getsize(backup_path),
        }

    @staticmethod
    def create_weekly_automatic_backup_if_needed() -> dict:
        """
        Cria backup automático.

        Regra:
        - usa sempre o mesmo arquivo;
        - se não existir, cria;
        - se existir e ainda estiver dentro do intervalo, não faz nada;
        - se existir e já passou do intervalo, sobrescreve.
        """

        database_path = BackupService.get_database_path()

        if not os.path.exists(database_path):
            raise FileNotFoundError(
                f"Banco de dados não encontrado: {database_path}"
            )

        backup_dir = BackupService._get_backup_dir()

        auto_filename = BackupService._get_auto_backup_filename()

        auto_backup_path = os.path.join(
            backup_dir,
            auto_filename,
        )

        interval_days = BackupService._get_auto_backup_interval_days()

        if os.path.exists(auto_backup_path):
            last_modified = datetime.fromtimestamp(
                os.path.getmtime(auto_backup_path)
            )

            next_backup_date = last_modified + timedelta(days=interval_days)

            if datetime.now() < next_backup_date:
                return {
                    "created": False,
                    "reason": "Backup automático ainda está atualizado.",
                    "filename": auto_filename,
                    "path": auto_backup_path,
                    "last_backup_at": last_modified,
                    "next_backup_at": next_backup_date,
                }

        shutil.copy2(database_path, auto_backup_path)

        return {
            "created": True,
            "type": "AUTOMATICO",
            "filename": auto_filename,
            "path": auto_backup_path,
            "created_at": datetime.now(),
            "size_bytes": os.path.getsize(auto_backup_path),
        }

    @staticmethod
    def get_automatic_backup() -> dict | None:
        """
        Retorna o backup automático, se existir.
        """

        backup_dir = BackupService._get_backup_dir()

        auto_filename = BackupService._get_auto_backup_filename()

        path = os.path.join(
            backup_dir,
            auto_filename,
        )

        if not os.path.exists(path):
            return None

        last_modified = datetime.fromtimestamp(
            os.path.getmtime(path)
        )

        interval_days = BackupService._get_auto_backup_interval_days()

        return {
            "type": "AUTOMATICO",
            "filename": auto_filename,
            "path": path,
            "created_at": last_modified,
            "next_backup_at": last_modified + timedelta(days=interval_days),
            "size_bytes": os.path.getsize(path),
        }

    @staticmethod
    def list_manual_backups() -> List[dict]:
        """
        Lista somente backups manuais.

        O backup automático não aparece nesta lista.
        """

        backup_dir = BackupService._get_backup_dir()

        auto_filename = BackupService._get_auto_backup_filename()

        backups = []

        for filename in os.listdir(backup_dir):
            if not filename.endswith(".db"):
                continue

            if filename == auto_filename:
                continue

            path = os.path.join(backup_dir, filename)

            backups.append(
                {
                    "type": "MANUAL",
                    "filename": filename,
                    "path": path,
                    "created_at": datetime.fromtimestamp(
                        os.path.getmtime(path)
                    ),
                    "size_bytes": os.path.getsize(path),
                }
            )

        backups.sort(
            key=lambda item: item["created_at"],
            reverse=True,
        )

        return backups

    @staticmethod
    def cleanup_old_manual_backups() -> None:
        """
        Mantém apenas os últimos BACKUP_KEEP_LAST backups manuais.

        O backup automático não entra nessa limpeza.
        """

        keep_last = BackupService._get_keep_last_manual_backups()

        backups = BackupService.list_manual_backups()

        old_backups = backups[keep_last:]

        for backup in old_backups:
            try:
                os.remove(backup["path"])
            except OSError:
                pass

    @staticmethod
    def get_backup_file_path(filename: str) -> str:
        """
        Retorna caminho de backup específico, validando se existe.
        """

        backup_dir = BackupService._get_backup_dir()

        path = os.path.join(
            backup_dir,
            filename,
        )

        if not os.path.exists(path):
            raise FileNotFoundError("Backup não encontrado.")

        valid_files = [
            BackupService._get_auto_backup_filename(),
        ]

        valid_files.extend(
            backup["filename"]
            for backup in BackupService.list_manual_backups()
        )

        if filename not in valid_files:
            raise FileNotFoundError("Backup não encontrado.")

        return path