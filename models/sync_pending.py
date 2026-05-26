from datetime import datetime

from database.database import db


class SyncPending(db.Model):
    """
    Registra pendências de sincronização com sistemas externos.

    Exemplo:
    - item salvo no banco;
    - tentativa de atualizar Excel falhou;
    - pendência fica registrada para tentativa posterior.
    """

    __tablename__ = "sync_pendings"

    id = db.Column(db.Integer, primary_key=True)

    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)

    action = db.Column(db.String(100), nullable=False)

    target = db.Column(db.String(100), nullable=False, default="EXCEL")

    status = db.Column(db.String(50), nullable=False, default="PENDENTE")
    attempts = db.Column(db.Integer, default=0)

    last_error = db.Column(db.Text)

    created_by = db.Column(db.String(255), default="SISTEMA")
    resolved_by = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_attempt_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)