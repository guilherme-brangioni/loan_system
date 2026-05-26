import os
from dotenv import load_dotenv


# Carrega variáveis do arquivo .env, se existir.
# Isso permite configurar senha SMTP, SECRET_KEY etc. sem colocar no código.
load_dotenv()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Configurações principais do Flask.

    Em produção, a SECRET_KEY deve vir obrigatoriamente de variável de ambiente.
    Para uso local, deixei um valor padrão apenas para facilitar testes.
    """

    SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Prazo máximo permitido para um empréstimo.
    # Pode ser alterado por variável de ambiente.
    MAX_LOAN_DAYS = int(os.getenv("MAX_LOAN_DAYS", "30"))

    # Tempo máximo de validade do link de aprovação, em segundos.
    # 86400 segundos = 24 horas.
    APPROVAL_TOKEN_MAX_AGE_SECONDS = int(
        os.getenv("APPROVAL_TOKEN_MAX_AGE_SECONDS", "86400")
    )

    # URL base usada para montar links enviados por e-mail.
    # Em rede interna, futuramente pode ser algo como:
    # http://servidor-interno:5000
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

    # Diretório de PDFs gerados.
    GENERATED_PDF_DIR = os.path.join(BASE_DIR, "generated", "pdfs")

    LOGO_PATH = os.getenv(
        "LOGO_PATH",
        os.path.join(BASE_DIR, "static", "img", "logo.png"),
    )

    FIXED_NOTIFICATION_EMAILS_FILE = os.path.join(
        BASE_DIR,
        "fixed_notification_emails.txt",
    )

    EXCEL_INVENTORY_FILE = os.getenv(
        "EXCEL_INVENTORY_FILE",
        r"D:\PROJETOS\db\loan_system_db\Inventário_Reserva _Técnica _PCA_-_AT.xlsx",
    )

    EXCEL_INVENTORY_SHEET = os.getenv(
        "EXCEL_INVENTORY_SHEET",
        "ATPM",
    )

    EQUIPMENT_IMAGE_UPLOAD_DIR = os.path.join(
        BASE_DIR,
        "generated",
        "equipment_images",
    )

    ALLOWED_IMAGE_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg",
        "webp",
    }

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    EXCEL_MOVEMENTS_FILE = os.getenv(
        "EXCEL_MOVEMENTS_FILE",
        os.path.join(BASE_DIR, "generated", "powerbi_movimentacoes.xlsx"),
    )

    EXCEL_MOVEMENTS_SHEET = os.getenv(
        "EXCEL_MOVEMENTS_SHEET",
        "Movimentacoes_Emprestimos",
    )

    BACKUP_DIR = os.path.join(
        BASE_DIR,
        "backups",
    )

    BACKUP_KEEP_LAST = int(
        os.getenv("BACKUP_KEEP_LAST", "20")
    )

    AUTO_BACKUP_FILENAME = os.getenv(
        "AUTO_BACKUP_FILENAME",
        "database_backup_automatico_semanal.db",
    )

    AUTO_BACKUP_INTERVAL_DAYS = int(
        os.getenv("AUTO_BACKUP_INTERVAL_DAYS", "7")
    )