from datetime import datetime

from database.database import db

from models.equipment import Equipment
from models.sync_pending import SyncPending

from services.audit_service import AuditService
from services.excel_inventory_service import ExcelInventoryService


class SyncPendingService:
    """
    Serviço para controlar pendências de sincronização externa.

    Nesta etapa, usamos principalmente para falhas ao atualizar a planilha Excel.
    """

    STATUS_PENDENTE = "PENDENTE"
    STATUS_ERRO = "ERRO"
    STATUS_RESOLVIDO = "RESOLVIDO"

    TARGET_EXCEL = "EXCEL"

    ACTION_UPSERT_EQUIPMENT_TO_EXCEL = "UPSERT_EQUIPMENT_TO_EXCEL"

    @staticmethod
    def create_equipment_excel_pending(
        equipment: Equipment,
        error: str,
        created_by: str = "SISTEMA",
    ) -> SyncPending:
        """
        Cria ou atualiza uma pendência de sincronização de equipamento com Excel.

        Evita criar várias pendências duplicadas para o mesmo equipamento.
        """

        existing = SyncPending.query.filter(
            SyncPending.entity_type == "EQUIPMENT",
            SyncPending.entity_id == equipment.id,
            SyncPending.action == SyncPendingService.ACTION_UPSERT_EQUIPMENT_TO_EXCEL,
            SyncPending.target == SyncPendingService.TARGET_EXCEL,
            SyncPending.status.in_([
                SyncPendingService.STATUS_PENDENTE,
                SyncPendingService.STATUS_ERRO,
            ]),
        ).first()

        if existing:
            existing.last_error = error
            existing.status = SyncPendingService.STATUS_ERRO
            db.session.commit()
            return existing

        pending = SyncPending()

        pending.entity_type = "EQUIPMENT"
        pending.entity_id = equipment.id
        pending.action = SyncPendingService.ACTION_UPSERT_EQUIPMENT_TO_EXCEL
        pending.target = SyncPendingService.TARGET_EXCEL
        pending.status = SyncPendingService.STATUS_ERRO
        pending.last_error = error
        pending.created_by = created_by

        db.session.add(pending)
        db.session.commit()

        return pending

    @staticmethod
    def list_active_pendings():
        """
        Lista pendências ainda não resolvidas.
        """

        return (
            SyncPending.query
            .filter(
                SyncPending.status.in_([
                    SyncPendingService.STATUS_PENDENTE,
                    SyncPendingService.STATUS_ERRO,
                ])
            )
            .order_by(SyncPending.created_at.desc())
            .all()
        )

    @staticmethod
    def list_resolved_pendings(limit: int = 100):
        """
        Lista últimas pendências resolvidas.
        """

        return (
            SyncPending.query
            .filter_by(status=SyncPendingService.STATUS_RESOLVIDO)
            .order_by(SyncPending.resolved_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def retry_pending(pending: SyncPending, performed_by: str = "SISTEMA") -> dict:
        """
        Tenta processar novamente uma pendência.
        """

        pending.attempts = int(pending.attempts or 0) + 1
        pending.last_attempt_at = datetime.utcnow()

        try:
            if (
                pending.entity_type == "EQUIPMENT"
                and pending.action == SyncPendingService.ACTION_UPSERT_EQUIPMENT_TO_EXCEL
                and pending.target == SyncPendingService.TARGET_EXCEL
            ):
                equipment = db.session.get(Equipment, pending.entity_id)

                if not equipment:
                    raise ValueError(
                        f"Equipamento ID {pending.entity_id} não encontrado."
                    )

                ExcelInventoryService.upsert_equipment_to_excel(equipment)

                pending.status = SyncPendingService.STATUS_RESOLVIDO
                pending.last_error = None
                pending.resolved_at = datetime.utcnow()
                pending.resolved_by = performed_by

                db.session.commit()

                AuditService.register(
                    entity_type="SYNC_PENDING",
                    entity_id=pending.id,
                    action="RESOLVE_SYNC_PENDING",
                    performed_by=performed_by,
                    new_data={
                        "entity_type": pending.entity_type,
                        "entity_id": pending.entity_id,
                        "action": pending.action,
                        "target": pending.target,
                    },
                )

                return {
                    "success": True,
                    "message": "Pendência resolvida com sucesso.",
                }

            raise ValueError(
                f"Ação de sincronização não suportada: {pending.action}"
            )

        except Exception as exc:
            pending.status = SyncPendingService.STATUS_ERRO
            pending.last_error = str(exc)

            db.session.commit()

            AuditService.register(
                entity_type="SYNC_PENDING",
                entity_id=pending.id,
                action="RETRY_SYNC_PENDING_FAILED",
                performed_by=performed_by,
                new_data={
                    "error": str(exc),
                    "attempts": pending.attempts,
                },
            )

            return {
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def retry_all_active(performed_by: str = "SISTEMA") -> dict:
        """
        Tenta reprocessar todas as pendências ativas.
        """

        pendings = SyncPendingService.list_active_pendings()

        total = len(pendings)
        success = 0
        failed = 0

        for pending in pendings:
            result = SyncPendingService.retry_pending(
                pending=pending,
                performed_by=performed_by,
            )

            if result.get("success"):
                success += 1
            else:
                failed += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
        }
    
    @staticmethod
    def count_active_pendings() -> int:
        """
        Conta pendências de sincronização ainda não resolvidas.
        """

        return (
            SyncPending.query
            .filter(
                SyncPending.status.in_([
                    SyncPendingService.STATUS_PENDENTE,
                    SyncPendingService.STATUS_ERRO,
                ])
            )
            .count()
        )