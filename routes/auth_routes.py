from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from sqlalchemy import func

from database.database import db
from enums.user_role import UserRole
from models.system_user import SystemUser
from services.app_setting_service import AppSettingService
from services.auth_service import AuthService
from services.password_reset_service import PasswordResetService
from utils.auth_decorators import role_required


auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


def build_login_url() -> str:
    """
    Monta URL absoluta de login usando APP_BASE_URL.
    """

    base_url = AppSettingService.get(
        "APP_BASE_URL",
        current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
    )

    base_url = str(base_url or "http://127.0.0.1:5000").strip().rstrip("/")

    return f"{base_url}{url_for('auth_bp.login')}"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login por e-mail e senha.
    """

    if AuthService.count_users() == 0:
        return redirect(url_for("auth_bp.setup_first_admin"))

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            user = AuthService.authenticate(
                email=form_data.get("email", ""),
                password=form_data.get("password", ""),
            )

            AuthService.login_user(user)

            if getattr(user, "must_change_password", False):
                flash(
                    "Você está usando uma senha temporária. Crie uma nova senha para continuar.",
                    "warning",
                )

                return redirect(url_for("auth_bp.force_change_password"))

            flash("Login realizado com sucesso.", "success")

            return redirect(url_for("main_bp.dashboard"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template("auth_login.html")


@auth_bp.route("/logout")
def logout():
    """
    Sai do sistema.
    """

    AuthService.logout_user()

    flash("Você saiu do sistema.", "success")

    return redirect(url_for("auth_bp.login"))


@auth_bp.route("/primeiro-admin", methods=["GET", "POST"])
def setup_first_admin():
    """
    Cria o primeiro administrador.

    Só funciona enquanto não existir nenhum usuário cadastrado.
    """

    if AuthService.count_users() > 0:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            user = AuthService.create_user(
                nome=form_data.get("nome", ""),
                email=form_data.get("email", ""),
                password=form_data.get("password", ""),
                role=UserRole.ADMIN.value,
                active=True,
            )

            AuthService.login_user(user)

            flash("Primeiro administrador criado com sucesso.", "success")

            return redirect(url_for("main_bp.dashboard"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template("auth_setup_first_admin.html")


@auth_bp.route("/usuarios")
@role_required(UserRole.ADMIN.value)
def list_users():
    """
    Lista usuários do sistema com filtros.
    """

    q = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "").strip().upper()
    active_filter = request.args.get("active", "").strip()
    password_filter = request.args.get("password", "").strip()

    query = SystemUser.query

    if q:
        pattern = f"%{q}%"

        query = query.filter(
            (SystemUser.nome.ilike(pattern))
            | (SystemUser.email.ilike(pattern))
            | (SystemUser.matricula.ilike(pattern))
            | (SystemUser.telefone.ilike(pattern))
            | (SystemUser.gerencia.ilike(pattern))
            | (SystemUser.regional.ilike(pattern))
            | (SystemUser.equipe.ilike(pattern))
        )

    if role_filter:
        query = query.filter(SystemUser.role == role_filter)

    if active_filter == "ATIVO":
        query = query.filter(SystemUser.active.is_(True))

    elif active_filter == "INATIVO":
        query = query.filter(SystemUser.active.is_(False))

    if password_filter == "TROCA_PENDENTE":
        query = query.filter(SystemUser.must_change_password.is_(True))

    elif password_filter == "NORMAL":
        query = query.filter(SystemUser.must_change_password.is_(False))

    users = (
        query
        .order_by(SystemUser.nome.asc())
        .all()
    )

    return render_template(
        "auth_users.html",
        users=users,
        q=q,
        role_filter=role_filter,
        active_filter=active_filter,
        password_filter=password_filter,
        roles=[role.value for role in UserRole],
    )


@auth_bp.route("/usuarios/novo", methods=["GET", "POST"])
@role_required(UserRole.ADMIN.value)
def new_user():
    """
    Cria usuário do sistema.
    """

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            AuthService.create_user(
                nome=form_data.get("nome", ""),
                email=form_data.get("email", ""),
                password=form_data.get("password", ""),
                role=form_data.get("role", ""),
                active=form_data.get("active") == "on",
                matricula=form_data.get("matricula", ""),
                telefone=form_data.get("telefone", ""),
                gerencia=form_data.get("gerencia", ""),
                regional=form_data.get("regional", ""),
                equipe=form_data.get("equipe", ""),
            )

            flash("Usuário criado com sucesso.", "success")

            return redirect(url_for("auth_bp.list_users"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "auth_user_form.html",
        user=None,
        roles=[role.value for role in UserRole],
    )


@auth_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@role_required(UserRole.ADMIN.value)
def edit_user(user_id: int):
    """
    Edita usuário do sistema.
    """

    user = SystemUser.query.get_or_404(user_id)

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            nome = form_data.get("nome", "").strip()
            email = AuthService.normalize_email(form_data.get("email", ""))
            role = form_data.get("role", "").strip().upper()

            if not nome:
                raise ValueError("Nome é obrigatório.")

            if not email:
                raise ValueError("E-mail é obrigatório.")

            if role not in [item.value for item in UserRole]:
                raise ValueError("Perfil inválido.")

            existing = SystemUser.query.filter(
                SystemUser.email == email,
                SystemUser.id != user.id,
            ).first()

            if existing:
                raise ValueError("Já existe outro usuário com este e-mail.")

            user.nome = nome
            user.email = email
            user.role = role
            user.active = form_data.get("active") == "on"
            
            user.matricula = form_data.get("matricula", "").strip()
            user.telefone = form_data.get("telefone", "").strip()
            user.gerencia = form_data.get("gerencia", "").strip()
            user.regional = form_data.get("regional", "").strip()
            user.equipe = form_data.get("equipe", "").strip()

            new_password = form_data.get("password", "").strip()

            if new_password:
                user.set_password(new_password)
                user.must_change_password = False
                user.password_changed_at = datetime.utcnow()

            db.session.commit()

            flash("Usuário atualizado com sucesso.", "success")

            return redirect(url_for("auth_bp.list_users"))

        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template(
        "auth_user_form.html",
        user=user,
        roles=[role.value for role in UserRole],
    )


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def forgot_password():
    """
    Solicita reset de senha.

    Por segurança, a resposta visual é genérica.
    """

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        user = (
            SystemUser.query
            .filter(func.lower(SystemUser.email) == email)
            .first()
        )

        if user and user.active:
            result = PasswordResetService.reset_password_and_send_email(
                user=user,
                login_url=build_login_url(),
                performed_by="RESET_SOLICITADO_PELO_USUARIO",
            )

            if not result.get("success"):
                flash(
                    "Não foi possível enviar a senha temporária. Verifique a configuração de e-mail ou contate o administrador.",
                    "error",
                )

                return redirect(url_for("auth_bp.forgot_password"))

        flash(
            "Se o e-mail estiver cadastrado e ativo, uma senha temporária será enviada.",
            "success",
        )

        return redirect(url_for("auth_bp.login"))

    return render_template("auth_forgot_password.html")


@auth_bp.route("/alterar-senha", methods=["GET", "POST"])
def change_password():
    """
    Usuário logado altera a própria senha.
    """

    user = AuthService.get_current_user()

    if not user:
        flash("Faça login para alterar sua senha.", "error")
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            AuthService.change_password(
                user=user,
                current_password=form_data.get("current_password", ""),
                new_password=form_data.get("new_password", ""),
                confirm_password=form_data.get("confirm_password", ""),
            )

            user.must_change_password = False
            user.password_changed_at = datetime.utcnow()

            db.session.commit()

            flash("Senha alterada com sucesso.", "success")

            return redirect(url_for("main_bp.dashboard"))

        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template("auth_change_password.html")


@auth_bp.route("/alterar-senha-obrigatoria", methods=["GET", "POST"])
def force_change_password():
    """
    Tela obrigatória após login com senha temporária.
    """

    current_user = AuthService.get_current_user()

    if not current_user:
        flash("Faça login para continuar.", "error")
        return redirect(url_for("auth_bp.login"))

    if not getattr(current_user, "must_change_password", False):
        return redirect(url_for("main_bp.dashboard"))

    if request.method == "POST":
        try:
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if len(new_password) < 6:
                raise ValueError("A nova senha deve ter pelo menos 6 caracteres.")

            if new_password != confirm_password:
                raise ValueError("A confirmação da senha não confere.")

            current_user.set_password(new_password)
            current_user.must_change_password = False
            current_user.password_changed_at = datetime.utcnow()

            db.session.commit()

            flash("Senha alterada com sucesso. Acesso liberado.", "success")

            return redirect(url_for("main_bp.dashboard"))

        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template("auth_force_change_password.html")


@auth_bp.route("/usuarios/<int:user_id>/resetar-senha", methods=["POST"])
@role_required(UserRole.ADMIN.value)
def reset_user_password(user_id: int):
    """
    ADMIN gera senha temporária para um usuário.
    """

    user = db.session.get(SystemUser, user_id)

    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("auth_bp.list_users"))

    if not user.active:
        flash("Não é possível resetar senha de usuário inativo.", "error")
        return redirect(url_for("auth_bp.list_users"))

    performed_by = AuthService.get_current_user_display_name()

    result = PasswordResetService.reset_password_and_send_email(
        user=user,
        login_url=build_login_url(),
        performed_by=performed_by,
    )

    if result.get("success"):
        flash(
            f"Senha temporária enviada para {user.email}.",
            "success",
        )
    else:
        flash(
            "Falha ao resetar senha: "
            + result.get("error", "Erro desconhecido."),
            "error",
        )

    return redirect(url_for("auth_bp.list_users"))

@auth_bp.route("/meu-perfil")
def my_profile():
    """
    Exibe dados do usuário logado.
    """

    user = AuthService.get_current_user()

    if not user:
        flash("Faça login para acessar seu perfil.", "error")
        return redirect(url_for("auth_bp.login"))

    return render_template(
        "auth_my_profile.html",
        user=user,
    )