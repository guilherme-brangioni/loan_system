from typing import Any
from database.database import db
from datetime import datetime
from math import ceil
from sqlalchemy import or_
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from enums.loan_status import LoanStatus

from models.loan_item import LoanItem
from models.loan import Loan
from models.loan_item import LoanItem
from models.equipment import Equipment
from models.loan_item import LoanItem
from models.user import User

from services.email_service import EmailService
from services.email_log_service import EmailLogService
from services.loan_service import LoanService
from services.notification_recipient_service import NotificationRecipientService
from services.pdf_service import PDFService
from services.image_upload_service import ImageUploadService
from services.audit_service import AuditService
from services.excel_movement_service import ExcelMovementService
from services.auth_service import AuthService
from services.verification_token_service import VerificationTokenService

from utils.normalize import normalize_name


loan_bp = Blueprint("loan_bp", __name__, url_prefix="/emprestimos")

def _parse_date_filter(value: str):
    """
    Converte texto YYYY-MM-DD vindo do filtro de data.
    """

    value = str(value or "").strip()

    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _loan_has_pending_validation(loan) -> bool:
    """
    Verifica se o empréstimo possui equipamento pendente de validação.
    """

    for item in getattr(loan, "items", []) or []:
        equipment = getattr(item, "equipment", None)

        if equipment is not None and not bool(getattr(equipment, "validado", False)):
            return True

    return False

