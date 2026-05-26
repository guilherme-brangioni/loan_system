from datetime import datetime

from database.database import db


class Equipment(db.Model):
    """
    Equipamento ou material emprestável.

    Os dados podem vir:
    - de cadastro manual;
    - da planilha de inventário em rede;
    - do auto-cadastro feito durante um empréstimo.
    """

    __tablename__ = "equipments"

    id = db.Column(db.Integer, primary_key=True)

    # Código interno gerado pelo próprio sistema.
    codigo_interno = db.Column(db.String(100), unique=True, index=True)

    # Nome composto usado para exibição.
    nome = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)

    # Dados principais.
    fabricante = db.Column(db.String(255))
    modelo = db.Column(db.String(255))
    tipo_equipamento = db.Column(db.String(255))

    # Patrimônio real. Pode ser N/A.
    patrimonio = db.Column(db.String(255), index=True)

    # Código vindo da planilha.
    # Não é patrimônio.
    codigo_equipamento = db.Column(db.String(255), index=True)

    serial = db.Column(db.String(255), index=True)
    categoria = db.Column(db.String(255))

    # Status operacional controlado pelo sistema.
    # Ex.: DISPONIVEL, RESERVADO, EMPRESTADO.
    status = db.Column(db.String(50), default="DISPONIVEL", index=True)

    # Status vindo da planilha, apenas informativo.
    # Não deve sobrescrever automaticamente o status operacional.
    status_planilha = db.Column(db.String(255))

    # Campos vindos da planilha.
    regional = db.Column(db.String(255))
    data_inventario = db.Column(db.DateTime)
    local_armazenagem = db.Column(db.String(255))
    subestacao_origem = db.Column(db.String(255))
    emprestado_para_planilha = db.Column(db.String(255))
    data_emprestimo_planilha = db.Column(db.DateTime)

    validado = db.Column(db.Boolean, default=False)

    observacoes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    loan_items = db.relationship("LoanItem", back_populates="equipment")