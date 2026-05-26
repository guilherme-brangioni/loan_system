from enum import Enum


class LoanItemStatus(Enum):
    """
    Status de cada item dentro do empréstimo.

    Isso permite devolução parcial.
    """

    EMPRESTADO = "EMPRESTADO"
    PARCIALMENTE_DEVOLVIDO = "PARCIALMENTE_DEVOLVIDO"
    DEVOLVIDO = "DEVOLVIDO"
    CANCELADO = "CANCELADO"