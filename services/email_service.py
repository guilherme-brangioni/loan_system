from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Optional
from flask import current_app


SMTP_CONFIG_FILE = "smtp_settings.json"
DEFAULT_PASSWORD_ENV_VAR = "OSCILO_SMTP_PASSWORD"


class EmailService:
    """
    Serviço de e-mail.

    Foi mantida a lógica parecida com o código que você já possui:
    - configuração por JSON
    - senha via variável de ambiente
    - STARTTLS
    - anexo opcional
    """

    @staticmethod
    def _load_json(file_path: str) -> dict:
        """
        Carrega o arquivo JSON de configuração SMTP.

        Primeiro tenta localizar o arquivo pelo caminho informado.
        Se não encontrar, tenta procurar na raiz do projeto Flask.
        """

        if not os.path.exists(file_path):
            project_root_path = os.path.join(
                current_app.root_path,
                file_path,
            )

            if os.path.exists(project_root_path):
                file_path = project_root_path
            else:
                raise FileNotFoundError(
                    f"Arquivo SMTP não encontrado: {file_path}"
                )

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_smtp_settings(file_path: str = SMTP_CONFIG_FILE) -> dict:
        data = EmailService._load_json(file_path)

        required = ["host", "port", "username", "from_email"]
        missing = [
            key for key in required
            if not str(data.get(key, "")).strip()
        ]

        if missing:
            raise ValueError(
                "Configuração SMTP incompleta. Campos ausentes: "
                + ", ".join(missing)
            )

        password = str(data.get("password", "")).strip()

        password_env_var = str(
            data.get("password_env_var", DEFAULT_PASSWORD_ENV_VAR)
        ).strip() or DEFAULT_PASSWORD_ENV_VAR

        if not password:
            password = os.getenv(password_env_var, "").strip()

        if not password:
            raise ValueError(
                "Senha SMTP não encontrada. Defina a variável de ambiente "
                f"'{password_env_var}' ou informe senha no JSON."
            )

        result = dict(data)
        result["password"] = password
        result["password_env_var"] = password_env_var

        return result

    @staticmethod
    def send_email(
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        smtp_settings_file: str = SMTP_CONFIG_FILE,
    ) -> dict:
        smtp_cfg = EmailService.load_smtp_settings(smtp_settings_file)

        host = str(smtp_cfg["host"]).strip()
        port = int(smtp_cfg["port"])
        username = str(smtp_cfg["username"]).strip()
        password = str(smtp_cfg["password"])
        from_email = str(smtp_cfg["from_email"]).strip()
        use_starttls = bool(smtp_cfg.get("use_starttls", True))
        timeout = int(smtp_cfg.get("timeout", 30))

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        if attachment_path:
            if not os.path.exists(attachment_path):
                raise FileNotFoundError(
                    f"Anexo não encontrado: {attachment_path}"
                )

            with open(attachment_path, "rb") as f:
                file_bytes = f.read()

            msg.add_attachment(
                file_bytes,
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(attachment_path),
            )

        context = ssl.create_default_context()

        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()

            if use_starttls:
                server.starttls(context=context)
                server.ehlo()

            server.login(username, password)
            server.send_message(msg)

        return {
            "success": True,
            "host": host,
            "port": port,
            "subject": subject,
            "recipients": recipients,
            "attachment": attachment_path,
        }

    @staticmethod
    def try_send_email(*args, **kwargs) -> dict:
        """
        Versão segura: não derruba o sistema se o SMTP falhar.
        """

        try:
            return EmailService.send_email(*args, **kwargs)
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def build_approval_body(loan, review_url: str) -> str:
        """
        Monta o corpo do e-mail de aprovação.

        Agora o aprovador não aprova diretamente pelo link.
        O link abre uma tela de revisão com botões de Aprovar/Rejeitar.
        """

        item_lines = []

        for item in loan.items:
            if item.equipment:
                equipment = item.equipment

                item_lines.append(
                    f"- {equipment.tipo_equipamento or 'EQUIPAMENTO'} | "
                    f"Fabricante: {equipment.fabricante or '-'} | "
                    f"Modelo: {equipment.modelo or '-'} | "
                    f"Patrimônio: {equipment.patrimonio or '-'} | "
                    f"Código equipamento: {equipment.codigo_equipamento or '-'} | "
                    f"Série: {equipment.serial or '-'} | "
                    f"Código interno: {equipment.codigo_interno}"
                )

        items_text = "\n".join(item_lines) or "- Nenhum item informado"

        return f"""Olá,

Existe uma solicitação de empréstimo pendente de aprovação.

Número de controle:
{loan.numero_controle}

Solicitante:
{loan.user.nome}

Matrícula:
{loan.user.matricula}

Gerência:
{loan.user.gerencia or "Não informado"}

Regional:
{loan.user.regional or "Não informado"}

Equipe:
{loan.user.equipe or "Não informado"}

Local de utilização:
{loan.local_utilizacao or "Não informado"}

Data prevista de devolução:
{loan.data_prevista_devolucao.strftime("%d/%m/%Y")}

Itens solicitados:
{items_text}

Para revisar, aprovar ou rejeitar a solicitação, acesse:
{review_url}

Atenciosamente,
AT/PM - Gestão de Empréstimos e Sobressalentes
"""

    @staticmethod
    def build_confirmation_body(loan) -> str:
        """
        Monta o e-mail de confirmação enviado ao solicitante
        após a retirada ser confirmada.
        """

        item_lines = []

        for item in loan.items:
            if item.equipment:
                equipment = item.equipment

                item_lines.append(
                    f"- {equipment.tipo_equipamento or 'EQUIPAMENTO'} | "
                    f"Fabricante: {equipment.fabricante or '-'} | "
                    f"Modelo: {equipment.modelo or '-'} | "
                    f"Patrimônio: {equipment.patrimonio or '-'} | "
                    f"Código equipamento: {equipment.codigo_equipamento or '-'} | "
                    f"Série: {equipment.serial or '-'} | "
                    f"Código interno: {equipment.codigo_interno}"
                )

        items_text = "\n".join(item_lines) or "- Nenhum item informado"

        return f"""Olá,

O empréstimo abaixo foi confirmado.

Número de controle:
{loan.numero_controle}

Solicitante:
{loan.user.nome}

Responsável pela coleta/entrega:
{loan.responsavel_entrega_nome}
{loan.responsavel_entrega_email or "E-mail não informado"}

Aprovador:
{loan.approver.nome}
{loan.approver.email}

Data do empréstimo:
{loan.data_emprestimo.strftime("%d/%m/%Y")}

Data prevista de devolução:
{loan.data_prevista_devolucao.strftime("%d/%m/%Y")}

Itens:
{items_text}

O comprovante em PDF está anexado.

Atenciosamente,
AT/PM - Gestão de Empréstimos e Sobressalentes
"""
    
    @staticmethod
    def build_loan_notification_body(loan) -> str:
        """
        Monta e-mail informativo para a lista de acompanhamento.

        Esse e-mail é enviado para os destinatários fixos e variáveis.
        """

        item_lines = []

        for item in loan.items:
            if item.equipment:
                equipment = item.equipment

                item_lines.append(
                    f"- {equipment.tipo_equipamento or 'EQUIPAMENTO'} | "
                    f"Fabricante: {equipment.fabricante or '-'} | "
                    f"Modelo: {equipment.modelo or '-'} | "
                    f"Patrimônio: {equipment.patrimonio or '-'} | "
                    f"Código equipamento: {equipment.codigo_equipamento or '-'} | "
                    f"Série: {equipment.serial or '-'} | "
                    f"Código interno: {equipment.codigo_interno}"
                )

        items_text = "\n".join(item_lines) or "- Nenhum item informado"

        return f"""Olá,

Uma solicitação de empréstimo foi registrada no sistema.

Número de controle:
{loan.numero_controle}

Status:
{loan.status}

Solicitante:
{loan.user.nome}

Matrícula:
{loan.user.matricula}

E-mail:
{loan.user.email}

Gerência:
{loan.user.gerencia or "Não informado"}

Regional:
{loan.user.regional or "Não informado"}

Equipe:
{loan.user.equipe or "Não informado"}

Responsável pela entrega:
{loan.responsavel_entrega_nome}

Local de utilização:
{loan.local_utilizacao or "Não informado"}

Data prevista de devolução:
{loan.data_prevista_devolucao.strftime("%d/%m/%Y")}

Equipamentos/materiais:
{items_text}

Atenciosamente,
AT/PM - Gestão de Empréstimos e Sobressalentes
"""
    
    @staticmethod
    def build_validation_reminder_body(loan) -> str:
        """
        E-mail enviado quando há equipamento pendente de validação
        após 24h do empréstimo.
        """

        item_lines = []

        for item in loan.items:
            equipment = getattr(item, "equipment", None)

            if equipment is None:
                continue

            if bool(getattr(equipment, "validado", False)):
                continue

            item_lines.append(
                f"- {equipment.tipo_equipamento or 'EQUIPAMENTO'} | "
                f"Fabricante: {equipment.fabricante or '-'} | "
                f"Modelo: {equipment.modelo or '-'} | "
                f"Patrimônio: {equipment.patrimonio or '-'} | "
                f"Código equipamento: {equipment.codigo_equipamento or '-'} | "
                f"Série: {equipment.serial or '-'} | "
                f"Código interno: {equipment.codigo_interno or '-'}"
            )

        items_text = "\n".join(item_lines) or "- Nenhum item pendente encontrado."

        return f"""Olá,

Existe equipamento pendente de validação no empréstimo abaixo.

Número de controle:
{loan.numero_controle}

Status do empréstimo:
{loan.status}

Solicitante:
{loan.user.nome}
{loan.user.email}

Aprovador:
{loan.approver.nome}
{loan.approver.email}

Responsável pela coleta/entrega:
{loan.responsavel_entrega_nome}
{loan.responsavel_entrega_email or "E-mail não informado"}

Data do empréstimo:
{loan.data_emprestimo.strftime("%d/%m/%Y") if loan.data_emprestimo else "Não informado"}

Data prevista de devolução:
{loan.data_prevista_devolucao.strftime("%d/%m/%Y") if loan.data_prevista_devolucao else "Não informado"}

Equipamentos pendentes de validação:
{items_text}

Favor acessar o sistema e validar os equipamentos vinculados a este empréstimo.

Atenciosamente,
AT/PM - Gestão de Empréstimos e Sobressalentes
"""
    
    @staticmethod
    def build_return_confirmation_body(
        loan,
        returned_by: str,
        return_type: str = "DEVOLUCAO",
    ) -> str:
        """
        Monta o e-mail de confirmação de devolução.

        return_type:
        - DEVOLUCAO_ITEM
        - DEVOLUCAO_TOTAL
        """

        item_lines = []

        for item in getattr(loan, "items", []) or []:
            equipment = getattr(item, "equipment", None)

            if equipment is None:
                continue

            item_lines.append(
                f"- {equipment.tipo_equipamento or 'EQUIPAMENTO'} | "
                f"Fabricante: {equipment.fabricante or '-'} | "
                f"Modelo: {equipment.modelo or '-'} | "
                f"Patrimônio: {equipment.patrimonio or '-'} | "
                f"Código equipamento: {equipment.codigo_equipamento or '-'} | "
                f"Série: {equipment.serial or '-'} | "
                f"Código interno: {equipment.codigo_interno or '-'} | "
                f"Status do item: {item.status}"
            )

        items_text = "\n".join(item_lines) or "- Nenhum item encontrado."

        if return_type == "DEVOLUCAO_TOTAL":
            title = "A devolução total do empréstimo foi registrada."
        else:
            title = "A devolução de item do empréstimo foi registrada."

        return f"""Olá,

{title}

Número de controle:
{loan.numero_controle}

Status atual do empréstimo:
{loan.status}

Solicitante:
{loan.user.nome}
{loan.user.email}

Aprovador:
{loan.approver.nome}
{loan.approver.email}

Responsável pela coleta/entrega:
{loan.responsavel_entrega_nome}
{loan.responsavel_entrega_email or "E-mail não informado"}

Devolução registrada por:
{returned_by or "Não informado"}

Data do empréstimo:
{loan.data_emprestimo.strftime("%d/%m/%Y") if loan.data_emprestimo else "Não informado"}

Data prevista de devolução:
{loan.data_prevista_devolucao.strftime("%d/%m/%Y") if loan.data_prevista_devolucao else "Não informado"}

Data real de devolução:
{loan.data_real_devolucao.strftime("%d/%m/%Y") if loan.data_real_devolucao else "Ainda não finalizado"}

Local de utilização:
{loan.local_utilizacao or "Não informado"}

Itens:
{items_text}

O comprovante atualizado está anexado.

Atenciosamente,
AT/PM - Gestão de Empréstimos e Sobressalentes
"""