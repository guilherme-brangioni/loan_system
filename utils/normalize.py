import re


def normalize_name(name: str) -> str:
    """
    Normaliza texto para reduzir cadastros duplicados.

    Exemplo:
    ' notebook   dell ' vira 'NOTEBOOK DELL'
    """

    if not name:
        return ""

    name = name.upper().strip()

    # Remove espaços duplicados.
    name = re.sub(r"\s+", " ", name)

    return name