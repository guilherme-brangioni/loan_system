import json
import os
import re
from typing import List

from flask import current_app


class NotificationRecipientService:
    """
    Serviço responsável por tratar os destinatários informativos.

    Existem dois tipos:
    - fixos: vêm do arquivo fixed_notification_emails.txt;
    - variáveis: são digitados no momento do empréstimo.
    """

    EMAIL_REGEX = re.compile(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )

    @staticmethod
    def parse_email_list(raw_text: str) -> List[str]:
        """
        Recebe texto com e-mails separados por:
        - linha;
        - vírgula;
        - ponto e vírgula.

        Retorna lista limpa, sem duplicidade.
        """

        if not raw_text:
            return []

        normalized_text = raw_text.replace(";", ",").replace("\n", ",")

        emails: list[str] = []
        seen: set[str] = set()

        for part in normalized_text.split(","):
            email = part.strip().lower()

            if not email:
                continue

            if not NotificationRecipientService.EMAIL_REGEX.match(email):
                raise ValueError(f"E-mail inválido: {email}")

            if email not in seen:
                seen.add(email)
                emails.append(email)

        return emails

    @staticmethod
    def get_fixed_notification_emails() -> List[str]:
        """
        Lê os e-mails fixos do arquivo configurado.

        Se o arquivo não existir, retorna lista vazia.
        Isso evita quebrar o sistema durante testes.
        """

        file_path = current_app.config["FIXED_NOTIFICATION_EMAILS_FILE"]

        if not os.path.exists(file_path):
            return []

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        return NotificationRecipientService.parse_email_list(content)

    @staticmethod
    def merge_recipients(
        fixed_emails: List[str],
        extra_emails: List[str],
    ) -> List[str]:
        """
        Junta listas de e-mails removendo:
        - valores vazios;
        - None;
        - duplicidades.

        Essa proteção é importante porque empréstimos antigos podem não ter
        responsavel_entrega_email preenchido.
        """

        result: list[str] = []
        seen: set[str] = set()

        for raw_email in fixed_emails + extra_emails:
            if raw_email is None:
                continue

            email_normalized = str(raw_email).strip().lower()

            if not email_normalized:
                continue

            if email_normalized not in seen:
                seen.add(email_normalized)
                result.append(email_normalized)

        return result

    @staticmethod
    def to_json(emails: List[str]) -> str:
        """
        Salva lista em JSON para guardar no banco.
        """

        return json.dumps(emails, ensure_ascii=False)

    @staticmethod
    def from_json(raw_json: str | None) -> List[str]:
        """
        Lê lista salva no banco.

        Se vier vazio, None ou JSON inválido, retorna lista vazia.
        """

        if not raw_json:
            return []

        try:
            data = json.loads(raw_json)

            if not isinstance(data, list):
                return []

            emails: list[str] = []

            for item in data:
                if item is None:
                    continue

                email = str(item).strip().lower()

                if email:
                    emails.append(email)

            return emails

        except Exception:
            return []

    @staticmethod
    def get_loan_all_recipients(loan) -> List[str]:
        """
        Retorna todos os destinatários salvos no empréstimo.
        """

        return NotificationRecipientService.from_json(
            loan.notification_all_emails
        )
    
    @staticmethod
    def get_loan_receipt_recipients(loan) -> List[str]:
        """
        Retorna todos os destinatários que devem receber o comprovante PDF.

        Inclui:
        - e-mails fixos;
        - e-mails variáveis informados no empréstimo;
        - solicitante;
        - aprovador;
        - responsável pela coleta/entrega.

        Protege contra valores None em empréstimos antigos.
        """

        notification_emails = NotificationRecipientService.from_json(
            getattr(loan, "notification_all_emails", None)
        )

        user_email = ""
        approver_email = ""
        responsible_email = ""

        if getattr(loan, "user", None) is not None:
            user_email = getattr(loan.user, "email", "") or ""

        if getattr(loan, "approver", None) is not None:
            approver_email = getattr(loan.approver, "email", "") or ""

        responsible_email = getattr(loan, "responsavel_entrega_email", "") or ""

        involved_emails = [
            user_email,
            approver_email,
            responsible_email,
        ]

        return NotificationRecipientService.merge_recipients(
            notification_emails,
            involved_emails,
        )