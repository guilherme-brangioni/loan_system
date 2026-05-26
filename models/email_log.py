from datetime import datetime

from database.database import db


class EmailLog(db.Model):
    """
    Registra tentativas de envio de e-mail.

    Isso é importante porque o SMTP pode falhar por vários motivos:
    - senha incorreta
    - SMTP AUTH bloqueado
    - porta bloqueada
    - política do Outlook corporativo
    - arquivo smtp_settings.json ausente
    """

    __tablename__ = "email_logs"

    id = db.Column(db.Integer, primary_key=True)

    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id"), nullable=True)

    email_type = db.Column(db.String(100), nullable=False)

    recipients = db.Column(db.Text, nullable=False)

    subject = db.Column(db.String(255), nullable=False)

    success = db.Column(db.Boolean, default=False)

    error = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)