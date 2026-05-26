from datetime import datetime

from database.database import db


class Renewal(db.Model):
    """
    Cada renovação é registrada separadamente.

    Não apagamos o prazo antigo.
    Isso preserva auditoria.
    """

    __tablename__ = "renewals"

    id = db.Column(db.Integer, primary_key=True)

    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id"), nullable=False)

    old_due_date = db.Column(db.DateTime, nullable=False)
    new_due_date = db.Column(db.DateTime, nullable=False)

    renewed_by = db.Column(db.String(255), nullable=False)

    reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loan = db.relationship("Loan", back_populates="renewals")