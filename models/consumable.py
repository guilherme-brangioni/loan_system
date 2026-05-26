from datetime import datetime

from database.database import db


class Consumable(db.Model):
    """
    Consumíveis ou acessórios controlados por quantidade.

    Exemplo:
    - Cabo HDMI
    - Adaptador
    - Mouse simples
    """

    __tablename__ = "consumables"

    id = db.Column(db.Integer, primary_key=True)

    codigo_interno = db.Column(db.String(100), unique=True, index=True)

    nome = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)

    categoria = db.Column(db.String(255))

    quantidade = db.Column(db.Integer, default=0)

    # Quando a quantidade ficar abaixo ou igual ao limite,
    # o dashboard deve alertar.
    limite_alerta = db.Column(db.Integer, default=1)

    validado = db.Column(db.Boolean, default=False)

    observacoes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loan_items = db.relationship("LoanItem", back_populates="consumable")