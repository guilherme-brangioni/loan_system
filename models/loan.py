from datetime import datetime

from database.database import db


class Loan(db.Model):
    """
    Representa o empréstimo.

    Um empréstimo pode conter vários itens:
    - equipamentos patrimoniais
    - consumíveis quantitativos
    """

    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)

    numero_controle = db.Column(db.String(100), unique=True, index=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("approvers.id"), nullable=False)

    responsavel_entrega_nome = db.Column(db.String(255), nullable=False)
    responsavel_entrega_matricula = db.Column(db.String(100))
    responsavel_entrega_email = db.Column(db.String(255))

    status = db.Column(db.String(100), default="PENDENTE_APROVACAO", index=True)

    data_emprestimo = db.Column(db.DateTime)
    data_prevista_devolucao = db.Column(db.DateTime)
    data_real_devolucao = db.Column(db.DateTime)

    local_utilizacao = db.Column(db.String(255))

    aprovado = db.Column(db.Boolean, default=False)
    aprovado_em = db.Column(db.DateTime)

    rejeitado_em = db.Column(db.DateTime)
    motivo_rejeicao = db.Column(db.Text)

    approval_token = db.Column(db.Text)

    observacoes = db.Column(db.Text)

    notification_fixed_emails = db.Column(db.Text)      # E-mails fixos lidos do arquivo no momento da criação
    notification_extra_emails = db.Column(db.Text)      # E-mails adicionais digitados no momento do empréstimo
    notification_all_emails = db.Column(db.Text)        # União de Fixos + adicionais, preservada para auditoria

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = db.relationship("User", back_populates="loans")
    approver = db.relationship("Approver", back_populates="loans")

    items = db.relationship(
        "LoanItem",
        back_populates="loan",
        lazy=True,
        cascade="all, delete-orphan",
    )

    renewals = db.relationship(
        "Renewal",
        back_populates="loan",
        lazy=True,
        cascade="all, delete-orphan",
    )

