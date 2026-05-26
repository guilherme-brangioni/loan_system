from functools import wraps

from flask import flash, redirect, request, url_for

from enums.user_role import UserRole
from services.auth_service import AuthService


def login_required(view_func):
    """
    Exige que o usuário esteja logado.
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not AuthService.is_authenticated():
            flash("Faça login para acessar o sistema.", "error")
            return redirect(url_for("auth_bp.login"))

        return view_func(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """
    Exige que o usuário tenha um dos perfis permitidos.

    ADMIN sempre tem acesso.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = AuthService.get_current_user()

            if not user:
                flash("Faça login para acessar o sistema.", "error")
                return redirect(url_for("auth_bp.login"))

            if user.role == UserRole.ADMIN.value:
                return view_func(*args, **kwargs)

            if user.role not in allowed_roles:
                flash("Você não tem permissão para acessar esta função.", "error")
                return redirect(request.referrer or url_for("main_bp.dashboard"))

            return view_func(*args, **kwargs)

        return wrapped

    return decorator