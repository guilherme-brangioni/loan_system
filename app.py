from flask import Flask, flash, redirect, request, url_for

from config import Config

from database.database import db, migrate

import models  # noqa: F401

from routes.main_routes import main_bp
from routes.equipment_routes import equipment_bp
from routes.loan_routes import loan_bp
from routes.validation_routes import validation_bp
from routes.audit_routes import audit_bp
from routes.email_routes import email_bp
from routes.excel_routes import excel_bp
from routes.maintenance_routes import maintenance_bp
from routes.auth_routes import auth_bp
from routes.sync_routes import sync_bp
from routes.settings_routes import settings_bp
from routes.diagnostic_routes import diagnostic_bp
from routes.external_pending_routes import external_pending_bp
from routes.approval_routes import approval_bp
from routes.search_routes import search_bp
from routes.operational_status_routes import operational_status_bp


def create_app(config_override: dict | None = None):

    app = Flask(__name__)
    app.config.from_object(Config)

    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(loan_bp)
    app.register_blueprint(validation_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(excel_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(diagnostic_bp)
    app.register_blueprint(external_pending_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(operational_status_bp)

    @app.context_processor
    def inject_current_user():
        from services.auth_service import AuthService
        from services.approval_service import ApprovalService
        from utils.status_ui import format_status_label, status_badge_class

        current_user = AuthService.get_current_user()

        approval_pending_count = 0

        if current_user:
            try:
                approval_pending_count = ApprovalService.count_pending_for_current_user()
            except Exception:
                approval_pending_count = 0

        return {
            "current_user": current_user,
            "approval_pending_count": approval_pending_count,
            "status_badge_class": status_badge_class,
            "format_status_label": format_status_label,
        }

    @app.before_request
    def require_login_and_permissions():
        from enums.user_role import UserRole
        from services.auth_service import AuthService

        endpoint = request.endpoint or ""

        public_endpoints = {
            "static",
            "auth_bp.login",
            "auth_bp.logout",
            "auth_bp.setup_first_admin",
            "auth_bp.forgot_password",
            "loan_bp.verify_loan_document",

            # Se ainda existir link antigo de aprovação por e-mail, deixe aqui
            # apenas se ele redirecionar para /aprovacoes/ e não aprovar direto.
            "loan_bp.approve_loan",
        }

        if endpoint in public_endpoints:
            return None

        if endpoint.startswith("static"):
            return None

        if AuthService.count_users() == 0:
            return redirect(url_for("auth_bp.setup_first_admin"))

        current_user = AuthService.get_current_user()

        if not current_user:
            flash("Faça login para acessar o sistema.", "error")
            return redirect(url_for("auth_bp.login"))

        forced_password_endpoints = {
            "auth_bp.force_change_password",
            "auth_bp.logout",
        }

        if (
            getattr(current_user, "must_change_password", False)
            and endpoint not in forced_password_endpoints
            and not endpoint.startswith("static")
        ):
            flash(
                "Você precisa alterar sua senha temporária antes de continuar.",
                "warning",
            )
            return redirect(url_for("auth_bp.force_change_password"))

        # Manutenção e usuários: somente ADMIN.
        admin_only_prefixes = [
            "maintenance_bp.",
            "sync_bp.",
            "settings_bp.",
            "diagnostic_bp.",
            "external_pending_bp.",
            "operational_status_bp",
        ]

        admin_only_endpoints = {
            "auth_bp.list_users",
            "auth_bp.new_user",
            "auth_bp.edit_user",
            "auth_bp.reset_user_password",
        }

        if (
            endpoint in admin_only_endpoints
            or any(endpoint.startswith(prefix) for prefix in admin_only_prefixes)
        ):
            if current_user.role != UserRole.ADMIN.value:
                flash("Acesso restrito ao administrador.", "error")
                return redirect(url_for("main_bp.dashboard"))

        # Perfil CONSULTA pode navegar, mas não executar ações POST,
        # exceto ações explicitamente permitidas.
        allowed_post_for_consulta = {
            "auth_bp.change_password",
            "auth_bp.force_change_password",
            "approval_bp.approve_loan",
            "approval_bp.reject_loan",
        }

        if (
            current_user.role == UserRole.CONSULTA.value
            and request.method != "GET"
            and endpoint not in allowed_post_for_consulta
        ):
            flash("Seu perfil é somente consulta.", "error")
            return redirect(request.referrer or url_for("main_bp.dashboard"))

        return None

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)