@loan_bp.route("/")
def list_loans():
    """
    Lista empréstimos com filtros avançados.

    Filtros:
    - busca geral;
    - status;
    - pendência de validação;
    - data inicial/final;
    - somente atrasados;
    - paginação.
    """

    search_text = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    validation_filter = request.args.get("validacao", "").strip()
    overdue_filter = request.args.get("atrasados", "").strip()

    date_from_text = request.args.get("data_inicio", "").strip()
    date_to_text = request.args.get("data_fim", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    if per_page not in [25, 50, 100]:
        per_page = 50

    query = Loan.query

    if status_filter:
        query = query.filter(Loan.status == status_filter)

    date_from = _parse_date_filter(date_from_text)
    date_to = _parse_date_filter(date_to_text)

    if date_from:
        query = query.filter(Loan.data_emprestimo >= date_from)

    if date_to:
        query = query.filter(Loan.data_emprestimo <= date_to)

    if overdue_filter == "SIM":
        query = query.filter(Loan.status == LoanStatus.ATRASADO.value)

    if search_text:
        normalized_search = normalize_name(search_text)
        pattern = f"%{normalized_search}%"

        loan_ids_from_user = [
            row[0] for row in (
                db.session.query(Loan.id)
                .join(User, Loan.user_id == User.id)
                .filter(
                    or_(
                        Loan.numero_controle.ilike(pattern),
                        User.nome.ilike(pattern),
                        User.matricula.ilike(pattern),
                        User.email.ilike(pattern),
                        User.gerencia.ilike(pattern),
                        User.regional.ilike(pattern),
                        User.equipe.ilike(pattern),
                    )
                )
                .distinct()
                .all()
            )
        ]

        loan_ids_from_equipment = [
            row[0] for row in (
                db.session.query(LoanItem.loan_id)
                .join(Equipment, LoanItem.equipment_id == Equipment.id)
                .filter(
                    or_(
                        Equipment.codigo_interno.ilike(pattern),
                        Equipment.nome_normalizado.ilike(pattern),
                        Equipment.tipo_equipamento.ilike(pattern),
                        Equipment.fabricante.ilike(pattern),
                        Equipment.modelo.ilike(pattern),
                        Equipment.patrimonio.ilike(pattern),
                        Equipment.codigo_equipamento.ilike(pattern),
                        Equipment.serial.ilike(pattern),
                    )
                )
                .distinct()
                .all()
            )
        ]

        loan_ids = set(loan_ids_from_user + loan_ids_from_equipment)

        if loan_ids:
            query = query.filter(Loan.id.in_(loan_ids))
        else:
            query = query.filter(Loan.id == -1)

    loans_all = (
        query
        .order_by(Loan.created_at.desc())
        .all()
    )

    if validation_filter == "PENDENTE":
        loans_all = [
            loan for loan in loans_all
            if _loan_has_pending_validation(loan)
        ]
    elif validation_filter == "VALIDADO":
        loans_all = [
            loan for loan in loans_all
            if not _loan_has_pending_validation(loan)
        ]

    total = len(loans_all)
    pages = max(ceil(total / per_page), 1)

    if page < 1:
        page = 1

    if page > pages:
        page = pages

    start = (page - 1) * per_page
    end = start + per_page

    loans = loans_all[start:end]

    pagination = {
        "page": page,
        "pages": pages,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1,
        "next_num": page + 1,
    }

    return render_template(
        "loan_list.html",
        loans=loans,
        pagination=pagination,
        search_text=search_text,
        status_filter=status_filter,
        validation_filter=validation_filter,
        overdue_filter=overdue_filter,
        date_from_text=date_from_text,
        date_to_text=date_to_text,
        per_page=per_page,
        status_options=[status.value for status in LoanStatus],
    )


@loan_bp.route("/novo", methods=["GET", "POST"])
def new_loan():
    """
    Cria um novo empréstimo.

    Agora os equipamentos são selecionados a partir do banco,
    usando selected_equipment_ids[].
    """

    fixed_notification_emails = (
        NotificationRecipientService.get_fixed_notification_emails()
    )

    if request.method == "POST":
        try:
            form_data: dict[str, Any] = request.form.to_dict(flat=True)

            selected_equipment_ids = request.form.getlist("selected_equipment_ids[]")

            if not selected_equipment_ids:
                raise ValueError(
                    "Selecione ao menos um equipamento/material para o empréstimo."
                )

            form_data["selected_equipment_ids"] = selected_equipment_ids

            extra_notification_text = form_data.get(
                "notification_emails",
                "",
            )

            extra_notification_emails = (
                NotificationRecipientService.parse_email_list(
                    extra_notification_text
                )
            )

            form_data["notification_extra_emails"] = extra_notification_emails

            loan = LoanService.create_loan(form_data)

            loan_items = LoanItem.query.filter_by(
                loan_id=loan.id
            ).all()

            for item in loan_items:
                if not item.equipment_id:
                    continue

                image_field_name = f"equipment_image_{item.equipment_id}"

                uploaded_file = request.files.get(image_field_name)

                if uploaded_file and uploaded_file.filename:
                    ImageUploadService.save_loan_item_image(
                        loan_item=item,
                        file_storage=uploaded_file,
                    )

            ExcelMovementService.try_append_loan_movement(
                loan=loan,
                movement_type="SOLICITACAO",
                performed_by=loan.responsavel_entrega_nome,
                notes="Solicitação de empréstimo criada.",
            )

            review_url = (
                current_app.config["APP_BASE_URL"]
                + url_for(
                    "loan_bp.review_approval",
                    token=loan.approval_token,
                )
            )

            body = EmailService.build_approval_body(
                loan,
                review_url,
            )

            result = EmailService.try_send_email(
                recipients=[loan.approver.email],
                subject=f"Aprovação de empréstimo - {loan.numero_controle}",
                body=body,
            )

            if result.get("success"):
                flash(
                    "Empréstimo criado e e-mail de aprovação enviado.",
                    "success",
                )
            else:
                flash(
                    "Empréstimo criado, mas o e-mail não foi enviado: "
                    + result.get("error", "Erro desconhecido."),
                    "error",
                )

            notification_recipients = (
                NotificationRecipientService.get_loan_all_recipients(loan)
            )

            if notification_recipients:
                notification_subject = (
                    f"Solicitação de empréstimo registrada - "
                    f"{loan.numero_controle}"
                )

                notification_body = EmailService.build_loan_notification_body(
                    loan
                )

                notification_result = EmailService.try_send_email(
                    recipients=notification_recipients,
                    subject=notification_subject,
                    body=notification_body,
                )

                EmailLogService.register(
                    email_type="LOAN_NOTIFICATION",
                    loan_id=loan.id,
                    recipients=notification_recipients,
                    subject=notification_subject,
                    success=bool(notification_result.get("success")),
                    error=notification_result.get("error"),
                )

            return redirect(
                url_for("loan_bp.loan_detail", loan_id=loan.id)
            )

        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "loan_form.html",
        fixed_notification_emails=fixed_notification_emails,
    )


