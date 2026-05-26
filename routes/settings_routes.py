from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from enums.user_role import UserRole
from services.app_setting_service import AppSettingService
from services.auth_service import AuthService
from utils.auth_decorators import role_required


settings_bp = Blueprint(
    "settings_bp",
    __name__,
    url_prefix="/configuracoes",
)


@settings_bp.route("/", methods=["GET", "POST"])
@role_required(UserRole.ADMIN.value)
def settings_page():
    """
    Tela de configurações do sistema.

    Restrita ao ADMIN.
    """

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            updated_by = AuthService.get_current_user_display_name()

            for setting in AppSettingService.SETTINGS:
                key = setting["key"]

                AppSettingService.set_value(
                    key=key,
                    value=form_data.get(key, ""),
                    updated_by=updated_by,
                )

            flash("Configurações atualizadas com sucesso.", "success")

            return redirect(url_for("settings_bp.settings_page"))

        except Exception as exc:
            flash(str(exc), "error")

    settings = AppSettingService.list_settings_with_values(
        current_app.config
    )

    return render_template(
        "settings.html",
        settings=settings,
    )