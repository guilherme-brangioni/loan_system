from datetime import datetime

from flask import session

from database.database import db
from enums.user_role import UserRole
from models.system_user import SystemUser


class AuthService:
    """
    Serviço de autenticação do sistema.

    Usa sessão do Flask para manter o usuário logado.
    """

    SESSION_USER_ID_KEY = "system_user_id"

    @staticmethod
    def normalize_email(email: str) -> str:
        return str(email or "").strip().lower()

    @staticmethod
    def count_users() -> int:
        return SystemUser.query.count()

    @staticmethod
    def create_user(
        nome: str,
        email: str,
        password: str,
        role: str,
        active: bool = True,
        matricula: str = "",
        telefone: str = "",
        gerencia: str = "",
        regional: str = "",
        equipe: str = "",
    )-> SystemUser:
        nome = str(nome or "").strip()
        email = AuthService.normalize_email(email)
        password = str(password or "").strip()
        role = str(role or "").strip().upper()
        matricula = str(matricula or "").strip()
        telefone = str(telefone or "").strip()
        gerencia = str(gerencia or "").strip()
        regional = str(regional or "").strip()
        equipe = str(equipe or "").strip()

        if not nome:
            raise ValueError("Nome é obrigatório.")

        if not email:
            raise ValueError("E-mail é obrigatório.")

        if not password:
            raise ValueError("Senha é obrigatória.")

        if role not in [item.value for item in UserRole]:
            raise ValueError("Perfil inválido.")

        existing = SystemUser.query.filter_by(email=email).first()

        if existing:
            raise ValueError("Já existe usuário com este e-mail.")

        user = SystemUser()

        user.nome = nome
        user.email = email
        user.role = role
        user.active = active
        user.matricula = str(matricula or "").strip()
        user.telefone = str(telefone or "").strip()
        user.gerencia = str(gerencia or "").strip()
        user.regional = str(regional or "").strip()
        user.equipe = str(equipe or "").strip()
        
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def authenticate(email: str, password: str) -> SystemUser:
        email = AuthService.normalize_email(email)

        user = SystemUser.query.filter_by(email=email).first()

        if not user:
            raise ValueError("E-mail ou senha inválidos.")

        if not user.active:
            raise ValueError("Usuário inativo.")

        if not user.check_password(password):
            raise ValueError("E-mail ou senha inválidos.")

        user.last_login_at = datetime.utcnow()

        db.session.commit()

        return user

    @staticmethod
    def login_user(user: SystemUser) -> None:
        session[AuthService.SESSION_USER_ID_KEY] = user.id

    @staticmethod
    def logout_user() -> None:
        session.pop(AuthService.SESSION_USER_ID_KEY, None)

    @staticmethod
    def get_current_user() -> SystemUser | None:
        user_id = session.get(AuthService.SESSION_USER_ID_KEY)

        if not user_id:
            return None

        user = db.session.get(SystemUser, user_id)

        if not user or not user.active:
            AuthService.logout_user()
            return None

        return user

    @staticmethod
    def is_authenticated() -> bool:
        return AuthService.get_current_user() is not None

    @staticmethod
    def is_admin(user: SystemUser | None = None) -> bool:
        user = user or AuthService.get_current_user()

        if not user:
            return False

        return user.role == UserRole.ADMIN.value

    @staticmethod
    def change_password(
        user: SystemUser,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        if not user.check_password(current_password):
            raise ValueError("Senha atual incorreta.")

        if not new_password:
            raise ValueError("Nova senha é obrigatória.")

        if new_password != confirm_password:
            raise ValueError("A confirmação da senha não confere.")

        user.set_password(new_password)

        db.session.commit()

    @staticmethod
    def get_current_user_display_name(default: str = "SISTEMA") -> str:
        """
        Retorna o nome do usuário logado para auditoria e ações do sistema.

        Se não houver usuário logado, retorna SISTEMA.
        """

        user = AuthService.get_current_user()

        if not user:
            return default

        return user.nome or default