from typing import Any

from database.database import db
from models.app_setting import AppSetting


class AppSettingService:
    """
    Serviço central de configurações do sistema.

    Regra:
    - tenta buscar no banco;
    - se não existir, usa o valor padrão do config.py;
    - se a tabela ainda não existir, não quebra o sistema.
    """

    SETTINGS = [
        {
            "key": "APP_BASE_URL",
            "label": "URL base do sistema",
            "description": "Usada em links de aprovação, QR Code e e-mails.",
        },
        {
            "key": "LOGO_PATH",
            "label": "Caminho da logo",
            "description": "Imagem usada no cabeçalho do PDF.",
        },
        {
            "key": "EXCEL_INVENTORY_FILE",
            "label": "Planilha de inventário",
            "description": "Caminho da planilha de equipamentos em rede.",
        },
        {
            "key": "EXCEL_INVENTORY_SHEET",
            "label": "Aba da planilha de inventário",
            "description": "Nome da aba onde estão os equipamentos.",
        },
        {
            "key": "EXCEL_MOVEMENTS_FILE",
            "label": "Planilha de movimentações Power BI",
            "description": "Arquivo Excel usado para exportar movimentações.",
        },
        {
            "key": "EXCEL_MOVEMENTS_SHEET",
            "label": "Aba de movimentações Power BI",
            "description": "Nome da aba de movimentações de empréstimos.",
        },
        {
            "key": "BACKUP_DIR",
            "label": "Pasta de backups",
            "description": "Local onde os backups do banco serão salvos.",
        },
        {
            "key": "BACKUP_KEEP_LAST",
            "label": "Quantidade de backups manuais",
            "description": "Número máximo de backups manuais mantidos.",
        },
        {
            "key": "AUTO_BACKUP_FILENAME",
            "label": "Nome do backup automático",
            "description": "Arquivo fixo do backup automático semanal.",
        },
        {
            "key": "AUTO_BACKUP_INTERVAL_DAYS",
            "label": "Intervalo do backup automático",
            "description": "Intervalo em dias para atualizar o backup automático.",
        },
    ]

    @staticmethod
    def get_setting_definition(key: str) -> dict[str, str] | None:
        for setting in AppSettingService.SETTINGS:
            if setting["key"] == key:
                return setting

        return None

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Retorna configuração do banco.

        Se não existir, estiver vazia ou o banco/tabela ainda não estiver pronto,
        retorna o valor padrão.
        """

        try:
            setting = AppSetting.query.filter_by(key=key).first()

            if not setting:
                return default

            value = str(setting.value or "").strip()

            if not value:
                return default

            return value

        except Exception:
            return default

    @staticmethod
    def get_int(key: str, default: int) -> int:
        """
        Retorna configuração inteira.
        """

        value = AppSettingService.get(key, default)

        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def set_value(
        key: str,
        value: str,
        updated_by: str = "SISTEMA",
    ) -> AppSetting:
        """
        Cria ou atualiza uma configuração.
        """

        definition = AppSettingService.get_setting_definition(key)

        if not definition:
            raise ValueError(f"Configuração não permitida: {key}")

        setting = AppSetting.query.filter_by(key=key).first()

        if not setting:
            setting = AppSetting()
            setting.key = key
            setting.description = definition.get("description", "")
            db.session.add(setting)

        setting.value = str(value or "").strip()
        setting.updated_by = updated_by

        db.session.commit()

        return setting

    @staticmethod
    def list_settings_with_values(app_config) -> list[dict[str, Any]]:
        """
        Lista configurações permitidas com valor atual.

        Se não existir no banco, mostra valor vindo do config.py.
        """

        result: list[dict[str, Any]] = []

        for definition in AppSettingService.SETTINGS:
            key = definition["key"]

            db_setting = None

            try:
                db_setting = AppSetting.query.filter_by(key=key).first()
            except Exception:
                db_setting = None

            config_default = app_config.get(key, "")

            if db_setting and str(db_setting.value or "").strip():
                value = db_setting.value
                source = "BANCO"
            else:
                value = config_default
                source = "CONFIG"

            result.append(
                {
                    "key": key,
                    "label": definition["label"],
                    "description": definition["description"],
                    "value": value or "",
                    "source": source,
                    "updated_by": db_setting.updated_by if db_setting else "",
                    "updated_at": db_setting.updated_at if db_setting else None,
                }
            )

        return result