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
#from routes.settings_routes import settings_bp


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
    #app.register_blueprint(settings_bp)

    @app.context_processor
    def inject_current_user():
        from services.auth_service import AuthService

        return {
            "current_user": AuthService.get_current_user(),
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
            "loan_bp.verify_loan_document",
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

        # Manutenção e usuários: somente ADMIN.
        admin_only_prefixes = [
            "maintenance_bp.",
            "sync_bp.",
            #"settings_bp.",
        ]

        admin_only_endpoints = {
            "auth_bp.list_users",
            "auth_bp.new_user",
            "auth_bp.edit_user",
        }

        if (
            endpoint in admin_only_endpoints
            or any(endpoint.startswith(prefix) for prefix in admin_only_prefixes)
        ):
            if current_user.role != UserRole.ADMIN.value:
                flash("Acesso restrito ao administrador.", "error")
                return redirect(url_for("main_bp.dashboard"))

        # Perfil CONSULTA pode navegar, mas não executar ações POST.
        allowed_post_for_consulta = {
            "auth_bp.change_password",
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