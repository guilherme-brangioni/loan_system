import secrets
import string
from datetime import datetime

from database.database import db
from models.system_user import SystemUser
from services.email_service import EmailService


class PasswordResetService:
    """
    Serviço para geração de senha temporária e reset de senha.

    Fluxo:
    - gera senha aleatória;
    - salva no usuário;
    - marca must_change_password=True;
    - envia e-mail;
    - no próximo login, usuário é obrigado a trocar.
    """

    @staticmethod
    def generate_temporary_password(length: int = 12) -> str:
        alphabet = (
            string.ascii_letters
            + string.digits
            + "!@#$%&*"
        )

        while True:
            password = "".join(
                secrets.choice(alphabet)
                for _ in range(length)
            )

            has_lower = any(char.islower() for char in password)
            has_upper = any(char.isupper() for char in password)
            has_digit = any(char.isdigit() for char in password)
            has_special = any(char in "!@#$%&*" for char in password)

            if has_lower and has_upper and has_digit and has_special:
                return password

    @staticmethod
    def build_temporary_password_body(
        user: SystemUser,
        temporary_password: str,
        login_url: str,
    ) -> str:
        return f"""Olá, {user.nome}.

Foi gerada uma senha temporária para acesso ao Sistema de Empréstimos.

E-mail de acesso:
{user.email}

Senha temporária:
{temporary_password}

Acesse o sistema pelo link abaixo:

{login_url}

Após entrar, o sistema solicitará a criação de uma nova senha.

Se você não solicitou essa alteração, entre em contato com o administrador do sistema.

Atenciosamente,
Sistema de Empréstimos
"""

    @staticmethod
    def reset_password_and_send_email(
        user: SystemUser,
        login_url: str,
        performed_by: str = "SISTEMA",
    ) -> dict:
        """
        Gera senha temporária, envia por e-mail e marca troca obrigatória.

        Se o e-mail falhar, desfaz a alteração antes do commit.
        """

        temporary_password = PasswordResetService.generate_temporary_password()

        user.set_password(temporary_password)
        user.must_change_password = True
        user.temporary_password_generated_at = datetime.utcnow()

        body = PasswordResetService.build_temporary_password_body(
            user=user,
            temporary_password=temporary_password,
            login_url=login_url,
        )

        result = EmailService.try_send_email(
            recipients=[user.email],
            subject="Senha temporária - Sistema de Empréstimos",
            body=body,
        )

        if not result.get("success"):
            db.session.rollback()

            return {
                "success": False,
                "error": result.get("error", "Falha ao enviar e-mail."),
            }

        db.session.commit()

        return {
            "success": True,
        }