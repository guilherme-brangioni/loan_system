from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    send_file,
    url_for,
)

from services.backup_service import BackupService


maintenance_bp = Blueprint(
    "maintenance_bp",
    __name__,
    url_prefix="/manutencao",
)


@maintenance_bp.route("/")
def maintenance_page():
    """
    Tela de manutenção do sistema.

    Mostra:
    - backup automático semanal;
    - backups manuais.
    """

    automatic_backup = BackupService.get_automatic_backup()
    manual_backups = BackupService.list_manual_backups()

    return render_template(
        "maintenance.html",
        automatic_backup=automatic_backup,
        manual_backups=manual_backups,
    )


@maintenance_bp.route("/backup", methods=["POST"])
def create_backup():
    """
    Cria backup manual do banco.
    """

    try:
        backup = BackupService.create_backup()

        flash(
            f"Backup criado com sucesso: {backup['filename']}",
            "success",
        )

    except Exception as exc:
        flash(
            "Erro ao criar backup: " + str(exc),
            "error",
        )

    return redirect(url_for("maintenance_bp.maintenance_page"))


@maintenance_bp.route("/backup/<filename>")
def download_backup(filename: str):
    """
    Baixa um backup existente.
    """

    try:
        backup_path = BackupService.get_backup_file_path(filename)

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
        )

    except Exception as exc:
        flash(
            "Erro ao baixar backup: " + str(exc),
            "error",
        )

        return redirect(url_for("maintenance_bp.maintenance_page"))