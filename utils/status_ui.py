def normalize_status(status: str) -> str:
    """
    Normaliza texto de status para comparação.
    """

    return str(status or "").strip().upper()


def format_status_label(status: str) -> str:
    """
    Formata status para exibição.

    Exemplo:
    PENDENTE_APROVACAO -> PENDENTE APROVAÇÃO
    """

    text = normalize_status(status)

    if not text:
        return "-"

    replacements = {
        "PENDENTE_APROVACAO": "PENDENTE APROVAÇÃO",
        "PARCIALMENTE_DEVOLVIDO": "PARCIALMENTE DEVOLVIDO",
        "DEVOLUCAO_ITEM": "DEVOLUÇÃO ITEM",
        "DEVOLUCAO_TOTAL": "DEVOLUÇÃO TOTAL",
        "REJEICAO": "REJEIÇÃO",
        "APROVACAO": "APROVAÇÃO",
        "VALIDACAO": "VALIDAÇÃO",
    }

    return replacements.get(text, text.replace("_", " "))


def status_badge_class(status: str) -> str:
    """
    Retorna classe CSS para status.

    Funciona para:
    - empréstimos;
    - itens;
    - equipamentos;
    - pendências externas;
    - sincronizações.
    """

    text = normalize_status(status)

    warning_statuses = {
        "PENDENTE",
        "PENDENTE_APROVACAO",
        "PENDENTE_VALIDACAO",
        "RESERVADO",
        "PROCESSANDO",
    }

    success_statuses = {
        "APROVADO",
        "DISPONIVEL",
        "VALIDADO",
        "RESOLVIDO",
        "FINALIZADO",
        "DEVOLVIDO",
    }

    info_statuses = {
        "RETIRADO",
        "EMPRESTADO",
        "PARCIALMENTE_DEVOLVIDO",
        "RENOVADO",
    }

    danger_statuses = {
        "ATRASADO",
        "ERRO",
        "REJEITADO",
        "CANCELADO",
        "INDISPONIVEL",
    }

    neutral_statuses = {
        "",
        None,
    }

    if text in warning_statuses:
        return "status-warning"

    if text in success_statuses:
        return "status-success"

    if text in info_statuses:
        return "status-info"

    if text in danger_statuses:
        return "status-danger"

    if text in neutral_statuses:
        return "status-neutral"

    return "status-neutral"