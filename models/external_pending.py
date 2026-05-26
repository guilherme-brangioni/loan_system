import json
from datetime import datetime

from database.database import db


class ExternalPending(db.Model):
    """
    Pendência de operação externa.

    Usada para tarefas que podem falhar ou demorar:
    - envio de e-mail;
    - geração de PDF;
    - exportação para Excel/Power BI.

    A operação principal do empréstimo não deve depender dessas tarefas.
    """

    __tablename__ = "external_pendings"

    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)

    status = db.Column(db.String(50), nullable=False, default="PENDENTE", index=True)

    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=5)

    payload_json = db.Column(db.Text)
    dedupe_key = db.Column(db.String(255), index=True)

    last_error = db.Column(db.Text)

    created_by = db.Column(db.String(255), default="SISTEMA")
    resolved_by = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_attempt_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)

    def get_payload(self) -> dict:
        if not self.payload_json:
            return {}

        try:
            return json.loads(self.payload_json)
        except Exception:
            return {}

    def set_payload(self, payload: dict) -> None:
        self.payload_json = json.dumps(
            payload or {},
            ensure_ascii=False,
            default=str,
        )