@loan_bp.route("/<int:loan_id>")
def loan_detail(loan_id: int):
    """
    Exibe os detalhes de um empréstimo.
    """

    loan = Loan.query.get_or_404(loan_id)

    return render_template(
        "loan_detail.html",
        loan=loan,
    )


@loan_bp.route("/revisar-aprovacao/<token>", methods=["GET"])
def review_approval(token: str):
    """
    Tela segura de revisão da aprovação.

    O link do e-mail abre esta página.
    O aprovador visualiza os dados antes de aprovar ou rejeitar.
    """

    try:
        loan = LoanService.get_loan_by_approval_token(token)

        return render_template(
            "approval_review.html",
            loan=loan,
            token=token,
        )

    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("main_bp.dashboard"))


@loan_bp.route("/aprovar/<token>", methods=["POST"])
def approve_loan(token: str):
    """
    Aprova o empréstimo após confirmação na tela de revisão.
    """

    try:
        loan = LoanService.approve_loan(token)

        ExcelMovementService.try_append_loan_movement(
            loan=loan,
            movement_type="APROVACAO",
            performed_by=loan.approver.nome,
            notes="Solicitação aprovada.",
        )

        flash(
            f"Empréstimo {loan.numero_controle} aprovado com sucesso.",
            "success",
        )

        return redirect(
            url_for("loan_bp.loan_detail", loan_id=loan.id)
        )

    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("main_bp.dashboard"))


@loan_bp.route("/rejeitar/<token>", methods=["POST"])
def reject_loan(token: str):
    """
    Rejeita o empréstimo após confirmação na tela de revisão.
    """

    try:
        form_data = request.form.to_dict(flat=True)

        reason = form_data.get("reason", "").strip()

        loan = LoanService.reject_loan(
            token,
            reason=reason or "Rejeitado pelo aprovador.",
        )

        ExcelMovementService.try_append_loan_movement(
            loan=loan,
            movement_type="REJEICAO",
            performed_by=loan.approver.nome,
            notes=reason or "Rejeitado pelo aprovador.",
        )

        flash(
            f"Empréstimo {loan.numero_controle} rejeitado.",
            "success",
        )

        return redirect(
            url_for("loan_bp.loan_detail", loan_id=loan.id)
        )

    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("main_bp.dashboard"))


@loan_bp.route("/<int:loan_id>/confirmar-retirada", methods=["POST"])
def confirm_withdrawal(loan_id: int):
    """
    Confirma que o equipamento/material foi entregue ao solicitante.

    Após a retirada:
    - empréstimo muda para RETIRADO;
    - equipamentos reservados mudam para EMPRESTADO;
    - PDF é gerado;
    - comprovante é enviado ao solicitante.
    """

    try:
        form_data = request.form.to_dict(flat=True)

        performed_by = form_data.get("performed_by", "").strip()

        loan = LoanService.confirm_withdrawal(
            loan_id=loan_id,
            performed_by=performed_by,
        )

        ExcelMovementService.try_append_loan_movement(
            loan=loan,
            movement_type="RETIRADA",
            performed_by=performed_by,
            notes="Retirada/coleta confirmada.",
        )

        pdf_path = PDFService.generate_loan_pdf(loan)

        body = EmailService.build_confirmation_body(loan)

        receipt_recipients = (
    NotificationRecipientService.get_loan_receipt_recipients(loan)
)

        result = EmailService.try_send_email(
            recipients=receipt_recipients,
            subject=f"Comprovante de empréstimo - {loan.numero_controle}",
            body=body,
            attachment_path=pdf_path,
        )

        EmailLogService.register(
            email_type="LOAN_RECEIPT",
            loan_id=loan.id,
            recipients=receipt_recipients,
            subject=f"Comprovante de empréstimo - {loan.numero_controle}",
            success=bool(result.get("success")),
            error=result.get("error"),
        )

        if result.get("success"):
            flash(
                "Retirada confirmada e comprovante enviado por e-mail.",
                "success",
            )
        else:
            flash(
                "Retirada confirmada, mas houve falha ao enviar e-mail: "
                + result.get("error", "Erro desconhecido."),
                "error",
            )

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan_id))


