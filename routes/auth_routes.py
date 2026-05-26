from flask import Blueprint, flash, redirect, render_template, request, url_for

from database.database import db
from enums.user_role import UserRole
from models.system_user import SystemUser
from services.auth_service import AuthService
from utils.auth_decorators import role_required


auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


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
    Lista usuários do sistema.
    """

    users = SystemUser.query.order_by(
        SystemUser.nome.asc()
    ).all()

    return render_template(
        "auth_users.html",
        users=users,
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

            new_password = form_data.get("password", "").strip()

            if new_password:
                user.set_password(new_password)

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


@auth_bp.route("/alterar-senha", methods=["GET", "POST"])
def change_password():
    """
    Usuário logado altera a própria senha.
    """

    user = AuthService.get_current_user()

    if not user:
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

            flash("Senha alterada com sucesso.", "success")

            return redirect(url_for("main_bp.dashboard"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template("auth_change_password.html")