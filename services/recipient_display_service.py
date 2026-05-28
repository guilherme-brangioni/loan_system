import json
from typing import Any

from sqlalchemy import func

from models.approver import Approver
from models.system_user import SystemUser
from models.user import User


class RecipientDisplayService:
    """
    Converte destinatários de e-mail em nomes para exibição.

    Mantém fallback para e-mail quando o nome não for encontrado.
    """

    @staticmethod
    def parse_recipients(value: Any) -> list[str]:
        if not value:
            return []

        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        text = str(value).strip()

        if not text:
            return []

        try:
            parsed = json.loads(text)

            if isinstance(parsed, list):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip()
                ]

            if isinstance(parsed, str):
                return [parsed.strip()] if parsed.strip() else []

        except Exception:
            pass

        normalized = (
            text
            .replace("[", "")
            .replace("]", "")
            .replace('"', "")
            .replace("'", "")
            .replace(";", ",")
            .replace("\n", ",")
        )

        return [
            item.strip()
            for item in normalized.split(",")
            if item.strip()
        ]

    @staticmethod
    def get_email_name_map(emails: list[str]) -> dict[str, str]:
        normalized_emails = [
            email.strip().lower()
            for email in emails
            if email.strip()
        ]

        if not normalized_emails:
            return {}

        email_name_map: dict[str, str] = {}

        system_users = (
            SystemUser.query
            .filter(func.lower(SystemUser.email).in_(normalized_emails))
            .all()
        )

        for user in system_users:
            if user.email and user.nome:
                email_name_map[user.email.lower()] = user.nome

        users = (
            User.query
            .filter(func.lower(User.email).in_(normalized_emails))
            .all()
        )

        for user in users:
            if user.email and user.nome and user.email.lower() not in email_name_map:
                email_name_map[user.email.lower()] = user.nome

        approvers = (
            Approver.query
            .filter(func.lower(Approver.email).in_(normalized_emails))
            .all()
        )

        for approver in approvers:
            if approver.email and approver.nome and approver.email.lower() not in email_name_map:
                email_name_map[approver.email.lower()] = approver.nome

        return email_name_map

    @staticmethod
    def display_recipient_names(value: Any) -> str:
        emails = RecipientDisplayService.parse_recipients(value)

        if not emails:
            return "-"

        email_name_map = RecipientDisplayService.get_email_name_map(emails)

        names = []

        for email in emails:
            normalized_email = email.strip().lower()
            name = email_name_map.get(normalized_email)

            if name:
                names.append(name)
            else:
                names.append(email)

        return ", ".join(names)
    
    @staticmethod
    def display_recipient_names_list(value: Any) -> list[str]:
        emails = RecipientDisplayService.parse_recipients(value)

        if not emails:
            return []

        email_name_map = RecipientDisplayService.get_email_name_map(emails)

        names = []

        for email in emails:
            normalized_email = email.strip().lower()
            name = email_name_map.get(normalized_email)

            if name:
                names.append(name)
            else:
                names.append(email)

        return names