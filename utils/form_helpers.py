from datetime import datetime
from typing import Optional


class FormValidationError(ValueError):
    """
    Erro específico para validação de formulário.

    Usamos essa classe para separar erro de preenchimento
    de erro interno do sistema.
    """
    pass


def get_required(form_data: dict, field_name: str, label: Optional[str] = None) -> str:
    """
    Busca um campo obrigatório no formulário.

    Se vier vazio, None ou só com espaços, gera erro claro.
    """

    label = label or field_name

    value = form_data.get(field_name, "")

    if value is None:
        value = ""

    value = str(value).strip()

    if not value:
        raise FormValidationError(f"O campo '{label}' é obrigatório.")

    return value


def get_optional(form_data: dict, field_name: str, default: str = "") -> str:
    """
    Busca campo opcional.

    Sempre retorna string, nunca None.
    """

    value = form_data.get(field_name, default)

    if value is None:
        return default

    return str(value).strip()


def get_int(
    form_data: dict,
    field_name: str,
    label: Optional[str] = None,
    default: int = 0,
    required: bool = False,
) -> int:
    """
    Busca e converte um campo inteiro.
    """

    label = label or field_name

    value = form_data.get(field_name, "")

    if value is None or str(value).strip() == "":
        if required:
            raise FormValidationError(f"O campo '{label}' é obrigatório.")
        return default

    try:
        return int(value)
    except ValueError:
        raise FormValidationError(f"O campo '{label}' deve ser um número inteiro.")


def get_date(
    form_data: dict,
    field_name: str,
    label: Optional[str] = None,
    required: bool = True,
) -> Optional[datetime]:
    """
    Busca e converte data enviada por input type=date.

    O HTML envia no formato:
    AAAA-MM-DD
    """

    label = label or field_name

    value = form_data.get(field_name, "")

    if value is None or str(value).strip() == "":
        if required:
            raise FormValidationError(f"O campo '{label}' é obrigatório.")
        return None

    value = str(value).strip()

    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise FormValidationError(
            f"O campo '{label}' deve estar no formato AAAA-MM-DD."
        )