@loan_bp.route("/<int:loan_id>/devolver", methods=["GET", "POST"])
def return_items(loan_id: int):
    """
    Tela de devolução parcial ou total.
    """

    loan = Loan.query.get_or_404(loan_id)

    if request.method == "POST":
        try:
            form_data = request.form.to_dict(flat=True)

            loan_item_id_text = form_data.get("loan_item_id", "")
            quantidade_text = form_data.get("quantidade", "1")
            devolvido_por = form_data.get("devolvido_por", "").strip()

            if not loan_item_id_text:
                raise ValueError("Selecione um item para devolução.")

            if not devolvido_por:
                raise ValueError("Informe quem recebeu a devolução.")

            loan_item_id = int(loan_item_id_text)
            quantidade = int(quantidade_text or 1)

            loan = LoanService.return_item(
                loan_item_id=loan_item_id,
                quantidade=quantidade,
                devolvido_por=devolvido_por,
            )

            ExcelMovementService.try_append_loan_movement(
                loan=loan,
                movement_type="DEVOLUCAO_ITEM",
                performed_by=devolvido_por,
                notes="Devolução de item registrada.",
            )

            pdf_path = PDFService.generate_loan_pdf(loan)

            return_recipients = (
                NotificationRecipientService.get_loan_receipt_recipients(loan)
            )

            if return_recipients:
                subject = (
                    f"Confirmação de devolução - "
                    f"{loan.numero_controle}"
                )

                body = EmailService.build_return_confirmation_body(
                    loan=loan,
                    returned_by=devolvido_por,
                    return_type="DEVOLUCAO_ITEM",
                )

                result = EmailService.try_send_email(
                    recipients=return_recipients,
                    subject=subject,
                    body=body,
                    attachment_path=pdf_path,
                )

                EmailLogService.register(
                    email_type="RETURN_CONFIRMATION",
                    loan_id=loan.id,
                    recipients=return_recipients,
                    subject=subject,
                    success=bool(result.get("success")),
                    error=result.get("error"),
                )

                if result.get("success"):
                    flash(
                        "E-mail de confirmação de devolução enviado.",
                        "success",
                    )
                else:
                    flash(
                        "Devolução registrada, mas houve falha ao enviar e-mail: "
                        + result.get("error", "Erro desconhecido."),
                        "error",
                    )

            flash("Item devolvido com sucesso.", "success")

            return redirect(
                url_for("loan_bp.loan_detail", loan_id=loan_id)
            )

        except Exception as exc:
            flash(str(exc), "error")

    return render_template("return_form.html", loan=loan)


@loan_bp.route("/<int:loan_id>/renovar", methods=["POST"])
def renew_loan(loan_id: int):
    """
    Renova o prazo de devolução do empréstimo.
    """

    try:
        form_data = request.form.to_dict(flat=True)

        loan = LoanService.renew_loan(
            loan_id=loan_id,
            new_due_date_text=form_data.get("new_due_date", ""),
            renewed_by=AuthService.get_current_user_display_name(),
            reason=form_data.get("reason", ""),
        )

        ExcelMovementService.try_append_loan_movement(
            loan=loan,
            movement_type="RENOVACAO",
            performed_by=AuthService.get_current_user_display_name(),
            notes=form_data.get("reason", ""),
        )

        flash("Empréstimo renovado com sucesso.", "success")

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan_id))


@loan_bp.route("/<int:loan_id>/pdf")
def loan_pdf(loan_id: int):
    """
    Gera e baixa o PDF do empréstimo.
    """

    loan = Loan.query.get_or_404(loan_id)

    pdf_path = PDFService.generate_loan_pdf(loan)

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"{loan.numero_controle}.pdf",
    )


