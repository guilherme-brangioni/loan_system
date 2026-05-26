from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_

from database.database import db

from enums.equipment_status import EquipmentStatus

from models.equipment import Equipment
from models.loan_item import LoanItem

from services.audit_service import AuditService
from services.equipment_service import EquipmentService
from services.excel_inventory_service import ExcelInventoryService
from services.sync_pending_service import SyncPendingService
from services.auth_service import AuthService

from utils.form_helpers import get_optional, get_required
from utils.normalize import normalize_name


equipment_bp = Blueprint("equipment_bp", __name__, url_prefix="/itens")


@equipment_bp.route("/")
def list_items():
    """
    Lista equipamentos/materiais com busca, filtros e paginação.
    """

    search_text = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    validado_filter = request.args.get("validado", "").strip()
    regional_filter = request.args.get("regional", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    if per_page not in [25, 50, 100]:
        per_page = 50

    query = Equipment.query

    if search_text:
        normalized_search = normalize_name(search_text)
        pattern = f"%{normalized_search}%"

        query = query.filter(
            or_(
                Equipment.codigo_interno.ilike(pattern),
                Equipment.nome_normalizado.ilike(pattern),
                Equipment.tipo_equipamento.ilike(pattern),
                Equipment.fabricante.ilike(pattern),
                Equipment.modelo.ilike(pattern),
                Equipment.patrimonio.ilike(pattern),
                Equipment.codigo_equipamento.ilike(pattern),
                Equipment.serial.ilike(pattern),
                Equipment.status.ilike(pattern),
                Equipment.status_planilha.ilike(pattern),
                Equipment.regional.ilike(pattern),
                Equipment.local_armazenagem.ilike(pattern),
                Equipment.subestacao_origem.ilike(pattern),
            )
        )

    if status_filter:
        query = query.filter(Equipment.status == status_filter)

    if validado_filter == "SIM":
        query = query.filter(Equipment.validado.is_(True))
    elif validado_filter == "NAO":
        query = query.filter(Equipment.validado.is_(False))

    if regional_filter:
        query = query.filter(Equipment.regional == regional_filter)

    pagination = query.order_by(
        Equipment.codigo_interno.asc(),
        Equipment.tipo_equipamento.asc(),
        Equipment.fabricante.asc(),
        Equipment.modelo.asc(),
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    equipments = pagination.items

    regionais = [
        row[0] for row in (
            db.session.query(Equipment.regional)
            .filter(Equipment.regional.isnot(None))
            .distinct()
            .order_by(Equipment.regional.asc())
            .all()
        )
        if row[0]
    ]

    return render_template(
        "equipment_list.html",
        equipments=equipments,
        pagination=pagination,
        search_text=search_text,
        status_filter=status_filter,
        validado_filter=validado_filter,
        regional_filter=regional_filter,
        regionais=regionais,
        per_page=per_page,
        status_options=[status.value for status in EquipmentStatus],
    )


@equipment_bp.route("/novo", methods=["GET", "POST"])
def new_item():
    """
    Cadastro manual de equipamento/material.

    Fluxo:
    - salva primeiro no banco;
    - depois tenta atualizar a planilha;
    - se a planilha falhar, o cadastro permanece no banco.
    """

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            equipment = EquipmentService.create_equipment(
                fabricante=get_required(form_data, "fabricante", "Fabricante"),
                modelo=get_required(form_data, "modelo", "Modelo"),
                tipo_equipamento=get_required(
                    form_data,
                    "tipo_equipamento",
                    "Tipo de equipamento",
                ),
                patrimonio=get_required(form_data, "patrimonio", "Patrimônio"),
                codigo_equipamento=get_optional(form_data, "codigo_equipamento"),
                categoria=get_optional(form_data, "categoria"),
                serial=get_optional(form_data, "serial"),
                observacoes=get_optional(form_data, "observacoes"),
                validado=True,
            )

            flash("Item cadastrado com sucesso no banco de dados.", "success")

            try:
                excel_result = ExcelInventoryService.upsert_equipment_to_excel(
                    equipment
                )

                if excel_result.get("action") == "updated":
                    flash("Planilha atualizada com sucesso.", "success")
                elif excel_result.get("action") == "created":
                    flash("Item adicionado à planilha com sucesso.", "success")

            except Exception as exc:
                flash(
                    "O item foi cadastrado no banco, mas não foi possível atualizar a planilha: "
                    + str(exc),
                    "error",
                )

                AuditService.register(
                    entity_type="EQUIPMENT",
                    entity_id=equipment.id,
                    action="EXCEL_UPDATE_FAILED",
                    performed_by="SISTEMA",
                    new_data={
                        "codigo_interno": equipment.codigo_interno,
                        "erro": str(exc),
                    },
                )

                SyncPendingService.create_equipment_excel_pending(
                    equipment=equipment,
                    error=str(exc),
                    created_by="SISTEMA",
                )

            return redirect(url_for("equipment_bp.list_items"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template("equipment_form.html")


@equipment_bp.route("/<int:equipment_id>/editar", methods=["GET", "POST"])
def edit_item(equipment_id: int):
    """
    Edição completa do equipamento.

    Permite corrigir dados importados da planilha, validar equipamento
    e ajustar status operacional.
    """

    equipment = Equipment.query.get_or_404(equipment_id)

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            old_data = {
                "fabricante": equipment.fabricante,
                "modelo": equipment.modelo,
                "tipo_equipamento": equipment.tipo_equipamento,
                "patrimonio": equipment.patrimonio,
                "codigo_equipamento": equipment.codigo_equipamento,
                "serial": equipment.serial,
                "categoria": equipment.categoria,
                "regional": equipment.regional,
                "local_armazenagem": equipment.local_armazenagem,
                "subestacao_origem": equipment.subestacao_origem,
                "status": equipment.status,
                "validado": equipment.validado,
            }

            fabricante = get_required(form_data, "fabricante", "Fabricante")
            modelo = get_required(form_data, "modelo", "Modelo")
            tipo_equipamento = get_required(
                form_data,
                "tipo_equipamento",
                "Tipo de equipamento",
            )

            patrimonio = get_required(form_data, "patrimonio", "Patrimônio")

            equipamento_nome = EquipmentService.build_equipment_name(
                fabricante=fabricante,
                modelo=modelo,
                tipo_equipamento=tipo_equipamento,
            )

            equipment.nome = equipamento_nome
            equipment.nome_normalizado = normalize_name(equipamento_nome)

            equipment.fabricante = normalize_name(fabricante)
            equipment.modelo = normalize_name(modelo)
            equipment.tipo_equipamento = normalize_name(tipo_equipamento)

            equipment.patrimonio = normalize_name(patrimonio)
            equipment.codigo_equipamento = normalize_name(
                get_optional(form_data, "codigo_equipamento")
            ) or None
            equipment.serial = normalize_name(
                get_optional(form_data, "serial")
            ) or None

            equipment.categoria = normalize_name(
                get_optional(form_data, "categoria")
            ) or None

            equipment.regional = normalize_name(
                get_optional(form_data, "regional")
            ) or None

            equipment.local_armazenagem = normalize_name(
                get_optional(form_data, "local_armazenagem")
            ) or None

            equipment.subestacao_origem = normalize_name(
                get_optional(form_data, "subestacao_origem")
            ) or None

            equipment.status = get_required(form_data, "status", "Status")
            equipment.observacoes = get_optional(form_data, "observacoes")
            equipment.validado = form_data.get("validado") == "on"

            db.session.commit()

            AuditService.register(
                entity_type="EQUIPMENT",
                entity_id=equipment.id,
                action="UPDATE_EQUIPMENT",
                performed_by=AuthService.get_current_user_display_name(),
                old_data=old_data,
                new_data={
                    "fabricante": equipment.fabricante,
                    "modelo": equipment.modelo,
                    "tipo_equipamento": equipment.tipo_equipamento,
                    "patrimonio": equipment.patrimonio,
                    "codigo_equipamento": equipment.codigo_equipamento,
                    "serial": equipment.serial,
                    "categoria": equipment.categoria,
                    "regional": equipment.regional,
                    "local_armazenagem": equipment.local_armazenagem,
                    "subestacao_origem": equipment.subestacao_origem,
                    "status": equipment.status,
                    "validado": equipment.validado,
                },
            )

            flash("Equipamento atualizado com sucesso.", "success")

            try:
                ExcelInventoryService.upsert_equipment_to_excel(equipment)
                flash("Planilha atualizada com sucesso.", "success")
            
            except Exception as exc:
                flash(
                    "Equipamento atualizado no banco, mas a planilha não foi atualizada: "
                    + str(exc),
                    "error",
                )

                SyncPendingService.create_equipment_excel_pending(
                    equipment=equipment,
                    error=str(exc),
                    created_by="SISTEMA",
                )

            return redirect(url_for("equipment_bp.list_items"))

        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template(
        "equipment_edit.html",
        equipment=equipment,
        status_options=[status.value for status in EquipmentStatus],
    )


@equipment_bp.route("/buscar")
def search_items():
    """
    API de busca de equipamentos para a tela de novo empréstimo.

    Retorna apenas equipamentos DISPONÍVEIS.
    """

    query_text = request.args.get("q", "").strip()

    if not query_text:
        return jsonify([])

    query_normalized = normalize_name(query_text)
    search_pattern = f"%{query_normalized}%"

    equipments = Equipment.query.filter(
        Equipment.status == EquipmentStatus.DISPONIVEL.value,
        or_(
            Equipment.codigo_interno.ilike(search_pattern),
            Equipment.nome_normalizado.ilike(search_pattern),
            Equipment.patrimonio.ilike(search_pattern),
            Equipment.codigo_equipamento.ilike(search_pattern),
            Equipment.serial.ilike(search_pattern),
            Equipment.fabricante.ilike(search_pattern),
            Equipment.modelo.ilike(search_pattern),
            Equipment.tipo_equipamento.ilike(search_pattern),
            Equipment.regional.ilike(search_pattern),
            Equipment.local_armazenagem.ilike(search_pattern),
        ),
    ).order_by(
        Equipment.codigo_interno.asc(),
        Equipment.tipo_equipamento.asc(),
        Equipment.fabricante.asc(),
        Equipment.modelo.asc(),
    ).limit(20).all()

    result = []

    for equipment in equipments:
        result.append(
            {
                "id": equipment.id,
                "codigo_interno": equipment.codigo_interno or "",
                "tipo_equipamento": equipment.tipo_equipamento or "",
                "fabricante": equipment.fabricante or "",
                "modelo": equipment.modelo or "",
                "patrimonio": equipment.patrimonio or "",
                "codigo_equipamento": equipment.codigo_equipamento or "",
                "serial": equipment.serial or "",
                "status": equipment.status or "",
                "regional": equipment.regional or "",
                "local_armazenagem": equipment.local_armazenagem or "",
            }
        )

    return jsonify(result)

@equipment_bp.route("/<int:equipment_id>/historico")
def item_history(equipment_id: int):
    """
    Mostra o histórico completo de empréstimos de um equipamento.

    Permite rastrear:
    - em quais empréstimos o equipamento apareceu;
    - quem solicitou;
    - datas;
    - devolução;
    - status do item;
    - imagem vinculada ao empréstimo.
    """

    equipment = Equipment.query.get_or_404(equipment_id)

    loan_items = (
        LoanItem.query
        .filter_by(equipment_id=equipment.id)
        .order_by(LoanItem.created_at.desc())
        .all()
    )

    return render_template(
        "equipment_history.html",
        equipment=equipment,
        loan_items=loan_items,
    )