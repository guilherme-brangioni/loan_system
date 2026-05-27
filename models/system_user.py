from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from database.database import db


class SystemUser(db.Model):
    """
    Usuário que acessa o sistema.

    Não confundir com models.user.User, que representa o solicitante
    do empréstimo.
    """

    __tablename__ = "system_users"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(255), nullable=False)

    email = db.Column(db.String(255), nullable=False, unique=True, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), nullable=False, default="CONSULTA")

    active = db.Column(db.Boolean, default=True)

    must_change_password = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    temporary_password_generated_at = db.Column(db.DateTime)

    password_changed_at = db.Column(db.DateTime)

    last_login_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)