from datetime import datetime

from database.database import db


class Approver(db.Model):
    """
    Representa o aprovador.

    Não existe aprovador fixo.
    Cada empréstimo escolhe seu próprio aprovador.
    """

    __tablename__ = "approvers"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(255), nullable=False)
    matricula = db.Column(db.String(100))
    email = db.Column(db.String(255), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loans = db.relationship("Loan", back_populates="approver")