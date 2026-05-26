from datetime import datetime

from database.database import db


class AppSetting(db.Model):
    """
    Configuração editável do sistema.

    Nesta primeira etapa, as configurações são apenas salvas e exibidas.
    Ainda não alteram o comportamento dos serviços críticos.
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