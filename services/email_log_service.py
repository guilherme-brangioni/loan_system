import json
from typing import List, Optional

from database.database import db
from models.email_log import EmailLog


class EmailLogService:
    """
    Serviço para registrar tentativas de envio de e-mail.
    """

    @staticmethod
    def register(
        email_type: str,
        recipients: List[str],
        subject: str,
        success: bool,
        loan_id: Optional[int] = None,
        error: Optional[str] = None,
    ) -> EmailLog:
        log = EmailLog()

        log.loan_id = loan_id
        log.email_type = email_type
        log.recipients = json.dumps(recipients, ensure_ascii=False)
        log.subject = subject
        log.success = success
        log.error = error

        db.session.add(log)
        db.session.commit()

        return log