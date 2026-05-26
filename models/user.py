from datetime import datetime

from database.database import db


class User(db.Model):
    """
    Representa o solicitante, ou seja, quem usará o equipamento.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(255), nullable=False)
    matricula = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(100))

    gerencia = db.Column(db.String(255))
    regional = db.Column(db.String(255))
    equipe = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loans = db.relationship("Loan", back_populates="user")