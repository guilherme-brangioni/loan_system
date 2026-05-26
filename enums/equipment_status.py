from enum import Enum


class EquipmentStatus(Enum):
    """
    Status de equipamentos patrimoniais.

    RESERVADO é importante porque, após criar uma solicitação,
    o item não deve continuar disponível enquanto aguarda aprovação.
    """

    DISPONIVEL = "DISPONIVEL"
    RESERVADO = "RESERVADO"
    EMPRESTADO = "EMPRESTADO"
    MANUTENCAO = "MANUTENCAO"
    INATIVO = "INATIVO"