from datetime import datetime

from database.database import db


class LoanItem(db.Model):
    """
    Item individual dentro do empréstimo.

    A devolução parcial só é possível porque controlamos item por item.
    """

    __tablename__ = "loan_items"

    id = db.Column(db.Integer, primary_key=True)

    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id"), nullable=False)

    equipment_id = db.Column(db.Integer, db.ForeignKey("equipments.id"))
    consumable_id = db.Column(db.Integer, db.ForeignKey("consumables.id"))

    tipo_item = db.Column(db.String(100), nullable=False)

    quantidade = db.Column(db.Integer, default=1)

    # Para consumíveis, pode devolver parte da quantidade.
    quantidade_devolvida = db.Column(db.Integer, default=0)

    status = db.Column(db.String(100), default="EMPRESTADO")

    devolvido_em = db.Column(db.DateTime)
    devolvido_por = db.Column(db.String(255))

    image_path = db.Column(db.String(500))
    image_original_filename = db.Column(db.String(255))

    observacoes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loan = db.relationship("Loan", back_populates="items")
    equipment = db.relationship("Equipment", back_populates="loan_items")
    consumable = db.relationship("Consumable", back_populates="loan_items")