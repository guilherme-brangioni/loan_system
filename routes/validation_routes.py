from flask import Blueprint, flash, redirect, render_template, request, url_for

from database.database import db

from models.consumable import Consumable
from models.equipment import Equipment

from services.audit_service import AuditService

from utils.form_helpers import get_int, get_optional, get_required
from utils.normalize import normalize_name


validation_bp = Blueprint(
    "validation_bp",
    __name__,
    url_prefix="/validacao",
)


@validation_bp.route("/")
def validation_list():
    """
    Lista todos os itens criados automaticamente
    que ainda precisam ser conferidos.

    Esses itens possuem validado=False.
    """

    pending_equipments = Equipment.query.filter_by(
        validado=False
    ).order_by(
        Equipment.created_at.desc()
    ).all()

    pending_consumables = Consumable.query.filter_by(
        validado=False
    ).order_by(
        Consumable.created_at.desc()
    ).all()

    return render_template(
        "validation_list.html",
        pending_equipments=pending_equipments,
        pending_consumables=pending_consumables,
    )


@validation_bp.route("/equipamento/<int:equipment_id>", methods=["GET", "POST"])
def validate_equipment(equipment_id: int):
    """
    Tela para validar/corrigir equipamento patrimonial
    criado automaticamente.
    """

    equipment = Equipment.query.get_or_404(equipment_id)

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            old_data = {
                "nome": equipment.nome,
                "patrimonio": equipment.patrimonio,
                "serial": equipment.serial,
                "categoria": equipment.categoria,
                "validado": equipment.validado,
            }

            equipment.nome = normalize_name(
                get_required(form_data, "nome", "Nome")
            )

            equipment.nome_normalizado = normalize_name(equipment.nome)

            patrimonio = get_optional(form_data, "patrimonio")
            serial = get_optional(form_data, "serial")
            categoria = get_optional(form_data, "categoria")
            observacoes = get_optional(form_data, "observacoes")

            equipment.patrimonio = normalize_name(patrimonio) if patrimonio else None
            equipment.serial = normalize_name(serial) if serial else None
            equipment.categoria = normalize_name(categoria) if categoria else None
            equipment.observacoes = observacoes
            equipment.validado = True

            db.session.commit()

            AuditService.register(
                entity_type="EQUIPMENT",
                entity_id=equipment.id,
                action="VALIDATE_EQUIPMENT",
                performed_by=get_optional(form_data, "validated_by", "SISTEMA"),
                old_data=old_data,
                new_data={
                    "nome": equipment.nome,
                    "patrimonio": equipment.patrimonio,
                    "serial": equipment.serial,
                    "categoria": equipment.categoria,
                    "validado": equipment.validado,
                },
            )

            flash("Equipamento validado com sucesso.", "success")

            return redirect(url_for("validation_bp.validation_list"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "validate_equipment.html",
        equipment=equipment,
    )


@validation_bp.route("/consumivel/<int:consumable_id>", methods=["GET", "POST"])
def validate_consumable(consumable_id: int):
    """
    Tela para validar/corrigir consumível criado automaticamente.
    """

    consumable = Consumable.query.get_or_404(consumable_id)

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            old_data = {
                "nome": consumable.nome,
                "categoria": consumable.categoria,
                "quantidade": consumable.quantidade,
                "limite_alerta": consumable.limite_alerta,
                "validado": consumable.validado,
            }

            consumable.nome = normalize_name(
                get_required(form_data, "nome", "Nome")
            )

            consumable.nome_normalizado = normalize_name(consumable.nome)

            categoria = get_optional(form_data, "categoria")
            observacoes = get_optional(form_data, "observacoes")

            consumable.categoria = normalize_name(categoria) if categoria else None

            consumable.quantidade = get_int(
                form_data,
                "quantidade",
                "Quantidade",
                default=0,
            )

            consumable.limite_alerta = get_int(
                form_data,
                "limite_alerta",
                "Limite de alerta",
                default=1,
            )

            consumable.observacoes = observacoes
            consumable.validado = True

            db.session.commit()

            AuditService.register(
                entity_type="CONSUMABLE",
                entity_id=consumable.id,
                action="VALIDATE_CONSUMABLE",
                performed_by=get_optional(form_data, "validated_by", "SISTEMA"),
                old_data=old_data,
                new_data={
                    "nome": consumable.nome,
                    "categoria": consumable.categoria,
                    "quantidade": consumable.quantidade,
                    "limite_alerta": consumable.limite_alerta,
                    "validado": consumable.validado,
                },
            )

            flash("Consumível validado com sucesso.", "success")

            return redirect(url_for("validation_bp.validation_list"))

        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "validate_consumable.html",
        consumable=consumable,
    )