from enum import Enum


class ItemType(Enum):
    """
    Define se o item emprestado é individual ou quantitativo.
    """

    PATRIMONIAL = "PATRIMONIAL"
    CONSUMIVEL = "CONSUMIVEL"