@loan_bp.route("/<int:loan_id>/devolver-tudo", methods=["POST"])
def return_all_items(loan_id: int):
    """
    Marca todos os itens do empréstimo como devolvidos.

    Usado principalmente em devolução antecipada total.
    """

    try:
        form_data = request.form.to_dict(flat=True)

        devolvido_por = form_data.get("devolvido_por", "").strip()

        if not devolvido_por:
            raise ValueError("Informe quem devolveu o equipamento.")

        loan = LoanService.return_all_items(
            loan_id=loan_id,
            devolvido_por=devolvido_por,
        )

        ExcelMovementService.try_append_loan_movement(
            loan=loan,
            movement_type="DEVOLUCAO_TOTAL",
            performed_by=devolvido_por,
            notes="Devolução total registrada.",
        )

        pdf_path = PDFService.generate_loan_pdf(loan)

        return_recipients = (
            NotificationRecipientService.get_loan_receipt_recipients(loan)
        )

        if return_recipients:
            subject = (
                f"Confirmação de devolução total - "
                f"{loan.numero_controle}"
            )

            body = EmailService.build_return_confirmation_body(
                loan=loan,
                returned_by=devolvido_por,
                return_type="DEVOLUCAO_TOTAL",
            )

            result = EmailService.try_send_email(
                recipients=return_recipients,
                subject=subject,
                body=body,
                attachment_path=pdf_path,
            )

            EmailLogService.register(
                email_type="RETURN_TOTAL_CONFIRMATION",
                loan_id=loan.id,
                recipients=return_recipients,
                subject=subject,
                success=bool(result.get("success")),
                error=result.get("error"),
            )

            if result.get("success"):
                flash(
                    "E-mail de confirmação de devolução total enviado.",
                    "success",
                )
            else:
                flash(
                    "Devolução registrada, mas houve falha ao enviar e-mail: "
                    + result.get("error", "Erro desconhecido."),
                    "error",
                )

        flash("Empréstimo marcado como devolvido com sucesso.", "success")

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan_id))

@loan_bp.route("/<int:loan_id>/validar-equipamentos", methods=["POST"])
def validate_loan_equipments(loan_id: int):
    """
    Valida todos os equipamentos pendentes vinculados a um empréstimo.

    Pode ser acionado pelo dashboard, pela aba de empréstimos ou pelo detalhe.
    """

    loan = Loan.query.get_or_404(loan_id)

    try:
        validated_by = AuthService.get_current_user_display_name()

        loan_items = LoanItem.query.filter_by(
            loan_id=loan.id
        ).all()

        validated_count = 0

        for item in loan_items:
            equipment = getattr(item, "equipment", None)

            if equipment is None:
                continue

            if not bool(equipment.validado):
                equipment.validado = True
                validated_count += 1

        db.session.commit()

        AuditService.register(
            entity_type="LOAN",
            entity_id=loan.id,
            action="VALIDATE_LOAN_EQUIPMENTS",
            performed_by=validated_by,
            new_data={
                "numero_controle": loan.numero_controle,
                "validated_count": validated_count,
            },
        )

        if validated_count:
            flash(
                f"{validated_count} equipamento(s) validado(s) com sucesso.",
                "success",
            )
        else:
            flash(
                "Nenhum equipamento pendente de validação neste empréstimo.",
                "success",
            )

    except Exception as exc:
        db.session.rollback()
        flash(str(exc), "error")

    return redirect(url_for("loan_bp.loan_detail", loan_id=loan.id))

@loan_bp.route("/atrasados")
def overdue_report():
    """
    Relatório visual de empréstimos atrasados.
    """

    LoanService.mark_overdue_loans()

    loans = (
        Loan.query
        .filter(Loan.status == LoanStatus.ATRASADO.value)
        .order_by(Loan.data_prevista_devolucao.asc())
        .all()
    )

    return render_template(
        "overdue_report.html",
        loans=loans,
    )

@loan_bp.route("/verificar/<token>")
def verify_loan_document(token: str):
    """
    Página de verificação do comprovante via QR Code.

    Esta rota é apenas consultiva.
    Não executa nenhuma ação no empréstimo.
    """

    try:
        data = VerificationTokenService.validate_token(token)

        loan = Loan.query.get_or_404(data["loan_id"])

        return render_template(
            "loan_verification.html",
            loan=loan,
        )

    except Exception as exc:
        return render_template(
            "loan_verification_error.html",
            error=str(exc),
        )