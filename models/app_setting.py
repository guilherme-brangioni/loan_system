from datetime import datetime

from database.database import db


class AppSetting(db.Model):
    """
    Configuração editável do sistema.

    Usada para parâmetros operacionais que podem mudar sem alterar código:
    - caminhos de planilha;
    - URL base;
    - logo;
    - backup;
    - parâmetros gerais.
    """

    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(db.String(100), nullable=False, unique=True, index=True)

    value = db.Column(db.Text)

    description = db.Column(db.String(255))

    updated_by = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )