from flask import Blueprint, current_app, flash, render_template, redirect, url_for

from services.excel_inventory_service import ExcelInventoryService


excel_bp = Blueprint("excel_bp", __name__, url_prefix="/excel")


@excel_bp.route("/")
def excel_sync_page():
    """
    Tela principal da integração com Excel.

    Mostra:
    - caminho configurado da planilha;
    - nome da aba;
    - botão de sincronização.
    """

    excel_file = current_app.config["EXCEL_INVENTORY_FILE"]
    excel_sheet = current_app.config["EXCEL_INVENTORY_SHEET"]

    return render_template(
        "excel_sync.html",
        excel_file=excel_file,
        excel_sheet=excel_sheet,
    )


@excel_bp.route("/sincronizar", methods=["POST"])
def sync_inventory():
    """
    Executa a sincronização da planilha Excel para o banco de dados.

    Importante:
    - não apaga equipamentos do banco;
    - cria equipamentos novos;
    - atualiza equipamentos existentes;
    - registra auditoria da sincronização.
    """

    try:
        result = ExcelInventoryService.sync_inventory_from_excel()

        flash(
            "Sincronização concluída com sucesso. "
            f"Criados: {result['created']} | "
            f"Atualizados: {result['updated']} | "
            f"Ignorados: {result['ignored']} | "
            f"Erros: {len(result['errors'])}",
            "success",
        )

        # Mostra os primeiros erros na tela.
        for error in result["errors"][:20]:
            flash(error, "error")

        if len(result["errors"]) > 20:
            flash(
                f"Existem mais {len(result['errors']) - 20} erros não exibidos.",
                "error",
            )

    except Exception as exc:
        flash(
            "Falha ao sincronizar inventário: "
            + str(exc),
            "error",
        )

    return redirect(url_for("excel_bp.excel_sync_page"))