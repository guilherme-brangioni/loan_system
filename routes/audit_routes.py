from flask import Blueprint, render_template, request

from models.audit_log import AuditLog


audit_bp = Blueprint("audit_bp", __name__, url_prefix="/auditoria")


@audit_bp.route("/")
def audit_list():
    """
    Lista registros de auditoria do sistema.

    Permite filtrar por:
    - entity_type
    - action
    - entity_id
    """

    entity_type = request.args.get("entity_type", "").strip()
    action = request.args.get("action", "").strip()
    entity_id = request.args.get("entity_id", "").strip()

    query = AuditLog.query

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    if action:
        query = query.filter(AuditLog.action == action)

    if entity_id:
        try:
            query = query.filter(AuditLog.entity_id == int(entity_id))
        except ValueError:
            pass

    logs = query.order_by(
        AuditLog.created_at.desc()
    ).limit(300).all()

    return render_template(
        "audit_list.html",
        logs=logs,
        entity_type=entity_type,
        action=action,
        entity_id=entity_id,
    )