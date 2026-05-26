import json
from typing import Any, Optional

from database.database import db
from models.audit_log import AuditLog


class AuditService:
    """
    Serviço central de auditoria.

    Correção importante:
    Não criamos AuditLog passando parâmetros no construtor,
    porque o Pylance pode acusar erro em models SQLAlchemy.
    """

    @staticmethod
    def register(
        entity_type: str,
        entity_id: int,
        action: str,
        performed_by: str,
        old_data: Optional[Any] = None,
        new_data: Optional[Any] = None,
    ) -> AuditLog:
        audit = AuditLog()

        audit.entity_type = entity_type
        audit.entity_id = entity_id
        audit.action = action
        audit.performed_by = performed_by or "SISTEMA"

        if old_data is not None:
            audit.old_data = json.dumps(
                old_data,
                ensure_ascii=False,
                default=str,
            )
        else:
            audit.old_data = None

        if new_data is not None:
            audit.new_data = json.dumps(
                new_data,
                ensure_ascii=False,
                default=str,
            )
        else:
            audit.new_data = None

        db.session.add(audit)
        db.session.commit()

        return audit