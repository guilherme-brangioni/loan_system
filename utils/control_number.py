from datetime import datetime


def generate_control_number(loan_id: int) -> str:
    """
    Gera número de controle no padrão:
    EMP-ATPM-AAAAMMDD-0001

    O ID do banco entra no final para evitar colisão.
    """

    today = datetime.now().strftime("%Y%m%d")
    return f"EMP-ATPM-{today}-{loan_id:04d}"