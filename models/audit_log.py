from datetime import datetime

from database.database import db


class AuditLog(db.Model):
    """
    Registro de auditoria.

    Toda ação importante deve passar por aqui:
    - criação
    - aprovação
    - rejeição
    - retirada
    - devolução
    - renovação
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)

    action = db.Column(db.String(255), nullable=False)

    performed_by = db.Column(db.String(255), nullable=False)

    old_data = db.Column(db.Text)
    new_data = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)